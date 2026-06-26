//! Compute Budget program instruction builders.
//!
//! Mirrors ``solana-compute-budget-interface``: request heap frame, set
//! compute unit limit/price, set loaded accounts data size limit.

use pyo3::prelude::*;
use solana_compute_budget_interface::ComputeBudgetInstruction;

use crate::instruction::Instruction;

/// Compute Budget program instruction builders (namespace class).
///
/// All methods are static and return :class:`~solana_kit.Instruction`.
/// These instructions are typically prepended to a transaction to control
/// its compute budget and prioritization.
#[pyclass(name = "ComputeBudgetInstruction")]
pub struct ComputeBudgetInstructionNS;

#[pymethods]
impl ComputeBudgetInstructionNS {
    /// Request a specific transaction-wide program heap region size in bytes.
    ///
    /// The value must be a multiple of 1024. This applies to each program
    /// executed in the transaction, including CPIs.
    #[staticmethod]
    fn request_heap_frame(bytes: u32) -> Instruction {
        ComputeBudgetInstruction::request_heap_frame(bytes).into()
    }

    /// Set a specific compute unit limit that the transaction is allowed to consume.
    #[staticmethod]
    fn set_compute_unit_limit(units: u32) -> Instruction {
        ComputeBudgetInstruction::set_compute_unit_limit(units).into()
    }

    /// Set a compute unit price in "micro-lamports" to pay a higher transaction
    /// fee for higher transaction prioritization.
    #[staticmethod]
    fn set_compute_unit_price(micro_lamports: u64) -> Instruction {
        ComputeBudgetInstruction::set_compute_unit_price(micro_lamports).into()
    }

    /// Set a specific transaction-wide account data size limit, in bytes,
    /// that is allowed to load.
    #[staticmethod]
    fn set_loaded_accounts_data_size_limit(bytes: u32) -> Instruction {
        ComputeBudgetInstruction::set_loaded_accounts_data_size_limit(bytes).into()
    }
}
