"""
物料数据访问对象(DAO)

作者：C
创建日期：2025-08-04
修复日期：2025-08-19
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from database.db_connection import db_manager

@dataclass
class Material:
    id: Optional[int] = None
    material_name: str = ""
    ai_status: str = "未学习"  # 未学习、已学习、已生产
    create_time: Optional[datetime] = None
    is_enabled: int = 1  # 1启用，0禁用
    update_time: Optional[datetime] = None

class MaterialDAO:
    
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
    def get_all_materials(enabled_only: bool = True) -> List[Material]:
        try:
            sql = "SELECT * FROM materials"
            params = None
            
            if enabled_only:
                sql += " WHERE is_enabled = ?"
                params = (1,)
            
            sql += " ORDER BY create_time DESC"
            
            results = db_manager.execute_query(sql, params)
            
            materials = []
            for row in results:
                material = Material(
                    id=row['id'],
                    material_name=row['material_name'],
                    ai_status=row['ai_status'],
                    create_time=MaterialDAO._parse_datetime(row['create_time']),
                    is_enabled=row['is_enabled'],
                    update_time=MaterialDAO._parse_datetime(row['update_time'])
                )
                materials.append(material)
            
            return materials
            
        except Exception:
            return []
    
    @staticmethod
    def get_material_names(enabled_only: bool = True) -> List[str]:
        try:
            materials = MaterialDAO.get_all_materials(enabled_only)
            return [material.material_name for material in materials]
        except Exception:
            return []
    
    @staticmethod
    def get_material_by_id(material_id: int) -> Optional[Material]:
        try:
            sql = "SELECT * FROM materials WHERE id = ?"
            results = db_manager.execute_query(sql, (material_id,))
            
            if results:
                row = results[0]
                return Material(
                    id=row['id'],
                    material_name=row['material_name'],
                    ai_status=row['ai_status'],
                    create_time=MaterialDAO._parse_datetime(row['create_time']),
                    is_enabled=row['is_enabled'],
                    update_time=MaterialDAO._parse_datetime(row['update_time'])
                )
            
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def get_material_by_name(material_name: str) -> Optional[Material]:
        try:
            sql = "SELECT * FROM materials WHERE material_name = ?"
            results = db_manager.execute_query(sql, (material_name,))
            
            if results:
                row = results[0]
                return Material(
                    id=row['id'],
                    material_name=row['material_name'],
                    ai_status=row['ai_status'],
                    create_time=MaterialDAO._parse_datetime(row['create_time']),
                    is_enabled=row['is_enabled'],
                    update_time=MaterialDAO._parse_datetime(row['update_time'])
                )
            
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def create_material(material_name: str, ai_status: str = "未学习", is_enabled: int = 1) -> Tuple[bool, str, Optional[int]]:
        try:
            existing_material = MaterialDAO.get_material_by_name(material_name)
            if existing_material:
                return False, f"物料名称'{material_name}'已存在", None
            
            sql = "INSERT INTO materials (material_name, ai_status, is_enabled) VALUES (?, ?, ?)"
            material_id = db_manager.execute_insert(sql, (material_name, ai_status, is_enabled))
            
            return True, f"物料'{material_name}'创建成功", material_id
            
        except Exception as e:
            error_msg = f"创建物料失败: {str(e)}"
            return False, error_msg, None
    
    @staticmethod
    def update_material_ai_status(material_id: int, ai_status: str) -> Tuple[bool, str]:
        try:
            valid_statuses = ["未学习", "已学习", "已生产"]
            if ai_status not in valid_statuses:
                return False, f"无效的AI状态值: {ai_status}"
            
            sql = "UPDATE materials SET ai_status = ? WHERE id = ?"
            affected_rows = db_manager.execute_update(sql, (ai_status, material_id))
            
            if affected_rows > 0:
                return True, f"物料AI状态已更新为'{ai_status}'"
            else:
                return False, "未找到指定的物料"
                
        except Exception as e:
            error_msg = f"更新物料AI状态失败: {str(e)}"
            return False, error_msg
    
    @staticmethod
    def update_material_ai_status_by_name(material_name: str, ai_status: str) -> Tuple[bool, str]:
        try:
            valid_statuses = ["未学习", "已学习", "已生产"]
            if ai_status not in valid_statuses:
                return False, f"无效的AI状态值: {ai_status}"
            
            sql = "UPDATE materials SET ai_status = ? WHERE material_name = ?"
            affected_rows = db_manager.execute_update(sql, (ai_status, material_name))
            
            if affected_rows > 0:
                return True, f"物料'{material_name}'的AI状态已更新为'{ai_status}'"
            else:
                return False, f"未找到物料'{material_name}'"
                
        except Exception as e:
            error_msg = f"更新物料AI状态失败: {str(e)}"
            return False, error_msg
    
    @staticmethod
    def enable_material(material_id: int) -> Tuple[bool, str]:
        try:
            sql = "UPDATE materials SET is_enabled = 1 WHERE id = ?"
            affected_rows = db_manager.execute_update(sql, (material_id,))
            
            if affected_rows > 0:
                return True, "物料已启用"
            else:
                return False, "未找到指定的物料"
                
        except Exception as e:
            error_msg = f"启用物料失败: {str(e)}"
            return False, error_msg
    
    @staticmethod
    def disable_material(material_id: int) -> Tuple[bool, str]:
        try:
            sql = "UPDATE materials SET is_enabled = 0 WHERE id = ?"
            affected_rows = db_manager.execute_update(sql, (material_id,))
            
            if affected_rows > 0:
                return True, "物料已禁用"
            else:
                return False, "未找到指定的物料"
                
        except Exception as e:
            error_msg = f"禁用物料失败: {str(e)}"
            return False, error_msg
    
    @staticmethod
    def delete_material(material_id: int) -> Tuple[bool, str]:
        try:
            sql = "DELETE FROM materials WHERE id = ?"
            affected_rows = db_manager.execute_update(sql, (material_id,))
            
            if affected_rows > 0:
                return True, "物料已删除"
            else:
                return False, "未找到指定的物料"
                
        except Exception as e:
            error_msg = f"删除物料失败: {str(e)}"
            return False, error_msg
    
    @staticmethod
    def get_materials_by_ai_status(ai_status: str, enabled_only: bool = True) -> List[Material]:
        try:
            sql = "SELECT * FROM materials WHERE ai_status = ?"
            params = [ai_status]
            
            if enabled_only:
                sql += " AND is_enabled = ?"
                params.append(1)
            
            sql += " ORDER BY create_time DESC"
            
            results = db_manager.execute_query(sql, tuple(params))
            
            materials = []
            for row in results:
                material = Material(
                    id=row['id'],
                    material_name=row['material_name'],
                    ai_status=row['ai_status'],
                    create_time=MaterialDAO._parse_datetime(row['create_time']),
                    is_enabled=row['is_enabled'],
                    update_time=MaterialDAO._parse_datetime(row['update_time'])
                )
                materials.append(material)
            
            return materials
            
        except Exception:
            return []