//! Hash — 32-byte hash (blockhash / lifetime specifier).

use pyo3::prelude::*;
use solana_sdk::hash::Hash as RustHash;

#[pyclass(get_all, name = "Hash")]
#[derive(Clone)]
pub struct Hash {
    pub data: [u8; 32],
}

#[pymethods]
impl Hash {
    #[classattr]
    const HASH_BYTES: usize = 32;

    /// Construct from 32 raw bytes.
    #[new]
    fn new(data: &[u8]) -> PyResult<Self> {
        Self::from_bytes(data)
    }

    /// Wrap 32 raw bytes.
    #[staticmethod]
    fn from_bytes(data: &[u8]) -> PyResult<Self> {
        let arr: [u8; 32] = data.try_into().map_err(|_| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Hash must be exactly 32 bytes")
        })?;
        Ok(Self { data: arr })
    }

    /// Generate a unique Hash (for testing).
    #[staticmethod]
    fn new_unique() -> Self {
        Self {
            data: RustHash::new_unique().to_bytes(),
        }
    }

    fn to_bytes(&self) -> &[u8] {
        &self.data
    }

    fn __bytes__(&self) -> &[u8] {
        &self.data
    }

    fn __repr__(&self) -> String {
        format!("Hash({})", RustHash::from(self.data))
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

impl From<RustHash> for Hash {
    fn from(h: RustHash) -> Self {
        Self { data: h.to_bytes() }
    }
}

/// Convert any 32-byte hash to our Hash.
pub(crate) fn hash_to_py(h: &RustHash) -> Hash {
    Hash { data: h.to_bytes() }
}
