"""
智能学习数据访问对象(DAO)

作者：C
创建日期：2025-08-06
修复日期：2025-08-19
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from database.db_connection import db_manager

@dataclass
class IntelligentLearning:
    id: Optional[int] = None
    material_name: str = ""
    target_weight: float = 0.0
    bucket_id: int = 0
    coarse_speed: int = 0
    fine_speed: int = 44
    coarse_advance: float = 0.0
    fall_value: float = 0.0
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

class IntelligentLearningDAO:
    
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
                
            except Exception:
                return None
        
        return None
    
    @staticmethod
    def save_learning_result(material_name: str, target_weight: float, bucket_id: int,
                    coarse_speed: int, fine_speed: int, coarse_advance: float, fall_value: float) -> Tuple[bool, str]:
        try:
            existing_record = IntelligentLearningDAO.get_learning_result(material_name, target_weight, bucket_id)

            if existing_record:
                update_sql = """
                UPDATE intelligent_learning 
                SET coarse_speed = ?, fine_speed = ?, coarse_advance = ?, fall_value = ?, update_time = datetime('now', 'localtime')
                WHERE material_name = ? AND target_weight = ? AND bucket_id = ?
                """
                params = (coarse_speed, fine_speed, coarse_advance, fall_value, material_name, target_weight, bucket_id)

                affected_rows = db_manager.execute_update(update_sql, params)

                if affected_rows > 0:
                    return True, f"料斗{bucket_id}学习结果已更新（覆盖历史记录）"
                else:
                    return False, f"料斗{bucket_id}学习结果更新失败"
            else:
                insert_sql = """
                INSERT INTO intelligent_learning (material_name, target_weight, bucket_id, coarse_speed, fine_speed, coarse_advance, 
                fall_value, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                """
                params = (material_name, target_weight, bucket_id, coarse_speed, fine_speed, coarse_advance, fall_value)

                affected_rows = db_manager.execute_update(insert_sql, params)

                if affected_rows > 0:
                    return True, f"料斗{bucket_id}学习结果已保存"
                else:
                    return False, f"料斗{bucket_id}学习结果保存失败"

        except Exception as e:
            error_msg = f"保存学习结果失败: {str(e)}"
            return False, error_msg
    
    @staticmethod
    def get_learning_result(material_name: str, target_weight: float, bucket_id: int) -> Optional[IntelligentLearning]:
        try:
            sql = """
            SELECT * FROM intelligent_learning 
            WHERE material_name = ? AND target_weight = ? AND bucket_id = ?
            """
            results = db_manager.execute_query(sql, (material_name, target_weight, bucket_id))
            
            if results:
                row = results[0]
                return IntelligentLearning(
                    id=row['id'],
                    material_name=row['material_name'],
                    target_weight=float(row['target_weight']),
                    bucket_id=row['bucket_id'],
                    coarse_speed=row['coarse_speed'],
                    fine_speed=row['fine_speed'],
                    coarse_advance=float(row['coarse_advance']),
                    fall_value=float(row['fall_value']),
                    create_time=IntelligentLearningDAO._parse_datetime(row['create_time']),
                    update_time=IntelligentLearningDAO._parse_datetime(row['update_time'])
                )
            
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def get_all_learning_results_by_material(material_name: str, target_weight: float) -> List[IntelligentLearning]:
        try:
            sql = """
            SELECT * FROM intelligent_learning 
            WHERE material_name = ? AND target_weight = ?
            ORDER BY bucket_id
            """
            results = db_manager.execute_query(sql, (material_name, target_weight))
            
            learning_results = []
            for row in results:
                learning_result = IntelligentLearning(
                    id=row['id'],
                    material_name=row['material_name'],
                    target_weight=float(row['target_weight']),
                    bucket_id=row['bucket_id'],
                    coarse_speed=row['coarse_speed'],
                    fine_speed=row['fine_speed'],
                    coarse_advance=float(row['coarse_advance']),
                    fall_value=float(row['fall_value']),
                    create_time=IntelligentLearningDAO._parse_datetime(row['create_time']),
                    update_time=IntelligentLearningDAO._parse_datetime(row['update_time'])
                )
                learning_results.append(learning_result)
            
            return learning_results
            
        except Exception:
            return []
    
    @staticmethod
    def has_learning_data(material_name: str, target_weight: float) -> bool:
        try:
            sql = """
            SELECT COUNT(*) as count FROM intelligent_learning 
            WHERE material_name = ? AND target_weight = ?
            """
            results = db_manager.execute_query(sql, (material_name, target_weight))
            
            if results:
                return results[0]['count'] > 0
            
            return False
            
        except Exception:
            return False
    
    @staticmethod
    def delete_learning_results(material_name: str, target_weight: float) -> Tuple[bool, str]:
        try:
            sql = "DELETE FROM intelligent_learning WHERE material_name = ? AND target_weight = ?"
            affected_rows = db_manager.execute_update(sql, (material_name, target_weight))
            
            if affected_rows > 0:
                return True, f"已删除{affected_rows}条学习记录"
            else:
                return False, "未找到匹配的学习记录"
                
        except Exception as e:
            error_msg = f"删除智能学习结果异常: {str(e)}"
            return False, error_msg