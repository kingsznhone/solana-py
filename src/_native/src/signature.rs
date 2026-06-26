//! Signature — 64-byte Ed25519 signature.

use pyo3::prelude::*;
use solana_sdk::signature::Signature as RustSignature;

#[pyclass(get_all, name = "Signature")]
#[derive(Clone)]
pub struct Signature {
    pub data: [u8; 64],
}

#[pymethods]
impl Signature {
    #[new]
    fn new(data: &[u8]) -> PyResult<Self> {
        let arr: [u8; 64] = data.try_into().map_err(|_| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Signature must be exactly 64 bytes")
        })?;
        Ok(Self { data: arr })
    }

    fn __bytes__(&self) -> &[u8] {
        &self.data
    }

    fn __repr__(&self) -> String {
        format!("Signature({})", RustSignature::from(self.data))
    }

    fn __richcmp__(&self, other: &Self, op: pyo3::pyclass::CompareOp) -> bool {
        op.matches(self.data.cmp(&other.data))
    }
}
