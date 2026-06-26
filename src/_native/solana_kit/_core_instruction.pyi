"""Type stubs for AccountMeta and Instruction exposed by ``solana_kit._core``.

Mirrors ``src/_native/src/instruction.rs``.
"""

from __future__ import annotations

from ._core_pubkey import Pubkey

class AccountMeta:
    """Account metadata for a Solana instruction."""

    pubkey: Pubkey
    is_signer: bool
    is_writable: bool

    def __init__(self, pubkey: Pubkey, is_signer: bool) -> None: ...
    @staticmethod
    def new_readonly(pubkey: Pubkey, is_signer: bool) -> AccountMeta: ...
    def __repr__(self) -> str: ...

class Instruction:
    """A single Solana instruction."""

    program_id: Pubkey
    accounts: list[AccountMeta]
    data: bytes

    def __init__(
        self, program_id: Pubkey, accounts: list[AccountMeta], data: bytes
    ) -> None: ...
    @staticmethod
    def new_with_bytes(
        program_id: Pubkey, data: bytes, accounts: list[AccountMeta]
    ) -> Instruction: ...
    def __repr__(self) -> str: ...
