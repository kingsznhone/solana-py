"""Unit tests for the websocket client lifecycle and typed API."""

import itertools
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
from solders.signature import Signature
from websockets.exceptions import ProtocolError

from solana.rpc.websocket_api import (
    ConnectionState,
    SolanaWsClient,
    Subscription,
    SubscriptionKind,
)


def test_subscription_kinds_are_typed():
    assert SubscriptionKind.ACCOUNT.value == "account"
    assert SubscriptionKind.SLOTS_UPDATES.value == "slotsUpdates"


async def test_client_starts_closed():
    client = SolanaWsClient()
    assert client.connection_state is ConnectionState.CLOSED
    await client.close()


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
    await client.logs_subscribe(
        filter_=RpcTransactionLogsFilterMentions(Pubkey.default())
    )
    await client.signature_subscribe(signature=Signature.default())
    assert [kind for kind, _ in captured] == [
        SubscriptionKind.ACCOUNT,
        SubscriptionKind.LOGS,
        SubscriptionKind.SIGNATURE,
    ]
    assert [request.id for _, request in captured] == [1, 2, 3]


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
    client._state = ConnectionState.OPEN
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
    client._state = ConnectionState.OPEN
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
    client._state = ConnectionState.OPEN
    notification = _notification(
        '{"jsonrpc":"2.0","method":"slotNotification","params":'
        '{"result":{"parent":1,"root":1,"slot":2},"subscription":1}}'
    )
    client._dispatch_notification(notification)
    with pytest.raises(ProtocolError):
        client._dispatch_notification(notification)
    await client.close()
