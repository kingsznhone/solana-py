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

## Explanation

1. **Create WebSocket connection**: Connect to the Solana WebSocket endpoint
2. **Subscribe to account changes**: Monitor changes to a specific account
3. **Subscribe to logs**: Listen to transaction logs
4. **Process messages**: Handle incoming event messages
5. **Unsubscribe**: Cancel each subscription with the handle returned by its subscribe call

## Subscription Types

- **account_subscribe**: Monitor account data changes
- **logs_subscribe**: Listen to transaction logs
- **program_subscribe**: Monitor program account changes
- **signature_subscribe**: Track transaction confirmations (one-shot; the client removes the
  handle automatically after the notification)
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