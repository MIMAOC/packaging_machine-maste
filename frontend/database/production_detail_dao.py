"""
生产明细数据访问对象

作者：C
创建日期：2025-08-06
更新日期：2025-08-19
"""

from datetime import datetime
from typing import List, Optional, Tuple, Union
from dataclasses import dataclass
from database.db_connection import db_manager

@dataclass
class ProductionDetail:
    id: Optional[int] = None
    production_id: str = ""
    bucket_id: int = 0
    real_weight: float = 0.0
    error_value: float = 0.0
    is_qualified: bool = False
    is_valid: bool = False
    create_time: Optional[datetime] = None

class ProductionDetailDAO:
    
    @staticmethod
    def generate_production_id() -> str:
        try:
            import random
            
            time_part = datetime.now().strftime('%y%m%d%H%M')
            
            random_part = f"{random.randint(0, 999):03d}"
            
            production_id = f"P{time_part}{random_part}"
            
            max_attempts = 10
            attempt = 0
            while attempt < max_attempts:
                if not ProductionDetailDAO._production_id_exists(production_id):
                    return production_id
                
                random_part = f"{random.randint(0, 999):03d}"
                production_id = f"P{time_part}{random_part}"
                attempt += 1
            
            extra_random = f"{random.randint(0, 99):02d}"
            return f"P{time_part}{random_part}{extra_random}"
            
        except Exception as e:
            return f"P{datetime.now().strftime('%y%m%d%H%M%S')}"
    
    @staticmethod
    def _production_id_exists(production_id: str) -> bool:
        try:
            query_sql = "SELECT COUNT(*) as count FROM production_details WHERE production_id = ?"
            result = db_manager.execute_query(query_sql, (production_id,))
            
            if result and len(result) > 0:
                return result[0].get('count', 0) > 0
            
            return False
            
        except Exception as e:
            return False
    
    @staticmethod
    def _parse_datetime(dt_str):
        if dt_str is None:
            return None
        
        if isinstance(dt_str, datetime):
            return dt_str
        
        if isinstance(dt_str, str):
            try:
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
                return None
                
            except Exception as e:
                return None
        
        return None
    
    @staticmethod
    def create_table():
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
                create_time DATETIME NOT NULL DEFAULT (datetime('now', 'localtime'))
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

            return True

        except Exception as e:
            return False
    
    @staticmethod
    def insert_detail(detail_or_production_id: Union[ProductionDetail, str], 
                     bucket_id: Optional[int] = None, real_weight: Optional[float] = None, 
                     error_value: Optional[float] = None, is_qualified: Optional[bool] = None, 
                     is_valid: Optional[bool] = None) -> Tuple[bool, str, int]:
        try:
            if isinstance(detail_or_production_id, ProductionDetail):
                detail = detail_or_production_id
                production_id = detail.production_id
                bucket_id = detail.bucket_id
                real_weight = detail.real_weight
                error_value = detail.error_value
                is_qualified = detail.is_qualified
                is_valid = detail.is_valid
            elif isinstance(detail_or_production_id, str):
                production_id = detail_or_production_id
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
            return 0.0, 0
    
    @staticmethod
    def get_valid_weight_sum_and_count(production_id: str) -> Tuple[float, int]:
        return ProductionDetailDAO.get_valid_weight_sum_by_production(production_id)
    
    @staticmethod
    def get_bucket_consecutive_unqualified_count(production_id: str, bucket_id: int) -> int:
        try:
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
                if record.get('is_qualified', 1) == 0:
                    consecutive_count += 1
                else:
                    break
            
            return consecutive_count
                
        except Exception as e:
            return 0

    @staticmethod  
    def get_production_statistics(production_id: str) -> dict:
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
            return {
                'total_records': 0,
                'valid_count': 0,
                'qualified_count': 0,
                'valid_weight_sum': 0.0,
                'avg_weight': 0.0
            }