//! VersionedTransaction — signed transaction ready for RPC submission.

use pyo3::prelude::*;
use solana_sdk::signature::Signature as RustSignature;
use solana_sdk::signer::keypair::Keypair as RustKeypair;
use solana_sdk::transaction::VersionedTransaction as RustVersionedTransaction;

use crate::hash::Hash;
use crate::instruction::Instruction;
use crate::keypair::Keypair;
use crate::message::{Message, MessageV0, MessageV1};
use crate::pubkey::Pubkey;
use crate::signature::Signature;

/// A signed, versioned transaction ready to be serialized and submitted to an RPC.
#[pyclass(name = "VersionedTransaction")]
pub struct VersionedTransaction {
    pub inner: RustVersionedTransaction,
}

#[pymethods]
impl VersionedTransaction {
    /// Sign a :class:`MessageV0` or :class:`MessageV1` with the given keypairs
    /// and return a transaction.
    ///
    /// The keypairs must match the message's required signers (in any order);
    /// signatures are reordered to match the message's account key ordering.
    #[new]
    fn new(py: Python<'_>, message: &Bound<'_, PyAny>, keypairs: Vec<Py<Keypair>>) -> PyResult<Self> {
        let rust_msg = if let Ok(m) = message.extract::<PyRef<'_, MessageV1>>() {
            solana_sdk::message::VersionedMessage::V1(m.inner.clone())
        } else if let Ok(m) = message.extract::<PyRef<'_, MessageV0>>() {
            solana_sdk::message::VersionedMessage::V0(m.inner.clone())
        } else {
            return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                "message must be MessageV0 or MessageV1",
            ));
        };
        Self::try_new_inner(py, rust_msg, &keypairs)
    }

    /// Serialize the transaction to bytes (wire format for RPC submission).
    fn serialize(&self) -> PyResult<Vec<u8>> {
        wincode::serialize(&self.inner)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("serialize error: {e:?}")))
    }

    /// Deserialize a transaction from bytes.
    #[staticmethod]
    fn deserialize(data: &[u8]) -> PyResult<Self> {
        let tx: RustVersionedTransaction = wincode::deserialize(data)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("deserialize error: {e:?}")))?;
        Ok(Self { inner: tx })
    }

    /// The signatures on the transaction.
    #[getter]
    fn signatures(&self) -> Vec<Signature> {
        self.inner
            .signatures
            .iter()
            .map(|s| Signature { data: *s.as_array() })
            .collect()
    }

    /// Number of signatures.
    #[getter]
    fn num_signatures(&self) -> usize {
        self.inner.signatures.len()
    }

    fn __repr__(&self) -> String {
        format!(
            "VersionedTransaction(signatures={}, message={})",
            self.inner.signatures.len(),
            match &self.inner.message {
                solana_sdk::message::VersionedMessage::Legacy(_) => "Legacy",
                solana_sdk::message::VersionedMessage::V0(_) => "V0",
                solana_sdk::message::VersionedMessage::V1(_) => "V1",
            }
        )
    }
}

impl VersionedTransaction {
    fn try_new_inner(
        py: Python<'_>,
        message: solana_sdk::message::VersionedMessage,
        keypairs: &[Py<Keypair>],
    ) -> PyResult<Self> {
        // Borrow each Keypair from its Python wrapper.
        let borrowed: Vec<PyRef<'_, Keypair>> = keypairs
            .iter()
            .map(|obj| obj.bind(py).borrow())
            .collect();
        let rust_keypairs: Vec<&RustKeypair> = borrowed.iter().map(|kp| &kp.inner).collect();
        let tx = RustVersionedTransaction::try_new(message, &rust_keypairs)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("sign error: {e:?}")))?;
        Ok(Self { inner: tx })
    }
}
