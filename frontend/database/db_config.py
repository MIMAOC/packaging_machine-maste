#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置文件
包装机系统SQLite数据库连接配置

作者：AI助手
创建日期：2025-08-04
更新日期：2025-08-06（改为SQLite）
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """数据库配置类"""
    db_path: str = "packaging_machine.db"  # SQLite数据库文件路径
    timeout: int = 30  # 连接超时时间（秒）
    check_same_thread: bool = False  # 允许多线程访问

def get_database_config() -> DatabaseConfig:
    """
    获取数据库配置
    
    Returns:
        DatabaseConfig: 数据库配置对象
    """
    return DatabaseConfig(
        db_path=os.getenv('DB_PATH', 'data/packaging_machine.db'),
        timeout=int(os.getenv('DB_TIMEOUT', '30')),
        check_same_thread=bool(os.getenv('DB_CHECK_SAME_THREAD', 'False'))
    )

def get_connection_string(config: Optional[DatabaseConfig] = None) -> str:
    """
    获取数据库连接字符串
    
    Args:
        config: 数据库配置对象，如果为None则使用默认配置
        
    Returns:
        str: 数据库文件路径
    """
    if config is None:
        config = get_database_config()
    
    return config.db_path