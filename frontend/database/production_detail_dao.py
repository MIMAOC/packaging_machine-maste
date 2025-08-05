#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产明细数据访问对象
处理生产明细表的数据库操作

作者：AI助手
创建日期：2025-08-06
"""

from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import dataclass
from database.db_connection import db_manager

@dataclass
class ProductionDetail:
    """生产明细数据类"""
    id: Optional[int] = None
    production_id: str = ""
    bucket_id: int = 0
    actual_weight: float = 0.0
    error_value: float = 0.0
    is_qualified: bool = False
    is_valid: bool = False
    create_time: Optional[datetime] = None

class ProductionDetailDAO:
    """生产明细数据访问对象"""
    
    @staticmethod
    def create_table():
        """创建生产明细表"""
        try:
            create_sql = """
            CREATE TABLE IF NOT EXISTS `production_details` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `production_id` varchar(20) NOT NULL COMMENT '生产编号',
                `bucket_id` int(11) NOT NULL COMMENT '料斗编号',
                `actual_weight` decimal(10,1) NOT NULL COMMENT '实时重量(g)',
                `error_value` decimal(10,1) NOT NOT COMMENT '误差值(g)',
                `is_qualified` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否合格(1合格，0不合格)',
                `is_valid` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否有效(1有效，0无效)',
                `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                PRIMARY KEY (`id`),
                KEY `idx_production_id` (`production_id`),
                KEY `idx_bucket_id` (`bucket_id`),
                KEY `idx_is_valid` (`is_valid`),
                KEY `idx_create_time` (`create_time`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生产明细表';
            """
            
            affected_rows = db_manager.execute_update(create_sql)
            print("生产明细表已创建")
            return True
            
        except Exception as e:
            print(f"创建生产明细表失败: {e}")
            return False
    
    @staticmethod
    def insert_detail(production_id: str, bucket_id: int, actual_weight: float, 
                     error_value: float, is_qualified: bool, is_valid: bool) -> Tuple[bool, str, int]:
        """
        插入生产明细记录
        
        Args:
            production_id: 生产编号
            bucket_id: 料斗编号
            actual_weight: 实时重量
            error_value: 误差值
            is_qualified: 是否合格
            is_valid: 是否有效
            
        Returns:
            Tuple[bool, str, int]: (成功状态, 消息, 记录ID)
        """
        try:
            insert_sql = """
            INSERT INTO production_details 
            (production_id, bucket_id, actual_weight, error_value, is_qualified, is_valid)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            params = (production_id, bucket_id, actual_weight, error_value, 
                     1 if is_qualified else 0, 1 if is_valid else 0)
            
            record_id = db_manager.execute_insert(insert_sql, params)
            
            if record_id > 0:
                return True, f"生产明细记录插入成功，ID: {record_id}", record_id
            else:
                return False, "生产明细记录插入失败", 0
                
        except Exception as e:
            return False, f"插入生产明细记录异常: {str(e)}", 0
    
    @staticmethod
    def get_valid_weight_sum_and_count(production_id: str) -> Tuple[float, int]:
        """
        获取指定生产编号的有效重量总和和数量
        
        Args:
            production_id: 生产编号
            
        Returns:
            Tuple[float, int]: (有效重量总和, 有效数量)
        """
        try:
            query_sql = """
            SELECT SUM(actual_weight) as total_weight, COUNT(*) as total_count
            FROM production_details 
            WHERE production_id = %s AND is_valid = 1
            """
            
            result = db_manager.execute_query(query_sql, (production_id,))
            
            if result and len(result) > 0:
                total_weight = result[0].get('total_weight', 0.0) or 0.0
                total_count = result[0].get('total_count', 0) or 0
                return total_weight, total_count
            else:
                return 0.0, 0
                
        except Exception as e:
            print(f"获取有效重量统计异常: {e}")
            return 0.0, 0
    
    @staticmethod
    def get_bucket_consecutive_unqualified_count(production_id: str, bucket_id: int) -> int:
        """
        获取指定料斗在当前生产中的连续不合格次数
        
        Args:
            production_id: 生产编号
            bucket_id: 料斗编号
            
        Returns:
            int: 连续不合格次数
        """
        try:
            # 获取该料斗最近的记录，按时间倒序
            query_sql = """
            SELECT is_qualified, is_valid
            FROM production_details 
            WHERE production_id = %s AND bucket_id = %s 
            ORDER BY create_time DESC
            LIMIT 10
            """
            
            result = db_manager.execute_query(query_sql, (production_id, bucket_id))
            
            consecutive_count = 0
            for record in result:
                if record.get('is_qualified', 1) == 0:  # 不合格
                    consecutive_count += 1
                else:  # 合格，终止计数
                    break
            
            return consecutive_count
                
        except Exception as e:
            print(f"获取连续不合格次数异常: {e}")
            return 0

    @staticmethod  
    def get_production_statistics(production_id: str) -> dict:
        """
        获取生产统计信息
        
        Args:
            production_id: 生产编号
            
        Returns:
            dict: 统计信息
        """
        try:
            query_sql = """
            SELECT 
                COUNT(*) as total_records,
                SUM(CASE WHEN is_valid = 1 THEN 1 ELSE 0 END) as valid_count,
                SUM(CASE WHEN is_qualified = 1 THEN 1 ELSE 0 END) as qualified_count,
                SUM(CASE WHEN is_valid = 1 THEN actual_weight ELSE 0 END) as valid_weight_sum,
                AVG(CASE WHEN is_valid = 1 THEN actual_weight ELSE NULL END) as avg_weight
            FROM production_details 
            WHERE production_id = %s
            """
            
            result = db_manager.execute_query(query_sql, (production_id,))
            
            if result and len(result) > 0:
                data = result[0]
                return {
                    'total_records': data.get('total_records', 0),
                    'valid_count': data.get('valid_count', 0), 
                    'qualified_count': data.get('qualified_count', 0),
                    'valid_weight_sum': data.get('valid_weight_sum', 0.0) or 0.0,
                    'avg_weight': data.get('avg_weight', 0.0) or 0.0
                }
            else:
                return {
                    'total_records': 0,
                    'valid_count': 0,
                    'qualified_count': 0, 
                    'valid_weight_sum': 0.0,
                    'avg_weight': 0.0
                }
                
        except Exception as e:
            print(f"获取生产统计信息异常: {e}")
            return {
                'total_records': 0,
                'valid_count': 0,
                'qualified_count': 0,
                'valid_weight_sum': 0.0,
                'avg_weight': 0.0
            }