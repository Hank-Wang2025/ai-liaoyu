"""
Tests for encryption service
测试加密服务

Requirements: 14.3 - 支持数据加密存储，使用 AES-256 加密算法
"""
import pytest
import tempfile
import os
import sys
from pathlib import Path

# Import directly from the module file to avoid __init__.py import chain
import importlib.util
encryption_path = Path(__file__).parent.parent / "services" / "encryption.py"
spec = importlib.util.spec_from_file_location("encryption", encryption_path)
encryption_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(encryption_module)

KeyManager = encryption_module.KeyManager
AES256Encryptor = encryption_module.AES256Encryptor
DataEncryptionService = encryption_module.DataEncryptionService
EncryptionError = encryption_module.EncryptionError


class TestKeyManager:
    """Tests for KeyManager"""
    
    def test_generate_key_length(self):
        """Test that generated key is 32 bytes (256 bits)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            key = km.generate_key()
            assert len(key) == 32
    
    def test_generate_key_randomness(self):
        """Test that generated keys are unique"""
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            key1 = km.generate_key()
            key2 = km.generate_key()
            assert key1 != key2
    
    def test_save_and_load_key(self):
        """Test saving and loading encryption key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            original_key = km.generate_key()
            km.save_key(original_key)
            
            loaded_key = km.load_key()
            assert loaded_key == original_key
    
    def test_initialize_key_creates_new(self):
        """Test initialize_key creates new key when none exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            assert not km.key_exists()
            
            key = km.initialize_key()
            assert len(key) == 32
            assert km.key_exists()
    
    def test_initialize_key_loads_existing(self):
        """Test initialize_key loads existing key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            original_key = km.initialize_key()
            
            # Create new manager instance
            km2 = KeyManager(key_dir=Path(tmpdir))
            loaded_key = km2.initialize_key()
            
            assert loaded_key == original_key
    
    def test_initialize_key_force_regenerate(self):
        """Test initialize_key with force=True regenerates key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            original_key = km.initialize_key()
            new_key = km.initialize_key(force=True)
            
            assert new_key != original_key
    
    def test_load_key_not_found(self):
        """Test load_key raises error when key file doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            with pytest.raises(EncryptionError):
                km.load_key()
    
    def test_derive_key_from_password(self):
        """Test password-based key derivation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            password = "test_password_123"
            
            key1, salt1 = km.derive_key_from_password(password)
            assert len(key1) == 32
            assert len(salt1) == 16
            
            # Same password and salt should produce same key
            key2, _ = km.derive_key_from_password(password, salt1)
            assert key1 == key2
            
            # Different salt should produce different key
            key3, salt3 = km.derive_key_from_password(password)
            assert key1 != key3


class TestAES256Encryptor:
    """Tests for AES256Encryptor"""
    
    @pytest.fixture
    def encryptor(self):
        """Create encryptor with test key"""
        key = os.urandom(32)
        return AES256Encryptor(key)
    
    def test_invalid_key_size(self):
        """Test that invalid key size raises error"""
        with pytest.raises(EncryptionError):
            AES256Encryptor(b"short_key")
    
    def test_encrypt_decrypt_string(self, encryptor):
        """Test encrypting and decrypting a string"""
        plaintext = "Hello, World! 你好世界"
        
        ciphertext = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(ciphertext)
        
        assert decrypted.decode('utf-8') == plaintext
    
    def test_encrypt_decrypt_bytes(self, encryptor):
        """Test encrypting and decrypting bytes"""
        plaintext = b"\x00\x01\x02\x03\x04\x05"
        
        ciphertext = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(ciphertext)
        
        assert decrypted == plaintext
    
    def test_encrypt_produces_different_ciphertext(self, encryptor):
        """Test that same plaintext produces different ciphertext (due to random IV)"""
        plaintext = "Same message"
        
        ciphertext1 = encryptor.encrypt(plaintext)
        ciphertext2 = encryptor.encrypt(plaintext)
        
        assert ciphertext1 != ciphertext2
    
    def test_encrypt_to_base64(self, encryptor):
        """Test base64 encoding of encrypted data"""
        plaintext = "Test message"
        
        encrypted_b64 = encryptor.encrypt_to_base64(plaintext)
        assert isinstance(encrypted_b64, str)
        
        decrypted = encryptor.decrypt_from_base64(encrypted_b64)
        assert decrypted.decode('utf-8') == plaintext
    
    def test_decrypt_to_string(self, encryptor):
        """Test decrypting directly to string"""
        plaintext = "Test message 测试"
        
        encrypted_b64 = encryptor.encrypt_to_base64(plaintext)
        decrypted = encryptor.decrypt_to_string(encrypted_b64)
        
        assert decrypted == plaintext
    
    def test_decrypt_invalid_ciphertext(self, encryptor):
        """Test that invalid ciphertext raises error"""
        with pytest.raises(EncryptionError):
            encryptor.decrypt(b"too_short")
    
    def test_decrypt_wrong_key(self):
        """Test that decryption with wrong key fails"""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        
        encryptor1 = AES256Encryptor(key1)
        encryptor2 = AES256Encryptor(key2)
        
        plaintext = "Secret message"
        ciphertext = encryptor1.encrypt(plaintext)
        
        with pytest.raises(EncryptionError):
            encryptor2.decrypt(ciphertext)
    
    def test_empty_string(self, encryptor):
        """Test encrypting empty string"""
        plaintext = ""
        
        ciphertext = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(ciphertext)
        
        assert decrypted.decode('utf-8') == plaintext
    
    def test_large_data(self, encryptor):
        """Test encrypting large data"""
        plaintext = "A" * 100000  # 100KB of data
        
        ciphertext = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(ciphertext)
        
        assert decrypted.decode('utf-8') == plaintext


class TestDataEncryptionService:
    """Tests for DataEncryptionService"""
    
    @pytest.fixture
    def service(self):
        """Create encryption service with temp directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            svc = DataEncryptionService(key_manager=km)
            svc.initialize()
            yield svc
    
    def test_encrypt_decrypt_field(self, service):
        """Test encrypting and decrypting a single field"""
        original = "sensitive data 敏感数据"
        
        encrypted = service.encrypt_field(original)
        assert encrypted != original
        
        decrypted = service.decrypt_field(encrypted)
        assert decrypted == original
    
    def test_encrypt_none_field(self, service):
        """Test that None values are preserved"""
        assert service.encrypt_field(None) is None
        assert service.decrypt_field(None) is None
    
    def test_encrypt_sensitive_fields(self, service):
        """Test encrypting sensitive fields in a dictionary"""
        data = {
            "id": "session_123",
            "audio_data": '{"emotion": "happy"}',
            "face_data": '{"expression": "smile"}',
            "bio_data": '{"heart_rate": 72}',
            "non_sensitive": "public info"
        }
        
        encrypted = service.encrypt_sensitive_fields(data)
        
        # Non-sensitive fields should be unchanged
        assert encrypted["id"] == data["id"]
        assert encrypted["non_sensitive"] == data["non_sensitive"]
        
        # Sensitive fields should be encrypted
        assert encrypted["audio_data"] != data["audio_data"]
        assert encrypted["face_data"] != data["face_data"]
        assert encrypted["bio_data"] != data["bio_data"]
    
    def test_decrypt_sensitive_fields(self, service):
        """Test decrypting sensitive fields in a dictionary"""
        original_data = {
            "id": "session_123",
            "audio_data": '{"emotion": "happy"}',
            "face_data": '{"expression": "smile"}',
            "bio_data": '{"heart_rate": 72}',
            "non_sensitive": "public info"
        }
        
        encrypted = service.encrypt_sensitive_fields(original_data)
        decrypted = service.decrypt_sensitive_fields(encrypted)
        
        assert decrypted == original_data
    
    def test_is_initialized(self):
        """Test is_initialized check"""
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            svc = DataEncryptionService(key_manager=km)
            
            assert not svc.is_initialized()
            svc.initialize()
            assert svc.is_initialized()
    
    def test_encrypted_data_not_readable(self, service):
        """
        Test that encrypted data cannot be read directly
        Requirements: 14.3 - 加密后的数据 SHALL 无法直接读取原文
        """
        original = "This is sensitive information"
        encrypted = service.encrypt_field(original)
        
        # Encrypted data should not contain the original text
        assert original not in encrypted
        
        # Encrypted data should be base64 encoded
        import base64
        try:
            decoded = base64.b64decode(encrypted)
            # Decoded bytes should not be readable as the original text
            assert original.encode('utf-8') not in decoded
        except Exception:
            pass  # If decoding fails, that's also fine
