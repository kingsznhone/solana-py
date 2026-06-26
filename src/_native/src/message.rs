//! Message types: MessageHeader, CompiledInstruction,
//! AddressLookupTableAccount, and the three message versions
//! (Legacy, V0, V1).

use pyo3::prelude::*;
use solana_sdk::hash::Hash as RustHash;
use solana_sdk::message::{
    compiled_instruction::CompiledInstruction as RustCompiledInstruction,
    legacy::Message as RustLegacyMessage,
    v0, v1,
    AddressLookupTableAccount as RustAddressLookupTableAccount,
    MessageHeader as RustMessageHeader,
};
use solana_sdk::instruction::Instruction as RustInstruction;
use solana_sdk::pubkey::Pubkey as RustPubkey;

use crate::hash::{hash_to_py, Hash};
use crate::instruction::Instruction;
use crate::pubkey::Pubkey;

// ===========================================================================
// MessageHeader
// ===========================================================================
#[pyclass(get_all, name = "MessageHeader")]
#[derive(Clone)]
pub struct MessageHeader {
    pub num_required_signatures: u8,
    pub num_readonly_signed_accounts: u8,
    pub num_readonly_unsigned_accounts: u8,
}

#[pymethods]
impl MessageHeader {
    #[new]
    fn new(num_required_signatures: u8, num_readonly_signed_accounts: u8, num_readonly_unsigned_accounts: u8) -> Self {
        Self {
            num_required_signatures,
            num_readonly_signed_accounts,
            num_readonly_unsigned_accounts,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "MessageHeader(num_required_signatures={}, num_readonly_signed_accounts={}, num_readonly_unsigned_accounts={})",
            self.num_required_signatures, self.num_readonly_signed_accounts, self.num_readonly_unsigned_accounts
        )
    }
}

impl From<RustMessageHeader> for MessageHeader {
    fn from(h: RustMessageHeader) -> Self {
        Self {
            num_required_signatures: h.num_required_signatures,
            num_readonly_signed_accounts: h.num_readonly_signed_accounts,
            num_readonly_unsigned_accounts: h.num_readonly_unsigned_accounts,
        }
    }
}

// ===========================================================================
// CompiledInstruction
// ===========================================================================
#[pyclass(get_all, name = "CompiledInstruction")]
#[derive(Clone)]
pub struct CompiledInstruction {
    pub program_id_index: u8,
    pub accounts: Vec<u8>,
    pub data: Vec<u8>,
}

#[pymethods]
impl CompiledInstruction {
    #[new]
    fn new(program_id_index: u8, accounts: Vec<u8>, data: Vec<u8>) -> Self {
        Self { program_id_index, accounts, data }
    }

    fn __repr__(&self) -> String {
        format!(
            "CompiledInstruction(program_id_index={}, accounts_len={}, data_len={})",
            self.program_id_index,
            self.accounts.len(),
            self.data.len()
        )
    }
}

impl From<RustCompiledInstruction> for CompiledInstruction {
    fn from(ci: RustCompiledInstruction) -> Self {
        Self {
            program_id_index: ci.program_id_index,
            accounts: ci.accounts,
            data: ci.data,
        }
    }
}

// ===========================================================================
// AddressLookupTableAccount (used by V0 messages)
// ===========================================================================
#[pyclass(get_all, name = "AddressLookupTableAccount")]
#[derive(Clone)]
pub struct AddressLookupTableAccount {
    pub key: Pubkey,
    pub addresses: Vec<Pubkey>,
}

#[pymethods]
impl AddressLookupTableAccount {
    #[new]
    fn new(key: Pubkey, addresses: Vec<Pubkey>) -> Self {
        Self { key, addresses }
    }

    fn __repr__(&self) -> String {
        format!(
            "AddressLookupTableAccount(key={}, addresses_len={})",
            RustPubkey::from(self.key.data).to_string(),
            self.addresses.len()
        )
    }
}

impl From<&AddressLookupTableAccount> for RustAddressLookupTableAccount {
    fn from(a: &AddressLookupTableAccount) -> Self {
        Self {
            key: RustPubkey::from(a.key.data),
            addresses: a.addresses.iter().map(|pk| RustPubkey::from(pk.data)).collect(),
        }
    }
}

// ===========================================================================
// Helper: convert Python Instruction list to Rust Instruction list
// ===========================================================================
fn to_rust_instructions(instructions: &[Instruction]) -> Vec<RustInstruction> {
    instructions
        .iter()
        .map(|ix| RustInstruction {
            program_id: RustPubkey::from(ix.program_id.data),
            accounts: ix
                .accounts
                .iter()
                .map(|a| solana_sdk::instruction::AccountMeta {
                    pubkey: RustPubkey::from(a.pubkey.data),
                    is_signer: a.is_signer,
                    is_writable: a.is_writable,
                })
                .collect(),
            data: ix.data.clone(),
        })
        .collect()
}

// ===========================================================================
// Legacy Message
// ===========================================================================
#[pyclass(name = "Message")]
pub struct Message {
    pub inner: RustLegacyMessage,
}

#[pymethods]
impl Message {
    /// Create a new legacy Message from instructions and an optional payer.
    ///
    /// Uses a default (zero) blockhash; use :meth:`new_with_blockhash` to set one.
    #[new]
    #[pyo3(signature = (instructions, payer=None))]
    fn new(instructions: Vec<Instruction>, payer: Option<Pubkey>) -> Self {
        let rust_ixs = to_rust_instructions(&instructions);
        let msg = RustLegacyMessage::new(&rust_ixs, payer.as_ref().map(|p| RustPubkey::from(p.data)).as_ref());
        Self { inner: msg }
    }

    /// Create a new legacy Message with an explicit recent blockhash.
    #[staticmethod]
    fn new_with_blockhash(
        instructions: Vec<Instruction>,
        payer: Option<Pubkey>,
        blockhash: &Hash,
    ) -> Self {
        let rust_ixs = to_rust_instructions(&instructions);
        let bh = RustHash::new_from_array(blockhash.data);
        let msg = RustLegacyMessage::new_with_blockhash(
            &rust_ixs,
            payer.as_ref().map(|p| RustPubkey::from(p.data)).as_ref(),
            &bh,
        );
        Self { inner: msg }
    }

    /// Serialize the message to bytes (legacy format, no version prefix).
    fn serialize(&self) -> Vec<u8> {
        self.inner.serialize()
    }

    /// The message header.
    #[getter]
    fn header(&self) -> MessageHeader {
        self.inner.header.into()
    }

    /// The account keys referenced by the message.
    #[getter]
    fn account_keys(&self) -> Vec<Pubkey> {
        self.inner
            .account_keys
            .iter()
            .map(|k| Pubkey { data: k.to_bytes() })
            .collect()
    }

    /// The recent blockhash.
    #[getter]
    fn recent_blockhash(&self) -> Hash {
        hash_to_py(&self.inner.recent_blockhash)
    }

    /// The compiled instructions.
    #[getter]
    fn instructions(&self) -> Vec<CompiledInstruction> {
        self.inner.instructions.iter().cloned().map(CompiledInstruction::from).collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "Message(header={:?}, account_keys_len={}, instructions_len={})",
            self.inner.header,
            self.inner.account_keys.len(),
            self.inner.instructions.len()
        )
    }
}

// ===========================================================================
// MessageV0
// ===========================================================================
#[pyclass(name = "MessageV0")]
pub struct MessageV0 {
    pub inner: v0::Message,
}

#[pymethods]
impl MessageV0 {
    /// Compile a V0 message from payer, instructions, lookup tables, and blockhash.
    #[staticmethod]
    fn try_compile(
        payer: &Pubkey,
        instructions: Vec<Instruction>,
        address_lookup_table_accounts: Vec<AddressLookupTableAccount>,
        recent_blockhash: &Hash,
    ) -> PyResult<Self> {
        let rust_ixs = to_rust_instructions(&instructions);
        let rust_alts: Vec<RustAddressLookupTableAccount> = address_lookup_table_accounts
            .iter()
            .map(RustAddressLookupTableAccount::from)
            .collect();
        let bh = RustHash::new_from_array(recent_blockhash.data);
        let msg = v0::Message::try_compile(
            &RustPubkey::from(payer.data),
            &rust_ixs,
            &rust_alts,
            bh,
        )
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("compile error: {e:?}")))?;
        Ok(Self { inner: msg })
    }

    /// Serialize the message with a version #0 prefix.
    fn serialize(&self) -> Vec<u8> {
        self.inner.serialize()
    }

    /// The message header.
    #[getter]
    fn header(&self) -> MessageHeader {
        self.inner.header.into()
    }

    /// The static account keys.
    #[getter]
    fn account_keys(&self) -> Vec<Pubkey> {
        self.inner
            .account_keys
            .iter()
            .map(|k| Pubkey { data: k.to_bytes() })
            .collect()
    }

    /// The recent blockhash.
    #[getter]
    fn recent_blockhash(&self) -> Hash {
        hash_to_py(&self.inner.recent_blockhash)
    }

    /// The compiled instructions.
    #[getter]
    fn instructions(&self) -> Vec<CompiledInstruction> {
        self.inner.instructions.iter().cloned().map(CompiledInstruction::from).collect()
    }

    /// The address table lookups.
    #[getter]
    fn address_table_lookups(&self) -> Vec<AddressTableLookup> {
        self.inner
            .address_table_lookups
            .iter()
            .map(AddressTableLookup::from)
            .collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "MessageV0(header={:?}, account_keys_len={}, instructions_len={}, lookups_len={})",
            self.inner.header,
            self.inner.account_keys.len(),
            self.inner.instructions.len(),
            self.inner.address_table_lookups.len(),
        )
    }
}

/// A single address table lookup entry (read-only view for V0 messages).
#[pyclass(get_all, name = "MessageAddressTableLookup")]
#[derive(Clone)]
pub struct AddressTableLookup {
    pub account_key: Pubkey,
    pub writable_indexes: Vec<u8>,
    pub readonly_indexes: Vec<u8>,
}

#[pymethods]
impl AddressTableLookup {
    fn __repr__(&self) -> String {
        format!(
            "MessageAddressTableLookup(account_key={}, writable={}, readonly={})",
            RustPubkey::from(self.account_key.data).to_string(),
            self.writable_indexes.len(),
            self.readonly_indexes.len(),
        )
    }
}

impl From<&v0::MessageAddressTableLookup> for AddressTableLookup {
    fn from(l: &v0::MessageAddressTableLookup) -> Self {
        Self {
            account_key: Pubkey { data: l.account_key.to_bytes() },
            writable_indexes: l.writable_indexes.clone(),
            readonly_indexes: l.readonly_indexes.clone(),
        }
    }
}

// ===========================================================================
// MessageV1 (SIMD-0385)
// ===========================================================================
#[pyclass(name = "MessageV1")]
pub struct MessageV1 {
    pub inner: v1::Message,
}

#[pymethods]
impl MessageV1 {
    /// Compile a V1 message from payer, instructions, and blockhash.
    #[staticmethod]
    fn try_compile(
        payer: &Pubkey,
        instructions: Vec<Instruction>,
        recent_blockhash: &Hash,
    ) -> PyResult<Self> {
        let rust_ixs = to_rust_instructions(&instructions);
        let bh = RustHash::new_from_array(recent_blockhash.data);
        let msg = v1::Message::try_compile(&RustPubkey::from(payer.data), &rust_ixs, bh)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("compile error: {e:?}")))?;
        Ok(Self { inner: msg })
    }

    /// Serialize the message with the V1 version prefix byte.
    fn serialize(&self) -> Vec<u8> {
        self.inner.serialize()
    }

    /// The message header.
    #[getter]
    fn header(&self) -> MessageHeader {
        self.inner.header.into()
    }

    /// The account keys.
    #[getter]
    fn account_keys(&self) -> Vec<Pubkey> {
        self.inner
            .account_keys
            .iter()
            .map(|k| Pubkey { data: k.to_bytes() })
            .collect()
    }

    /// The lifetime specifier (blockhash).
    #[getter]
    fn lifetime_specifier(&self) -> Hash {
        hash_to_py(&self.inner.lifetime_specifier)
    }

    /// The compiled instructions.
    #[getter]
    fn instructions(&self) -> Vec<CompiledInstruction> {
        self.inner.instructions.iter().cloned().map(CompiledInstruction::from).collect()
    }

    /// The serialized size in bytes.
    fn size(&self) -> usize {
        self.inner.size()
    }

    fn __repr__(&self) -> String {
        format!(
            "MessageV1(header={:?}, account_keys_len={}, instructions_len={}, size={})",
            self.inner.header,
            self.inner.account_keys.len(),
            self.inner.instructions.len(),
            self.inner.size(),
        )
    }
}
