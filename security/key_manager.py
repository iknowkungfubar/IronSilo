"""
Key management system for IronSilo.

This module provides secure key storage, rotation, and management
for the encryption system.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
import structlog

from .encryption import AESEncryptor, EncryptionError, KeyError

logger = structlog.get_logger(__name__)


class KeyInfo(BaseModel):
    """Information about a managed key."""
    
    id: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    fingerprint: str
    is_active: bool = True
    is_primary: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if key is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)."""
        return self.is_active and not self.is_expired


class KeyStore(BaseModel):
    """Secure key storage."""
    
    version: str = "1.0.0"
    keys: List[KeyInfo] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KeyManager:
    """
    Secure key management with rotation support.
    
    Features:
    - Secure key storage with encryption
    - Automatic key rotation
    - Key expiration
    - Audit logging
    - Backup and restore
    """
    
    def __init__(
        self,
        key_dir: Path,
        master_key: Optional[bytes] = None,
        key_rotation_days: int = 90,
        max_keys: int = 10,
    ):
        """
        Initialize key manager.
        
        Args:
            key_dir: Directory for key storage
            master_key: Master key for encrypting stored keys
            key_rotation_days: Days between key rotations
            max_keys: Maximum number of keys to keep
        """
        self.key_dir = Path(key_dir)
        self.key_rotation_days = key_rotation_days
        self.max_keys = max_keys
        
        # Ensure key directory exists
        self.key_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize master encryptor
        if master_key:
            self._master_encryptor = AESEncryptor(master_key)
        else:
            self._master_encryptor = None
        
        # Key store
        self._keystore_path = self.key_dir / "keystore.json"
        self._keystore: Optional[KeyStore] = None
        
        # In-memory key cache (key_id -> key bytes)
        self._key_cache: Dict[str, bytes] = {}
        
        logger.info(
            "Key manager initialized",
            key_dir=str(self.key_dir),
            rotation_days=key_rotation_days,
            max_keys=max_keys,
        )
    
    def initialize(self, password: Optional[str] = None) -> None:
        """
        Initialize key manager with optional password.
        
        If no keystore exists, creates a new one with initial key.
        """
        if self._keystore_path.exists():
            self._load_keystore()
        else:
            self._create_keystore(password)
    
    def _create_keystore(self, password: Optional[str] = None) -> None:
        """Create a new keystore."""
        self._keystore = KeyStore()
        
        # Create initial key
        self.generate_key(is_primary=True)
        
        # Save keystore
        self._save_keystore(password)
        
        logger.info("Created new keystore")
    
    def _load_keystore(self, password: Optional[str] = None) -> None:
        """Load keystore from disk."""
        try:
            if self._master_encryptor:
                # Load encrypted keystore
                encrypted = self._keystore_path.read_bytes()
                decrypted = self._master_encryptor.decrypt(encrypted)
                self._keystore = KeyStore.model_validate_json(decrypted)
            else:
                # Load unencrypted keystore
                self._keystore = KeyStore.model_validate_json(
                    self._keystore_path.read_text()
                )
            
            logger.info("Loaded keystore", key_count=len(self._keystore.keys))
            
        except Exception as e:
            logger.error("Failed to load keystore", error=str(e))
            raise KeyError(f"Failed to load keystore: {e}")
    
    def _save_keystore(self, password: Optional[str] = None) -> None:
        """Save keystore to disk."""
        if self._keystore is None:
            raise KeyError("Keystore not initialized")
        
        try:
            self._keystore.updated_at = datetime.now(timezone.utc)
            json_data = self._keystore.model_dump_json()
            
            if self._master_encryptor:
                # Encrypt keystore
                encrypted = self._master_encryptor.encrypt(json_data)
                self._keystore_path.write_bytes(encrypted)
            else:
                # Save unencrypted
                self._keystore_path.write_text(json_data)
            
            logger.debug("Saved keystore")
            
        except Exception as e:
            logger.error("Failed to save keystore", error=str(e))
            raise KeyError(f"Failed to save keystore: {e}")
    
    def generate_key(
        self,
        is_primary: bool = False,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[str, bytes]:
        """
        Generate a new encryption key.
        
        Args:
            is_primary: Whether this is the primary key
            expires_in_days: Optional expiration in days
            
        Returns:
            Tuple of (key_id, key_bytes)
        """
        if self._keystore is None:
            raise KeyError("Keystore not initialized")
        
        # Generate key
        key_bytes = AESEncryptor.generate_key()
        key_id = secrets.token_hex(8)
        fingerprint = self._create_fingerprint(key_bytes)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        # Create key info
        key_info = KeyInfo(
            id=key_id,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            fingerprint=fingerprint,
            is_active=True,
            is_primary=is_primary,
        )
        
        # If this is primary, demote other primary keys
        if is_primary:
            for key in self._keystore.keys:
                key.is_primary = False
        
        # Add to keystore
        self._keystore.keys.append(key_info)
        
        # Cache key
        self._key_cache[key_id] = key_bytes
        
        # Save keystore
        self._save_keystore()
        
        logger.info(
            "Generated new key",
            key_id=key_id,
            is_primary=is_primary,
            expires_at=expires_at,
        )
        
        return key_id, key_bytes
    
    def get_key(self, key_id: str) -> Optional[bytes]:
        """
        Get a key by ID.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Key bytes or None if not found
        """
        # Check cache first
        if key_id in self._key_cache:
            return self._key_cache[key_id]
        
        # Look up in keystore
        if self._keystore is None:
            return None
        
        key_info = self._get_key_info(key_id)
        if key_info is None:
            return None
        
        # Load key from disk
        key_path = self.key_dir / f"{key_id}.key"
        if not key_path.exists():
            return None
        
        try:
            if self._master_encryptor:
                encrypted = key_path.read_bytes()
                key_bytes = self._master_encryptor.decrypt(encrypted)
            else:
                key_bytes = key_path.read_bytes()
            
            # Cache key
            self._key_cache[key_id] = key_bytes
            
            return key_bytes
            
        except Exception as e:
            logger.error("Failed to load key", key_id=key_id, error=str(e))
            return None
    
    def get_primary_key(self) -> Optional[Tuple[str, bytes]]:
        """
        Get the current primary key.
        
        Returns:
            Tuple of (key_id, key_bytes) or None
        """
        if self._keystore is None:
            return None
        
        for key_info in self._keystore.keys:
            if key_info.is_primary and key_info.is_valid:
                key_bytes = self.get_key(key_info.id)
                if key_bytes:
                    return key_info.id, key_bytes
        
        return None
    
    def rotate_key(self) -> Tuple[str, bytes]:
        """
        Rotate to a new primary key.
        
        Returns:
            Tuple of (new_key_id, new_key_bytes)
        """
        if self._keystore is None:
            raise KeyError("Keystore not initialized")
        
        # Demote current primary
        for key_info in self._keystore.keys:
            if key_info.is_primary:
                key_info.is_primary = False
                logger.info("Demoted primary key", key_id=key_info.id)
        
        # Generate new primary key
        new_key_id, new_key_bytes = self.generate_key(
            is_primary=True,
            expires_in_days=self.key_rotation_days,
        )
        
        # Clean up old keys
        self._cleanup_old_keys()
        
        logger.info("Key rotation completed", new_key_id=new_key_id)
        
        return new_key_id, new_key_bytes
    
    def _cleanup_old_keys(self) -> None:
        """Remove old keys exceeding max_keys limit."""
        if self._keystore is None:
            return
        
        # Sort keys by creation date (newest first)
        sorted_keys = sorted(
            self._keystore.keys,
            key=lambda k: k.created_at,
            reverse=True,
        )
        
        # Keep only the newest max_keys
        if len(sorted_keys) > self.max_keys:
            keys_to_remove = sorted_keys[self.max_keys:]
            
            for key_info in keys_to_remove:
                # Don't remove primary key
                if key_info.is_primary:
                    continue
                
                # Mark as inactive
                key_info.is_active = False
                
                # Remove from disk
                key_path = self.key_dir / f"{key_info.id}.key"
                if key_path.exists():
                    key_path.unlink()
                
                # Remove from cache
                self._key_cache.pop(key_info.id, None)
                
                logger.info("Removed old key", key_id=key_info.id)
            
            # Remove from keystore
            self._keystore.keys = [
                k for k in self._keystore.keys
                if k.is_active or k.is_primary
            ]
            
            self._save_keystore()
    
    def _get_key_info(self, key_id: str) -> Optional[KeyInfo]:
        """Get key info by ID."""
        if self._keystore is None:
            return None
        
        for key_info in self._keystore.keys:
            if key_info.id == key_id:
                return key_info
        
        return None
    
    def _create_fingerprint(self, key: bytes) -> str:
        """Create fingerprint for key identification."""
        import hashlib
        return hashlib.sha256(key).hexdigest()[:16]
    
    def backup_keys(self, backup_path: Path) -> None:
        """
        Backup all keys to a secure location.
        
        Args:
            backup_path: Path for backup file
        """
        if self._keystore is None:
            raise KeyError("Keystore not initialized")
        
        backup_data = {
            "keystore": self._keystore.model_dump(),
            "keys": {},
        }
        
        # Export all keys
        for key_info in self._keystore.keys:
            key_bytes = self.get_key(key_info.id)
            if key_bytes:
                import base64
                backup_data["keys"][key_info.id] = base64.b64encode(key_bytes).decode('ascii')
        
        # Save backup
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(json.dumps(backup_data, indent=2))
        
        logger.info("Keys backed up", backup_path=str(backup_path), key_count=len(backup_data["keys"]))
    
    def restore_keys(self, backup_path: Path, password: Optional[str] = None) -> None:
        """
        Restore keys from backup.
        
        Args:
            backup_path: Path to backup file
            password: Optional password for encrypted backup
        """
        try:
            backup_data = json.loads(backup_path.read_text())
            
            # Restore keystore
            self._keystore = KeyStore(**backup_data["keystore"])
            
            # Restore keys
            import base64
            for key_id, key_b64 in backup_data["keys"].items():
                key_bytes = base64.b64decode(key_b64)
                
                # Save to disk
                key_path = self.key_dir / f"{key_id}.key"
                if self._master_encryptor:
                    encrypted = self._master_encryptor.encrypt(key_bytes)
                    key_path.write_bytes(encrypted)
                else:
                    key_path.write_bytes(key_bytes)
                
                # Cache
                self._key_cache[key_id] = key_bytes
            
            # Save keystore
            self._save_keystore(password)
            
            logger.info("Keys restored", backup_path=str(backup_path))
            
        except Exception as e:
            logger.error("Failed to restore keys", error=str(e))
            raise KeyError(f"Failed to restore keys: {e}")
    
    def get_key_status(self) -> Dict[str, Any]:
        """Get status of all keys."""
        if self._keystore is None:
            return {"status": "not_initialized"}
        
        status = {
            "total_keys": len(self._keystore.keys),
            "active_keys": sum(1 for k in self._keystore.keys if k.is_active),
            "primary_key": None,
            "expiring_soon": [],
        }
        
        for key_info in self._keystore.keys:
            if key_info.is_primary:
                status["primary_key"] = {
                    "id": key_info.id,
                    "fingerprint": key_info.fingerprint,
                    "created_at": key_info.created_at.isoformat(),
                    "expires_at": key_info.expires_at.isoformat() if key_info.expires_at else None,
                }
            
            # Check if expiring in next 7 days
            if key_info.expires_at:
                days_until_expiry = (key_info.expires_at - datetime.now(timezone.utc)).days
                if 0 < days_until_expiry <= 7:
                    status["expiring_soon"].append({
                        "id": key_info.id,
                        "days_until_expiry": days_until_expiry,
                    })
        
        return status


def create_key_manager(
    key_dir: Path,
    password: Optional[str] = None,
    rotation_days: int = 90,
) -> KeyManager:
    """
    Create and initialize a key manager.
    
    Args:
        key_dir: Directory for key storage
        password: Optional master password
        rotation_days: Days between rotations
        
    Returns:
        Initialized KeyManager
    """
    # Derive master key from password if provided
    master_key = None
    if password:
        master_key, _ = AESEncryptor.derive_key(password)
    
    manager = KeyManager(
        key_dir=key_dir,
        master_key=master_key,
        key_rotation_days=rotation_days,
    )
    
    manager.initialize(password)
    
    return manager
