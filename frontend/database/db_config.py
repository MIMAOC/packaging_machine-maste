"""
数据库配置文件

作者：C
创建日期：2025-08-04
更新日期：2025-08-19
"""

import os
import sys
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass
class DatabaseConfig:
    db_path: str = "packaging_machine.db"
    timeout: int = 30
    check_same_thread: bool = False

def get_application_path():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    return application_path

def ensure_directory_exists(dir_path):
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            raise

def get_database_path(relative_db_path="data/packaging_machine.db"):
    app_path = get_application_path()
    
    db_full_path = os.path.join(app_path, relative_db_path)
    
    db_dir = os.path.dirname(db_full_path)
    ensure_directory_exists(db_dir)
    
    return db_full_path

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

def get_database_config() -> DatabaseConfig:
    default_db_path = os.getenv('DB_PATH', 'data/packaging_machine.db')
    
    db_path = get_database_path(default_db_path)
    
    return DatabaseConfig(
        db_path=db_path,
        timeout=int(os.getenv('DB_TIMEOUT', '30')),
        check_same_thread=bool(os.getenv('DB_CHECK_SAME_THREAD', 'False') == 'True')
    )

def get_connection_string(config: Optional[DatabaseConfig] = None) -> str:
    if config is None:
        config = get_database_config()
    
    return config.db_path

def verify_database_setup():
    try:
        config = get_database_config()
        db_path = config.db_path
        
        if not os.path.exists(os.path.dirname(db_path)):
            return False
            
        test_file = os.path.join(os.path.dirname(db_path), "test_write.tmp")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception:
            return False
            
        return True
        
    except Exception:
        return False