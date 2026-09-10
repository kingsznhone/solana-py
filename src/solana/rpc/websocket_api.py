"""Confirmed Solana WebSocket subscriptions and JSON-RPC request dispatch."""

from __future__ import annotations

import asyncio
import itertools
import json
import math
from collections import deque
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum, StrEnum
from types import TracebackType
from typing import Any, Generic, TypeVar, cast

from solders.rpc.config import (
    RpcAccountInfoConfig,
    RpcBlockSubscribeFilter,
    RpcBlockSubscribeConfig,
    RpcProgramAccountsConfig,
    RpcSignatureSubscribeConfig,
    RpcTransactionLogsConfig,
    RpcTransactionLogsFilter,
    RpcTransactionLogsFilterMentions,
)
from solders.account_decoder import UiDataSliceConfig
from solders.rpc.filter import Memcmp
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction_status import TransactionDetails
from solders.rpc.requests import (
    AccountSubscribe,
    AccountUnsubscribe,
    BlockSubscribe,
    BlockUnsubscribe,
    LogsSubscribe,
    LogsUnsubscribe,
    ProgramSubscribe,
    ProgramUnsubscribe,
    RootSubscribe,
    RootUnsubscribe,
    SignatureSubscribe,
    SignatureUnsubscribe,
    SlotSubscribe,
    SlotsUpdatesSubscribe,
    SlotsUpdatesUnsubscribe,
    SlotUnsubscribe,
    VoteSubscribe,
    VoteUnsubscribe,
)
from solders.rpc.responses import (
    Notification,
    SignatureNotification,
    SubscriptionError,
    SubscriptionResult,
    UnsubscribeResult,
    parse_websocket_message,
)
from websockets.asyncio.client import ClientConnection
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import (
    ConcurrencyError,
    ConnectionClosedOK,
    ProtocolError,
)
from websockets.frames import Close, CloseCode

from solana.rpc.jsonrpc import JsonRpcRequestSerializer, SolanaJsonRpcError
from solana.rpc.core import (
    _ACCOUNT_ENCODING_TO_SOLDERS,
    _COMMITMENT_TO_SOLDERS,
    _TX_ENCODING_TO_SOLDERS,
)
from solana.rpc.models import DataSliceOpts, MemcmpOpts
from solana.rpc.commitment import Commitment

T = TypeVar("T")


class SubscriptionKind(StrEnum):
    """Solana subscription methods supported by the typed helpers."""

    ACCOUNT = "account"
    BLOCK = "block"
    LOGS = "logs"
    PROGRAM = "program"
    SIGNATURE = "signature"
    SLOT = "slot"
    SLOTS_UPDATES = "slotsUpdates"
    ROOT = "root"
    VOTE = "vote"


_UNSUBSCRIBE_REQUESTS: dict[SubscriptionKind, Callable[[int, int], JsonRpcRequestSerializer]] = {
    SubscriptionKind.ACCOUNT: AccountUnsubscribe,
    SubscriptionKind.BLOCK: BlockUnsubscribe,
    SubscriptionKind.LOGS: LogsUnsubscribe,
    SubscriptionKind.PROGRAM: ProgramUnsubscribe,
    SubscriptionKind.SIGNATURE: SignatureUnsubscribe,
    SubscriptionKind.SLOT: SlotUnsubscribe,
    SubscriptionKind.SLOTS_UPDATES: SlotsUpdatesUnsubscribe,
    SubscriptionKind.ROOT: RootUnsubscribe,
    SubscriptionKind.VOTE: VoteUnsubscribe,
}


@dataclass(frozen=True, slots=True)
class Subscription:
    """A server-confirmed subscription owned by one physical connection.

    Handles are created by subscribe helpers. Copying or reconstructing a handle
    doesn't grant ownership; unsubscribe checks its object identity.
    """

    subscription_id: int
    kind: SubscriptionKind


class ConnectionState(Enum):
    """Lifecycle of the RPC dispatcher, independent of the wire protocol state."""

    OPEN = "open"
    CLOSED = "closed"


class UnsubscribeError(Exception):
    """The server explicitly refused to cancel a subscription."""

    def __init__(self, subscription: Subscription) -> None:
        """Retain the handle whose unsubscribe request returned false."""
        self.subscription = subscription
        super().__init__(f"Unsubscribe returned false for {subscription.kind.value} {subscription.subscription_id}")


@dataclass(slots=True)
class _PendingRequest(Generic[T]):
    request_id: int
    future: asyncio.Future[T]
    method: str
    send_started: bool = False


def _positive_timeout(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return float(value)


def _consume_future_exception(future: asyncio.Future[Any]) -> None:
    # A cancelled caller may never await the exception set during shutdown.
    if not future.cancelled():
        future.exception()


class SolanaWsClient:
    """One reader dispatches RPC responses and delivers typed notifications.

    Use :func:`connect` to open and manage the connection. Subscribe helpers
    await confirmation and return :class:`Subscription`; :meth:`recv` returns
    notifications only. Fatal errors abort every subscription on this connection.
    """

    def __init__(
        self,
        uri: str = "ws://localhost:8900",
        *,
        request_timeout: float = 10.0,
        notification_queue_size: int = 1024,
        **kwargs: Any,
    ) -> None:
        """Create a client; the WebSocket is opened by :meth:`connect`."""
        self._uri = uri
        self._connect_kwargs = dict(kwargs)
        self._connect_kwargs["close_timeout"] = _positive_timeout(kwargs.get("close_timeout", 10.0), "close_timeout")
        self._ws: ClientConnection | None = None
        self._loop = asyncio.get_running_loop()
        self.request_timeout = _positive_timeout(request_timeout, "request_timeout")
        if type(notification_queue_size) is not int or notification_queue_size <= 0:
            raise ValueError("notification_queue_size must be a positive integer")
        self._notification_queue_size = notification_queue_size
        self._notifications: deque[Notification] = deque()
        self._notification_ready = asyncio.Event()
        self._receiving = False
        self._connect_lock = asyncio.Lock()
        self._started = False
        self._pending_requests: dict[int, _PendingRequest[Any]] = {}
        self._request_counter = itertools.count(1)
        self._subscriptions: dict[int, Subscription] = {}
        self._unsubscribing: set[int] = set()
        self._send_lock = asyncio.Lock()
        self._state = ConnectionState.CLOSED
        self._terminal_error: BaseException | None = None
        self._aborting = False
        self._reader_task: asyncio.Task[None] | None = None
        self._shutdown_task: asyncio.Task[None] | None = None
        self._close_frame = Close(CloseCode.NORMAL_CLOSURE, "")

    async def connect(self) -> SolanaWsClient:
        """Open and own the native WebSocket, then start its sole reader."""
        async with self._connect_lock:
            if self._started:
                if self._state is ConnectionState.OPEN:
                    return self
                raise RuntimeError("SolanaWsClient instances cannot be reused")
            self._started = True
            self._ws = await ws_connect(self._uri, **self._connect_kwargs)
            self._state = ConnectionState.OPEN
            self._reader_task = self._loop.create_task(self._read_loop(), name="solana-ws-reader")
            self._reader_task.add_done_callback(self._reader_finished)
            return self

    async def __aenter__(self) -> SolanaWsClient:
        """Connect this client for use as an async context manager."""
        return await self.connect()

    @property
    def connection_state(self) -> ConnectionState:
        """Return the RPC dispatcher's lifecycle state."""
        return self._state

    def _reader_finished(self, task: asyncio.Task[None]) -> None:
        # Also covers cancellation before the reader coroutine first executes.
        if self._state is not ConnectionState.OPEN:
            return
        if task.cancelled():
            self._begin_shutdown(asyncio.CancelledError("WebSocket reader cancelled"), abort=True)
            return
        cause = task.exception()
        if isinstance(cause, ConnectionClosedOK):
            self._begin_shutdown(abort=False)
        else:
            self._begin_shutdown(
                cause or RuntimeError("WebSocket reader stopped unexpectedly"),
                abort=True,
            )

    def _begin_shutdown(self, cause: BaseException | None = None, *, abort: bool) -> None:
        if self._state is ConnectionState.CLOSED:
            return
        if cause is not None and self._terminal_error is None:
            self._terminal_error = cause
        self._aborting |= abort
        self._state = ConnectionState.CLOSED
        self._notifications.clear()
        self._notification_ready.set()
        self._fail_pending_requests()
        self._subscriptions.clear()
        self._unsubscribing.clear()
        if self._aborting:
            self._abort_transport()
        if self._shutdown_task is None:
            self._shutdown_task = self._loop.create_task(self._shutdown(), name="solana-ws-shutdown")
            self._shutdown_task.add_done_callback(_consume_future_exception)

    def _fail_pending_requests(self) -> None:
        if not self._pending_requests:
            return
        error = self._terminal_error
        if error is None and self._ws is not None and self._ws.protocol.state.name == "CLOSED":
            error = self._ws.protocol.close_exc
        if error is None:
            error = RuntimeError("WebSocket connection closed")
        for pending in self._pending_requests.values():
            if not pending.future.done():
                pending.future.set_exception(error)
        self._pending_requests.clear()

    def _abort_transport(self) -> None:
        ws = self._ws
        if ws is not None:
            ws.transport.abort()

    async def _shutdown(self) -> None:
        try:
            ws = self._ws
            if ws is not None:
                if self._aborting:
                    self._abort_transport()
                else:
                    await ws.close(self._close_frame.code, self._close_frame.reason)
                await ws.wait_closed()
        except Exception as exc:  # noqa: BLE001 - shutdown must never propagate
            if self._terminal_error is None:
                self._terminal_error = exc
            self._aborting = True
            self._abort_transport()
            ws = self._ws
            if ws is not None:
                with suppress(Exception):
                    await ws.wait_closed()
        finally:
            if self._reader_task is not None:
                if not self._reader_task.done():
                    self._reader_task.cancel()
                await asyncio.gather(self._reader_task, return_exceptions=True)
            self._state = ConnectionState.CLOSED

    async def close(self, code: int = CloseCode.NORMAL_CLOSURE, reason: str = "") -> None:
        """Run the standard close workflow, forcing transport cleanup on timeout."""
        frame = Close(code, reason)
        frame.check()
        if self._state is not ConnectionState.CLOSED:
            self._close_frame = frame
        cause = None if code in (CloseCode.NORMAL_CLOSURE, CloseCode.GOING_AWAY) else ProtocolError(reason)
        self._begin_shutdown(cause, abort=False)
        task = self._shutdown_task
        if task is None:
            return
        try:
            await asyncio.wait_for(asyncio.shield(task), self._connect_kwargs["close_timeout"])
        except TimeoutError:
            self._aborting = True
            self._abort_transport()
            await asyncio.shield(task)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Abort on exceptional context exit and always await cleanup."""
        if exc_value is not None:
            self._begin_shutdown(exc_value, abort=True)
        await self.close()

    async def recv(self) -> Notification:
        """Receive one notification; cancellation leaves queued notifications intact.

        Only one caller may receive at a time. Connection lifecycle exceptions
        are propagated from the underlying ``websockets`` connection.
        Raw text/bytes decoding isn't supported.
        """
        if self._receiving:
            raise ConcurrencyError("Only one notification receiver may run at a time")
        self._receiving = True
        try:
            while True:
                if self._state is not ConnectionState.OPEN:
                    if self._ws is None:
                        raise RuntimeError("WebSocket is not connected")
                    error = self._terminal_error or (self._ws.protocol.close_exc if self._ws is not None else None)
                    if error is not None:
                        raise error
                if self._notifications:
                    return self._notifications.popleft()
                self._notification_ready.clear()
                await self._notification_ready.wait()
        finally:
            self._receiving = False

    async def __aiter__(self) -> AsyncIterator[Notification]:
        """Iterate over notifications until a normal connection closure."""
        try:
            while True:
                yield await self.recv()
        except ConnectionClosedOK:
            return

    async def _read_loop(self) -> None:
        while self._state is ConnectionState.OPEN:
            ws = self._ws
            if ws is None:
                return
            raw = await ws.recv()
            for envelope in parse_websocket_message(raw.decode() if isinstance(raw, bytes) else raw):
                if self._state is not ConnectionState.OPEN:
                    return
                if isinstance(envelope, (SubscriptionResult, SubscriptionError, UnsubscribeResult)):
                    self._dispatch_response(envelope)
                else:
                    self._dispatch_notification(cast(Notification, envelope))

    def _dispatch_response(self, envelope: SubscriptionResult | SubscriptionError | UnsubscribeResult) -> None:
        request_id = envelope.id
        pending = self._pending_requests[request_id]
        if isinstance(envelope, SubscriptionError):
            error = SolanaJsonRpcError(
                int(getattr(cast(Any, envelope.error), "code", -32603)),
                str(getattr(cast(Any, envelope.error), "message", envelope.error)),
                request_id=request_id,
                method=pending.method,
            )
            pending.future.set_exception(error)
        else:
            # Commit response-derived state before waking the caller.  This
            # keeps subscription registration atomic with confirmation and
            # prevents an immediately-following notification from racing the
            # subscribe() coroutine.
            pending.future.set_result(envelope.result)
        self._pending_requests.pop(request_id, None)

    def _dispatch_notification(self, notification: Notification) -> None:
        subscription_id = notification.subscription
        if isinstance(notification, SignatureNotification):
            self._subscriptions.pop(subscription_id, None)
        if len(self._notifications) >= self._notification_queue_size:
            raise ProtocolError("WebSocket notification queue overflow")
        self._notifications.append(notification)
        self._notification_ready.set()

    async def _request(
        self,
        request: JsonRpcRequestSerializer,
    ) -> _PendingRequest[T]:
        ws = self._ws
        if self._state is not ConnectionState.OPEN or ws is None:
            raise RuntimeError("WebSocket is not connected")
        serialized = request.to_json()
        body = json.loads(serialized)
        # solders request serializers produce valid JSON-RPC envelopes.
        # The protocol serializer exposes ``id`` at runtime; the shared
        # serializer type omits that concrete request attribute.
        request_id = cast(Any, request).id
        future: asyncio.Future[T] = cast(asyncio.Future[T], self._loop.create_future())
        future.add_done_callback(_consume_future_exception)
        pending = _PendingRequest(request_id, future, body["method"])
        self._pending_requests[request_id] = pending
        try:
            async with self._send_lock:
                if self._state is not ConnectionState.OPEN:
                    raise ws.protocol.close_exc
                pending.send_started = True
                try:
                    await ws.send(serialized)
                except Exception as exc:
                    self._begin_shutdown(exc, abort=True)
                    raise
        except BaseException:
            self._pending_requests.pop(request_id, None)
            if not future.done():
                future.cancel()
            raise
        return pending

    async def _wait_pending(self, pending: _PendingRequest[T], timeout: float | None = None) -> T:
        """Await a registered request and remove it on caller cancellation/timeout."""
        duration = self.request_timeout if timeout is None else _positive_timeout(timeout, "timeout")
        timer = asyncio.timeout(duration)
        try:
            async with timer:
                return await asyncio.shield(pending.future)
        except asyncio.CancelledError as exc:
            if pending.send_started:
                self._begin_shutdown(exc, abort=True)
            raise
        except TimeoutError as exc:
            if pending.send_started and timer.expired():
                self._begin_shutdown(exc, abort=True)
            raise
        finally:
            self._pending_requests.pop(pending.request_id, None)
            if not pending.future.done():
                pending.future.cancel()

    async def _subscribe(
        self,
        kind: SubscriptionKind,
        request: JsonRpcRequestSerializer,
    ) -> Subscription:
        pending: _PendingRequest[int] = await self._request(request)
        subscription_id = await self._wait_pending(pending)
        return self._register_subscription(kind, subscription_id)

    def _register_subscription(self, kind: SubscriptionKind, subscription_id: int) -> Subscription:
        subscription = Subscription(subscription_id, kind)
        self._subscriptions[subscription_id] = subscription
        return subscription

    def _remove_subscription(self, subscription_id: int) -> None:
        self._subscriptions.pop(subscription_id, None)

    def _unsubscribe_request(self, subscription: Subscription) -> JsonRpcRequestSerializer:
        """Build the JSON-RPC request that cancels a subscription."""
        request_type = _UNSUBSCRIBE_REQUESTS[subscription.kind]
        return request_type(subscription.subscription_id, next(self._request_counter))

    async def unsubscribe(self, subscription: Subscription) -> None:
        """Cancel a live subscription after receiving server confirmation."""
        subscription_id = subscription.subscription_id
        if self._subscriptions.get(subscription_id) is not subscription:
            raise ValueError("Subscription handle is no longer active")
        if subscription_id in self._unsubscribing:
            raise ValueError("Unsubscribe is already pending for this handle")
        request = self._unsubscribe_request(subscription)
        self._unsubscribing.add(subscription_id)
        try:
            pending: _PendingRequest[bool] = await self._request(request)
            result = await self._wait_pending(pending)
            if not result:
                raise UnsubscribeError(subscription)
            self._remove_subscription(subscription_id)
        finally:
            self._unsubscribing.discard(subscription_id)

    async def account_subscribe(
        self,
        *,
        pubkey: Pubkey,
        commitment: Commitment | None = None,
        encoding: str | None = None,
        data_slice: DataSliceOpts | None = None,
        min_context_slot: int | None = None,
    ) -> Subscription:
        """Subscribe to account notifications for a public key."""
        config = None
        if any(value is not None for value in (commitment, encoding, data_slice, min_context_slot)):
            account_encoding = _ACCOUNT_ENCODING_TO_SOLDERS[encoding] if encoding is not None else None
            account_commitment = _COMMITMENT_TO_SOLDERS[commitment] if commitment is not None else None
            account_data_slice = (
                UiDataSliceConfig(offset=data_slice.offset, length=data_slice.length) if data_slice else None
            )
            config = RpcAccountInfoConfig(
                account_encoding,
                account_data_slice,
                account_commitment,
                min_context_slot,
            )
        return await self._subscribe(
            SubscriptionKind.ACCOUNT,
            AccountSubscribe(pubkey, config, next(self._request_counter)),
        )

    async def program_subscribe(
        self,
        *,
        program_id: Pubkey,
        commitment: Commitment | None = None,
        encoding: str | None = None,
        data_slice: DataSliceOpts | None = None,
        min_context_slot: int | None = None,
        filters: Sequence[int | MemcmpOpts] | None = None,
        with_context: bool | None = None,
        sort_results: bool | None = None,
    ) -> Subscription:
        """Subscribe to program account notifications."""
        config = None
        if any(
            value is not None
            for value in (
                commitment,
                encoding,
                data_slice,
                min_context_slot,
                filters,
                with_context,
                sort_results,
            )
        ):
            account = RpcAccountInfoConfig(
                encoding=(None if encoding is None else _ACCOUNT_ENCODING_TO_SOLDERS[encoding]),
                commitment=(None if commitment is None else _COMMITMENT_TO_SOLDERS[commitment]),
                min_context_slot=min_context_slot,
                data_slice=(
                    None
                    if data_slice is None
                    else UiDataSliceConfig(offset=data_slice.offset, length=data_slice.length)
                ),
            )
            parsed_filters = (
                None
                if filters is None
                else [x if isinstance(x, int) else Memcmp(offset=x.offset, bytes_=x.bytes) for x in filters]
            )
            config = cast(Any, RpcProgramAccountsConfig)(account, parsed_filters, with_context, sort_results)
        return await self._subscribe(
            SubscriptionKind.PROGRAM,
            ProgramSubscribe(program_id, config, next(self._request_counter)),
        )

    async def logs_subscribe(
        self,
        *,
        filter_: (RpcTransactionLogsFilter | RpcTransactionLogsFilterMentions) = RpcTransactionLogsFilter.All,
        commitment: Commitment | None = None,
    ) -> Subscription:
        """Subscribe to transaction log notifications."""
        logs_commitment = _COMMITMENT_TO_SOLDERS[commitment] if commitment is not None else None
        config = RpcTransactionLogsConfig(logs_commitment)
        return await self._subscribe(
            SubscriptionKind.LOGS,
            LogsSubscribe(filter_, config, next(self._request_counter)),
        )

    async def block_subscribe(
        self,
        *,
        filter_: RpcBlockSubscribeFilter = RpcBlockSubscribeFilter.All,
        commitment: Commitment | None = None,
        encoding: str | None = None,
        transaction_details: TransactionDetails | None = None,
        show_rewards: bool | None = None,
        max_supported_transaction_version: int | None = None,
    ) -> Subscription:
        """Subscribe to block notifications."""
        block_commitment = _COMMITMENT_TO_SOLDERS[commitment] if commitment is not None else None
        block_encoding = _TX_ENCODING_TO_SOLDERS[encoding] if encoding is not None else None
        config = RpcBlockSubscribeConfig(
            block_commitment,
            block_encoding,
            transaction_details,
            show_rewards,
            max_supported_transaction_version,
        )
        return await self._subscribe(
            SubscriptionKind.BLOCK,
            BlockSubscribe(filter_, config, next(self._request_counter)),
        )

    async def signature_subscribe(
        self,
        *,
        signature: Signature,
        commitment: Commitment | None = None,
        enable_received_notification: bool | None = None,
    ) -> Subscription:
        """Subscribe to signature status notifications."""
        config = None
        if commitment is not None or enable_received_notification is not None:
            signature_commitment = _COMMITMENT_TO_SOLDERS[commitment] if commitment is not None else None
            config = RpcSignatureSubscribeConfig(signature_commitment, enable_received_notification)
        return await self._subscribe(
            SubscriptionKind.SIGNATURE,
            SignatureSubscribe(signature, config, next(self._request_counter)),
        )

    async def slot_subscribe(self) -> Subscription:
        """Subscribe to slot notifications."""
        return await self._subscribe(SubscriptionKind.SLOT, SlotSubscribe(next(self._request_counter)))

    async def slots_updates_subscribe(self) -> Subscription:
        """Subscribe to slot update notifications."""
        return await self._subscribe(
            SubscriptionKind.SLOTS_UPDATES,
            SlotsUpdatesSubscribe(next(self._request_counter)),
        )

    async def root_subscribe(self) -> Subscription:
        """Subscribe to root notifications."""
        return await self._subscribe(SubscriptionKind.ROOT, RootSubscribe(next(self._request_counter)))

    async def vote_subscribe(self) -> Subscription:
        """Subscribe to vote notifications."""
        return await self._subscribe(SubscriptionKind.VOTE, VoteSubscribe(next(self._request_counter)))
