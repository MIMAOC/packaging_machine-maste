#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置文件
包装机系统SQLite数据库连接配置

作者：AI助手
创建日期：2025-08-04
更新日期：2025-08-15（优化exe兼容性）
"""

import os
import sys
import logging
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass
class DatabaseConfig:
    """数据库配置类"""
    db_path: str = "packaging_machine.db"  # SQLite数据库文件路径
    timeout: int = 30  # 连接超时时间（秒）
    check_same_thread: bool = False  # 允许多线程访问

def get_application_path():
    """
    获取应用程序所在目录的绝对路径
    兼容开发环境和打包后的exe环境
    
    Returns:
        str: 应用程序目录的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # 打包后的exe环境
        # sys.executable 指向exe文件的完整路径
        application_path = os.path.dirname(sys.executable)
        print(f"[DEBUG] 检测到打包环境，exe路径: {sys.executable}")
        print(f"[DEBUG] 应用程序目录: {application_path}")
    else:
        # 开发环境 - 获取当前脚本所在目录
        application_path = os.path.dirname(os.path.abspath(__file__))
        print(f"[DEBUG] 检测到开发环境，脚本目录: {application_path}")
    
    return application_path

def ensure_directory_exists(dir_path):
    """
    确保目录存在，如果不存在则创建
    
    Args:
        dir_path (str): 目录路径
    """
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"[INFO] 创建目录: {dir_path}")
        except Exception as e:
            print(f"[ERROR] 创建目录失败: {dir_path}, 错误: {e}")
            raise

def get_database_path(relative_db_path="data/packaging_machine.db"):
    """
    获取数据库文件的绝对路径
    数据库将存储在exe文件同目录下
    
    Args:
        relative_db_path (str): 相对数据库路径
        
    Returns:
        str: 数据库文件的绝对路径
    """
    # 获取应用程序目录
    app_path = get_application_path()
    
    # 构建数据库完整路径
    db_full_path = os.path.join(app_path, relative_db_path)
    
    # 确保数据库目录存在
    db_dir = os.path.dirname(db_full_path)
    ensure_directory_exists(db_dir)
    
    print(f"[INFO] 数据库路径: {db_full_path}")
    return db_full_path

def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径，兼容打包后的程序
    注意：这个函数用于获取程序资源文件，不是数据库文件
    
    Args:
        relative_path (str): 相对路径
        
    Returns:
        str: 资源文件的绝对路径
    """
    try:
        # PyInstaller创建的临时文件夹（用于程序资源）
        base_path = sys._MEIPASS
        print(f"[DEBUG] 使用PyInstaller临时目录: {base_path}")
    except AttributeError:
        # 开发环境 - 获取当前脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
        print(f"[DEBUG] 使用开发环境目录: {base_path}")
    
    return os.path.join(base_path, relative_path)

def get_database_config() -> DatabaseConfig:
    """
    获取数据库配置
    
    Returns:
        DatabaseConfig: 数据库配置对象
    """
    # 使用环境变量或默认的相对路径
    default_db_path = os.getenv('DB_PATH', 'data/packaging_machine.db')
    
    # 获取数据库的绝对路径（存储在exe同目录）
    db_path = get_database_path(default_db_path)
    
    return DatabaseConfig(
        db_path=db_path,
        timeout=int(os.getenv('DB_TIMEOUT', '30')),
        check_same_thread=bool(os.getenv('DB_CHECK_SAME_THREAD', 'False') == 'True')
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

def verify_database_setup():
    """
    验证数据库设置是否正确
    在程序启动时调用此函数进行检查
    """
    try:
        config = get_database_config()
        db_path = config.db_path
        
        print(f"[INFO] 数据库配置验证:")
        print(f"  - 数据库路径: {db_path}")
        print(f"  - 目录是否存在: {os.path.exists(os.path.dirname(db_path))}")
        print(f"  - 数据库文件是否存在: {os.path.exists(db_path)}")
        print(f"  - 连接超时: {config.timeout}秒")
        print(f"  - 多线程访问: {not config.check_same_thread}")
        
        # 测试目录写入权限
        test_file = os.path.join(os.path.dirname(db_path), "test_write.tmp")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print(f"  - 目录写入权限: 正常")
        except Exception as e:
            print(f"  - 目录写入权限: 异常 - {e}")
            
        return True
        
    except Exception as e:
        print(f"[ERROR] 数据库设置验证失败: {e}")
        return False

# 程序启动时的调试信息
if __name__ == "__main__":
    print("=== 数据库配置调试信息 ===")
    verify_database_setup()
    
    # 显示关键路径信息
    print(f"\n=== 路径信息 ===")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"脚本文件路径: {__file__}")
    print(f"应用程序目录: {get_application_path()}")
    
    if getattr(sys, 'frozen', False):
        print(f"exe文件路径: {sys.executable}")
        if hasattr(sys, '_MEIPASS'):
            print(f"临时资源目录: {sys._MEIPASS}")
    
    config = get_database_config()
    print(f"最终数据库路径: {config.db_path}")