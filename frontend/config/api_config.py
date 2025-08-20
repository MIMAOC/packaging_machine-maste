"""
API配置模块

作者：C
创建日期：2025-07-23
更新日期：2025-08-19
"""

import json
import os
from typing import Dict, Any

class APIConfig:
    
    def __init__(self, host: str = "xiaoajia.cn", port: int = 8443, 
                 timeout: int = 10, protocol: str = "https"):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.protocol = protocol
        
        self.endpoints = {
            "health": "/api/health",
            "weight_analyze": "/api/weight/analyze",
            "weight_rules": "/api/weight/rules",
            "coarse_time_analyze": "/api/coarse_time/analyze",
            "flight_material_analyze": "/api/flight_material/analyze",
            "fine_time_analyze": "/api/fine_time/analyze",
            "adaptive_learning_analyze": "/api/adaptive_learning/analyze"
        }
    
    @property
    def base_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def get_endpoint_url(self, endpoint_name: str) -> str:
        if endpoint_name not in self.endpoints:
            raise ValueError(f"未知的端点: {endpoint_name}")
        
        return f"{self.base_url}{self.endpoints[endpoint_name]}"
    
    def get_config_dict(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "timeout": self.timeout,
            "protocol": self.protocol,
            "base_url": self.base_url,
            "endpoints": self.endpoints
        }

_global_config = APIConfig()

def get_api_config() -> APIConfig:
    return _global_config

def set_api_config(host: str, port: int, timeout: int = 10, protocol: str = "https") -> None:
    global _global_config
    _global_config = APIConfig(host, port, timeout, protocol)

def load_config_from_file(config_file: str = "config.json") -> None:
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            api_config = config_data.get('api', {})
            set_api_config(
                host=api_config.get('host', 'xiaoajia.cn'),
                port=api_config.get('port', 8443),
                timeout=api_config.get('timeout', 10),
                protocol=api_config.get('protocol', 'https')
            )
    except Exception as e:
        print(f"加载配置文件失败: {e}，使用默认配置")

def save_config_to_file(config_file: str = "config.json") -> None:
    try:
        config_data = {
            "api": {
                "host": _global_config.host,
                "port": _global_config.port,
                "timeout": _global_config.timeout,
                "protocol": _global_config.protocol
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
            
    except Exception as e:
        print(f"保存配置文件失败: {e}")

load_config_from_file()