"""
应用启动降级测试
"""
import importlib
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_app_imports_with_core_routes_available():
    """即使可选模块导入失败，核心应用也应可导入并暴露基础路由。"""
    main = importlib.import_module("main")

    route_paths = {route.path for route in main.app.routes}

    assert "/" in route_paths
    assert "/health" in route_paths
    assert any(path.startswith("/api/admin") for path in route_paths)


def test_app_registers_business_routers():
    """模型层存在时，主要业务路由应全部注册。"""
    main = importlib.import_module("main")

    route_paths = {route.path for route in main.app.routes}

    assert any(path.startswith("/api/emotion") for path in route_paths)
    assert any(path.startswith("/api/therapy") for path in route_paths)
    assert any(path.startswith("/api/session") for path in route_paths)
    assert any(path.startswith("/api/community") for path in route_paths)
