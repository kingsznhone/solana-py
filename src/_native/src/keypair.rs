//! Keypair generation, signing, and verification.

use pyo3::prelude::*;
use solana_sdk::signer::{keypair::Keypair as RustKeypair, Signer};

use crate::pubkey::Pubkey;
use crate::signature::Signature;

/// An Ed25519 keypair.
///
/// Class attributes:
///     SECRET_KEY_LENGTH: 32 (seed bytes)
///     KEYPAIR_LENGTH: 64 (full secret key bytes)
#[pyclass(name = "Keypair")]
pub struct Keypair {
    pub(crate) inner: RustKeypair,
}

#[pymethods]
impl Keypair {
    /// Constructs a new, random `Keypair` using `OsRng`.
    #[staticmethod]
    fn generate() -> Self {
        Self {
            inner: RustKeypair::new(),
        }
    }

    /// Recover a keypair from raw bytes: 32-byte seed or 64-byte secret key.
    ///
    /// 32 bytes → treated as the Ed25519 seed (``new_from_array``).
    /// 64 bytes → treated as the full keypair (``try_from``).
    #[staticmethod]
    fn from_bytes(data: &[u8]) -> PyResult<Self> {
        let inner = match data.len() {
            32 => {
                let mut arr = [0u8; 32];
                arr.copy_from_slice(data);
                RustKeypair::new_from_array(arr)
            }
            64 => {
                RustKeypair::try_from(data)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("{e}")))?
            }
            n => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Keypair expects 32 or 64 bytes, got {n}"
                )));
            }
        };
        Ok(Self { inner })
    }

    /// Recover a keypair from a base58-encoded string.
    ///
    /// Uses ``try_from_base58_string`` — raises ``ValueError`` on malformed input.
    #[staticmethod]
    fn from_base58_string(s: &str) -> PyResult<Self> {
        let inner = RustKeypair::try_from_base58_string(s)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("invalid base58 keypair: {e}")))?;
        Ok(Self { inner })
    }

    /// Construct a `Keypair` from a 32-byte seed slice.
    ///
    /// Equivalent to ``solana_keypair::keypair_from_seed``.
    #[staticmethod]
    fn from_seed(seed: &[u8]) -> PyResult<Self> {
        if seed.len() < 32 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "seed must be at least 32 bytes",
            ));
        }
        let arr: [u8; 32] = seed[..32].try_into().unwrap();
        Ok(Self {
            inner: RustKeypair::new_from_array(arr),
        })
    }

    /// The public key derived from the secret key.
    fn pubkey(&self) -> Pubkey {
        Pubkey {
            data: self.inner.pubkey().to_bytes(),
        }
    }

    /// Sign an arbitrary message and return a 64-byte ``Signature``.
    fn sign(&self, message: &[u8]) -> Signature {
        let sig = self.inner.sign_message(message);
        Signature {
            data: <[u8; 64]>::from(sig),
        }
    }

    /// Verify *message* was signed by *pubkey* producing *signature*.
    #[staticmethod]
    fn verify(message: &[u8], signature: &Signature, pubkey: &Pubkey) -> bool {
        let sig = solana_sdk::signature::Signature::from(signature.data);
        sig.verify(&pubkey.data, message)
    }

    /// Export the 64-byte secret key as a base58-encoded string.
    fn to_base58_string(&self) -> String {
        self.inner.to_base58_string()
    }

    /// The 32-byte Ed25519 seed (first half of ``__bytes__``).
    #[getter]
    fn secret_bytes(&self) -> Vec<u8> {
        self.inner.secret_bytes().to_vec()
    }

    /// The 32-byte secret seed length.
    #[classattr]
    const SECRET_KEY_LENGTH: usize = 32;

    /// The 64-byte keypair length.
    #[classattr]
    const KEYPAIR_LENGTH: usize = 64;

    /// Explicit in-memory copy of the keypair (use sparingly).
    fn clone(&self) -> Self {
        Self {
            inner: self.inner.insecure_clone(),
        }
    }

    /// Full 64-byte secret key.
    fn __bytes__(&self) -> Vec<u8> {
        self.inner.to_bytes().to_vec()
    }

    fn __repr__(&self) -> String {
        format!("Keypair({})", self.inner.pubkey())
    }
}
