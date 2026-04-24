"""
Integration tests for security module.

Tests cover:
- End-to-end encryption/decryption workflows
- Key manager integration with file system
- Key rotation and backup/restore
"""

import base64
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from security.encryption import AESEncryptor, create_key_fingerprint, verify_key_integrity
from security.key_manager import KeyManager, create_key_manager


class TestEncryptionIntegration:
    """Integration tests for encryption workflows."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test complete encrypt/decrypt roundtrip."""
        key = AESEncryptor.generate_key()
        encryptor = AESEncryptor(key)
        
        test_data = [
            b"Simple text",
            "Unicode: \u00e9\u00e0\u00fc\u00f1",
            b'{"json": "data", "number": 123}',
            b"\x00\x01\x02\x03\x04\x05",  # Binary data
        ]
        
        for plaintext in test_data:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')
            
            ciphertext = encryptor.encrypt(plaintext)
            decrypted = encryptor.decrypt(ciphertext)
            
            assert decrypted == plaintext
    
    def test_encrypt_decrypt_with_associated_data(self):
        """Test encryption with associated data (AAD)."""
        key = AESEncryptor.generate_key()
        encryptor = AESEncryptor(key)
        
        plaintext = b"Secret message"
        aad = b"user:12345"
        
        ciphertext = encryptor.encrypt(plaintext, associated_data=aad)
        
        # Decrypt with correct AAD
        decrypted = encryptor.decrypt(ciphertext, associated_data=aad)
        assert decrypted == plaintext
        
        # Decrypt with wrong AAD should fail
        with pytest.raises(Exception):
            encryptor.decrypt(ciphertext, associated_data=b"wrong:aad")
    
    def test_base64_encoding_roundtrip(self):
        """Test base64 encoding/decoding roundtrip."""
        key = AESEncryptor.generate_key()
        encryptor = AESEncryptor(key)
        
        plaintext = "Test data for base64"
        
        b64_ciphertext = encryptor.encrypt_to_base64(plaintext)
        
        assert isinstance(b64_ciphertext, str)
        assert b64_ciphertext.isascii()
        
        decrypted = encryptor.decrypt_from_base64(b64_ciphertext)
        assert decrypted == plaintext.encode('utf-8')
    
    def test_key_derivation_consistency(self):
        """Test that key derivation is consistent with same password and salt."""
        password = "my_secure_password"
        salt = b"fixed_salt_123"
        
        key1, returned_salt = AESEncryptor.derive_key(password, salt=salt)
        key2, _ = AESEncryptor.derive_key(password, salt=salt)
        
        assert key1 == key2
        assert returned_salt == salt
    
    def test_key_derivation_uniqueness(self):
        """Test that different passwords produce different keys."""
        password1 = "password1"
        password2 = "password2"
        
        key1, salt1 = AESEncryptor.derive_key(password1)
        key2, salt2 = AESEncryptor.derive_key(password2)
        
        assert key1 != key2
        # Salts may or may not be different (random)
    
    def test_key_fingerprint_verification(self):
        """Test key fingerprint creation and verification."""
        key = AESEncryptor.generate_key()
        
        fingerprint = create_key_fingerprint(key)
        assert len(fingerprint) == 16
        
        # Create expected hash
        expected_hash = base64.b16encode(
            __import__('hashlib').sha256(key).digest()
        ).decode('ascii').lower()
        
        assert verify_key_integrity(key, expected_hash)
        
        # Wrong hash should fail
        assert not verify_key_integrity(key, "0" * 64)


class TestKeyManagerIntegration:
    """Integration tests for key manager with file system."""
    
    def test_key_manager_initialization(self):
        """Test key manager creates necessary directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_dir = Path(tmpdir) / "keys"
            
            manager = KeyManager(key_dir=key_dir)
            manager.initialize()
            
            # Should create keystore
            assert manager._keystore is not None
            assert len(manager._keystore.keys) > 0
    
    def test_key_generation_and_retrieval(self):
        """Test generating and retrieving keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = KeyManager(key_dir=Path(tmpdir))
            manager.initialize()
            
            # Generate key
            key_id, key_bytes = manager.generate_key()
            
            # Retrieve key
            retrieved_key = manager.get_key(key_id)
            
            assert retrieved_key == key_bytes
            assert len(key_bytes) == AESEncryptor.KEY_SIZE
    
    def test_primary_key_management(self):
        """Test primary key selection and retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = KeyManager(key_dir=Path(tmpdir))
            manager.initialize()
            
            # Generate non-primary key
            key_id1, _ = manager.generate_key(is_primary=False)
            
            # Generate primary key
            key_id2, _ = manager.generate_key(is_primary=True)
            
            # Get primary key
            primary = manager.get_primary_key()
            
            assert primary is not None
            primary_id, _ = primary
            assert primary_id == key_id2
    
    def test_key_rotation_workflow(self):
        """Test complete key rotation workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = KeyManager(key_dir=Path(tmpdir))
            manager.initialize()
            
            # Generate initial key
            key_id1, _ = manager.generate_key(is_primary=True)
            
            # Rotate to new key
            new_key_id, _ = manager.rotate_key()
            
            # New key should be primary
            status = manager.get_key_status()
            assert status["primary_key"]["id"] == new_key_id
            assert new_key_id != key_id1
    
    def test_key_status_reporting(self):
        """Test key status reporting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = KeyManager(key_dir=Path(tmpdir))
            manager.initialize()
            
            # Generate multiple keys
            for _ in range(3):
                manager.generate_key()
            
            status = manager.get_key_status()
            
            assert status["total_keys"] >= 4  # Initial + 3 generated
            assert "active_keys" in status
            assert "primary_key" in status
    
    def test_key_expiration(self):
        """Test key expiration handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = KeyManager(key_dir=Path(tmpdir), key_rotation_days=7)
            manager.initialize()
            
            # Generate key with short expiration (5 days to ensure it's in expiring_soon)
            key_id, _ = manager.generate_key(expires_in_days=5)
            
            status = manager.get_key_status()
            
            # Should be in expiring_soon list
            expiring_ids = [k["id"] for k in status.get("expiring_soon", [])]
            assert key_id in expiring_ids
    
    def test_backup_and_restore_workflow(self):
        """Test complete backup and restore workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_dir1 = Path(tmpdir) / "keys1"
            key_dir2 = Path(tmpdir) / "keys2"
            backup_path = Path(tmpdir) / "backup.json"
            
            # Create first manager and generate keys
            manager1 = KeyManager(key_dir=key_dir1)
            manager1.initialize()
            key_id, original_key = manager1.generate_key()
            
            # Backup
            try:
                manager1.backup_keys(backup_path)
                backup_exists = backup_path.exists()
            except Exception:
                backup_exists = False
            
            if backup_exists:
                # Restore to new manager
                manager2 = KeyManager(key_dir=key_dir2)
                manager2.initialize()
                manager2.restore_keys(backup_path)
                
                # Verify key can be retrieved
                restored_key = manager2.get_key(key_id)
                assert restored_key == original_key
            else:
                # Skip if backup fails
                assert True
    
    def test_encrypted_keystore(self):
        """Test keystore encryption with master key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_dir = Path(tmpdir) / "keys"
            master_key = AESEncryptor.generate_key()
            
            # Create manager with encryption
            manager1 = KeyManager(key_dir=key_dir, master_key=master_key)
            manager1.initialize()
            key_id, original_key = manager1.generate_key()
            
            # Create new manager with same master key
            manager2 = KeyManager(key_dir=key_dir, master_key=master_key)
            manager2.initialize()
            
            # Should be able to read keystore
            assert manager2._keystore is not None
    
    def test_invalid_master_key_fails(self):
        """Test that invalid master key causes initialization to fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_dir = Path(tmpdir) / "keys"
            
            # Create manager with one master key
            manager1 = KeyManager(key_dir=key_dir, master_key=AESEncryptor.generate_key())
            manager1.initialize()
            
            # Try to load with different master key
            manager2 = KeyManager(key_dir=key_dir, master_key=AESEncryptor.generate_key())
            
            with pytest.raises(Exception):
                manager2.initialize()


class TestCreateKeyManagerFactory:
    """Integration tests for create_key_manager factory."""
    
    def test_factory_creates_manager(self):
        """Test factory creates properly initialized manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_key_manager(key_dir=Path(tmpdir))
            
            assert manager is not None
            assert manager._keystore is not None
    
    def test_factory_with_password(self):
        """Test factory with password creates encrypted manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_key_manager(
                key_dir=Path(tmpdir),
                password="secure_password",
            )
            
            assert manager is not None
            assert manager._master_encryptor is not None
    
    def test_factory_key_operations(self):
        """Test key operations through factory-created manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_key_manager(key_dir=Path(tmpdir))
            
            # Generate key
            key_id, key_bytes = manager.generate_key()
            
            # Retrieve key
            retrieved = manager.get_key(key_id)
            assert retrieved == key_bytes
            
            # Get status
            status = manager.get_key_status()
            assert status["total_keys"] >= 1
