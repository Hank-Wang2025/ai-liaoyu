"""
设备配置加载器测试
Device Configuration Loader Tests
"""
import os
import tempfile
import pytest
from pathlib import Path

from backend.services.device_config import (
    DeviceConfigLoader,
    DeviceConfiguration,
    HeartRateConfig,
    LightsConfig,
    LightDeviceConfig,
    ChairConfig,
    ScentConfig,
    AudioConfig,
    GlobalConfig,
    DiscoveryConfig,
    get_device_config,
    reload_device_config,
    set_config_path,
)


class TestDeviceConfigLoader:
    """设备配置加载器测试"""
    
    def test_default_configuration(self):
        """测试默认配置（无配置文件时）"""
        old_env = os.environ.pop("HEALING_POD_DEVICE_CONFIG", None)
        old_cwd = os.getcwd()
        
        try:
            # 切换到临时目录，避免找到实际的配置文件
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                
                loader = DeviceConfigLoader("/nonexistent/path/config.yaml")
                config = loader.load()
                
                assert isinstance(config, DeviceConfiguration)
                assert isinstance(config.global_config, GlobalConfig)
                assert isinstance(config.heart_rate, HeartRateConfig)
                assert isinstance(config.lights, LightsConfig)
                assert isinstance(config.chair, ChairConfig)
                assert isinstance(config.scent, ScentConfig)
                assert isinstance(config.audio, AudioConfig)
                assert isinstance(config.discovery, DiscoveryConfig)
        finally:
            os.chdir(old_cwd)
            if old_env:
                os.environ["HEALING_POD_DEVICE_CONFIG"] = old_env
    
    def test_default_global_config_values(self):
        """测试默认全局配置值"""
        old_env = os.environ.pop("HEALING_POD_DEVICE_CONFIG", None)
        old_cwd = os.getcwd()
        
        try:
            # 切换到临时目录，避免找到实际的配置文件
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                
                loader = DeviceConfigLoader("/nonexistent/path/config.yaml")
                config = loader.load()
                
                assert config.global_config.connection_timeout == 10
                assert config.global_config.reconnect_interval == 30
                assert config.global_config.enable_mock_fallback is True
                assert config.global_config.log_level == "INFO"
        finally:
            os.chdir(old_cwd)
            if old_env:
                os.environ["HEALING_POD_DEVICE_CONFIG"] = old_env
    
    def test_default_heart_rate_config_values(self):
        """测试默认心率配置值"""
        # 确保环境变量不影响测试
        old_env = os.environ.pop("HEALING_POD_DEVICE_CONFIG", None)
        old_cwd = os.getcwd()
        
        try:
            # 切换到临时目录，避免找到实际的配置文件
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                
                loader = DeviceConfigLoader("/nonexistent/path/config.yaml")
                config = loader.load()
                
                assert config.heart_rate.enabled is True
                assert config.heart_rate.type == "mock"
                assert config.heart_rate.scan_timeout == 10
                assert config.heart_rate.buffer_size == 600
        finally:
            os.chdir(old_cwd)
            if old_env:
                os.environ["HEALING_POD_DEVICE_CONFIG"] = old_env
    
    def test_load_from_yaml_file(self):
        """测试从 YAML 文件加载配置"""
        yaml_content = """
global:
  connection_timeout: 15
  reconnect_interval: 45
  enable_mock_fallback: false
  log_level: DEBUG

heart_rate:
  enabled: true
  type: ble
  ble:
    device_address: "AA:BB:CC:DD:EE:FF"
    device_name_keywords:
      - "TestDevice"
    scan_timeout: 20
    buffer_size: 1000
  mock:
    base_bpm: 80
    variability: 10

lights:
  enabled: true
  devices:
    - name: test_light
      type: yeelight
      enabled: true
      config:
        ip: "192.168.1.200"
  defaults:
    brightness: 80
    transition_ms: 2000
    breath:
      min_brightness: 20
      max_brightness: 90
      period_ms: 5000

chair:
  enabled: false
  type: mock

scent:
  enabled: true
  type: wifi
  wifi:
    ip: "192.168.1.150"
    port: 8080
    api_path: "/control"

audio:
  enabled: true
  default_volume: 70
  fade_duration_ms: 3000

discovery:
  auto_discover: false
  timeout: 20
"""
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yaml', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = DeviceConfigLoader(temp_path)
            config = loader.load()
            
            # 验证全局配置
            assert config.global_config.connection_timeout == 15
            assert config.global_config.reconnect_interval == 45
            assert config.global_config.enable_mock_fallback is False
            assert config.global_config.log_level == "DEBUG"
            
            # 验证心率配置
            assert config.heart_rate.enabled is True
            assert config.heart_rate.type == "ble"
            assert config.heart_rate.device_address == "AA:BB:CC:DD:EE:FF"
            assert "TestDevice" in config.heart_rate.device_name_keywords
            assert config.heart_rate.scan_timeout == 20
            assert config.heart_rate.buffer_size == 1000
            assert config.heart_rate.mock_base_bpm == 80
            
            # 验证灯光配置
            assert config.lights.enabled is True
            assert len(config.lights.devices) == 1
            assert config.lights.devices[0].name == "test_light"
            assert config.lights.devices[0].type == "yeelight"
            assert config.lights.devices[0].config["ip"] == "192.168.1.200"
            assert config.lights.default_brightness == 80
            assert config.lights.breath_min_brightness == 20
            
            # 验证座椅配置
            assert config.chair.enabled is False
            assert config.chair.type == "mock"
            
            # 验证香薰配置
            assert config.scent.enabled is True
            assert config.scent.type == "wifi"
            assert config.scent.wifi_ip == "192.168.1.150"
            assert config.scent.wifi_port == 8080
            
            # 验证音频配置
            assert config.audio.default_volume == 70
            assert config.audio.fade_duration_ms == 3000
            
            # 验证发现配置
            assert config.discovery.auto_discover is False
            assert config.discovery.timeout == 20
            
        finally:
            os.unlink(temp_path)
    
    def test_find_config_file_with_explicit_path(self):
        """测试使用显式路径查找配置文件"""
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yaml', 
            delete=False
        ) as f:
            f.write("global:\n  log_level: INFO\n")
            temp_path = f.name
        
        try:
            loader = DeviceConfigLoader(temp_path)
            found_path = loader.find_config_file()
            assert found_path == temp_path
        finally:
            os.unlink(temp_path)
    
    def test_find_config_file_from_env(self):
        """测试从环境变量查找配置文件"""
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yaml', 
            delete=False
        ) as f:
            f.write("global:\n  log_level: DEBUG\n")
            temp_path = f.name
        
        try:
            os.environ["HEALING_POD_DEVICE_CONFIG"] = temp_path
            loader = DeviceConfigLoader()
            found_path = loader.find_config_file()
            assert found_path == temp_path
        finally:
            os.unlink(temp_path)
            del os.environ["HEALING_POD_DEVICE_CONFIG"]
    
    def test_reload_configuration(self):
        """测试重新加载配置"""
        yaml_content_v1 = "global:\n  log_level: INFO\n"
        yaml_content_v2 = "global:\n  log_level: DEBUG\n"
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yaml', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(yaml_content_v1)
            temp_path = f.name
        
        try:
            loader = DeviceConfigLoader(temp_path)
            config1 = loader.load()
            assert config1.global_config.log_level == "INFO"
            
            # 修改配置文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content_v2)
            
            # 重新加载
            config2 = loader.reload()
            assert config2.global_config.log_level == "DEBUG"
            
        finally:
            os.unlink(temp_path)
    
    def test_config_property_auto_loads(self):
        """测试 config 属性自动加载"""
        loader = DeviceConfigLoader()
        # 不调用 load()，直接访问 config 属性
        config = loader.config
        assert isinstance(config, DeviceConfiguration)
    
    def test_get_raw_config(self):
        """测试获取原始配置字典"""
        yaml_content = """
global:
  log_level: WARNING
custom_key: custom_value
"""
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yaml', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = DeviceConfigLoader(temp_path)
            loader.load()
            raw = loader.get_raw_config()
            
            assert "global" in raw
            assert raw["global"]["log_level"] == "WARNING"
            assert raw.get("custom_key") == "custom_value"
        finally:
            os.unlink(temp_path)
    
    def test_invalid_yaml_uses_defaults(self):
        """测试无效 YAML 使用默认配置"""
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yaml', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            loader = DeviceConfigLoader(temp_path)
            config = loader.load()
            # 应该返回默认配置
            assert isinstance(config, DeviceConfiguration)
        finally:
            os.unlink(temp_path)
    
    def test_empty_yaml_uses_defaults(self):
        """测试空 YAML 文件使用默认配置"""
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yaml', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write("")
            temp_path = f.name
        
        try:
            loader = DeviceConfigLoader(temp_path)
            config = loader.load()
            assert isinstance(config, DeviceConfiguration)
            # 应该使用默认值
            assert config.global_config.log_level == "INFO"
        finally:
            os.unlink(temp_path)
    
    def test_partial_config_uses_defaults_for_missing(self):
        """测试部分配置使用默认值填充缺失项"""
        yaml_content = """
heart_rate:
  enabled: false
"""
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yaml', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = DeviceConfigLoader(temp_path)
            config = loader.load()
            
            # 心率配置应该被更新
            assert config.heart_rate.enabled is False
            
            # 其他配置应该使用默认值
            assert config.global_config.log_level == "INFO"
            assert config.lights.enabled is True
            assert config.chair.enabled is True
        finally:
            os.unlink(temp_path)


class TestLightDeviceConfig:
    """灯光设备配置测试"""
    
    def test_light_device_config_creation(self):
        """测试灯光设备配置创建"""
        config = LightDeviceConfig(
            name="test_light",
            type="yeelight",
            enabled=True,
            config={"ip": "192.168.1.100"}
        )
        
        assert config.name == "test_light"
        assert config.type == "yeelight"
        assert config.enabled is True
        assert config.config["ip"] == "192.168.1.100"
    
    def test_multiple_light_devices(self):
        """测试多个灯光设备配置"""
        yaml_content = """
lights:
  enabled: true
  devices:
    - name: main_light
      type: yeelight
      enabled: true
      config:
        ip: "192.168.1.100"
    - name: ambient_light
      type: hue
      enabled: true
      config:
        bridge_ip: "192.168.1.50"
        api_key: "test-key"
        light_id: "1"
    - name: disabled_light
      type: mock
      enabled: false
"""
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yaml', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = DeviceConfigLoader(temp_path)
            config = loader.load()
            
            # 只有启用的设备会被加载
            assert len(config.lights.devices) == 2
            
            # 验证设备配置
            device_names = [d.name for d in config.lights.devices]
            assert "main_light" in device_names
            assert "ambient_light" in device_names
            assert "disabled_light" not in device_names
        finally:
            os.unlink(temp_path)


class TestGlobalConfigFunctions:
    """全局配置函数测试"""
    
    def test_get_device_config_singleton(self):
        """测试获取设备配置单例"""
        config1 = get_device_config()
        config2 = get_device_config()
        
        # 应该返回相同的配置对象
        assert config1 is config2
    
    def test_set_config_path(self):
        """测试设置配置文件路径"""
        yaml_content = "global:\n  log_level: ERROR\n"
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yaml', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            set_config_path(temp_path)
            config = get_device_config()
            assert config.global_config.log_level == "ERROR"
        finally:
            os.unlink(temp_path)
            # 重置为默认
            set_config_path(None)
