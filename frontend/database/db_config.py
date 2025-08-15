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
import sys
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """数据库配置类"""
    db_path: str = "packaging_machine.db"  # SQLite数据库文件路径
    timeout: int = 30  # 连接超时时间（秒）
    check_same_thread: bool = False  # 允许多线程访问
    
def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容打包后的程序"""
    try:
        # PyInstaller创建的临时文件夹
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境 - 获取当前脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

def get_database_config() -> DatabaseConfig:
    """
    获取数据库配置
    
    Returns:
        DatabaseConfig: 数据库配置对象
    """
    # 使用环境变量或默认的相对路径
    default_db_path = os.getenv('DB_PATH', 'data/packaging_machine.db')
    
    # 获取正确的绝对路径
    db_path = get_resource_path(default_db_path)
    
    return DatabaseConfig(
        db_path=db_path,
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