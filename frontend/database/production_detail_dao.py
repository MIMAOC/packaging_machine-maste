#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产明细数据访问对象
处理生产明细表的数据库操作

作者：AI助手
创建日期：2025-08-06
修复日期：2025-08-06（修复SQLite语法和datetime转换问题）
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
    real_weight: float = 0.0
    error_value: float = 0.0
    is_qualified: bool = False
    is_valid: bool = False
    create_time: Optional[datetime] = None

class ProductionDetailDAO:
    """生产明细数据访问对象"""
    
    @staticmethod
    def _parse_datetime(dt_str):
        """
        解析datetime字符串为datetime对象
        
        Args:
            dt_str: 日期时间字符串或datetime对象
            
        Returns:
            datetime对象或None
        """
        if dt_str is None:
            return None
        
        if isinstance(dt_str, datetime):
            return dt_str
        
        if isinstance(dt_str, str):
            try:
                # 尝试多种格式解析
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%d",
                    "%Y/%m/%d %H:%M:%S",
                    "%Y/%m/%d"
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(dt_str, fmt)
                    except ValueError:
                        continue
                
                # 如果所有格式都失败，返回None
                print(f"警告：无法解析日期时间字符串: {dt_str}")
                return None
                
            except Exception as e:
                print(f"解析日期时间异常: {e}")
                return None
        
        return None
    
    @staticmethod
    def create_table():
        """创建生产明细表"""
        try:
            create_sql = """
            CREATE TABLE IF NOT EXISTS production_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                production_id TEXT NOT NULL,
                bucket_id INTEGER NOT NULL,
                real_weight REAL NOT NULL,
                error_value REAL NOT NULL,
                is_qualified INTEGER NOT NULL DEFAULT 0 CHECK(is_qualified IN (0,1)),
                is_valid INTEGER NOT NULL DEFAULT 0 CHECK(is_valid IN (0,1)),
                create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """

            affected_rows = db_manager.execute_update(create_sql)

            # 创建索引
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS idx_production_details_production_id ON production_details(production_id);",
                "CREATE INDEX IF NOT EXISTS idx_production_details_bucket_id ON production_details(bucket_id);",
                "CREATE INDEX IF NOT EXISTS idx_production_details_is_valid ON production_details(is_valid);",
                "CREATE INDEX IF NOT EXISTS idx_production_details_create_time ON production_details(create_time);"
            ]

            for index_sql in index_sqls:
                db_manager.execute_update(index_sql)

            print("生产明细表已创建")
            return True

        except Exception as e:
            print(f"创建生产明细表失败: {e}")
            return False
    
    @staticmethod
    def insert_detail(production_id: str, bucket_id: int, real_weight: float, 
                     error_value: float, is_qualified: bool, is_valid: bool) -> Tuple[bool, str, int]:
        """
        插入生产明细记录
        
        Args:
            production_id: 生产编号
            bucket_id: 料斗编号
            real_weight: 实时重量
            error_value: 误差值
            is_qualified: 是否合格
            is_valid: 是否有效
            
        Returns:
            Tuple[bool, str, int]: (成功状态, 消息, 记录ID)
        """
        try:
            insert_sql = """
            INSERT INTO production_details 
            (production_id, bucket_id, real_weight, error_value, is_qualified, is_valid)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
            params = (production_id, bucket_id, real_weight, error_value, 
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
            SELECT SUM(real_weight) as total_weight, COUNT(*) as total_count
            FROM production_details 
            WHERE production_id = ? AND is_valid = 1
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
            WHERE production_id = ? AND bucket_id = ? 
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
                SUM(CASE WHEN is_valid = 1 THEN real_weight ELSE 0 END) as valid_weight_sum,
                AVG(CASE WHEN is_valid = 1 THEN real_weight ELSE NULL END) as avg_weight
            FROM production_details 
            WHERE production_id = ?
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