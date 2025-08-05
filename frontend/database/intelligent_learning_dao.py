#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能学习数据访问对象(DAO)
包装机系统智能学习数据库操作

作者：AI助手
创建日期：2025-08-06
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from database.db_connection import db_manager

@dataclass
class IntelligentLearning:
    """智能学习数据类"""
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
    """智能学习数据访问对象"""
    
    @staticmethod
    def save_learning_result(material_name: str, target_weight: float, bucket_id: int,
                    coarse_speed: int, fine_speed: int, coarse_advance: float, fall_value: float) -> Tuple[bool, str]:
        """
        保存智能学习结果（覆盖已有记录）

        Args:
            material_name (str): 物料名称
            target_weight (float): 目标重量
            bucket_id (int): 料斗编号
            coarse_speed (int): 快加速度
            fine_speed (int): 慢加速度
            coarse_advance (float): 快加提前量
            fall_value (float): 落差值

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 先检查是否已存在相同的记录
            existing_record = IntelligentLearningDAO.get_learning_result(material_name, target_weight, bucket_id)

            if existing_record:
                # 存在则更新（覆盖）
                update_sql = """
                UPDATE intelligent_learning 
                SET coarse_speed = %s, fine_speed = %s, coarse_advance = %s, fall_value = %s, update_time = NOW()
                WHERE material_name = %s AND target_weight = %s AND bucket_id = %s
                """
                params = (coarse_speed, fine_speed, coarse_advance, fall_value, material_name, target_weight, bucket_id)

                # 执行更新操作
                affected_rows = db_manager.execute_update(update_sql, params)

                if affected_rows > 0:
                    return True, f"料斗{bucket_id}学习结果已更新（覆盖历史记录）"
                else:
                    return False, f"料斗{bucket_id}学习结果更新失败"
            else:
                # 不存在则插入新记录
                insert_sql = """
                INSERT INTO intelligent_learning (material_name, target_weight, bucket_id, coarse_speed, fine_speed, coarse_advance, 
                fall_value, create_time, update_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """
                params = (material_name, target_weight, bucket_id, coarse_speed, fine_speed, coarse_advance, fall_value)

                # 执行插入操作
                affected_rows = db_manager.execute_update(insert_sql, params)

                if affected_rows > 0:
                    return True, f"料斗{bucket_id}学习结果已保存"
                else:
                    return False, f"料斗{bucket_id}学习结果保存失败"

        except Exception as e:
            error_msg = f"保存学习结果失败: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    @staticmethod
    def get_learning_result(material_name: str, target_weight: float, bucket_id: int) -> Optional[IntelligentLearning]:
        """
        根据物料名称、目标重量、料斗编号获取智能学习结果
        
        Args:
            material_name (str): 物料名称
            target_weight (float): 目标重量
            bucket_id (int): 料斗编号
            
        Returns:
            Optional[IntelligentLearning]: 智能学习对象，如果不存在则返回None
        """
        try:
            sql = """
            SELECT * FROM intelligent_learning 
            WHERE material_name = %s AND target_weight = %s AND bucket_id = %s
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
                    create_time=row['create_time'],
                    update_time=row['update_time']
                )
            
            return None
            
        except Exception as e:
            print(f"获取智能学习结果失败: {e}")
            return None
    
    @staticmethod
    def get_all_learning_results_by_material(material_name: str, target_weight: float) -> List[IntelligentLearning]:
        """
        根据物料名称和目标重量获取所有料斗的智能学习结果
        
        Args:
            material_name (str): 物料名称
            target_weight (float): 目标重量
            
        Returns:
            List[IntelligentLearning]: 智能学习结果列表
        """
        try:
            sql = """
            SELECT * FROM intelligent_learning 
            WHERE material_name = %s AND target_weight = %s
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
                    create_time=row['create_time'],
                    update_time=row['update_time']
                )
                learning_results.append(learning_result)
            
            return learning_results
            
        except Exception as e:
            print(f"获取智能学习结果列表失败: {e}")
            return []
    
    @staticmethod
    def has_learning_data(material_name: str, target_weight: float) -> bool:
        """
        检查指定物料和重量是否有学习数据
        
        Args:
            material_name (str): 物料名称
            target_weight (float): 目标重量
            
        Returns:
            bool: 是否存在学习数据
        """
        try:
            sql = """
            SELECT COUNT(*) as count FROM intelligent_learning 
            WHERE material_name = %s AND target_weight = %s
            """
            results = db_manager.execute_query(sql, (material_name, target_weight))
            
            if results:
                return results[0]['count'] > 0
            
            return False
            
        except Exception as e:
            print(f"检查智能学习数据失败: {e}")
            return False
    
    @staticmethod
    def delete_learning_results(material_name: str, target_weight: float) -> Tuple[bool, str]:
        """
        删除指定物料和重量的所有学习结果
        
        Args:
            material_name (str): 物料名称
            target_weight (float): 目标重量
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            sql = "DELETE FROM intelligent_learning WHERE material_name = %s AND target_weight = %s"
            affected_rows = db_manager.execute_update(sql, (material_name, target_weight))
            
            if affected_rows > 0:
                return True, f"已删除{affected_rows}条学习记录"
            else:
                return False, "未找到匹配的学习记录"
                
        except Exception as e:
            error_msg = f"删除智能学习结果异常: {str(e)}"
            print(error_msg)
            return False, error_msg