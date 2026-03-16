"""
数据加密服务
Data Encryption Service using AES-256

Requirements: 14.3 - 支持数据加密存储，使用 AES-256 加密算法
"""
import os
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from loguru import logger


class EncryptionError(Exception):
    """Encryption related errors"""
    pass


class KeyManager:
    """
    密钥管理器
    Key Manager for AES-256 encryption keys
    
    Requirements: 14.3 - 实现密钥管理
    """
    
    KEY_SIZE = 32  # 256 bits for AES-256
    KEY_FILE_NAME = ".encryption_key"
    
    def __init__(self, key_dir: Optional[Path] = None):
        """
        Initialize key manager
        
        Args:
            key_dir: Directory to store the encryption key file
        """
        if key_dir is None:
            key_dir = Path(__file__).parent.parent.parent / "config"
        self.key_dir = Path(key_dir)
        self.key_file = self.key_dir / self.KEY_FILE_NAME
        self._key: Optional[bytes] = None
    
    def _ensure_key_dir(self) -> None:
        """Ensure key directory exists"""
        self.key_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_key(self) -> bytes:
        """
        Generate a new AES-256 key
        
        Returns:
            32-byte key for AES-256
        """
        return secrets.token_bytes(self.KEY_SIZE)
    
    def save_key(self, key: bytes) -> None:
        """
        Save encryption key to file
        
        Args:
            key: The encryption key to save
        """
        self._ensure_key_dir()
        
        # Encode key as base64 for storage
        encoded_key = base64.b64encode(key).decode('utf-8')
        
        # Write to file with restricted permissions
        self.key_file.write_text(encoded_key)
        
        # Set file permissions to owner-only (Unix systems)
        try:
            os.chmod(self.key_file, 0o600)
        except (OSError, AttributeError):
            # Windows doesn't support chmod the same way
            pass
        
        logger.info(f"Encryption key saved to {self.key_file}")
    
    def load_key(self) -> bytes:
        """
        Load encryption key from file
        
        Returns:
            The encryption key
            
        Raises:
            EncryptionError: If key file doesn't exist or is invalid
        """
        if not self.key_file.exists():
            raise EncryptionError(
                f"Encryption key file not found: {self.key_file}. "
                "Call initialize_key() first."
            )
        
        try:
            encoded_key = self.key_file.read_text().strip()
            key = base64.b64decode(encoded_key)
            
            if len(key) != self.KEY_SIZE:
                raise EncryptionError(
                    f"Invalid key size: expected {self.KEY_SIZE}, got {len(key)}"
                )
            
            return key
        except Exception as e:
            raise EncryptionError(f"Failed to load encryption key: {e}")
    
    def get_key(self) -> bytes:
        """
        Get the encryption key, loading from file if necessary
        
        Returns:
            The encryption key
        """
        if self._key is None:
            self._key = self.load_key()
        return self._key
    
    def initialize_key(self, force: bool = False) -> bytes:
        """
        Initialize encryption key (generate and save if not exists)
        
        Args:
            force: If True, regenerate key even if it exists
            
        Returns:
            The encryption key
        """
        if self.key_file.exists() and not force:
            logger.info("Encryption key already exists, loading existing key")
            return self.load_key()
        
        key = self.generate_key()
        self.save_key(key)
        self._key = key
        logger.info("New encryption key generated and saved")
        return key
    
    def key_exists(self) -> bool:
        """Check if encryption key file exists"""
        return self.key_file.exists()
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """
        Derive an encryption key from a password using PBKDF2
        
        Args:
            password: The password to derive key from
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        
        # Use PBKDF2 with SHA-256
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations=100000,
            dklen=self.KEY_SIZE
        )
        
        return key, salt


class AES256Encryptor:
    """
    AES-256 加密器
    AES-256 Encryptor for sensitive data
    
    Requirements: 14.3 - 使用 AES-256 加密算法
    """
    
    BLOCK_SIZE = 16  # AES block size in bytes
    IV_SIZE = 16  # Initialization vector size
    
    def __init__(self, key: bytes):
        """
        Initialize encryptor with key
        
        Args:
            key: 32-byte AES-256 key
        """
        if len(key) != 32:
            raise EncryptionError(f"Invalid key size: expected 32, got {len(key)}")
        self._key = key
    
    def encrypt(self, plaintext: Union[str, bytes]) -> bytes:
        """
        Encrypt data using AES-256-CBC
        
        Args:
            plaintext: Data to encrypt (string or bytes)
            
        Returns:
            Encrypted data with IV prepended
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        # Generate random IV
        iv = secrets.token_bytes(self.IV_SIZE)
        
        # Pad plaintext to block size
        padder = padding.PKCS7(self.BLOCK_SIZE * 8).padder()
        padded_data = padder.update(plaintext) + padder.finalize()
        
        # Create cipher and encrypt
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # Prepend IV to ciphertext
        return iv + ciphertext
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypt data using AES-256-CBC
        
        Args:
            ciphertext: Encrypted data with IV prepended
            
        Returns:
            Decrypted data
            
        Raises:
            EncryptionError: If decryption fails
        """
        if len(ciphertext) < self.IV_SIZE + self.BLOCK_SIZE:
            raise EncryptionError("Ciphertext too short")
        
        # Extract IV and ciphertext
        iv = ciphertext[:self.IV_SIZE]
        actual_ciphertext = ciphertext[self.IV_SIZE:]
        
        try:
            # Create cipher and decrypt
            cipher = Cipher(
                algorithms.AES(self._key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(actual_ciphertext) + decryptor.finalize()
            
            # Remove padding
            unpadder = padding.PKCS7(self.BLOCK_SIZE * 8).unpadder()
            plaintext = unpadder.update(padded_data) + unpadder.finalize()
            
            return plaintext
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")
    
    def encrypt_to_base64(self, plaintext: Union[str, bytes]) -> str:
        """
        Encrypt data and return as base64 string
        
        Args:
            plaintext: Data to encrypt
            
        Returns:
            Base64-encoded encrypted data
        """
        encrypted = self.encrypt(plaintext)
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_from_base64(self, ciphertext_b64: str) -> bytes:
        """
        Decrypt base64-encoded data
        
        Args:
            ciphertext_b64: Base64-encoded encrypted data
            
        Returns:
            Decrypted data
        """
        ciphertext = base64.b64decode(ciphertext_b64)
        return self.decrypt(ciphertext)
    
    def decrypt_to_string(self, ciphertext: Union[bytes, str]) -> str:
        """
        Decrypt data and return as string
        
        Args:
            ciphertext: Encrypted data (bytes or base64 string)
            
        Returns:
            Decrypted string
        """
        if isinstance(ciphertext, str):
            plaintext = self.decrypt_from_base64(ciphertext)
        else:
            plaintext = self.decrypt(ciphertext)
        return plaintext.decode('utf-8')


class DataEncryptionService:
    """
    数据加密服务
    High-level service for encrypting sensitive data fields
    
    Requirements: 14.3 - 加密敏感数据字段
    """
    
    # Fields that should be encrypted
    SENSITIVE_FIELDS = [
        'audio_data',
        'face_data', 
        'bio_data',
        'details',
        'previous_state',
        'new_state',
        'message',
        'user_feedback'
    ]
    
    def __init__(self, key_manager: Optional[KeyManager] = None):
        """
        Initialize data encryption service
        
        Args:
            key_manager: Optional key manager instance
        """
        self.key_manager = key_manager or KeyManager()
        self._encryptor: Optional[AES256Encryptor] = None
    
    def initialize(self, force_new_key: bool = False) -> None:
        """
        Initialize the encryption service
        
        Args:
            force_new_key: If True, generate a new key even if one exists
        """
        key = self.key_manager.initialize_key(force=force_new_key)
        self._encryptor = AES256Encryptor(key)
        logger.info("Data encryption service initialized")
    
    def _get_encryptor(self) -> AES256Encryptor:
        """Get or create encryptor instance"""
        if self._encryptor is None:
            key = self.key_manager.get_key()
            self._encryptor = AES256Encryptor(key)
        return self._encryptor
    
    def encrypt_field(self, value: Optional[str]) -> Optional[str]:
        """
        Encrypt a single field value
        
        Args:
            value: The value to encrypt
            
        Returns:
            Encrypted value as base64 string, or None if input is None
        """
        if value is None:
            return None
        
        encryptor = self._get_encryptor()
        return encryptor.encrypt_to_base64(value)
    
    def decrypt_field(self, value: Optional[str]) -> Optional[str]:
        """
        Decrypt a single field value
        
        Args:
            value: The encrypted value (base64 string)
            
        Returns:
            Decrypted value, or None if input is None
        """
        if value is None:
            return None
        
        encryptor = self._get_encryptor()
        return encryptor.decrypt_to_string(value)
    
    def encrypt_sensitive_fields(self, data: dict) -> dict:
        """
        Encrypt all sensitive fields in a dictionary
        
        Args:
            data: Dictionary containing data to encrypt
            
        Returns:
            Dictionary with sensitive fields encrypted
        """
        result = data.copy()
        
        for field in self.SENSITIVE_FIELDS:
            if field in result and result[field] is not None:
                result[field] = self.encrypt_field(str(result[field]))
        
        return result
    
    def decrypt_sensitive_fields(self, data: dict) -> dict:
        """
        Decrypt all sensitive fields in a dictionary
        
        Args:
            data: Dictionary containing encrypted data
            
        Returns:
            Dictionary with sensitive fields decrypted
        """
        result = data.copy()
        
        for field in self.SENSITIVE_FIELDS:
            if field in result and result[field] is not None:
                try:
                    result[field] = self.decrypt_field(result[field])
                except EncryptionError:
                    # Field might not be encrypted (legacy data)
                    logger.warning(f"Could not decrypt field {field}, keeping original value")
        
        return result
    
    def is_initialized(self) -> bool:
        """Check if encryption service is initialized"""
        return self.key_manager.key_exists()


# Singleton instance
_encryption_service: Optional[DataEncryptionService] = None


def get_encryption_service() -> DataEncryptionService:
    """Get the singleton encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = DataEncryptionService()
    return _encryption_service


async def init_encryption() -> None:
    """Initialize the encryption service"""
    service = get_encryption_service()
    service.initialize()
    logger.info("Encryption service initialized")
