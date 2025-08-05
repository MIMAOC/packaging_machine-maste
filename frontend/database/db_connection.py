#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接管理
包装机系统数据库连接池和操作管理

作者：AI助手
创建日期：2025-08-04
"""

import pymysql
import threading
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
            self.connection_pool = []
            self.pool_lock = threading.Lock()
            self.initialized = True
            
            # 创建数据库（如果不存在）
            self._create_database_if_not_exists()
    
    def _create_database_if_not_exists(self):
        """创建数据库（如果不存在）"""
        try:
            # 连接到MySQL服务器（不指定数据库）
            connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                charset=self.config.charset
            )
            
            with connection.cursor() as cursor:
                # 创建数据库
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.config.database}` CHARACTER SET {self.config.charset} COLLATE {self.config.charset}_general_ci")
                print(f"数据库 '{self.config.database}' 已确保存在")
            
            connection.close()
            
            # 创建表结构
            self._create_tables()
            
        except Exception as e:
            print(f"创建数据库失败: {e}")
            raise
    
    def _create_tables(self):
        """创建表结构"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 创建物料表
                    create_material_table = """
                    CREATE TABLE IF NOT EXISTS `materials` (
                        `id` int(11) NOT NULL AUTO_INCREMENT,
                        `material_name` varchar(100) NOT NULL COMMENT '物料名称',
                        `ai_status` enum('未学习','已学习','已生产') NOT NULL DEFAULT '未学习' COMMENT 'AI状态',
                        `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        `is_enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用(1启用，0禁用)',
                        `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                        PRIMARY KEY (`id`),
                        UNIQUE KEY `uk_material_name` (`material_name`),
                        KEY `idx_ai_status` (`ai_status`),
                        KEY `idx_is_enabled` (`is_enabled`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='物料表';
                    """
                    cursor.execute(create_material_table)
                    
                    # 创建智能学习表
                    create_intelligent_learning_table = """
                    CREATE TABLE IF NOT EXISTS `intelligent_learning` (
                        `id` int(11) NOT NULL AUTO_INCREMENT,
                        `material_name` varchar(100) NOT NULL COMMENT '物料名称',
                        `target_weight` decimal(10,1) NOT NULL COMMENT '目标重量(g)',
                        `bucket_id` int(11) NOT NULL COMMENT '料斗编号',
                        `coarse_speed` int(11) NOT NULL COMMENT '快加速度',
                        `fine_speed` int(11) NOT NULL COMMENT '慢加速度',
                        `coarse_advance` decimal(10,1) NOT NULL COMMENT '快加提前量(g)',
                        `fall_value` decimal(10,1) NOT NULL COMMENT '落差值(g)',
                        `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                        PRIMARY KEY (`id`),
                        UNIQUE KEY `uk_material_weight_bucket` (`material_name`, `target_weight`, `bucket_id`),
                        KEY `idx_material_name` (`material_name`),
                        KEY `idx_target_weight` (`target_weight`),
                        KEY `idx_bucket_id` (`bucket_id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能学习表';
                    """
                    cursor.execute(create_intelligent_learning_table)
                    
                    # 新增：创建生产明细表
                    create_production_details_table = """
                    CREATE TABLE IF NOT EXISTS `production_details` (
                        `id` int(11) NOT NULL AUTO_INCREMENT,
                        `production_id` varchar(20) NOT NULL COMMENT '生产编号',
                        `bucket_id` int(11) NOT NULL COMMENT '料斗编号',
                        `real_weight` decimal(10,1) NOT NULL COMMENT '实时重量(g)',
                        `error_value` decimal(10,1) NOT NULL COMMENT '误差值(g)',
                        `is_qualified` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否合格(1合格，0不合格)',
                        `is_valid` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否有效(1有效，0无效)',
                        `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        PRIMARY KEY (`id`),
                        KEY `idx_production_id` (`production_id`),
                        KEY `idx_bucket_id` (`bucket_id`),
                        KEY `idx_is_valid` (`is_valid`),
                        KEY `idx_create_time` (`create_time`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生产明细表';
                    """
                    cursor.execute(create_production_details_table)
                    
                    # 新增：创建生产记录表
                    create_production_records_table = """
                    CREATE TABLE IF NOT EXISTS `production_records` (
                        `id` int(11) NOT NULL AUTO_INCREMENT,
                        `production_date` date NOT NULL COMMENT '生产日期',
                        `production_id` varchar(20) NOT NULL COMMENT '生产编号',
                        `material_name` varchar(100) NOT NULL COMMENT '物料名称',
                        `target_weight` decimal(10,1) NOT NULL COMMENT '目标重量(g)',
                        `package_quantity` int(11) NOT NULL COMMENT '包装数量',
                        `completed_packages` int(11) NOT NULL DEFAULT 0 COMMENT '完成包数',
                        `completion_rate` decimal(5,2) NOT NULL DEFAULT 0.00 COMMENT '完成率(%)',
                        `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                        PRIMARY KEY (`id`),
                        UNIQUE KEY `uk_production_id` (`production_id`),
                        KEY `idx_production_date` (`production_date`),
                        KEY `idx_material_name` (`material_name`),
                        KEY `idx_create_time` (`create_time`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生产记录表';
                    """
                    cursor.execute(create_production_records_table)
                    
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
                                "INSERT INTO materials (material_name, ai_status, is_enabled) VALUES (%s, %s, %s)",
                                (material_name, ai_status, is_enabled)
                            )
                        
                        print("默认物料数据已插入")
                    
                conn.commit()
                print("数据库表结构已创建")
                
        except Exception as e:
            print(f"创建表结构失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        connection = None
        try:
            connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset,
                autocommit=self.config.autocommit
            )
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
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
    
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
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                conn.commit()
                return affected_rows
    
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
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
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
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    if result and result[0] == 1:
                        return True, "数据库连接正常"
                    else:
                        return False, "数据库连接测试失败"
        except Exception as e:
            return False, f"数据库连接失败: {str(e)}"

# 全局数据库管理器实例
db_manager = DatabaseManager()