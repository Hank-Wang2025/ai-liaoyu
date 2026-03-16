"""
设备管理器模块测试
Device Manager Module Tests

测试硬件设备扫描、自动连接和连接状态监控功能
"""
import asyncio
import pytest
from datetime import datetime

from services.device_manager import (
    DeviceType,
    ConnectionStatus,
    ConnectionProtocol,
    DeviceInfo,
    ConnectionMonitor,
    HardwareDeviceManager,
    init_device_manager,
    get_device_manager,
    cleanup_device_manager
)


# ============== Test Fixtures ==============

@pytest.fixture
def device_info():
    """创建测试设备信息"""
    return DeviceInfo(
        device_id="test_device_001",
        device_type=DeviceType.LIGHT,
        name="Test Light",
        protocol=ConnectionProtocol.WIFI,
        address="192.168.1.100"
    )


@pytest.fixture
def connection_monitor():
    """创建连接监控器"""
    return ConnectionMonitor(check_interval=1.0, max_reconnect_attempts=2)


@pytest.fixture
def device_manager():
    """创建设备管理器"""
    return HardwareDeviceManager()


# ============== DeviceInfo Tests ==============

class TestDeviceInfo:
    """DeviceInfo 测试"""
    
    def test_initial_state(self, device_info):
        """测试初始状态"""
        assert device_info.device_id == "test_device_001"
        assert device_info.device_type == DeviceType.LIGHT
        assert device_info.status == ConnectionStatus.DISCONNECTED
        assert device_info.error_message is None
    
    def test_to_dict(self, device_info):
        """测试转换为字典"""
        data = device_info.to_dict()
        
        assert data["device_id"] == "test_device_001"
        assert data["device_type"] == "light"
        assert data["protocol"] == "wifi"
        assert data["status"] == "disconnected"
    
    def test_with_metadata(self):
        """测试带元数据的设备信息"""
        device = DeviceInfo(
            device_id="test_001",
            device_type=DeviceType.AUDIO,
            name="Test Audio",
            protocol=ConnectionProtocol.USB,
            metadata={"channels": 2, "sample_rate": 44100}
        )
        
        assert device.metadata["channels"] == 2
        assert device.metadata["sample_rate"] == 44100


# ============== ConnectionMonitor Tests ==============

class TestConnectionMonitor:
    """ConnectionMonitor 测试"""
    
    @pytest.mark.asyncio
    async def test_register_and_connect_device(self, connection_monitor, device_info):
        """测试注册和连接设备"""
        connected = False
        
        async def mock_connect():
            nonlocal connected
            connected = True
            return True
        
        connection_monitor.register_device(device_info, mock_connect)
        
        result = await connection_monitor.connect_device(device_info.device_id)
        
        assert result is True
        assert connected is True
        
        status = connection_monitor.get_device_status(device_info.device_id)
        assert status.status == ConnectionStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_connection_failure(self, connection_monitor, device_info):
        """测试连接失败"""
        async def mock_connect():
            return False
        
        connection_monitor.register_device(device_info, mock_connect)
        
        result = await connection_monitor.connect_device(device_info.device_id)
        
        assert result is False
        
        status = connection_monitor.get_device_status(device_info.device_id)
        assert status.status == ConnectionStatus.ERROR
    
    @pytest.mark.asyncio
    async def test_connection_exception(self, connection_monitor, device_info):
        """测试连接异常"""
        async def mock_connect():
            raise RuntimeError("Connection error")
        
        connection_monitor.register_device(device_info, mock_connect)
        
        result = await connection_monitor.connect_device(device_info.device_id)
        
        assert result is False
        
        status = connection_monitor.get_device_status(device_info.device_id)
        assert status.status == ConnectionStatus.ERROR
        assert "Connection error" in status.error_message
    
    @pytest.mark.asyncio
    async def test_disconnect_device(self, connection_monitor, device_info):
        """测试断开设备连接"""
        disconnected = False
        
        async def mock_connect():
            return True
        
        async def mock_disconnect():
            nonlocal disconnected
            disconnected = True
        
        connection_monitor.register_device(device_info, mock_connect, mock_disconnect)
        
        await connection_monitor.connect_device(device_info.device_id)
        await connection_monitor.disconnect_device(device_info.device_id)
        
        assert disconnected is True
        
        status = connection_monitor.get_device_status(device_info.device_id)
        assert status.status == ConnectionStatus.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_connect_all_devices(self, connection_monitor):
        """测试连接所有设备"""
        devices = [
            DeviceInfo(
                device_id=f"device_{i}",
                device_type=DeviceType.LIGHT,
                name=f"Device {i}",
                protocol=ConnectionProtocol.WIFI
            )
            for i in range(3)
        ]
        
        async def mock_connect():
            return True
        
        for device in devices:
            connection_monitor.register_device(device, mock_connect)
        
        results = await connection_monitor.connect_all()
        
        assert len(results) == 3
        assert all(results.values())
    
    @pytest.mark.asyncio
    async def test_status_callback(self, connection_monitor, device_info):
        """测试状态变化回调"""
        status_changes = []
        
        def callback(device_id, status):
            status_changes.append((device_id, status))
        
        connection_monitor.register_status_callback(callback)
        
        async def mock_connect():
            return True
        
        connection_monitor.register_device(device_info, mock_connect)
        await connection_monitor.connect_device(device_info.device_id)
        
        # 应该有 CONNECTING 和 CONNECTED 两个状态变化
        assert len(status_changes) >= 2
        assert any(s == ConnectionStatus.CONNECTING for _, s in status_changes)
        assert any(s == ConnectionStatus.CONNECTED for _, s in status_changes)
    
    @pytest.mark.asyncio
    async def test_get_connected_devices(self, connection_monitor):
        """测试获取已连接设备列表"""
        device1 = DeviceInfo(
            device_id="device_1",
            device_type=DeviceType.LIGHT,
            name="Device 1",
            protocol=ConnectionProtocol.WIFI
        )
        device2 = DeviceInfo(
            device_id="device_2",
            device_type=DeviceType.AUDIO,
            name="Device 2",
            protocol=ConnectionProtocol.USB
        )
        
        async def success_connect():
            return True
        
        async def fail_connect():
            return False
        
        connection_monitor.register_device(device1, success_connect)
        connection_monitor.register_device(device2, fail_connect)
        
        await connection_monitor.connect_all()
        
        connected = connection_monitor.get_connected_devices()
        
        assert len(connected) == 1
        assert connected[0].device_id == "device_1"
    
    @pytest.mark.asyncio
    async def test_status_summary(self, connection_monitor):
        """测试状态摘要"""
        device1 = DeviceInfo(
            device_id="device_1",
            device_type=DeviceType.LIGHT,
            name="Device 1",
            protocol=ConnectionProtocol.WIFI
        )
        device2 = DeviceInfo(
            device_id="device_2",
            device_type=DeviceType.AUDIO,
            name="Device 2",
            protocol=ConnectionProtocol.USB
        )
        
        async def success_connect():
            return True
        
        async def fail_connect():
            return False
        
        connection_monitor.register_device(device1, success_connect)
        connection_monitor.register_device(device2, fail_connect)
        
        await connection_monitor.connect_all()
        
        summary = connection_monitor.get_status_summary()
        
        assert summary["total"] == 2
        assert summary["connected"] == 1
        assert summary["error"] == 1


# ============== HardwareDeviceManager Tests ==============

class TestHardwareDeviceManager:
    """HardwareDeviceManager 测试"""
    
    @pytest.mark.asyncio
    async def test_register_device_controller(self, device_manager):
        """测试注册设备控制器"""
        device_info = DeviceInfo(
            device_id="light_001",
            device_type=DeviceType.LIGHT,
            name="Test Light",
            protocol=ConnectionProtocol.WIFI
        )
        
        # 先添加到发现的设备中
        device_manager._discovered_devices[device_info.device_id] = device_info
        
        mock_controller = object()
        
        async def mock_connect():
            return True
        
        device_manager.register_device_controller(
            device_info.device_id,
            mock_controller,
            mock_connect
        )
        
        controller = device_manager.get_device_controller(device_info.device_id)
        assert controller is mock_controller
    
    @pytest.mark.asyncio
    async def test_get_connection_status(self, device_manager):
        """测试获取连接状态"""
        status = device_manager.get_connection_status()
        
        assert "total" in status
        assert "connected" in status
        assert "devices" in status


# ============== Global Instance Tests ==============

class TestGlobalInstance:
    """全局实例测试"""
    
    @pytest.mark.asyncio
    async def test_init_and_get_device_manager(self):
        """测试初始化和获取设备管理器"""
        await cleanup_device_manager()
        
        manager = init_device_manager()
        assert manager is not None
        
        same_manager = get_device_manager()
        assert same_manager is manager
        
        await cleanup_device_manager()
