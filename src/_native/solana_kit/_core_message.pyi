"""Type stubs for message types exposed by ``solana_kit._core``.

Mirrors ``src/_native/src/message.rs``.
"""

from __future__ import annotations

from typing import Optional

from ._core_hash import Hash
from ._core_instruction import Instruction
from ._core_pubkey import Pubkey

class MessageHeader:
    """Message header: signer/readonly account counts."""

    num_required_signatures: int
    num_readonly_signed_accounts: int
    num_readonly_unsigned_accounts: int

    def __init__(
        self,
        num_required_signatures: int,
        num_readonly_signed_accounts: int,
        num_readonly_unsigned_accounts: int,
    ) -> None: ...
    def __repr__(self) -> str: ...

class CompiledInstruction:
    """A compiled instruction referencing accounts by index."""

    program_id_index: int
    accounts: list[int]
    data: bytes

    def __init__(
        self, program_id_index: int, accounts: list[int], data: bytes
    ) -> None: ...
    def __repr__(self) -> str: ...

class AddressLookupTableAccount:
    """An address lookup table account (used by V0 messages)."""

    key: Pubkey
    addresses: list[Pubkey]

    def __init__(self, key: Pubkey, addresses: list[Pubkey]) -> None: ...
    def __repr__(self) -> str: ...

class MessageAddressTableLookup:
    """A single address table lookup entry in a V0 message (read-only view)."""

    account_key: Pubkey
    writable_indexes: list[int]
    readonly_indexes: list[int]

    def __repr__(self) -> str: ...

class Message:
    """A legacy (V0-unversioned) transaction message.

    Use this for deserializing historical message data. For new
    transactions, prefer :class:`MessageV1`.
    """

    def __init__(
        self, instructions: list[Instruction], payer: Optional[Pubkey] = None
    ) -> None: ...
    @staticmethod
    def new_with_blockhash(
        instructions: list[Instruction], payer: Optional[Pubkey], blockhash: Hash
    ) -> Message: ...
    def serialize(self) -> bytes: ...
    @property
    def header(self) -> MessageHeader: ...
    @property
    def account_keys(self) -> list[Pubkey]: ...
    @property
    def recent_blockhash(self) -> Hash: ...
    @property
    def instructions(self) -> list[CompiledInstruction]: ...
    def __repr__(self) -> str: ...

class MessageV0:
    """A versioned V0 transaction message (with address lookup tables).

    Use this for deserializing historical V0 message data. For new
    transactions, prefer :class:`MessageV1`.
    """

    @staticmethod
    def try_compile(
        payer: Pubkey,
        instructions: list[Instruction],
        address_lookup_table_accounts: list[AddressLookupTableAccount],
        recent_blockhash: Hash,
    ) -> MessageV0: ...
    def serialize(self) -> bytes: ...
    @property
    def header(self) -> MessageHeader: ...
    @property
    def account_keys(self) -> list[Pubkey]: ...
    @property
    def recent_blockhash(self) -> Hash: ...
    @property
    def instructions(self) -> list[CompiledInstruction]: ...
    @property
    def address_table_lookups(self) -> list[MessageAddressTableLookup]: ...
    def __repr__(self) -> str: ...

class MessageV1:
    """A V1 transaction message (SIMD-0385).

    Supports 4KB transactions with inline compute budget configuration.
    This is the recommended message version for new transactions.
    """

    @staticmethod
    def try_compile(
        payer: Pubkey, instructions: list[Instruction], recent_blockhash: Hash
    ) -> MessageV1: ...
    def serialize(self) -> bytes: ...
    @property
    def header(self) -> MessageHeader: ...
    @property
    def account_keys(self) -> list[Pubkey]: ...
    @property
    def lifetime_specifier(self) -> Hash: ...
    @property
    def instructions(self) -> list[CompiledInstruction]: ...
    def size(self) -> int: ...
    def __repr__(self) -> str: ...
