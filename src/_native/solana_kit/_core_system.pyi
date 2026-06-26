"""Type stubs for SystemInstruction exposed by ``solana_kit._core``.

The class is defined in the native ``_core`` extension module (single
``.so``); this file exists only to keep the stub layer split by domain.
"""

from __future__ import annotations

from typing import Optional

from ._core_instruction import Instruction, Pubkey

class SystemInstruction:
    """System program instruction builders.

    All methods are static and return :class:`Instruction`
    (or a list thereof for the nonce-account creation helpers).
    """

    # --- Account creation / ownership ---

    @staticmethod
    def create_account(
        from_pubkey: Pubkey, to_pubkey: Pubkey, lamports: int, space: int, owner: Pubkey
    ) -> Instruction: ...
    @staticmethod
    def create_account_with_seed(
        from_pubkey: Pubkey,
        to_pubkey: Pubkey,
        base: Pubkey,
        seed: str,
        lamports: int,
        space: int,
        owner: Pubkey,
    ) -> Instruction: ...
    @staticmethod
    def create_account_allow_prefund(
        new_account: Pubkey,
        payer_and_lamports: Optional[tuple[Pubkey, int]],
        space: int,
        owner: Pubkey,
    ) -> Instruction: ...
    @staticmethod
    def assign(account: Pubkey, owner: Pubkey) -> Instruction: ...
    @staticmethod
    def assign_with_seed(
        account: Pubkey, base: Pubkey, seed: str, owner: Pubkey
    ) -> Instruction: ...

    # --- Transfers ---

    @staticmethod
    def transfer(
        from_pubkey: Pubkey, to_pubkey: Pubkey, lamports: int
    ) -> Instruction: ...
    @staticmethod
    def transfer_with_seed(
        from_pubkey: Pubkey,
        from_base: Pubkey,
        from_seed: str,
        from_owner: Pubkey,
        to_pubkey: Pubkey,
        lamports: int,
    ) -> Instruction: ...
    @staticmethod
    def transfer_many(
        from_pubkey: Pubkey, to_lamports: list[tuple[Pubkey, int]]
    ) -> list[Instruction]: ...

    # --- Allocation ---

    @staticmethod
    def allocate(new_account: Pubkey, space: int) -> Instruction: ...
    @staticmethod
    def allocate_with_seed(
        new_account: Pubkey, base: Pubkey, seed: str, space: int, owner: Pubkey
    ) -> Instruction: ...

    # --- Nonce account management ---

    @staticmethod
    def advance_nonce_account(
        nonce_account: Pubkey, authorized: Pubkey
    ) -> Instruction: ...
    @staticmethod
    def withdraw_nonce_account(
        nonce_account: Pubkey, authorized: Pubkey, to_pubkey: Pubkey, lamports: int
    ) -> Instruction: ...
    @staticmethod
    def authorize_nonce_account(
        nonce_account: Pubkey, authorized: Pubkey, new_authority: Pubkey
    ) -> Instruction: ...
    @staticmethod
    def upgrade_nonce_account(nonce_account: Pubkey) -> Instruction: ...

    # --- Nonce account creation helpers (return multiple instructions) ---

    @staticmethod
    def create_nonce_account(
        from_pubkey: Pubkey, nonce_account: Pubkey, authority: Pubkey, lamports: int
    ) -> list[Instruction]: ...
    @staticmethod
    def create_nonce_account_with_seed(
        from_pubkey: Pubkey,
        nonce_account: Pubkey,
        base: Pubkey,
        seed: str,
        authority: Pubkey,
        lamports: int,
    ) -> list[Instruction]: ...
