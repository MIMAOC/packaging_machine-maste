#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物料数据访问对象(DAO)
包装机系统物料数据库操作

作者：AI助手
创建日期：2025-08-04
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from database.db_connection import db_manager

@dataclass
class Material:
    """物料数据类"""
    id: Optional[int] = None
    material_name: str = ""
    ai_status: str = "未学习"  # 未学习、已学习、已生产
    create_time: Optional[datetime] = None
    is_enabled: int = 1  # 1启用，0禁用
    update_time: Optional[datetime] = None

class MaterialDAO:
    """物料数据访问对象"""
    
    @staticmethod
    def get_all_materials(enabled_only: bool = True) -> List[Material]:
        """
        获取所有物料列表
        
        Args:
            enabled_only: 是否只获取启用的物料
            
        Returns:
            List[Material]: 物料列表
        """
        try:
            sql = "SELECT * FROM materials"
            params = None
            
            if enabled_only:
                sql += " WHERE is_enabled = %s"
                params = (1,)
            
            sql += " ORDER BY create_time DESC"
            
            results = db_manager.execute_query(sql, params)
            
            materials = []
            for row in results:
                material = Material(
                    id=row['id'],
                    material_name=row['material_name'],
                    ai_status=row['ai_status'],
                    create_time=row['create_time'],
                    is_enabled=row['is_enabled'],
                    update_time=row['update_time']
                )
                materials.append(material)
            
            return materials
            
        except Exception as e:
            print(f"获取物料列表失败: {e}")
            return []
    
    @staticmethod
    def get_material_names(enabled_only: bool = True) -> List[str]:
        """
        获取物料名称列表
        
        Args:
            enabled_only: 是否只获取启用的物料
            
        Returns:
            List[str]: 物料名称列表
        """
        try:
            materials = MaterialDAO.get_all_materials(enabled_only)
            return [material.material_name for material in materials]
        except Exception as e:
            print(f"获取物料名称列表失败: {e}")
            return []
    
    @staticmethod
    def get_material_by_id(material_id: int) -> Optional[Material]:
        """
        根据ID获取物料
        
        Args:
            material_id: 物料ID
            
        Returns:
            Optional[Material]: 物料对象，如果不存在则返回None
        """
        try:
            sql = "SELECT * FROM materials WHERE id = %s"
            results = db_manager.execute_query(sql, (material_id,))
            
            if results:
                row = results[0]
                return Material(
                    id=row['id'],
                    material_name=row['material_name'],
                    ai_status=row['ai_status'],
                    create_time=row['create_time'],
                    is_enabled=row['is_enabled'],
                    update_time=row['update_time']
                )
            
            return None
            
        except Exception as e:
            print(f"根据ID获取物料失败: {e}")
            return None
    
    @staticmethod
    def get_material_by_name(material_name: str) -> Optional[Material]:
        """
        根据名称获取物料
        
        Args:
            material_name: 物料名称
            
        Returns:
            Optional[Material]: 物料对象，如果不存在则返回None
        """
        try:
            sql = "SELECT * FROM materials WHERE material_name = %s"
            results = db_manager.execute_query(sql, (material_name,))
            
            if results:
                row = results[0]
                return Material(
                    id=row['id'],
                    material_name=row['material_name'],
                    ai_status=row['ai_status'],
                    create_time=row['create_time'],
                    is_enabled=row['is_enabled'],
                    update_time=row['update_time']
                )
            
            return None
            
        except Exception as e:
            print(f"根据名称获取物料失败: {e}")
            return None
    
    @staticmethod
    def create_material(material_name: str, ai_status: str = "未学习", is_enabled: int = 1) -> Tuple[bool, str, Optional[int]]:
        """
        创建新物料
        
        Args:
            material_name: 物料名称
            ai_status: AI状态，默认为"未学习"
            is_enabled: 是否启用，默认为1（启用）
            
        Returns:
            Tuple[bool, str, Optional[int]]: (成功状态, 消息, 新物料ID)
        """
        try:
            # 检查物料名称是否已存在
            existing_material = MaterialDAO.get_material_by_name(material_name)
            if existing_material:
                return False, f"物料名称'{material_name}'已存在", None
            
            # 插入新物料
            sql = "INSERT INTO materials (material_name, ai_status, is_enabled) VALUES (%s, %s, %s)"
            material_id = db_manager.execute_insert(sql, (material_name, ai_status, is_enabled))
            
            return True, f"物料'{material_name}'创建成功", material_id
            
        except Exception as e:
            error_msg = f"创建物料失败: {str(e)}"
            print(error_msg)
            return False, error_msg, None
    
    @staticmethod
    def update_material_ai_status(material_id: int, ai_status: str) -> Tuple[bool, str]:
        """
        更新物料的AI状态
        
        Args:
            material_id: 物料ID
            ai_status: 新的AI状态（未学习、已学习、已生产）
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 验证AI状态值
            valid_statuses = ["未学习", "已学习", "已生产"]
            if ai_status not in valid_statuses:
                return False, f"无效的AI状态值: {ai_status}"
            
            sql = "UPDATE materials SET ai_status = %s WHERE id = %s"
            affected_rows = db_manager.execute_update(sql, (ai_status, material_id))
            
            if affected_rows > 0:
                return True, f"物料AI状态已更新为'{ai_status}'"
            else:
                return False, "未找到指定的物料"
                
        except Exception as e:
            error_msg = f"更新物料AI状态失败: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    @staticmethod
    def update_material_ai_status_by_name(material_name: str, ai_status: str) -> Tuple[bool, str]:
        """
        根据物料名称更新AI状态
        
        Args:
            material_name: 物料名称
            ai_status: 新的AI状态（未学习、已学习、已生产）
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 验证AI状态值
            valid_statuses = ["未学习", "已学习", "已生产"]
            if ai_status not in valid_statuses:
                return False, f"无效的AI状态值: {ai_status}"
            
            sql = "UPDATE materials SET ai_status = %s WHERE material_name = %s"
            affected_rows = db_manager.execute_update(sql, (ai_status, material_name))
            
            if affected_rows > 0:
                return True, f"物料'{material_name}'的AI状态已更新为'{ai_status}'"
            else:
                return False, f"未找到物料'{material_name}'"
                
        except Exception as e:
            error_msg = f"更新物料AI状态失败: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    @staticmethod
    def enable_material(material_id: int) -> Tuple[bool, str]:
        """
        启用物料
        
        Args:
            material_id: 物料ID
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            sql = "UPDATE materials SET is_enabled = 1 WHERE id = %s"
            affected_rows = db_manager.execute_update(sql, (material_id,))
            
            if affected_rows > 0:
                return True, "物料已启用"
            else:
                return False, "未找到指定的物料"
                
        except Exception as e:
            error_msg = f"启用物料失败: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    @staticmethod
    def disable_material(material_id: int) -> Tuple[bool, str]:
        """
        禁用物料
        
        Args:
            material_id: 物料ID
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            sql = "UPDATE materials SET is_enabled = 0 WHERE id = %s"
            affected_rows = db_manager.execute_update(sql, (material_id,))
            
            if affected_rows > 0:
                return True, "物料已禁用"
            else:
                return False, "未找到指定的物料"
                
        except Exception as e:
            error_msg = f"禁用物料失败: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    @staticmethod
    def delete_material(material_id: int) -> Tuple[bool, str]:
        """
        删除物料（物理删除）
        
        Args:
            material_id: 物料ID
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            sql = "DELETE FROM materials WHERE id = %s"
            affected_rows = db_manager.execute_update(sql, (material_id,))
            
            if affected_rows > 0:
                return True, "物料已删除"
            else:
                return False, "未找到指定的物料"
                
        except Exception as e:
            error_msg = f"删除物料失败: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    @staticmethod
    def get_materials_by_ai_status(ai_status: str, enabled_only: bool = True) -> List[Material]:
        """
        根据AI状态获取物料列表
        
        Args:
            ai_status: AI状态（未学习、已学习、已生产）
            enabled_only: 是否只获取启用的物料
            
        Returns:
            List[Material]: 物料列表
        """
        try:
            sql = "SELECT * FROM materials WHERE ai_status = %s"
            params = [ai_status]
            
            if enabled_only:
                sql += " AND is_enabled = %s"
                params.append(1)
            
            sql += " ORDER BY create_time DESC"
            
            results = db_manager.execute_query(sql, tuple(params))
            
            materials = []
            for row in results:
                material = Material(
                    id=row['id'],
                    material_name=row['material_name'],
                    ai_status=row['ai_status'],
                    create_time=row['create_time'],
                    is_enabled=row['is_enabled'],
                    update_time=row['update_time']
                )
                materials.append(material)
            
            return materials
            
        except Exception as e:
            print(f"根据AI状态获取物料列表失败: {e}")
            return []