"""Type stub for the native ``_core`` extension module.

The runtime is a single ``_core.so`` that registers all classes under
``solana_kit._core``. This file aggregates the per-domain stub files so
type checkers see the full surface, while keeping each domain's
definitions in its own ``.pyi`` for maintainability.
"""

from ._core_pubkey import Pubkey
from ._core_signature import Signature
from ._core_instruction import AccountMeta, Instruction
from ._core_keypair import Keypair
from ._core_system import SystemInstruction
from ._core_compute_budget import ComputeBudgetInstruction
from ._core_hash import Hash
from ._core_message import (
    AddressLookupTableAccount,
    CompiledInstruction,
    Message,
    MessageAddressTableLookup,
    MessageHeader,
    MessageV0,
    MessageV1,
)
from ._core_transaction import VersionedTransaction

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
