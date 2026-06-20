# PR: Remove HTTP Batch Requests and Improve Custom RPC Extensibility

## Summary

Removes the deprecated HTTP batch request API and tightens the JSON-RPC request/response extension points.

Main changes:

- Removed deprecated `(Async)HTTPProvider.make_batch_request(_unparsed)` support.
- Removed the provider-side batch parsing/type overload machinery that existed only to support HTTP batch requests.
- Kept websocket request batching intact; websocket subscription batching uses a separate `batch_to_json` path and is not part of this removal.
- Added/clarified typed custom JSON-RPC request and response protocols.
- Added response decoding that supports solders-style response parser classes and preserves structured solders RPC errors.

## Motivation

The HTTP batch request code carried a large amount of historical type machinery for a deprecated API:

- batch request body tuple aliases,
- response tuple aliases,
- six overload variants,
- batch-specific provider helpers,
- solders batch encode/decode imports.

The API was already deprecated and scheduled for removal, and the implementation had no internal callers. Removing it simplifies the provider layer and avoids maintaining a public surface that users should no longer build against.

This removal is intentionally happening now because batch support would seriously interfere with the new 🦆duck-typed parser model. The new parser path is intentionally simple: one request body, one raw JSON-RPC response envelope, one parser class with `from_json(raw)`. Keeping HTTP batch support would require a second parsing model built around tuples of request bodies, tuples of parser classes, positional result matching, and solders batch decoding. That would either force the new custom parser system to grow batch-specific overloads immediately, or leave two incompatible parser paths in the provider layer. Removing batch first keeps the extension system coherent and prevents new custom-parser APIs from being shaped around deprecated behavior.

At the same time, there is demand for calling RPC-node-platform extension methods that are not part of the standard solders RPC API, such as `getPriorityFeeEstimate`. Those methods need a supported escape hatch without requiring every extension method to be added to solana-py first.

## Design

### Request extensibility

Custom request bodies use the `JsonRPCRequest` protocol:

- any object with `to_json() -> str` can be sent,
- solders request objects already satisfy this shape,
- custom request classes can subclass `RPCRequest` to get JSON-RPC envelope construction for free.

This means users can either:

- implement a full custom request constructor for a platform-specific method, or
- reuse a solders request object and only customize response parsing.

### Response extensibility

Custom response parsers use the `JsonRPCResponseParser` protocol and a solders-compatible shape:

- parser must be a class with `from_json(raw: str) -> T`,
- plain callable decoder functions are intentionally not supported,
- parser receives the full JSON-RPC response envelope, not just the `result` field.

This keeps custom parsers aligned with solders response classes and avoids adding another decoder style to the core path.

HTTP batch requests do not fit this model. A batch request is not one body and one parser; it is a collection of bodies and a collection of parsers whose responses must be matched by position. Supporting that alongside the 🦆duck-typed parser API would make every parser improvement pay a batch-specific complexity cost. Since batch was already deprecated, removing it is the cleaner migration path.

### Response decoding

The shared `_decode_rpc_response` helper is used by provider parsing and custom request APIs.

The decoder is parser-first:

1. Call `parser.from_json(raw)`.
2. If solders returns a structured `RPCError` variant, raise `RPCException(parsed)` so typed errors such as `SendTransactionPreflightFailureMessage` are preserved.
3. Otherwise validate the JSON-RPC envelope and map generic error/no-result envelopes to solana-py exceptions.

This ordering is important. Pre-validating the envelope would turn typed solders errors into generic dictionaries and break callers that rely on precise error classes.

## Usage

### Platform extension RPC method

For RPC Node platform specific methods such as `getPriorityFeeEstimate`, users can define both request and response classes:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from solana.rpc.core import RPCRequest, RPCResponse


@dataclass(frozen=True)
class PriorityFeeLevels:
    min: float
    low: float
    medium: float
    high: float
    very_high: float
    unsafe_max: float


@dataclass(frozen=True)
class PriorityFeeEstimateRequest(RPCRequest):
    _method: ClassVar[str] = "getPriorityFeeEstimate"
    account_keys: list[str]
    include_all_priority_fee_levels: bool = True
    recommended: bool | None = None

    def _params(self) -> list[dict]:
        return [
            {
                "accountKeys": self.account_keys,
                "options": {
                    "includeAllPriorityFeeLevels": self.include_all_priority_fee_levels,
                    **(
                        {"recommended": self.recommended}
                        if self.recommended is not None
                        else {}
                    ),
                },
            }
        ]


@dataclass(frozen=True)
class PriorityFeeEstimateResponse(RPCResponse):
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
```

Then send it through the public custom request entry point:

```python
resp = await client.send_custom_request(
    PriorityFeeEstimateRequest(account_keys=[str(pubkey)]),
    PriorityFeeEstimateResponse,
)
```

### Standard solders request with custom parser

For standard RPC methods, users can also reuse solders request constructors and provide their own parser:

```python
body = solders.rpc.requests.GetBalance(pubkey, config)
resp = client.send_custom_request(body, MyBalanceResponse)
```

This is useful when a user wants a different response model while still relying on solders to construct the standard request body.

## Breaking Change

The following APIs are removed:

- `HTTPProvider.make_batch_request`
- `HTTPProvider.make_batch_request_unparsed`
- `AsyncHTTPProvider.make_batch_request`
- `AsyncHTTPProvider.make_batch_request_unparsed`

Users should use individual requests instead. Async callers can use `asyncio.gather` for concurrency.

## Tests

Validation performed:

- `uv run ruff check --fix`
- `uv run mypy src/solana/rpc/core.py src/solana/rpc/providers/core.py src/solana/rpc/providers/http.py src/solana/rpc/providers/async_http.py src/solana/rpc/api.py src/solana/rpc/async_api.py custom_request.py`
- `uv run pytest tests/unit/test_rpc_response_decode.py tests/unit/test_provider_parse_raw.py`
- `uv run pytest tests/integration/test_async_http_client.py::test_send_bad_transaction`

The focused tests cover:

- solders response parser support,
- rejection of plain callable parsers,
- generic JSON-RPC error envelope mapping,
- missing-result mapping,
- preservation of typed solders RPC errors,
- removal of HTTP batch request methods.