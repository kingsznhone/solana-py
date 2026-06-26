//! System program instruction builders.
//!
//! Mirrors the instructions exposed by ``solana-system-interface``:
//!   create_account, create_account_with_seed, create_account_allow_prefund,
//!   assign, assign_with_seed, transfer, transfer_with_seed, transfer_many,
//!   allocate, allocate_with_seed,
//!   advance_nonce_account, withdraw_nonce_account, authorize_nonce_account,
//!   upgrade_nonce_account, create_nonce_account, create_nonce_account_with_seed.

use pyo3::prelude::*;
use solana_sdk::pubkey::Pubkey as RustPubkey;
use solana_system_interface::instruction;

use crate::instruction::Instruction;
use crate::pubkey::Pubkey;

/// Convert a Python ``Pubkey`` to a Rust ``Pubkey``.
fn to_rust(pk: &Pubkey) -> RustPubkey {
    RustPubkey::from(pk.data)
}

/// System program instruction builders (namespace class).
///
/// All methods are static and return :class:`~solana_kit.Instruction`
/// (or a list thereof for the nonce-account creation helpers).
#[pyclass(name = "SystemInstruction")]
pub struct SystemInstruction;

#[pymethods]
impl SystemInstruction {
    // -----------------------------------------------------------------
    // Account creation / ownership
    // -----------------------------------------------------------------

    /// Create a new account.
    ///
    /// Accounts:
    ///   0. ``[writable, signer]`` from (payer)
    ///   1. ``[writable, signer]`` to (new account)
    #[staticmethod]
    fn create_account(
        from: &Pubkey,
        to: &Pubkey,
        lamports: u64,
        space: u64,
        owner: &Pubkey,
    ) -> Instruction {
        instruction::create_account(&to_rust(from), &to_rust(to), lamports, space, &to_rust(owner)).into()
    }

    /// Create a new account derived from a base pubkey + seed.
    ///
    /// Accounts:
    ///   0. ``[writable, signer]`` from (payer)
    ///   1. ``[writable]`` to (new account, must match create_with_seed(base, seed, owner))
    ///   2. ``[signer]`` base (only if base != from)
    #[staticmethod]
    fn create_account_with_seed(
        from: &Pubkey,
        to: &Pubkey,
        base: &Pubkey,
        seed: &str,
        lamports: u64,
        space: u64,
        owner: &Pubkey,
    ) -> Instruction {
        instruction::create_account_with_seed(
            &to_rust(from), &to_rust(to), &to_rust(base), seed, lamports, space, &to_rust(owner),
        )
        .into()
    }

    /// Create a new account without enforcing zero lamports on the destination.
    ///
    /// Accounts:
    ///   0. ``[writable, signer]`` new_account
    ///   1. ``[writable, signer]`` payer (only if ``payer_and_lamports`` is provided)
    #[staticmethod]
    fn create_account_allow_prefund(
        new_account: &Pubkey,
        payer_and_lamports: Option<(Pubkey, u64)>,
        space: u64,
        owner: &Pubkey,
    ) -> Instruction {
        let payer_rust = payer_and_lamports.map(|(pk, l)| (to_rust(&pk), l));
        instruction::create_account_allow_prefund(
            &to_rust(new_account),
            payer_rust.as_ref().map(|(pk, l)| (pk, *l)),
            space,
            &to_rust(owner),
        )
        .into()
    }

    /// Assign ownership of an account to a program.
    ///
    /// Accounts:
    ///   0. ``[writable, signer]`` account
    #[staticmethod]
    fn assign(account: &Pubkey, owner: &Pubkey) -> Instruction {
        instruction::assign(&to_rust(account), &to_rust(owner)).into()
    }

    /// Assign ownership of a derived account to a program.
    ///
    /// Accounts:
    ///   0. ``[writable]`` account (must match create_with_seed(base, seed, owner))
    ///   1. ``[signer]`` base
    #[staticmethod]
    fn assign_with_seed(account: &Pubkey, base: &Pubkey, seed: &str, owner: &Pubkey) -> Instruction {
        instruction::assign_with_seed(&to_rust(account), &to_rust(base), seed, &to_rust(owner)).into()
    }

    // -----------------------------------------------------------------
    // Transfers
    // -----------------------------------------------------------------

    /// Transfer SOL between two accounts.
    ///
    /// Accounts:
    ///   0. ``[writable, signer]`` from
    ///   1. ``[writable]`` to
    #[staticmethod]
    fn transfer(from: &Pubkey, to: &Pubkey, lamports: u64) -> Instruction {
        instruction::transfer(&to_rust(from), &to_rust(to), lamports).into()
    }

    /// Transfer SOL from a derived account.
    ///
    /// Accounts:
    ///   0. ``[writable]`` from (must match create_with_seed(base, seed, owner))
    ///   1. ``[signer]`` from_base
    ///   2. ``[writable]`` to
    #[staticmethod]
    fn transfer_with_seed(
        from: &Pubkey,
        from_base: &Pubkey,
        from_seed: &str,
        from_owner: &Pubkey,
        to: &Pubkey,
        lamports: u64,
    ) -> Instruction {
        instruction::transfer_with_seed(
            &to_rust(from),
            &to_rust(from_base),
            from_seed.to_string(),
            &to_rust(from_owner),
            &to_rust(to),
            lamports,
        )
        .into()
    }

    /// Build a batch of transfer instructions from one source to many destinations.
    #[staticmethod]
    fn transfer_many(from: &Pubkey, to_lamports: Vec<(Pubkey, u64)>) -> Vec<Instruction> {
        let from_rust = to_rust(from);
        let pairs: Vec<(RustPubkey, u64)> = to_lamports.into_iter().map(|(pk, l)| (to_rust(&pk), l)).collect();
        instruction::transfer_many(&from_rust, &pairs)
            .into_iter()
            .map(Instruction::from)
            .collect()
    }

    // -----------------------------------------------------------------
    // Allocation
    // -----------------------------------------------------------------

    /// Allocate space for an account.
    ///
    /// Accounts:
    ///   0. ``[writable, signer]`` new_account
    #[staticmethod]
    fn allocate(new_account: &Pubkey, space: u64) -> Instruction {
        instruction::allocate(&to_rust(new_account), space).into()
    }

    /// Allocate space for a derived account.
    ///
    /// Accounts:
    ///   0. ``[writable]`` new_account (must match create_with_seed(base, seed, owner))
    ///   1. ``[signer]`` base
    #[staticmethod]
    fn allocate_with_seed(
        new_account: &Pubkey,
        base: &Pubkey,
        seed: &str,
        space: u64,
        owner: &Pubkey,
    ) -> Instruction {
        instruction::allocate_with_seed(
            &to_rust(new_account),
            &to_rust(base),
            seed,
            space,
            &to_rust(owner),
        )
        .into()
    }

    // -----------------------------------------------------------------
    // Nonce account management
    // -----------------------------------------------------------------

    /// Advance a durable nonce account.
    ///
    /// Accounts:
    ///   0. ``[writable]`` nonce_account
    ///   1. ``[readonly]`` recent_blockhashes_sysvar
    ///   2. ``[readonly, signer]`` nonce_authority
    #[staticmethod]
    fn advance_nonce_account(nonce_account: &Pubkey, authorized: &Pubkey) -> Instruction {
        instruction::advance_nonce_account(&to_rust(nonce_account), &to_rust(authorized)).into()
    }

    /// Withdraw lamports from a durable nonce account.
    ///
    /// Accounts:
    ///   0. ``[writable]`` nonce_account
    ///   1. ``[writable]`` to
    ///   2. ``[readonly]`` recent_blockhashes_sysvar
    ///   3. ``[readonly]`` rent_sysvar
    ///   4. ``[readonly, signer]`` nonce_authority
    #[staticmethod]
    fn withdraw_nonce_account(
        nonce_account: &Pubkey,
        authorized: &Pubkey,
        to: &Pubkey,
        lamports: u64,
    ) -> Instruction {
        instruction::withdraw_nonce_account(
            &to_rust(nonce_account),
            &to_rust(authorized),
            &to_rust(to),
            lamports,
        )
        .into()
    }

    /// Change the authority of a durable nonce account.
    ///
    /// Accounts:
    ///   0. ``[writable]`` nonce_account
    ///   1. ``[readonly, signer]`` nonce_authority
    #[staticmethod]
    fn authorize_nonce_account(
        nonce_account: &Pubkey,
        authorized: &Pubkey,
        new_authority: &Pubkey,
    ) -> Instruction {
        instruction::authorize_nonce_account(
            &to_rust(nonce_account),
            &to_rust(authorized),
            &to_rust(new_authority),
        )
        .into()
    }

    /// Upgrade a legacy nonce account to the durable nonce format.
    ///
    /// Accounts:
    ///   0. ``[writable]`` nonce_account
    #[staticmethod]
    fn upgrade_nonce_account(nonce_account: &Pubkey) -> Instruction {
        instruction::upgrade_nonce_account(to_rust(nonce_account)).into()
    }

    // -----------------------------------------------------------------
    // Nonce account creation helpers (return multiple instructions)
    // -----------------------------------------------------------------

    /// Create and initialize a durable nonce account.
    ///
    /// Returns two instructions: ``create_account`` + ``initialize_nonce_account``.
    #[staticmethod]
    fn create_nonce_account(
        from: &Pubkey,
        nonce_account: &Pubkey,
        authority: &Pubkey,
        lamports: u64,
    ) -> Vec<Instruction> {
        instruction::create_nonce_account(&to_rust(from), &to_rust(nonce_account), &to_rust(authority), lamports)
            .into_iter()
            .map(Instruction::from)
            .collect()
    }

    /// Create and initialize a durable nonce account derived from a base + seed.
    ///
    /// Returns two instructions: ``create_account_with_seed`` + ``initialize_nonce_account``.
    #[staticmethod]
    fn create_nonce_account_with_seed(
        from: &Pubkey,
        nonce_account: &Pubkey,
        base: &Pubkey,
        seed: &str,
        authority: &Pubkey,
        lamports: u64,
    ) -> Vec<Instruction> {
        instruction::create_nonce_account_with_seed(
            &to_rust(from),
            &to_rust(nonce_account),
            &to_rust(base),
            seed,
            &to_rust(authority),
            lamports,
        )
        .into_iter()
        .map(Instruction::from)
        .collect()
    }
}