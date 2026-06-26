"""Solana Kit — a native extension for core Solana types, keypairs, transactions, and system instructions.

This package wraps a single ``.so`` built from official solana-kit crates
(pubkey, signature, keypair, instruction, message, transaction, system-program).

Usage::

    from solana_kit import Keypair, Pubkey, SystemInstruction, VersionedTransaction
"""

from ._core import (
    AccountMeta,
    AddressLookupTableAccount,
    CompiledInstruction,
    ComputeBudgetInstruction,
    Hash,
    Instruction,
    Keypair,
    Message,
    MessageAddressTableLookup,
    MessageHeader,
    MessageV0,
    MessageV1,
    Pubkey,
    Signature,
    SystemInstruction,
    VersionedTransaction,
)

__all__ = [
    "AccountMeta",
    "AddressLookupTableAccount",
    "CompiledInstruction",
    "ComputeBudgetInstruction",
    "Hash",
    "Instruction",
    "Keypair",
    "Message",
    "MessageAddressTableLookup",
    "MessageHeader",
    "MessageV0",
    "MessageV1",
    "Pubkey",
    "Signature",
    "SystemInstruction",
    "VersionedTransaction",
]
