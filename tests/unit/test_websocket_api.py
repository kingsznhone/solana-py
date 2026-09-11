"""Unit tests for the websocket client lifecycle and typed API."""

import asyncio
import itertools
import json
from typing import cast

import pytest
from solders.pubkey import Pubkey
from solders.rpc.config import RpcTransactionLogsFilterMentions
from solders.rpc.requests import LogsUnsubscribe
from solders.rpc.responses import (
    Notification,
    SlotNotification,
    SignatureNotification,
    parse_websocket_message,
)
from solders.errors import SerdeJSONError
from solders.signature import Signature
from websockets.exceptions import ConnectionClosedOK, ProtocolError
from websockets.frames import Close, CloseCode

from solana.rpc.jsonrpc import SolanaJsonRpcError
from solana.rpc.websocket_api import (
    ConnectionState,
    SolanaWsClient,
    Subscription,
    SubscriptionKind,
)


class _FakeWebSocket:
    def __init__(self, response: str | None = None) -> None:
        self._response = response
        self._messages: asyncio.Queue[str] = asyncio.Queue()
        self.closed = False

    async def send(self, request: str) -> None:
        if self._response is not None:
            response = self._response.replace("{request_id}", str(json.loads(request)["id"]))
            await self._messages.put(response)

    async def recv(self) -> str:
        return await self._messages.get()

    async def close(self, *_args) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


class _SlowClosing(_FakeWebSocket):
    """The closing handshake suspends, so a cancellation can land in the middle of it."""

    async def close(self, *args) -> None:
        await asyncio.sleep(0.01)
        await super().close(*args)


def test_subscription_kinds_are_typed():
    assert SubscriptionKind.ACCOUNT.value == "account"
    assert SubscriptionKind.SLOTS_UPDATES.value == "slotsUpdates"


async def test_client_starts_closed():
    client = SolanaWsClient()
    assert client.connection_state is ConnectionState.CLOSED
    await client.close()


async def test_close_without_connect_is_safe():
    client = SolanaWsClient()
    await client.close()
    assert client.connection_state is ConnectionState.CLOSED


async def test_recv_without_connect_raises():
    client = SolanaWsClient()
    with pytest.raises(RuntimeError, match="not connected"):
        await client.recv()


async def test_connect_then_close(monkeypatch):
    fake_ws = _FakeWebSocket()
    client = await _connected(monkeypatch, fake_ws)
    assert client.connection_state is ConnectionState.OPEN
    await client.close()
    assert client.connection_state is ConnectionState.CLOSED
    assert fake_ws.closed


async def test_subscribe_propagates_server_request_error(monkeypatch):
    fake_ws = _FakeWebSocket('{"jsonrpc":"2.0","error":{"code":-32602,"message":"invalid params"},"id":{request_id}}')

    async def fake_connect(uri, **kwargs):
        return fake_ws

    monkeypatch.setattr("solana.rpc.websocket_api.ws_connect", fake_connect)
    client = SolanaWsClient()
    await client.connect()

    with pytest.raises(SolanaJsonRpcError) as exc_info:
        await client.account_subscribe(pubkey=Pubkey.default())

    # solders' typed subscription error exposes the message but not its code;
    # the client uses the documented internal-error fallback in that case.
    assert exc_info.value.code == -32603
    assert str(exc_info.value) == "invalid params"
    assert exc_info.value.request_id == 1
    assert exc_info.value.method == "accountSubscribe"
    await client.close()


async def test_subscribe_times_out_when_server_does_not_respond(monkeypatch):
    fake_ws = _FakeWebSocket()

    async def fake_connect(uri, **kwargs):
        return fake_ws

    monkeypatch.setattr("solana.rpc.websocket_api.ws_connect", fake_connect)
    client = SolanaWsClient(request_timeout=0.01)
    await client.connect()

    with pytest.raises(TimeoutError):
        await client.account_subscribe(pubkey=Pubkey.default())

    await client.close()
    assert client.connection_state is ConnectionState.CLOSED
    assert fake_ws.closed


async def test_subscribe_propagates_unparseable_server_response(monkeypatch):
    fake_ws = _FakeWebSocket("not json")

    async def fake_connect(uri, **kwargs):
        return fake_ws

    monkeypatch.setattr("solana.rpc.websocket_api.ws_connect", fake_connect)
    client = SolanaWsClient()
    await client.connect()

    with pytest.raises(SerdeJSONError):
        await client.account_subscribe(pubkey=Pubkey.default())

    await client.close()
    assert client.connection_state is ConnectionState.CLOSED


@pytest.mark.parametrize(
    "kwargs",
    [{"request_timeout": 0}, {"close_timeout": 0}, {"notification_queue_size": 0}],
)
async def test_client_rejects_invalid_options(kwargs):
    with pytest.raises(ValueError):
        SolanaWsClient(**kwargs)


async def test_subscribe_helpers_build_typed_requests(monkeypatch):
    client = SolanaWsClient.__new__(SolanaWsClient)
    client._request_counter = itertools.count(1)
    captured = []

    async def fake_subscribe(kind, request):
        captured.append((kind, request))
        return Subscription(42, kind)

    monkeypatch.setattr(client, "_subscribe", fake_subscribe)
    await client.account_subscribe(pubkey=Pubkey.default())
    await client.logs_subscribe(filter_=RpcTransactionLogsFilterMentions(Pubkey.default()))
    await client.signature_subscribe(signature=Signature.default())
    assert [kind for kind, _ in captured] == [
        SubscriptionKind.ACCOUNT,
        SubscriptionKind.LOGS,
        SubscriptionKind.SIGNATURE,
    ]
    assert [request.id for _, request in captured] == [1, 2, 3]


async def test_program_subscribe_builds_configured_request(monkeypatch):
    client = SolanaWsClient.__new__(SolanaWsClient)
    client._request_counter = itertools.count(1)
    captured = []

    async def fake_subscribe(kind, request):
        captured.append((kind, request))
        return Subscription(42, kind)

    monkeypatch.setattr(client, "_subscribe", fake_subscribe)
    await client.program_subscribe(program_id=Pubkey.default(), with_context=True)

    assert captured[0][0] is SubscriptionKind.PROGRAM
    assert captured[0][1].id == 1
    assert '"params"' in captured[0][1].to_json()


def test_unsubscribe_request_uses_subscription_kind():
    client = SolanaWsClient.__new__(SolanaWsClient)
    client._request_counter = itertools.count(9)
    request = cast(
        LogsUnsubscribe,
        client._unsubscribe_request(Subscription(77, SubscriptionKind.LOGS)),
    )
    assert request.id == 9
    assert '"params":[77]' in request.to_json()


def _notification(raw: str) -> Notification:
    return cast(Notification, next(iter(parse_websocket_message(raw))))


async def test_recv_preserves_notification_order():
    client = SolanaWsClient(notification_queue_size=2)
    first = _notification(
        '{"jsonrpc":"2.0","method":"slotNotification","params":'
        '{"result":{"parent":1,"root":1,"slot":2},"subscription":1}}'
    )
    second = _notification(
        '{"jsonrpc":"2.0","method":"slotNotification","params":'
        '{"result":{"parent":2,"root":2,"slot":3},"subscription":1}}'
    )
    client._dispatch_notification(first)
    client._dispatch_notification(second)
    assert isinstance(await client.recv(), SlotNotification)
    assert cast(SlotNotification, await client.recv()).result.slot == 3
    await client.close()


async def test_signature_notification_removes_subscription():
    client = SolanaWsClient()
    client._subscriptions[42] = Subscription(42, SubscriptionKind.SIGNATURE)
    notification = _notification(
        '{"jsonrpc":"2.0","method":"signatureNotification","params":'
        '{"result":{"context":{"slot":1},"value":{"err":null}},"subscription":42}}'
    )
    assert isinstance(notification, SignatureNotification)
    client._dispatch_notification(notification)
    assert 42 not in client._subscriptions
    await client.close()


async def test_unsubscribe_rejects_inactive_handle():
    client = SolanaWsClient()
    with pytest.raises(ValueError):
        await client.unsubscribe(Subscription(1, SubscriptionKind.SLOT))
    await client.close()


async def test_notification_queue_overflow():
    client = SolanaWsClient(notification_queue_size=1)
    notification = _notification(
        '{"jsonrpc":"2.0","method":"slotNotification","params":'
        '{"result":{"parent":1,"root":1,"slot":2},"subscription":1}}'
    )
    client._dispatch_notification(notification)
    with pytest.raises(ProtocolError):
        client._dispatch_notification(notification)
    await client.close()


async def _connected(monkeypatch, fake_ws):
    async def fake_connect(uri, **kwargs):
        return fake_ws

    monkeypatch.setattr("solana.rpc.websocket_api.ws_connect", fake_connect)
    return await SolanaWsClient().connect()


async def test_recv_blocked_during_local_close_reports_clean_closure(monkeypatch):
    client = await _connected(monkeypatch, _FakeWebSocket())
    receiver = asyncio.create_task(client.recv())
    await asyncio.sleep(0)
    assert client._receiving

    await client.close()

    with pytest.raises(ConnectionClosedOK) as exc_info:
        await receiver
    assert exc_info.value.rcvd.code == CloseCode.NORMAL_CLOSURE


async def test_async_for_exits_cleanly_on_local_close(monkeypatch):
    client = await _connected(monkeypatch, _FakeWebSocket())

    async def consume():
        async for _ in client:
            pass

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)
    await client.close()
    await task


def test_client_can_be_constructed_outside_a_running_loop():
    """The loop is pinned by connect(), so construction needs no loop at all."""
    client = SolanaWsClient()
    assert client.connection_state is ConnectionState.CLOSED


async def test_close_before_connect_refuses_to_open_a_socket(monkeypatch):
    opened = []

    async def fake_connect(uri, **kwargs):
        opened.append(uri)
        return _FakeWebSocket()

    monkeypatch.setattr("solana.rpc.websocket_api.ws_connect", fake_connect)
    client = SolanaWsClient()
    await client.close()

    with pytest.raises(RuntimeError, match="cannot be reused"):
        await client.connect()
    assert opened == []


async def test_close_drains_queued_notifications(monkeypatch):
    client = await _connected(monkeypatch, _FakeWebSocket())
    client._dispatch_notification(
        _notification(
            '{"jsonrpc":"2.0","method":"slotNotification","params":'
            '{"result":{"parent":1,"root":1,"slot":2},"subscription":1}}'
        )
    )

    await client.close()

    assert cast(SlotNotification, await client.recv()).result.slot == 2
    with pytest.raises(ConnectionClosedOK):
        await client.recv()


async def test_close_releases_socket_when_caller_is_cancelled(monkeypatch):
    fake_ws = _SlowClosing()
    client = await _connected(monkeypatch, fake_ws)

    closing = asyncio.create_task(client.close())
    await asyncio.sleep(0)
    closing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await closing

    assert fake_ws.closed
    assert client.connection_state is ConnectionState.CLOSED


async def test_close_releases_socket_when_caller_is_cancelled_twice(monkeypatch):
    fake_ws = _SlowClosing()
    client = await _connected(monkeypatch, fake_ws)

    closing = asyncio.create_task(client.close())
    await asyncio.sleep(0)
    closing.cancel()
    await asyncio.sleep(0)
    closing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await closing

    # The caller gave up, but the shielded handshake still runs to completion.
    await asyncio.sleep(0.05)
    assert fake_ws.closed


async def test_close_releases_socket_after_fatal_reader_error(monkeypatch):
    class _Broken(_FakeWebSocket):
        async def recv(self) -> str:
            raise RuntimeError("stream is corrupt")

    fake_ws = _Broken()
    client = await _connected(monkeypatch, fake_ws)

    with pytest.raises(RuntimeError, match="stream is corrupt"):
        await client.recv()

    await client.close()
    assert fake_ws.closed
    assert client.connection_state is ConnectionState.CLOSED


async def test_async_with_reports_its_own_failure_and_releases_socket(monkeypatch):
    fake_ws = _FakeWebSocket()

    async def fake_connect(uri, **kwargs):
        return fake_ws

    monkeypatch.setattr("solana.rpc.websocket_api.ws_connect", fake_connect)
    boom = ValueError("boom")
    receiver: asyncio.Task[Notification] | None = None

    with pytest.raises(ValueError) as exit_info:
        async with SolanaWsClient() as client:
            receiver = asyncio.create_task(client.recv())
            await asyncio.sleep(0)
            raise boom

    assert exit_info.value is boom
    assert receiver is not None
    with pytest.raises(ValueError) as recv_info:
        await receiver
    assert recv_info.value is boom
    assert fake_ws.closed


async def test_remote_closure_exception_is_propagated_verbatim(monkeypatch):
    frame = Close(CloseCode.GOING_AWAY, "server restarting")
    remote = ConnectionClosedOK(frame, frame, True)

    class _RemoteClosing(_FakeWebSocket):
        async def recv(self) -> str:
            raise remote

    client = await _connected(monkeypatch, _RemoteClosing())
    with pytest.raises(ConnectionClosedOK) as exc_info:
        await client.recv()
    assert exc_info.value is remote
    await client.close()


async def test_many_tasks_share_one_client(monkeypatch):
    """The pinned loop constrains loops, not tasks: concurrent callers each await their own id."""
    fake_ws = _FakeWebSocket('{"jsonrpc":"2.0","result":{request_id},"id":{request_id}}')
    client = await _connected(monkeypatch, fake_ws)

    subscriptions = await asyncio.gather(*(client.slot_subscribe() for _ in range(10)))

    assert sorted(sub.subscription_id for sub in subscriptions) == list(range(1, 11))
    assert len(client._subscriptions) == 10
    await client.close()


async def test_close_is_idempotent_and_concurrent_safe(monkeypatch):
    fake_ws = _FakeWebSocket()
    client = await _connected(monkeypatch, fake_ws)

    await asyncio.gather(client.close(), client.close())
    await client.close()

    assert fake_ws.closed
    assert client.connection_state is ConnectionState.CLOSED
