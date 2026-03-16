"""
管理后台权限控制属性测试
Admin Backend Permission Control Property Tests

**Feature: healing-pod-system, Property 31: 管理后台权限控制**
**Validates: Requirements 15.6**

Property 31: 管理后台权限控制
*For any* 未经授权的访问请求，管理后台 SHALL 拒绝访问并返回认证错误。
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from fastapi.testclient import TestClient
from fastapi import FastAPI
import hashlib
import jwt
from datetime import datetime, timedelta
import string

# 导入被测试的模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.admin import (
    router,
    JWT_SECRET,
    JWT_ALGORITHM,
    create_access_token,
    verify_token,
    AdminRole,
    ADMIN_USERS
)


# 创建测试应用
app = FastAPI()
app.include_router(router, prefix="/api/admin")
client = TestClient(app)


# 需要认证的端点列表
PROTECTED_ENDPOINTS = [
    ("GET", "/api/admin/devices"),
    ("GET", "/api/admin/stats"),
    ("GET", "/api/admin/logs"),
    ("GET", "/api/admin/config/plans"),
    ("GET", "/api/admin/config/devices"),
    ("GET", "/api/admin/config/content"),
    ("GET", "/api/admin/sessions"),
    ("POST", "/api/admin/logout"),
    ("GET", "/api/admin/verify"),
]

# 需要特定角色的端点
ROLE_PROTECTED_ENDPOINTS = [
    # (method, endpoint, allowed_roles)
    ("POST", "/api/admin/config/plans", [AdminRole.SUPER_ADMIN, AdminRole.ADMIN]),
    ("PUT", "/api/admin/config/plans/test-plan", [AdminRole.SUPER_ADMIN, AdminRole.ADMIN]),
    ("DELETE", "/api/admin/config/plans/test-plan", [AdminRole.SUPER_ADMIN]),
    ("PUT", "/api/admin/config/devices", [AdminRole.SUPER_ADMIN, AdminRole.ADMIN]),
]


class TestAdminPermissionControlProperties:
    """
    管理后台权限控制属性测试类
    
    **Feature: healing-pod-system, Property 31: 管理后台权限控制**
    **Validates: Requirements 15.6**
    """
    
    @given(st.sampled_from(PROTECTED_ENDPOINTS))
    @settings(max_examples=100)
    def test_unauthenticated_access_rejected(self, endpoint_info):
        """
        属性测试：未认证请求应被拒绝
        
        **Feature: healing-pod-system, Property 31: 管理后台权限控制**
        **Validates: Requirements 15.6**
        
        *For any* 受保护的端点，未携带认证 token 的请求 SHALL 返回 401 状态码
        """
        method, endpoint = endpoint_info
        
        # 发送无认证请求
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json={})
        elif method == "PUT":
            response = client.put(endpoint, json={})
        elif method == "DELETE":
            response = client.delete(endpoint)
        else:
            pytest.fail(f"Unsupported method: {method}")
        
        # 验证返回 401 未授权错误
        assert response.status_code == 401, \
            f"Expected 401 for unauthenticated {method} {endpoint}, got {response.status_code}"
        
        # 验证响应包含认证错误信息
        response_data = response.json()
        assert "detail" in response_data, \
            f"Response should contain 'detail' field for {method} {endpoint}"
    
    @given(st.text(alphabet=string.ascii_letters + string.digits + "_-.", min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_invalid_token_rejected(self, invalid_token):
        """
        属性测试：无效 token 应被拒绝
        
        **Feature: healing-pod-system, Property 31: 管理后台权限控制**
        **Validates: Requirements 15.6**
        
        *For any* 无效的 token 字符串，请求 SHALL 返回 401 状态码
        """
        # 跳过空字符串（已在其他测试中覆盖）
        assume(len(invalid_token.strip()) > 0)
        
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        # 测试一个受保护的端点
        response = client.get("/api/admin/devices", headers=headers)
        
        # 验证返回 401 未授权错误
        assert response.status_code == 401, \
            f"Expected 401 for invalid token, got {response.status_code}"
    
    @given(st.integers(min_value=1, max_value=24))
    @settings(max_examples=100)
    def test_expired_token_rejected(self, hours_expired):
        """
        属性测试：过期 token 应被拒绝
        
        **Feature: healing-pod-system, Property 31: 管理后台权限控制**
        **Validates: Requirements 15.6**
        
        *For any* 已过期的 token，请求 SHALL 返回 401 状态码
        """
        # 创建一个已过期的 token
        expire = datetime.utcnow() - timedelta(hours=hours_expired)
        payload = {
            "sub": "admin",
            "role": AdminRole.SUPER_ADMIN,
            "exp": expire,
            "iat": datetime.utcnow() - timedelta(hours=hours_expired + 1),
            "type": "access"
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        # 测试受保护的端点
        response = client.get("/api/admin/devices", headers=headers)
        
        # 验证返回 401 未授权错误
        assert response.status_code == 401, \
            f"Expected 401 for expired token, got {response.status_code}"
    
    @given(st.text(alphabet=string.ascii_letters + string.digits, min_size=10, max_size=50))
    @settings(max_examples=100)
    def test_wrong_secret_token_rejected(self, wrong_secret):
        """
        属性测试：使用错误密钥签名的 token 应被拒绝
        
        **Feature: healing-pod-system, Property 31: 管理后台权限控制**
        **Validates: Requirements 15.6**
        
        *For any* 使用错误密钥签名的 token，请求 SHALL 返回 401 状态码
        """
        # 确保使用的密钥与正确密钥不同
        assume(wrong_secret != JWT_SECRET)
        
        # 使用错误密钥创建 token
        expire = datetime.utcnow() + timedelta(hours=24)
        payload = {
            "sub": "admin",
            "role": AdminRole.SUPER_ADMIN,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        wrong_token = jwt.encode(payload, wrong_secret, algorithm=JWT_ALGORITHM)
        
        headers = {"Authorization": f"Bearer {wrong_token}"}
        
        # 测试受保护的端点
        response = client.get("/api/admin/devices", headers=headers)
        
        # 验证返回 401 未授权错误
        assert response.status_code == 401, \
            f"Expected 401 for token with wrong secret, got {response.status_code}"
    
    @given(
        st.text(min_size=1, max_size=20),
        st.text(min_size=1, max_size=20)
    )
    @settings(max_examples=100)
    def test_invalid_credentials_rejected(self, username, password):
        """
        属性测试：无效凭据登录应被拒绝
        
        **Feature: healing-pod-system, Property 31: 管理后台权限控制**
        **Validates: Requirements 15.6**
        
        *For any* 无效的用户名/密码组合，登录请求 SHALL 返回 401 状态码
        """
        # 跳过有效的凭据组合
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user = ADMIN_USERS.get(username)
        if user is not None and password_hash == user["password_hash"]:
            assume(False)  # 跳过有效凭据
        
        # 尝试登录
        response = client.post(
            "/api/admin/login",
            json={"username": username, "password": password}
        )
        
        # 验证返回 401 未授权错误
        assert response.status_code == 401, \
            f"Expected 401 for invalid credentials, got {response.status_code}"
    
    @given(st.sampled_from([AdminRole.OPERATOR]))
    @settings(max_examples=50)
    def test_insufficient_role_rejected(self, role):
        """
        属性测试：权限不足的角色应被拒绝访问特定端点
        
        **Feature: healing-pod-system, Property 31: 管理后台权限控制**
        **Validates: Requirements 15.6**
        
        *For any* 权限不足的角色，访问需要更高权限的端点 SHALL 返回 403 状态码
        """
        # 创建一个 operator 角色的 token
        token = create_access_token("test_operator", role)
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试需要 admin 或 super_admin 权限的端点
        # POST /config/plans 需要 admin 或 super_admin 权限
        response = client.post(
            "/api/admin/config/plans",
            headers=headers,
            json={
                "id": "test-plan",
                "name": "Test Plan",
                "target_emotions": ["anxious"],
                "intensity": "low",
                "style": "modern",
                "duration": 600
            }
        )
        
        # operator 角色应该被拒绝
        assert response.status_code == 403, \
            f"Expected 403 for operator role on admin endpoint, got {response.status_code}"
    
    @given(st.sampled_from([AdminRole.ADMIN, AdminRole.OPERATOR]))
    @settings(max_examples=50)
    def test_delete_requires_super_admin(self, role):
        """
        属性测试：删除操作需要超级管理员权限
        
        **Feature: healing-pod-system, Property 31: 管理后台权限控制**
        **Validates: Requirements 15.6**
        
        *For any* 非超级管理员角色，删除疗愈方案 SHALL 返回 403 状态码
        """
        # 创建一个非超级管理员的 token
        token = create_access_token("test_user", role)
        headers = {"Authorization": f"Bearer {token}"}
        
        # 尝试删除疗愈方案
        response = client.delete(
            "/api/admin/config/plans/test-plan",
            headers=headers
        )
        
        # 非超级管理员应该被拒绝
        assert response.status_code == 403, \
            f"Expected 403 for {role} role on delete endpoint, got {response.status_code}"


class TestValidAuthenticationAccess:
    """
    验证有效认证可以访问的测试
    
    这些测试确保权限控制不会错误地拒绝有效请求
    """
    
    def test_valid_token_accepted(self):
        """
        测试：有效 token 应被接受
        """
        # 创建有效 token
        token = create_access_token("admin", AdminRole.SUPER_ADMIN)
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试受保护的端点
        response = client.get("/api/admin/devices", headers=headers)
        
        # 验证请求成功
        assert response.status_code == 200, \
            f"Expected 200 for valid token, got {response.status_code}"
    
    def test_valid_login_returns_token(self):
        """
        测试：有效凭据登录应返回 token
        """
        response = client.post(
            "/api/admin/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_super_admin_can_delete(self):
        """
        测试：超级管理员可以执行删除操作（权限检查通过）
        """
        # 创建超级管理员 token
        token = create_access_token("admin", AdminRole.SUPER_ADMIN)
        headers = {"Authorization": f"Bearer {token}"}
        
        # 尝试删除（即使方案不存在或数据库未初始化，也应该通过权限检查）
        # 权限检查在数据库操作之前，所以如果返回 403 表示权限不足
        # 返回 404、500 或 200 都表示权限检查已通过
        response = client.delete(
            "/api/admin/config/plans/non-existent-plan",
            headers=headers
        )
        
        # 超级管理员应该通过权限检查
        # 403 表示权限不足，其他状态码表示权限检查已通过
        assert response.status_code != 403, \
            f"Super admin should pass permission check, got 403 Forbidden"


class TestTokenVerification:
    """
    Token 验证功能测试
    """
    
    @given(st.text(alphabet=string.ascii_letters + string.digits + "_-", min_size=1, max_size=30))
    @settings(max_examples=50)
    def test_verify_token_returns_none_for_invalid(self, invalid_token):
        """
        属性测试：verify_token 对无效 token 返回 None
        
        **Feature: healing-pod-system, Property 31: 管理后台权限控制**
        **Validates: Requirements 15.6**
        """
        result = verify_token(invalid_token)
        assert result is None, "verify_token should return None for invalid token"
    
    def test_verify_token_returns_payload_for_valid(self):
        """
        测试：verify_token 对有效 token 返回 payload
        """
        token = create_access_token("admin", AdminRole.SUPER_ADMIN)
        result = verify_token(token)
        
        assert result is not None
        assert result["sub"] == "admin"
        assert result["role"] == AdminRole.SUPER_ADMIN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
