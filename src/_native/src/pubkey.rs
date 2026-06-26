//! Pubkey — 32-byte Solana account address.

use pyo3::prelude::*;
#[allow(deprecated)]
use solana_sdk::pubkey::Pubkey as RustPubkey;

#[pyclass(get_all, name = "Pubkey")]
#[derive(Clone)]
pub struct Pubkey {
    pub data: [u8; 32],
}

#[pymethods]
impl Pubkey {
    /// Well-known program addresses.
    #[classattr]
    const PUBKEY_BYTES: usize = 32;

    /// Construct from 32 raw bytes.  Alias for ``from_bytes``.
    #[new]
    fn new(data: &[u8]) -> PyResult<Self> {
        Self::from_bytes(data)
    }

    /// Parse a base58-encoded string into a Pubkey.
    #[staticmethod]
    fn from_string(s: &str) -> PyResult<Self> {
        let pk = RustPubkey::try_from(s)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("invalid base58: {e}")))?;
        Ok(Self { data: pk.to_bytes() })
    }

    /// Wrap 32 raw bytes.
    #[staticmethod]
    fn from_bytes(data: &[u8]) -> PyResult<Self> {
        let arr: [u8; 32] = data.try_into().map_err(|_| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Pubkey must be exactly 32 bytes")
        })?;
        Ok(Self { data: arr })
    }

    /// Generate a new random Pubkey (not guaranteed to be a valid curve point).
    #[staticmethod]
    fn new_rand() -> Self {
        #[allow(deprecated)]
        let pk: RustPubkey = solana_sdk::pubkey::new_rand();
        Self { data: pk.to_bytes() }
    }

    /// Encode the Pubkey as a base58 string.
    fn to_string(&self) -> String {
        RustPubkey::from(self.data).to_string()
    }

    /// Check whether the underlying 32 bytes represent a valid Ed25519 curve point.
    fn is_on_curve(&self) -> bool {
        solana_sdk::pubkey::bytes_are_curve_point(self.data)
    }

    fn __bytes__(&self) -> &[u8] {
        &self.data
    }

    fn __repr__(&self) -> String {
        format!("Pubkey({})", RustPubkey::from(self.data))
    }

    fn __str__(&self) -> String {
        self.to_string()
    }

    fn __richcmp__(&self, other: &Self, op: pyo3::pyclass::CompareOp) -> bool {
        op.matches(self.data.cmp(&other.data))
    }

    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut h = std::collections::hash_map::DefaultHasher::new();
        self.data.hash(&mut h);
        h.finish()
    }
}
