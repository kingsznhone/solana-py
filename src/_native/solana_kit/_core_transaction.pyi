"""Type stub for VersionedTransaction exposed by ``solana_kit._core``.

Mirrors ``src/_native/src/transaction.rs``.
"""

from __future__ import annotations

from typing import Union

from ._core_keypair import Keypair
from ._core_message import MessageV0, MessageV1
from ._core_signature import Signature

class VersionedTransaction:
    """A signed, versioned transaction ready for RPC submission."""

    def __init__(
        self, message: Union[MessageV0, MessageV1], keypairs: list[Keypair]
    ) -> None: ...
    def serialize(self) -> bytes: ...
    @staticmethod
    def deserialize(data: bytes) -> VersionedTransaction: ...
    @property
    def signatures(self) -> list[Signature]: ...
    @property
    def num_signatures(self) -> int: ...
    def __repr__(self) -> str: ...
