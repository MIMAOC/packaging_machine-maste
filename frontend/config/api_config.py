# config/api_config.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API配置模块 - 前端版本
管理后端API服务的连接配置

作者：AI助手
创建日期：2025-07-23
更新日期：2025-07-24（添加自适应学习阶段分析端点）
"""

import json
import os
from typing import Dict, Any

class APIConfig:
    """API配置类"""
    
    def __init__(self, host: str = "localhost", port: int = 8080, 
                 timeout: int = 10, protocol: str = "http"):
        """
        初始化API配置
        
        Args:
            host (str): API服务器主机地址
            port (int): API服务器端口
            timeout (int): 请求超时时间（秒）
            protocol (str): 协议类型（http/https）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.protocol = protocol
        
        # API端点配置
        self.endpoints = {
            "health": "/api/health",
            "weight_analyze": "/api/weight/analyze",
            "weight_rules": "/api/weight/rules",
            "coarse_time_analyze": "/api/coarse_time/analyze",
            "flight_material_analyze": "/api/flight_material/analyze",
            "fine_time_analyze": "/api/fine_time/analyze",
            "adaptive_learning_analyze": "/api/adaptive_learning/analyze"  # 新增自适应学习分析端点
        }
    
    @property
    def base_url(self) -> str:
        """获取基础URL"""
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def get_endpoint_url(self, endpoint_name: str) -> str:
        """
        获取完整的端点URL
        
        Args:
            endpoint_name (str): 端点名称
            
        Returns:
            str: 完整的端点URL
        """
        if endpoint_name not in self.endpoints:
            raise ValueError(f"未知的端点: {endpoint_name}")
        
        return f"{self.base_url}{self.endpoints[endpoint_name]}"
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return {
            "host": self.host,
            "port": self.port,
            "timeout": self.timeout,
            "protocol": self.protocol,
            "base_url": self.base_url,
            "endpoints": self.endpoints
        }

# 全局配置实例
_global_config = APIConfig()

def get_api_config() -> APIConfig:
    """
    获取全局API配置实例
    
    Returns:
        APIConfig: API配置实例
    """
    return _global_config

def set_api_config(host: str, port: int, timeout: int = 10, protocol: str = "http") -> None:
    """
    设置全局API配置
    
    Args:
        host (str): API服务器主机地址
        port (int): API服务器端口
        timeout (int): 请求超时时间（秒）
        protocol (str): 协议类型（http/https）
    """
    global _global_config
    _global_config = APIConfig(host, port, timeout, protocol)

def load_config_from_file(config_file: str = "config.json") -> None:
    """
    从配置文件加载API配置
    
    Args:
        config_file (str): 配置文件路径
    """
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            api_config = config_data.get('api', {})
            set_api_config(
                host=api_config.get('host', 'localhost'),
                port=api_config.get('port', 8080),
                timeout=api_config.get('timeout', 10),
                protocol=api_config.get('protocol', 'http')
            )
    except Exception as e:
        print(f"加载配置文件失败: {e}，使用默认配置")

def save_config_to_file(config_file: str = "config.json") -> None:
    """
    保存API配置到文件
    
    Args:
        config_file (str): 配置文件路径
    """
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

# 程序启动时自动加载配置
load_config_from_file()