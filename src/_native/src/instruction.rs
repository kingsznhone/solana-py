//! AccountMeta and Instruction — instruction-related types.

use pyo3::prelude::*;
use solana_sdk::instruction::{AccountMeta as RustAccountMeta, Instruction as RustInstruction};
use solana_sdk::pubkey::Pubkey as RustPubkey;

use crate::pubkey::Pubkey;

// ---------------------------------------------------------------------------
// AccountMeta
// ---------------------------------------------------------------------------
#[pyclass(get_all, name = "AccountMeta")]
#[derive(Clone)]
pub struct AccountMeta {
    pub pubkey: Pubkey,
    pub is_signer: bool,
    pub is_writable: bool,
}

#[pymethods]
impl AccountMeta {
    /// Construct metadata for a writable account.
    ///
    /// Mirrors Rust's ``AccountMeta::new``.
    #[new]
    fn new(pubkey: Pubkey, is_signer: bool) -> Self {
        Self { pubkey, is_signer, is_writable: true }
    }

    /// Construct metadata for a read-only account.
    ///
    /// Mirrors Rust's ``AccountMeta::new_readonly``.
    #[staticmethod]
    fn new_readonly(pubkey: Pubkey, is_signer: bool) -> Self {
        Self { pubkey, is_signer, is_writable: false }
    }

    fn __repr__(&self) -> String {
        format!(
            "AccountMeta(pubkey={}, is_signer={}, is_writable={})",
            RustPubkey::from(self.pubkey.data).to_string(), self.is_signer, self.is_writable
        )
    }
}

impl From<&RustAccountMeta> for AccountMeta {
    fn from(a: &RustAccountMeta) -> Self {
        Self {
            pubkey: Pubkey { data: a.pubkey.to_bytes() },
            is_signer: a.is_signer,
            is_writable: a.is_writable,
        }
    }
}

// ---------------------------------------------------------------------------
// Instruction
// ---------------------------------------------------------------------------
#[pyclass(get_all, name = "Instruction")]
#[derive(Clone)]
pub struct Instruction {
    pub program_id: Pubkey,
    pub accounts: Vec<AccountMeta>,
    pub data: Vec<u8>,
}

#[pymethods]
impl Instruction {
    /// Construct an Instruction from its three fields.
    ///
    /// ``program_id`` — the program that will execute this instruction.
    /// ``accounts``   — list of AccountMeta describing accounts the program may access.
    /// ``data``       — opaque bytes passed to the program for its own interpretation.
    ///
    /// The caller is responsible for ensuring the correct encoding of ``data``
    /// as expected by the callee program.  This mirrors Rust's
    /// ``Instruction::new_with_bytes``.
    #[new]
    fn new(program_id: Pubkey, accounts: Vec<AccountMeta>, data: Vec<u8>) -> Self {
        Self { program_id, accounts, data }
    }

    /// Alias for :meth:`new`, matching Rust's ``Instruction::new_with_bytes``.
    #[staticmethod]
    fn new_with_bytes(program_id: Pubkey, data: Vec<u8>, accounts: Vec<AccountMeta>) -> Self {
        Self { program_id, accounts, data }
    }

    fn __repr__(&self) -> String {
        format!(
            "Instruction(program_id={}, accounts_len={}, data_len={})",
            RustPubkey::from(self.program_id.data).to_string(),
            self.accounts.len(),
            self.data.len()
        )
    }
}

impl From<RustInstruction> for Instruction {
    fn from(ix: RustInstruction) -> Self {
        Self {
            program_id: Pubkey { data: ix.program_id.to_bytes() },
            accounts: ix.accounts.iter().map(AccountMeta::from).collect(),
            data: ix.data,
        }
    }
}

/// Convert our Python Instruction back to a Rust Instruction.
pub(crate) fn to_rust_instruction(ix: &Instruction) -> RustInstruction {
    RustInstruction {
        program_id: RustPubkey::from(ix.program_id.data),
        accounts: ix
            .accounts
            .iter()
            .map(|a| RustAccountMeta {
                pubkey: RustPubkey::from(a.pubkey.data),
                is_signer: a.is_signer,
                is_writable: a.is_writable,
            })
            .collect(),
        data: ix.data.clone(),
    }
}
