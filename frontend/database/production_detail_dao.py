#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产明细数据访问对象
处理生产明细表的数据库操作

作者：AI助手
创建日期：2025-08-06
修复日期：2025-08-06（修复SQLite语法和datetime转换问题）
更新日期：2025-08-07（添加generate_production_id方法，修复insert_detail方法参数）
"""

from datetime import datetime
from typing import List, Optional, Tuple, Union
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
    def generate_production_id() -> str:
        """
        生成唯一的生产编号
        格式：P + 年月日时分 + 3位随机数
        例如：P2508071435001
        
        Returns:
            str: 生产编号
        """
        try:
            import random
            
            # 当前时间：年月日时分
            time_part = datetime.now().strftime('%y%m%d%H%M')
            
            # 3位随机数
            random_part = f"{random.randint(0, 999):03d}"
            
            production_id = f"P{time_part}{random_part}"
            
            # 检查生产编号是否已存在，如果存在则重新生成
            max_attempts = 10
            attempt = 0
            while attempt < max_attempts:
                if not ProductionDetailDAO._production_id_exists(production_id):
                    return production_id
                
                # 重新生成随机部分
                random_part = f"{random.randint(0, 999):03d}"
                production_id = f"P{time_part}{random_part}"
                attempt += 1
            
            # 如果10次尝试后仍有重复，添加更多随机数
            extra_random = f"{random.randint(0, 99):02d}"
            return f"P{time_part}{random_part}{extra_random}"
            
        except Exception as e:
            print(f"生成生产编号异常: {e}")
            # 备用方案：简单的时间戳
            return f"P{datetime.now().strftime('%y%m%d%H%M%S')}"
    
    @staticmethod
    def _production_id_exists(production_id: str) -> bool:
        """
        检查生产编号是否已存在
        
        Args:
            production_id: 生产编号
            
        Returns:
            bool: 是否存在
        """
        try:
            query_sql = "SELECT COUNT(*) as count FROM production_details WHERE production_id = ?"
            result = db_manager.execute_query(query_sql, (production_id,))
            
            if result and len(result) > 0:
                return result[0].get('count', 0) > 0
            
            return False
            
        except Exception as e:
            print(f"检查生产编号存在性异常: {e}")
            return False
    
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
    def insert_detail(detail_or_production_id: Union[ProductionDetail, str], 
                     bucket_id: Optional[int] = None, real_weight: Optional[float] = None, 
                     error_value: Optional[float] = None, is_qualified: Optional[bool] = None, 
                     is_valid: Optional[bool] = None) -> Tuple[bool, str, int]:
        """
        插入生产明细记录
        支持两种调用方式：
        1. insert_detail(production_detail_object)  # 传入ProductionDetail对象
        2. insert_detail(production_id, bucket_id, real_weight, error_value, is_qualified, is_valid)  # 传入单独参数
        
        Args:
            detail_or_production_id: ProductionDetail对象或生产编号
            bucket_id: 料斗编号（当第一个参数是字符串时使用）
            real_weight: 实时重量（当第一个参数是字符串时使用）
            error_value: 误差值（当第一个参数是字符串时使用）
            is_qualified: 是否合格（当第一个参数是字符串时使用）
            is_valid: 是否有效（当第一个参数是字符串时使用）
            
        Returns:
            Tuple[bool, str, int]: (成功状态, 消息, 记录ID)
        """
        try:
            # 判断第一个参数的类型
            if isinstance(detail_or_production_id, ProductionDetail):
                # 方式1：传入ProductionDetail对象
                detail = detail_or_production_id
                production_id = detail.production_id
                bucket_id = detail.bucket_id
                real_weight = detail.real_weight
                error_value = detail.error_value
                is_qualified = detail.is_qualified
                is_valid = detail.is_valid
            elif isinstance(detail_or_production_id, str):
                # 方式2：传入单独参数
                production_id = detail_or_production_id
                # 检查其他参数是否都提供了
                if any(param is None for param in [bucket_id, real_weight, error_value, is_qualified, is_valid]):
                    return False, "传入单独参数时，所有参数都必须提供", 0
            else:
                return False, "第一个参数必须是ProductionDetail对象或字符串", 0
            
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
    def get_valid_weight_sum_by_production(production_id: str) -> Tuple[float, int]:
        """
        获取指定生产编号的有效重量总和和有效记录数
        
        Args:
            production_id: 生产编号
            
        Returns:
            Tuple[float, int]: (有效重量总和, 有效记录数)
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
    def get_valid_weight_sum_and_count(production_id: str) -> Tuple[float, int]:
        """
        获取指定生产编号的有效重量总和和数量（兼容性方法）
        
        Args:
            production_id: 生产编号
            
        Returns:
            Tuple[float, int]: (有效重量总和, 有效数量)
        """
        return ProductionDetailDAO.get_valid_weight_sum_by_production(production_id)
    
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