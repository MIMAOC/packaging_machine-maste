__version__ = "1.5.1"
__author__ = "L&C"

try:
    from .api_config import APIConfig, get_api_config, set_api_config
    
    __all__ = ['APIConfig', 'get_api_config', 'set_api_config']
    
except ImportError as e:
    print(f"警告：配置模块导入失败: {e}")
    __all__ = []