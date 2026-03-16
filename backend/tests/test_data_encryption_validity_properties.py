"""
属性测试：数据加密有效性
Property Test: Data Encryption Validity

**Feature: healing-pod-system, Property 29: 数据加密有效性**
**Validates: Requirements 14.3**

Property 29: 数据加密有效性
*For any* 存储的敏感数据，系统 SHALL 使用 AES-256 算法进行加密，
加密后的数据 SHALL 无法直接读取原文。
"""
import pytest
import tempfile
import os
import base64
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume

# 直接从模块文件导入，避免 __init__.py 导入链
import importlib.util
encryption_path = Path(__file__).parent.parent / "services" / "encryption.py"
spec = importlib.util.spec_from_file_location("encryption", encryption_path)
encryption_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(encryption_module)

KeyManager = encryption_module.KeyManager
AES256Encryptor = encryption_module.AES256Encryptor
DataEncryptionService = encryption_module.DataEncryptionService
EncryptionError = encryption_module.EncryptionError


class TestDataEncryptionValidityProperties:
    """
    属性测试：数据加密有效性
    
    **Feature: healing-pod-system, Property 29: 数据加密有效性**
    **Validates: Requirements 14.3**
    """
    
    @given(plaintext=st.text(min_size=1, max_size=1000))
    @settings(max_examples=100)
    def test_encryption_round_trip(self, plaintext):
        """
        属性测试：加密-解密往返一致性
        
        **Feature: healing-pod-system, Property 29: 数据加密有效性**
        **Validates: Requirements 14.3**
        
        *For any* 明文字符串，加密后再解密 SHALL 得到原始明文。
        这证明了加密是有效的，数据可以被正确恢复。
        """
        key = os.urandom(32)
        encryptor = AES256Encryptor(key)
        
        # 加密
        ciphertext = encryptor.encrypt(plaintext)
        
        # 解密
        decrypted = encryptor.decrypt(ciphertext)
        
        # 验证往返一致性
        assert decrypted.decode('utf-8') == plaintext, \
            "解密后的数据应与原始明文一致"
    
    @given(plaintext=st.text(min_size=1, max_size=1000))
    @settings(max_examples=100)
    def test_wrong_key_cannot_decrypt_correctly(self, plaintext):
        """
        属性测试：错误密钥无法正确解密（数据无法直接读取）
        
        **Feature: healing-pod-system, Property 29: 数据加密有效性**
        **Validates: Requirements 14.3**
        
        *For any* 加密的数据，使用错误的密钥 SHALL 无法正确解密，
        要么抛出异常，要么解密出错误的数据。
        这证明了加密后的数据无法被未授权方读取。
        """
        assume(len(plaintext) > 0)
        
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        
        # 确保两个密钥不同
        assume(key1 != key2)
        
        encryptor1 = AES256Encryptor(key1)
        encryptor2 = AES256Encryptor(key2)
        
        # 使用 key1 加密
        ciphertext = encryptor1.encrypt(plaintext)
        
        # 使用 key2 尝试解密
        # 应该要么抛出异常，要么解密出错误的数据
        try:
            decrypted = encryptor2.decrypt(ciphertext)
            # 如果没有抛出异常，解密的数据应该与原文不同
            decrypted_str = decrypted.decode('utf-8', errors='replace')
            assert decrypted_str != plaintext, \
                "使用错误密钥不应该解密出正确的原文"
        except EncryptionError:
            # 预期的行为：解密失败
            pass
    
    @given(plaintext=st.text(min_size=1, max_size=1000))
    @settings(max_examples=100)
    def test_aes_256_key_size_enforced(self, plaintext):
        """
        属性测试：强制使用 AES-256 密钥大小
        
        **Feature: healing-pod-system, Property 29: 数据加密有效性**
        **Validates: Requirements 14.3**
        
        *For any* 加密操作，密钥大小 SHALL 为 256 位（32 字节）。
        非 256 位密钥应被拒绝。
        """
        # 验证只有 32 字节密钥才能创建加密器
        valid_key = os.urandom(32)
        encryptor = AES256Encryptor(valid_key)
        
        # 验证加密器可以正常工作
        ciphertext = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(ciphertext)
        assert decrypted.decode('utf-8') == plaintext
        
        # 验证非 32 字节密钥会被拒绝
        invalid_keys = [
            os.urandom(16),  # 128 bits - AES-128
            os.urandom(24),  # 192 bits - AES-192
            os.urandom(31),  # 太短
            os.urandom(33),  # 太长
        ]
        
        for invalid_key in invalid_keys:
            with pytest.raises(EncryptionError):
                AES256Encryptor(invalid_key)
    
    @given(plaintext=st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_ciphertext_differs_from_plaintext(self, plaintext):
        """
        属性测试：密文与明文不同
        
        **Feature: healing-pod-system, Property 29: 数据加密有效性**
        **Validates: Requirements 14.3**
        
        *For any* 非空明文，加密后的密文 SHALL 与原始明文字节不同。
        """
        assume(len(plaintext) > 0)
        
        key = os.urandom(32)
        encryptor = AES256Encryptor(key)
        
        plaintext_bytes = plaintext.encode('utf-8')
        ciphertext = encryptor.encrypt(plaintext)
        
        # 密文应该与明文不同
        assert ciphertext != plaintext_bytes, \
            "加密后的密文应与原始明文字节不同"
    
    @given(plaintext=st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_ciphertext_randomness_with_iv(self, plaintext):
        """
        属性测试：密文随机性（IV 随机化）
        
        **Feature: healing-pod-system, Property 29: 数据加密有效性**
        **Validates: Requirements 14.3**
        
        *For any* 明文，多次加密 SHALL 产生不同的密文（由于随机 IV），
        这增强了安全性，防止模式分析攻击。
        """
        assume(len(plaintext) > 0)
        
        key = os.urandom(32)
        encryptor = AES256Encryptor(key)
        
        # 同一明文加密两次
        ciphertext1 = encryptor.encrypt(plaintext)
        ciphertext2 = encryptor.encrypt(plaintext)
        
        # 验证：两次加密产生不同的密文
        assert ciphertext1 != ciphertext2, \
            "同一明文的多次加密应产生不同的密文（随机 IV）"
        
        # 验证：两次加密都能正确解密
        assert encryptor.decrypt(ciphertext1).decode('utf-8') == plaintext
        assert encryptor.decrypt(ciphertext2).decode('utf-8') == plaintext
    
    @given(
        field_value=st.text(min_size=1, max_size=500),
        field_name=st.sampled_from([
            'audio_data', 'face_data', 'bio_data', 
            'details', 'message', 'user_feedback'
        ])
    )
    @settings(max_examples=100)
    def test_sensitive_field_encryption_and_decryption(self, field_value, field_name):
        """
        属性测试：敏感字段加密和解密
        
        **Feature: healing-pod-system, Property 29: 数据加密有效性**
        **Validates: Requirements 14.3**
        
        *For any* 敏感字段值，加密后 SHALL 与原值不同，
        且解密后 SHALL 恢复原值。
        """
        assume(len(field_value.strip()) > 0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KeyManager(key_dir=Path(tmpdir))
            service = DataEncryptionService(key_manager=km)
            service.initialize()
            
            # 创建包含敏感字段的数据
            data = {
                "id": "test_123",
                field_name: field_value
            }
            
            # 加密敏感字段
            encrypted_data = service.encrypt_sensitive_fields(data)
            
            # 验证：加密后的字段值不等于原始值
            assert encrypted_data[field_name] != field_value, \
                f"敏感字段 {field_name} 应该被加密"
            
            # 验证：可以正确解密
            decrypted_data = service.decrypt_sensitive_fields(encrypted_data)
            assert decrypted_data[field_name] == field_value, \
                f"解密后的 {field_name} 应与原始值一致"
    
    @given(plaintext=st.binary(min_size=1, max_size=1000))
    @settings(max_examples=100)
    def test_binary_data_encryption_round_trip(self, plaintext):
        """
        属性测试：二进制数据加密往返
        
        **Feature: healing-pod-system, Property 29: 数据加密有效性**
        **Validates: Requirements 14.3**
        
        *For any* 二进制数据，加密后解密 SHALL 恢复原始数据。
        """
        key = os.urandom(32)
        encryptor = AES256Encryptor(key)
        
        # 加密二进制数据
        ciphertext = encryptor.encrypt(plaintext)
        
        # 验证：密文与明文不同
        assert ciphertext != plaintext, \
            "加密后的数据应与原始数据不同"
        
        # 验证：可以正确解密
        decrypted = encryptor.decrypt(ciphertext)
        assert decrypted == plaintext, \
            "解密后的数据应与原始二进制数据一致"
    
    @given(plaintext=st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_tampered_ciphertext_fails_decryption(self, plaintext):
        """
        属性测试：篡改的密文无法解密
        
        **Feature: healing-pod-system, Property 29: 数据加密有效性**
        **Validates: Requirements 14.3**
        
        *For any* 加密的数据，如果密文被篡改，解密 SHALL 失败。
        这证明了数据完整性保护。
        """
        assume(len(plaintext) > 0)
        
        key = os.urandom(32)
        encryptor = AES256Encryptor(key)
        
        ciphertext = encryptor.encrypt(plaintext)
        
        # 篡改密文（修改中间的一个字节）
        tampered = bytearray(ciphertext)
        mid_point = len(tampered) // 2
        tampered[mid_point] = (tampered[mid_point] + 1) % 256
        tampered = bytes(tampered)
        
        # 篡改后的密文应该无法正确解密
        # 可能抛出异常或解密出错误的数据
        try:
            decrypted = encryptor.decrypt(tampered)
            # 如果没有抛出异常，解密的数据应该与原文不同
            assert decrypted.decode('utf-8', errors='replace') != plaintext, \
                "篡改后的密文不应解密出原始明文"
        except EncryptionError:
            # 预期的行为：解密失败
            pass
    
    @given(plaintext=st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_base64_encoding_round_trip(self, plaintext):
        """
        属性测试：Base64 编码往返
        
        **Feature: healing-pod-system, Property 29: 数据加密有效性**
        **Validates: Requirements 14.3**
        
        *For any* 明文，Base64 编码的加密数据解密后 SHALL 恢复原文。
        """
        key = os.urandom(32)
        encryptor = AES256Encryptor(key)
        
        # 加密并转为 Base64
        encrypted_b64 = encryptor.encrypt_to_base64(plaintext)
        
        # 验证是有效的 Base64 字符串
        assert isinstance(encrypted_b64, str)
        try:
            base64.b64decode(encrypted_b64)
        except Exception:
            pytest.fail("加密结果应该是有效的 Base64 字符串")
        
        # 验证可以正确解密
        decrypted = encryptor.decrypt_to_string(encrypted_b64)
        assert decrypted == plaintext, \
            "Base64 解密后应恢复原始明文"
