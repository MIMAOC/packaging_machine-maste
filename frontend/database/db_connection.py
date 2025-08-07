#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接管理
包装机系统SQLite数据库连接和操作管理

作者：AI助手
创建日期：2025-08-04
更新日期：2025-08-06（改为SQLite）
"""

import sqlite3
import threading
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple
from database.db_config import get_database_config, DatabaseConfig

class DatabaseManager:
    """数据库管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化数据库管理器"""
        if not hasattr(self, 'initialized'):
            self.config = get_database_config()
            self.initialized = True
            
            # 确保数据目录存在
            self._ensure_data_directory()
            
            # 创建数据库文件和表结构（如果不存在）
            self._create_database_and_tables()
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        try:
            db_dir = os.path.dirname(self.config.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                print(f"数据目录 '{db_dir}' 已创建")
        except Exception as e:
            print(f"创建数据目录失败: {e}")
            raise
    
    def _create_database_and_tables(self):
        """创建数据库文件和表结构"""
        try:
            # 创建表结构
            self._create_tables()
            print(f"SQLite数据库 '{self.config.db_path}' 已初始化")
            
        except Exception as e:
            print(f"创建数据库失败: {e}")
            raise
    
    def _create_tables(self):
        """创建表结构"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建物料表
                create_material_table = """
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_name TEXT NOT NULL UNIQUE,
                    ai_status TEXT NOT NULL DEFAULT '未学习' CHECK(ai_status IN ('未学习','已学习','已生产')),
                    create_time DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK(is_enabled IN (0,1)),
                    update_time DATETIME NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
                """
                cursor.execute(create_material_table)
                
                # 创建物料表索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_ai_status ON materials(ai_status);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_is_enabled ON materials(is_enabled);")
                
                # 创建智能学习表
                create_intelligent_learning_table = """
                CREATE TABLE IF NOT EXISTS intelligent_learning (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_name TEXT NOT NULL,
                    target_weight REAL NOT NULL,
                    bucket_id INTEGER NOT NULL,
                    coarse_speed INTEGER NOT NULL,
                    fine_speed INTEGER NOT NULL,
                    coarse_advance REAL NOT NULL,
                    fall_value REAL NOT NULL,
                    create_time DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                    update_time DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                    UNIQUE(material_name, target_weight, bucket_id)
                );
                """
                cursor.execute(create_intelligent_learning_table)
                
                # 创建智能学习表索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_intelligent_learning_material_name ON intelligent_learning(material_name);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_intelligent_learning_target_weight ON intelligent_learning(target_weight);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_intelligent_learning_bucket_id ON intelligent_learning(bucket_id);")
                
                # 创建生产明细表
                create_production_details_table = """
                CREATE TABLE IF NOT EXISTS production_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    production_id TEXT NOT NULL,
                    bucket_id INTEGER NOT NULL,
                    real_weight REAL NOT NULL,
                    error_value REAL NOT NULL,
                    is_qualified INTEGER NOT NULL DEFAULT 1 CHECK(is_qualified IN (0,1)),
                    is_valid INTEGER NOT NULL DEFAULT 1 CHECK(is_valid IN (0,1)),
                    create_time DATETIME NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
                """
                cursor.execute(create_production_details_table)
                
                # 创建生产明细表索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_details_production_id ON production_details(production_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_details_bucket_id ON production_details(bucket_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_details_is_valid ON production_details(is_valid);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_details_create_time ON production_details(create_time);")
                
                # 创建生产记录表
                create_production_records_table = """
                CREATE TABLE IF NOT EXISTS production_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    production_date DATE NOT NULL,
                    production_id TEXT NOT NULL UNIQUE,
                    material_name TEXT NOT NULL,
                    target_weight REAL NOT NULL,
                    package_quantity INTEGER NOT NULL,
                    completed_packages INTEGER NOT NULL DEFAULT 0,
                    completion_rate REAL NOT NULL DEFAULT 0.00,
                    create_time DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                    update_time DATETIME NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
                """
                cursor.execute(create_production_records_table)
                
                # 创建生产记录表索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_records_production_date ON production_records(production_date);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_records_material_name ON production_records(material_name);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_production_records_create_time ON production_records(create_time);")
                
                # 创建更新时间触发器
                self._create_update_triggers(cursor)
                
                # 插入默认数据（如果表为空）
                cursor.execute("SELECT COUNT(*) FROM materials")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    default_materials = [
                        ("大米 - 密度1.2g/cm³", "未学习", 1),
                        ("小麦 - 密度1.4g/cm³", "未学习", 1),
                        ("玉米 - 密度1.3g/cm³", "未学习", 1),
                        ("黄豆 - 密度1.1g/cm³", "未学习", 1),
                        ("绿豆 - 密度1.2g/cm³", "未学习", 1),
                        ("红豆 - 密度1.15g/cm³", "未学习", 1)
                    ]
                    
                    for material_name, ai_status, is_enabled in default_materials:
                        cursor.execute(
                            "INSERT INTO materials (material_name, ai_status, is_enabled) VALUES (?, ?, ?)",
                            (material_name, ai_status, is_enabled)
                        )
                    
                    print("默认物料数据已插入")
                
                # 创建生产记录详情视图
                create_production_detail_view = """
                CREATE VIEW IF NOT EXISTS production_record_detail_view AS
                SELECT 
                    pr.production_id,
                    pr.material_name,
                    pr.target_weight,
                    pr.package_quantity,
                    pr.completed_packages,
                    pr.completion_rate,
                    pr.production_date,
                    pr.create_time,
                    pr.update_time,
                    -- 合格统计
                    COUNT(CASE WHEN pd.is_qualified = 1 AND pd.is_valid = 1 THEN 1 END) as qualified_count,
                    MIN(CASE WHEN pd.is_qualified = 1 AND pd.is_valid = 1 THEN pd.real_weight END) as qualified_min_weight,
                    MAX(CASE WHEN pd.is_qualified = 1 AND pd.is_valid = 1 THEN pd.real_weight END) as qualified_max_weight,
                    -- 不合格统计
                    COUNT(CASE WHEN pd.is_qualified = 0 AND pd.is_valid = 1 THEN 1 END) as unqualified_count,
                    MIN(CASE WHEN pd.is_qualified = 0 AND pd.is_valid = 1 THEN pd.real_weight END) as unqualified_min_weight,
                    MAX(CASE WHEN pd.is_qualified = 0 AND pd.is_valid = 1 THEN pd.real_weight END) as unqualified_max_weight
                FROM production_records pr
                LEFT JOIN production_details pd ON pr.production_id = pd.production_id
                GROUP BY pr.production_id, pr.material_name, pr.target_weight, pr.package_quantity, 
                         pr.completed_packages, pr.completion_rate, pr.production_date, pr.create_time, pr.update_time
                """
                cursor.execute(create_production_detail_view)

                print("数据库视图已创建")
                
                conn.commit()
                print("数据库表结构已创建")
                
        except Exception as e:
            print(f"创建表结构失败: {e}")
            raise
    
    def _create_update_triggers(self, cursor):
        """创建更新时间触发器"""
        try:
            # 物料表更新触发器
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_materials_timestamp 
                AFTER UPDATE ON materials
                BEGIN
                    UPDATE materials SET update_time = (datetime('now', 'localtime')) WHERE id = NEW.id;
                END;
            """)
            
            # 智能学习表更新触发器
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_intelligent_learning_timestamp 
                AFTER UPDATE ON intelligent_learning
                BEGIN
                    UPDATE intelligent_learning SET update_time = (datetime('now', 'localtime')) WHERE id = NEW.id;
                END;
            """)
            
            # 生产记录表更新触发器
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_production_records_timestamp 
                AFTER UPDATE ON production_records
                BEGIN
                    UPDATE production_records SET update_time = (datetime('now', 'localtime')) WHERE id = NEW.id;
                END;
            """)
            
        except Exception as e:
            print(f"创建触发器失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        connection = None
        try:
            connection = sqlite3.connect(
                self.config.db_path,
                timeout=self.config.timeout,
                check_same_thread=self.config.check_same_thread
            )
            # 启用外键约束
            connection.execute("PRAGMA foreign_keys = ON")
            # 设置行工厂以返回字典
            connection.row_factory = sqlite3.Row
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                connection.close()
    
    def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        执行查询语句
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            # 将sqlite3.Row对象转换为字典
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, sql: str, params: Optional[Tuple] = None) -> int:
        """
        执行更新语句
        
        Args:
            sql: SQL更新语句
            params: 更新参数
            
        Returns:
            int: 受影响的行数
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            conn.commit()
            return cursor.rowcount
    
    def execute_insert(self, sql: str, params: Optional[Tuple] = None) -> int:
        """
        执行插入语句
        
        Args:
            sql: SQL插入语句
            params: 插入参数
            
        Returns:
            int: 新插入记录的ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            conn.commit()
            return cursor.lastrowid
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        测试数据库连接
        
        Returns:
            Tuple[bool, str]: (连接状态, 消息)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    return True, "SQLite数据库连接正常"
                else:
                    return False, "SQLite数据库连接测试失败"
        except Exception as e:
            return False, f"SQLite数据库连接失败: {str(e)}"

# 全局数据库管理器实例
db_manager = DatabaseManager()