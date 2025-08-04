#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置文件
包装机系统数据库连接配置

作者：AI助手
创建日期：2025-08-04
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """数据库配置类"""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "1234"
    database: str = "packaging_machine"
    charset: str = "utf8mb4"
    autocommit: bool = True
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

def get_database_config() -> DatabaseConfig:
    """python init_database.py
    获取数据库配置
    
    Returns:
        DatabaseConfig: 数据库配置对象
    """
    return DatabaseConfig(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', '1234'),  # 建议通过环境变量设置
        database=os.getenv('DB_DATABASE', 'packaging_machine'),
        charset=os.getenv('DB_CHARSET', 'utf8mb4'),
        autocommit=bool(os.getenv('DB_AUTOCOMMIT', 'True')),
        pool_size=int(os.getenv('DB_POOL_SIZE', '5')),
        max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '10')),
        pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30'))
    )

def get_connection_string(config: Optional[DatabaseConfig] = None) -> str:
    """
    获取数据库连接字符串
    
    Args:
        config: 数据库配置对象，如果为None则使用默认配置
        
    Returns:
        str: 数据库连接字符串
    """
    if config is None:
        config = get_database_config()
    
    return f"mysql+pymysql://{config.user}:{config.password}@{config.host}:{config.port}/{config.database}?charset={config.charset}"