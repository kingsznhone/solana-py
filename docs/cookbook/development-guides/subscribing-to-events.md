# Subscribing to Events

This example demonstrates how to subscribe to Solana blockchain events using WebSocket connections.

## Code

```python
#!/usr/bin/env python3
"""
Solana Cookbook - Subscribing to Events
"""

import asyncio
from solana.rpc.websocket_api import SolanaWsClient
from solders.keypair import Keypair


async def main():
    keypair = Keypair()

    async with SolanaWsClient("wss://api.devnet.solana.com") as websocket:
        # Each subscribe call returns a confirmed Subscription handle
        account_sub = await websocket.account_subscribe(pubkey=keypair.pubkey())
        logs_sub = await websocket.logs_subscribe()

        try:
            # Listen for notifications
            async for message in websocket:
                print(f"Received: {message}")
        finally:
            await websocket.unsubscribe(logs_sub)
            await websocket.unsubscribe(account_sub)


if __name__ == "__main__":
    asyncio.run(main())
```

Iteration only ends when the connection closes, and closing already cancels
every subscription it owned, so the `unsubscribe()` calls above are no-ops on
that path. They matter when you stop early while the connection stays open:

```python
async with SolanaWsClient("wss://api.devnet.solana.com") as websocket:
    logs_sub = await websocket.logs_subscribe()
    try:
        async for message in websocket:
            print(f"Received: {message}")
            break
    finally:
        # Frees the server-side subscription; the connection stays usable.
        await websocket.unsubscribe(logs_sub)

    slot_sub = await websocket.slot_subscribe()
```

## Managing the connection lifecycle

The asynchronous context manager is the recommended form. It connects on entry
and closes the WebSocket when the block exits, including after an exception:

```python
async with SolanaWsClient("wss://api.devnet.solana.com") as websocket:
    subscription = await websocket.logs_subscribe()
    notification = await websocket.recv()
```

If you call `connect()` manually, the caller owns final cleanup. Always wrap
the client in `try/finally` and await `close()`:

```python
websocket = await SolanaWsClient("wss://api.devnet.solana.com").connect()
try:
    subscription = await websocket.logs_subscribe()
    notification = await websocket.recv()
finally:
    await websocket.close()
```

This covers cancellation, `KeyboardInterrupt`, and application errors while
the process is running. Forced termination such as `SIGKILL` or `os._exit`
cannot execute Python cleanup code.

## Explanation

1. **Create WebSocket connection**: Connect to the Solana WebSocket endpoint
2. **Subscribe to account changes**: Monitor changes to a specific account
3. **Subscribe to logs**: Listen to transaction logs
4. **Process messages**: Handle incoming event messages
5. **Unsubscribe**: Cancel each subscription with the handle returned by its subscribe call,
   which is a no-op once the connection is closed

## Subscription Types

- **account_subscribe**: Monitor account data changes
- **logs_subscribe**: Listen to transaction logs
- **program_subscribe**: Monitor program account changes
- **signature_subscribe**: Track transaction confirmations (one-shot; the server cancels it
  after the notification and the client drops its local handle)
- **slot_subscribe**: Monitor slot changes

## Key Concepts

- **Real-time updates**: WebSocket provides real-time blockchain data
- **Event-driven**: React to blockchain events as they happen
- **Asynchronous**: Use async/await for non-blocking operations
- **Typed handles**: `Subscription` objects identify a subscription instead of a bare integer ID
- **Notifications only**: `recv()` and iteration never yield subscription confirmations

## Usage

```bash
python subscribing_to_events.py
```

The script will run continuously, printing events as they occur.

## Network Endpoints

- **Devnet**: wss://api.devnet.solana.com
- **Testnet**: wss://api.testnet.solana.com  
- **Mainnet**: wss://api.mainnet.solana.com
