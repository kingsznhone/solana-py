"""Typed helpers for custom RPC methods (Helius, Triton, etc.).

Design — two abstract base classes (living in ``solana.rpc.core``) eliminate
JSON-RPC 2.0 envelope boilerplate:

* ``solana.rpc.core.JsonRPCRequest`` (Protocol) — any object with ``to_json()``.
* ``solana.rpc.core.JsonRPCResponseParser`` (Protocol) — any class with ``from_json(raw)``.

Custom response parsers should follow the same shape as solders response
classes. Plain callable decoder functions are not supported.

From solana-py v0.x onwards these Protocols are the canonical interface.
The concrete ABCs ``RPCRequest`` / ``RPCResponse`` are defined in
``solana.rpc.core`` and can be imported from one place::

    from solana.rpc.core import RPCRequest, RPCResponse
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import ClassVar, Optional

from solana.rpc.core import (
    JsonRPCRequestSerializer,
    JsonRPCResponseParser,
    RPCException,
    JsonRPCRequest,
    JsonRPCResponse,
)

__all__ = [
    "JsonRPCRequest",
    "JsonRPCRequestSerializer",
    "JsonRPCResponse",
    "JsonRPCResponseParser",
    "PriorityFeeEstimateRequest",
    "PriorityFeeEstimateResponse",
    "PriorityFeeLevels",
    "RPCException",
]

# -------------------------------------------------------
# getPriorityFeeEstimate
# -------------------------------------------------------


@dataclass(frozen=True)
class PriorityFeeLevels:
    """Priority fee estimates at each level (micro-lamports)."""

    min: float
    low: float
    medium: float
    high: float
    very_high: float
    unsafe_max: float


@dataclass(frozen=True)
class PriorityFeeEstimateRequest(JsonRPCRequest):
    """Request for ``getPriorityFeeEstimate``."""

    _method: ClassVar[str] = "getPriorityFeeEstimate"
    account_keys: list[str]
    include_all_priority_fee_levels: bool = True
    recommended: Optional[bool] = None

    def _params(self) -> list[dict]:
        return [
            {
                "accountKeys": self.account_keys,
                "options": {
                    "includeAllPriorityFeeLevels": self.include_all_priority_fee_levels,
                    **({"recommended": self.recommended} if self.recommended is not None else {}),
                },
            }
        ]


@dataclass(frozen=True)
class PriorityFeeEstimateResponse(JsonRPCResponse):
    """Response for ``getPriorityFeeEstimate``."""

    priority_fee_levels: PriorityFeeLevels

    @classmethod
    def _from_result(cls, result: dict) -> PriorityFeeEstimateResponse:
        raw_levels = result.get("priorityFeeLevels", {})
        return cls(
            priority_fee_levels=PriorityFeeLevels(
                min=raw_levels.get("min", 0.0),
                low=raw_levels.get("low", 0.0),
                medium=raw_levels.get("medium", 0.0),
                high=raw_levels.get("high", 0.0),
                very_high=raw_levels.get("veryHigh", 0.0),
                unsafe_max=raw_levels.get("unsafeMax", 0.0),
            )
        )


# ---------------------------------------------------------------------------
# Example
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    from solana.rpc.async_api import AsyncClient

    async def demo() -> None:
        """Demonstrate custom request usage with priority fee estimation."""
        endpoint = "https://mainnet.helius-rpc.com/?api-key=f5a49fb3-c330-4255-baf5-a64c05b36e24"
        async with AsyncClient(endpoint) as client:
            resp = await client.send_custom_request(
                PriorityFeeEstimateRequest(
                    account_keys=["1ottnnBbTsWukU6ArQr8HdUL6Jwh6jP9bNM6dHaUZt1"],
                    include_all_priority_fee_levels=True,
                    # recommended=True,
                ),
                PriorityFeeEstimateResponse,
            )
            levels = resp.priority_fee_levels
            print(json.dumps(levels.__dict__, indent=4))

    asyncio.run(demo())
