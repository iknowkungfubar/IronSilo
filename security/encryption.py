"""
AES-256 encryption module for IronSilo.

This module provides application-level encryption for data at rest,
using AES-256-GCM for authenticated encryption.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from typing import Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import structlog

logger = structlog.get_logger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption errors."""
    pass


class DecryptionError(EncryptionError):
    """Raised when decryption fails."""
    pass


class KeyError(EncryptionError):
    """Raised when key operations fail."""
    pass


class AESEncryptor:
    """
    AES-256-GCM encryptor for authenticated encryption.
    
    Features:
    - AES-256-GCM for confidentiality and authenticity
    - Random nonce generation (12 bytes)
    - Optional associated data (AAD)
    - Base64 encoding for storage
    
    Usage:
        encryptor = AESEncryptor(key)
        ciphertext = encryptor.encrypt(b"secret data")
        plaintext = encryptor.decrypt(ciphertext)
    """
    
    # Key size (256 bits)
    KEY_SIZE = 32
    
    # Nonce size (96 bits for GCM)
    NONCE_SIZE = 12
    
    # Tag size (128 bits for GCM)
    TAG_SIZE = 16
    
    def __init__(self, key: bytes):
        """
        Initialize encryptor with key.
        
        Args:
            key: Encryption key (must be 32 bytes for AES-256)
            
        Raises:
            KeyError: If key is not valid
        """
        if not isinstance(key, bytes):
            raise KeyError("Key must be bytes")
        
        if len(key) != self.KEY_SIZE:
            raise KeyError(f"Key must be {self.KEY_SIZE} bytes, got {len(key)}")
        
        self.key = key
        self._aesgcm = AESGCM(key)
    
    @classmethod
    def generate_key(cls) -> bytes:
        """Generate a random 256-bit key."""
        return secrets.token_bytes(cls.KEY_SIZE)
    
    @classmethod
    def derive_key(
        cls,
        password: str,
        salt: Optional[bytes] = None,
        iterations: int = 100000,
    ) -> tuple[bytes, bytes]:
        """
        Derive a key from a password using PBKDF2.
        
        Args:
            password: Password string
            salt: Optional salt (generated if not provided)
            iterations: Number of PBKDF2 iterations
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        
        # Use PBKDF2-HMAC-SHA256
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations,
            dklen=cls.KEY_SIZE,
        )
        
        return key, salt
    
    def encrypt(
        self,
        plaintext: Union[str, bytes],
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt (string will be UTF-8 encoded)
            associated_data: Optional additional authenticated data
            
        Returns:
            Encrypted data (nonce + ciphertext + tag)
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Convert string to bytes if needed
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')
            
            # Generate random nonce
            nonce = secrets.token_bytes(self.NONCE_SIZE)
            
            # Encrypt
            ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data)
            
            # Combine nonce + ciphertext (includes tag)
            result = nonce + ciphertext
            
            logger.debug(
                "Data encrypted",
                plaintext_size=len(plaintext),
                ciphertext_size=len(result),
            )
            
            return result
            
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(
        self,
        data: bytes,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """
        Decrypt data encrypted with AES-256-GCM.
        
        Args:
            data: Encrypted data (nonce + ciphertext + tag)
            associated_data: Optional additional authenticated data
            
        Returns:
            Decrypted plaintext
            
        Raises:
            DecryptionError: If decryption fails (wrong key, corrupted data, etc.)
        """
        try:
            if len(data) < self.NONCE_SIZE + self.TAG_SIZE:
                raise DecryptionError("Data too short")
            
            # Extract nonce and ciphertext
            nonce = data[:self.NONCE_SIZE]
            ciphertext = data[self.NONCE_SIZE:]
            
            # Decrypt
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, associated_data)
            
            logger.debug(
                "Data decrypted",
                ciphertext_size=len(data),
                plaintext_size=len(plaintext),
            )
            
            return plaintext
            
        except DecryptionError:
            raise
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise DecryptionError(f"Decryption failed: {e}")
    
    def encrypt_to_base64(
        self,
        plaintext: Union[str, bytes],
        associated_data: Optional[bytes] = None,
    ) -> str:
        """Encrypt and encode as base64 string."""
        ciphertext = self.encrypt(plaintext, associated_data)
        return base64.b64encode(ciphertext).decode('ascii')
    
    def decrypt_from_base64(
        self,
        data: str,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt from base64 string."""
        ciphertext = base64.b64decode(data)
        return self.decrypt(ciphertext, associated_data)


class EncryptedField:
    """
    Descriptor for encrypted model fields.
    
    Usage:
        class MyModel:
            secret = EncryptedField()
            
            def __init__(self, encryptor):
                self._encryptor = encryptor
    """
    
    def __init__(self, field_name: Optional[str] = None):
        self.field_name = field_name
    
    def __set_name__(self, owner, name):
        self.field_name = name
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._encrypted_data.get(self.field_name)
    
    def __set__(self, obj, value):
        if not hasattr(obj, '_encryptor'):
            raise EncryptionError("Object must have _encryptor attribute")
        
        if value is None:
            obj._encrypted_data[self.field_name] = None
        else:
            encrypted = obj._encryptor.encrypt(str(value))
            obj._encrypted_data[self.field_name] = base64.b64encode(encrypted).decode('ascii')


def verify_key_integrity(key: bytes, expected_hash: str) -> bool:
    """
    Verify key integrity using HMAC.
    
    Args:
        key: Key to verify
        expected_hash: Expected HMAC hash
        
    Returns:
        True if key is valid
    """
    computed_hash = hashlib.sha256(key).hexdigest()
    return hmac.compare_digest(computed_hash, expected_hash)


def create_key_fingerprint(key: bytes) -> str:
    """Create a fingerprint for key identification."""
    return hashlib.sha256(key).hexdigest()[:16]
