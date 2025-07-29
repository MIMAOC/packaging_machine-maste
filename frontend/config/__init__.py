# frontend/config/__init__.py
"""
配置模块包
管理前端应用的各种配置

模块列表：
- api_config: API连接配置管理
"""

__version__ = "1.5.1"
__author__ = "AI助手"

# 导入主要配置类
try:
    from .api_config import APIConfig, get_api_config, set_api_config
    
    __all__ = ['APIConfig', 'get_api_config', 'set_api_config']
    
except ImportError as e:
    print(f"警告：配置模块导入失败: {e}")
    __all__ = []