"""Type stub for Signature exposed by ``solana_kit._core``.

Mirrors ``src/_native/src/signature.rs``.
"""

from __future__ import annotations

class Signature:
    """64-byte Ed25519 signature."""

    data: bytes

    def __init__(self, data: bytes) -> None: ...
    def __bytes__(self) -> bytes: ...
    def __repr__(self) -> str: ...
