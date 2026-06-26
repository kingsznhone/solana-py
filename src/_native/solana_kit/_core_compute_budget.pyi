"""Type stub for ComputeBudgetInstruction exposed by ``solana_kit._core``.

Mirrors ``src/_native/src/compute_budget.rs``.
"""

from __future__ import annotations

from ._core_instruction import Instruction

class ComputeBudgetInstruction:
    """Compute Budget program instruction builders.

    All methods are static and return :class:`Instruction`.
    These instructions are typically prepended to a transaction to control
    its compute budget and prioritization.
    """

    @staticmethod
    def request_heap_frame(bytes: int) -> Instruction: ...
    @staticmethod
    def set_compute_unit_limit(units: int) -> Instruction: ...
    @staticmethod
    def set_compute_unit_price(micro_lamports: int) -> Instruction: ...
    @staticmethod
    def set_loaded_accounts_data_size_limit(bytes: int) -> Instruction: ...
