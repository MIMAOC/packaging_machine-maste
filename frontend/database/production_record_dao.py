#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产记录数据访问对象
处理生产记录表的数据库操作

作者：AI助手
创建日期：2025-08-06
修复日期：2025-08-06（修复SQLite语法和datetime转换问题）
"""

from datetime import datetime, date
from typing import Optional, List, Tuple
from dataclasses import dataclass
from database.db_connection import db_manager

@dataclass
class ProductionRecord:
    """生产记录数据类"""
    id: Optional[int] = None
    production_date: Optional[date] = None
    production_id: str = ""
    material_name: str = ""
    target_weight: float = 0.0
    package_quantity: int = 0
    completed_packages: int = 0
    completion_rate: float = 0.0
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    
@dataclass
class ProductionRecordDetail:
    """生产记录详情数据类（包含明细统计）"""
    id: Optional[int] = None
    production_date: Optional[date] = None
    production_id: str = ""
    material_name: str = ""
    target_weight: float = 0.0
    package_quantity: int = 0
    completed_packages: int = 0
    completion_rate: float = 0.0
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    # 合格统计
    qualified_count: int = 0
    qualified_min_weight: Optional[float] = None
    qualified_max_weight: Optional[float] = None
    # 不合格统计
    unqualified_count: int = 0
    unqualified_min_weight: Optional[float] = None
    unqualified_max_weight: Optional[float] = None

class ProductionRecordDAO:
    """生产记录数据访问对象"""
    
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
    def _parse_date(date_str):
        """
        解析date字符串为date对象
        
        Args:
            date_str: 日期字符串或date对象
            
        Returns:
            date对象或None
        """
        if date_str is None:
            return None
        
        if isinstance(date_str, date):
            return date_str
        
        if isinstance(date_str, str):
            try:
                # 尝试多种格式解析
                formats = [
                    "%Y-%m-%d",
                    "%Y/%m/%d"
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt).date()
                    except ValueError:
                        continue
                
                # 如果所有格式都失败，返回None
                print(f"警告：无法解析日期字符串: {date_str}")
                return None
                
            except Exception as e:
                print(f"解析日期异常: {e}")
                return None
        
        return None
    
    @staticmethod
    def create_production_record(production_id: str, material_name: str, 
                               target_weight: float, package_quantity: int,
                               completed_packages: int = 0) -> Tuple[bool, str, Optional[int]]:
        """
        创建生产记录
        
        Args:
            production_id (str): 生产编号
            material_name (str): 物料名称
            target_weight (float): 目标重量
            package_quantity (int): 包装数量
            completed_packages (int): 完成包数，默认为0
            
        Returns:
            Tuple[bool, str, Optional[int]]: (成功状态, 消息, 记录ID)
        """
        try:
            # 计算完成率
            completion_rate = (completed_packages / package_quantity * 100) if package_quantity > 0 else 0.0
            
            # 生产日期为当前日期
            production_date = datetime.now().date()
            
            sql = """
            INSERT INTO production_records (
                production_date, production_id, material_name, target_weight, 
                package_quantity, completed_packages, completion_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                production_date, production_id, material_name, target_weight,
                package_quantity, completed_packages, completion_rate
            )
            
            record_id = db_manager.execute_insert(sql, params)
            
            return True, f"生产记录创建成功，记录ID: {record_id}", record_id
            
        except Exception as e:
            error_msg = f"创建生产记录失败: {str(e)}"
            print(f"[错误] {error_msg}")
            return False, error_msg, None
    
    @staticmethod
    def update_production_record(production_id: str, completed_packages: int) -> Tuple[bool, str]:
        """
        更新生产记录的完成包数和完成率
        
        Args:
            production_id (str): 生产编号
            completed_packages (int): 完成包数
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 先获取原记录的包装数量
            record = ProductionRecordDAO.get_production_record_by_id(production_id)
            if not record:
                return False, f"未找到生产编号为 {production_id} 的记录"
            
            # 计算完成率
            completion_rate = (completed_packages / record.package_quantity * 100) if record.package_quantity > 0 else 0.0
            
            sql = """
            UPDATE production_records 
            SET completed_packages = ?, completion_rate = ?, update_time = (datetime('now', 'localtime'))
            WHERE production_id = ?
            """
            
            params = (completed_packages, completion_rate, production_id)
            
            affected_rows = db_manager.execute_update(sql, params)
            
            if affected_rows > 0:
                return True, f"生产记录更新成功，完成包数: {completed_packages}, 完成率: {completion_rate:.2f}%"
            else:
                return False, f"未找到生产编号为 {production_id} 的记录"
                
        except Exception as e:
            error_msg = f"更新生产记录失败: {str(e)}"
            print(f"[错误] {error_msg}")
            return False, error_msg
    
    @staticmethod
    def get_production_record_by_id(production_id: str) -> Optional[ProductionRecord]:
        """
        根据生产编号获取生产记录
        
        Args:
            production_id (str): 生产编号
            
        Returns:
            Optional[ProductionRecord]: 生产记录对象，如果不存在则返回None
        """
        try:
            sql = "SELECT * FROM production_records WHERE production_id = ?"
            results = db_manager.execute_query(sql, (production_id,))
            
            if results:
                result = results[0]
                return ProductionRecord(
                    id=result['id'],
                    production_date=ProductionRecordDAO._parse_date(result['production_date']),
                    production_id=result['production_id'],
                    material_name=result['material_name'],
                    target_weight=float(result['target_weight']),
                    package_quantity=result['package_quantity'],
                    completed_packages=result['completed_packages'],
                    completion_rate=float(result['completion_rate']),
                    create_time=ProductionRecordDAO._parse_datetime(result['create_time']),
                    update_time=ProductionRecordDAO._parse_datetime(result['update_time'])
                )
            
            return None
            
        except Exception as e:
            print(f"[错误] 获取生产记录失败: {str(e)}")
            return None
    
    @staticmethod
    def get_production_records_by_date(production_date: date) -> List[ProductionRecord]:
        """
        根据生产日期获取生产记录列表
        
        Args:
            production_date (date): 生产日期
            
        Returns:
            List[ProductionRecord]: 生产记录列表
        """
        try:
            sql = "SELECT * FROM production_records WHERE production_date = ? ORDER BY create_time DESC"
            results = db_manager.execute_query(sql, (production_date,))
            
            records = []
            for result in results:
                record = ProductionRecord(
                    id=result['id'],
                    production_date=ProductionRecordDAO._parse_date(result['production_date']),
                    production_id=result['production_id'],
                    material_name=result['material_name'],
                    target_weight=float(result['target_weight']),
                    package_quantity=result['package_quantity'],
                    completed_packages=result['completed_packages'],
                    completion_rate=float(result['completion_rate']),
                    create_time=ProductionRecordDAO._parse_datetime(result['create_time']),
                    update_time=ProductionRecordDAO._parse_datetime(result['update_time'])
                )
                records.append(record)
            
            return records
            
        except Exception as e:
            print(f"[错误] 获取生产记录列表失败: {str(e)}")
            return []
    
    @staticmethod
    def get_recent_production_records(limit: int = 50) -> List[ProductionRecord]:
        """
        获取最近的生产记录列表
        
        Args:
            limit (int): 限制返回记录数量，默认50
            
        Returns:
            List[ProductionRecord]: 生产记录列表
        """
        try:
            sql = "SELECT * FROM production_records ORDER BY create_time DESC LIMIT ?"
            results = db_manager.execute_query(sql, (limit,))
            
            records = []
            for result in results:
                record = ProductionRecord(
                    id=result['id'],
                    production_date=ProductionRecordDAO._parse_date(result['production_date']),
                    production_id=result['production_id'],
                    material_name=result['material_name'],
                    target_weight=float(result['target_weight']),
                    package_quantity=result['package_quantity'],
                    completed_packages=result['completed_packages'],
                    completion_rate=float(result['completion_rate']),
                    create_time=ProductionRecordDAO._parse_datetime(result['create_time']),
                    update_time=ProductionRecordDAO._parse_datetime(result['update_time'])
                )
                records.append(record)
            
            return records
            
        except Exception as e:
            print(f"[错误] 获取最近生产记录失败: {str(e)}")
            return []
    
    @staticmethod
    def get_production_record_detail_by_id(production_id: str) -> Optional[ProductionRecordDetail]:
        """
        根据生产编号获取生产记录详情（包含明细统计）
        
        Args:
            production_id (str): 生产编号
            
        Returns:
            Optional[ProductionRecordDetail]: 生产记录详情对象，如果不存在则返回None
        """
        try:
            sql = "SELECT * FROM production_record_detail_view WHERE production_id = ?"
            results = db_manager.execute_query(sql, (production_id,))
            
            if results:
                result = results[0]
                return ProductionRecordDetail(
                    production_date=ProductionRecordDAO._parse_date(result['production_date']),
                    production_id=result['production_id'],
                    material_name=result['material_name'],
                    target_weight=float(result['target_weight']),
                    package_quantity=result['package_quantity'],
                    completed_packages=result['completed_packages'],
                    completion_rate=float(result['completion_rate']),
                    create_time=ProductionRecordDAO._parse_datetime(result['create_time']),
                    update_time=ProductionRecordDAO._parse_datetime(result['update_time']),
                    qualified_count=result['qualified_count'] or 0,
                    qualified_min_weight=float(result['qualified_min_weight']) if result['qualified_min_weight'] else None,
                    qualified_max_weight=float(result['qualified_max_weight']) if result['qualified_max_weight'] else None,
                    unqualified_count=result['unqualified_count'] or 0,
                    unqualified_min_weight=float(result['unqualified_min_weight']) if result['unqualified_min_weight'] else None,
                    unqualified_max_weight=float(result['unqualified_max_weight']) if result['unqualified_max_weight'] else None
                )
            
            return None
            
        except Exception as e:
            print(f"[错误] 获取生产记录详情失败: {str(e)}")
            return None