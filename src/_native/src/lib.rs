pub mod compute_budget;
pub mod hash;
pub mod instruction;
pub mod keypair;
pub mod message;
pub mod pubkey;
pub mod signature;
pub mod system;
pub mod transaction;

use pyo3::prelude::*;

/// Native core of ``solana_kit`` — provides fundamental Solana types, keypairs,
/// transactions, and system program instruction builders.
///
/// Imported automatically by ``solana_kit/__init__.py``.
#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<pubkey::Pubkey>()?;
    m.add_class::<signature::Signature>()?;
    m.add_class::<instruction::AccountMeta>()?;
    m.add_class::<instruction::Instruction>()?;

    m.add_class::<keypair::Keypair>()?;

    m.add_class::<system::SystemInstruction>()?;
    m.add_class::<compute_budget::ComputeBudgetInstructionNS>()?;

    m.add_class::<hash::Hash>()?;
    m.add_class::<message::MessageHeader>()?;
    m.add_class::<message::CompiledInstruction>()?;
    m.add_class::<message::AddressLookupTableAccount>()?;
    m.add_class::<message::Message>()?;
    m.add_class::<message::MessageV0>()?;
    m.add_class::<message::MessageV1>()?;
    m.add_class::<message::AddressTableLookup>()?;

    m.add_class::<transaction::VersionedTransaction>()?;

    Ok(())
}