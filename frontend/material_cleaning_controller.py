#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物料清料控制器
负责清料操作的PLC控制和实时重量检测

作者：AI助手
创建日期：2025-07-24
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
from modbus_client import ModbusClient
from plc_addresses import BUCKET_MONITORING_ADDRESSES, GLOBAL_CONTROL_ADDRESSES

class MaterialCleaningController:
    """
    物料清料控制器
    
    负责：
    1. 向PLC发送总清料命令
    2. 定时读取6个料斗的实时重量
    3. 检测清料完成条件
    4. 通知界面清料状态
    """
    
    def __init__(self, modbus_client: ModbusClient):
        """
        初始化清料控制器
        
        Args:
            modbus_client (ModbusClient): Modbus客户端实例
        """
        self.modbus_client = modbus_client
        
        # 清料状态控制
        self.is_cleaning = False
        self.cleaning_start_time = None
        self.stop_cleaning_flag = threading.Event()
        self.cleaning_thread = None
        
        # 重量检测相关
        self.weight_readings = []  # 存储三次重量读取结果
        self.reading_interval = 3.0  # 每3秒读取一次
        self.required_readings = 3  # 需要连续3次读取
        self.weight_threshold = 2.0  # 重量变化阈值2g
        self.zero_threshold = 0.0   # 重量小于0g的阈值
        
        # 事件回调
        self.on_cleaning_completed: Optional[Callable[[], None]] = None  # 清料完成回调
        self.on_cleaning_failed: Optional[Callable[[str], None]] = None  # 清料失败回调
        self.on_log_message: Optional[Callable[[str], None]] = None  # 日志消息回调
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def start_cleaning(self) -> Tuple[bool, str]:
        """
        开始清料操作
        
        Returns:
            Tuple[bool, str]: (是否成功启动, 操作消息)
        """
        try:
            if self.is_cleaning:
                return False, "清料操作已在进行中"
            
            # 检查Modbus连接
            if not self.modbus_client or not self.modbus_client.is_connected:
                return False, "PLC未连接，无法执行清料操作"
            
            self._log("🚀 开始清料操作")
            
            # 发送总清料=1命令
            success = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalClean'], True)
            if not success:
                error_msg = "发送总清料=1命令失败"
                self._log(f"❌ {error_msg}")
                return False, error_msg
            
            self._log("✅ 已发送总清料=1命令")
            
            # 初始化状态
            self.is_cleaning = True
            self.cleaning_start_time = datetime.now()
            self.weight_readings = []
            self.stop_cleaning_flag.clear()
            
            # 启动清料监测线程
            self.cleaning_thread = threading.Thread(
                target=self._cleaning_monitor_thread,
                daemon=True,
                name="MaterialCleaning"
            )
            self.cleaning_thread.start()
            
            success_msg = "清料操作已启动，正在监测料斗重量变化"
            self._log(f"✅ {success_msg}")
            return True, success_msg
            
        except Exception as e:
            error_msg = f"启动清料操作异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False, error_msg
    
    def stop_cleaning(self) -> Tuple[bool, str]:
        """
        停止清料操作
        
        Returns:
            Tuple[bool, str]: (是否成功停止, 操作消息)
        """
        try:
            if not self.is_cleaning:
                return True, "清料操作未在进行中"
            
            self._log("🛑 停止清料操作")
            
            # 设置停止标志
            self.stop_cleaning_flag.set()
            
            # 等待清料线程结束
            if self.cleaning_thread and self.cleaning_thread.is_alive():
                self.cleaning_thread.join(timeout=2.0)
            
            # 发送总清料=0命令
            success = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalClean'], False)
            if not success:
                error_msg = "发送总清料=0命令失败"
                self._log(f"❌ {error_msg}")
                return False, error_msg
            
            self._log("✅ 已发送总清料=0命令")
            
            # 重置状态
            self.is_cleaning = False
            self.weight_readings = []
            
            success_msg = "清料操作已停止"
            self._log(f"✅ {success_msg}")
            return True, success_msg
            
        except Exception as e:
            error_msg = f"停止清料操作异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False, error_msg
    
    def _cleaning_monitor_thread(self):
        """
        清料监测线程主函数
        每3秒读取一次6个料斗的实时重量，连续检测3次
        """
        try:
            self._log("📊 开始监测料斗重量变化")
            
            while not self.stop_cleaning_flag.is_set() and self.is_cleaning:
                # 读取6个料斗的实时重量
                bucket_weights = self._read_all_bucket_weights()
                
                if bucket_weights is None:
                    # 读取失败，触发失败回调
                    error_msg = "读取料斗重量失败，清料监测中断"
                    self._log(f"❌ {error_msg}")
                    self._trigger_cleaning_failed(error_msg)
                    break
                
                # 记录本次重量读取结果
                self.weight_readings.append(bucket_weights)
                self._log(f"📝 第{len(self.weight_readings)}次重量读取: {bucket_weights}")
                
                # 保持最多3次读取记录
                if len(self.weight_readings) > self.required_readings:
                    self.weight_readings.pop(0)
                
                # 检查是否满足清料完成条件
                if len(self.weight_readings) >= self.required_readings:
                    if self._check_cleaning_completion():
                        # 清料完成
                        self._log("🎉 清料完成条件满足")
                        self._trigger_cleaning_completed()
                        break
                
                # 等待下次检测
                self.stop_cleaning_flag.wait(self.reading_interval)
                
        except Exception as e:
            error_msg = f"清料监测线程异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            self._trigger_cleaning_failed(error_msg)
    
    def _read_all_bucket_weights(self) -> Optional[Dict[int, float]]:
        """
        读取所有6个料斗的实时重量
        
        Returns:
            Optional[Dict[int, float]]: 重量字典{料斗ID: 重量(g)}，失败返回None
        """
        try:
            bucket_weights = {}
            
            # 读取6个料斗的实时重量
            for bucket_id in range(1, 4):
                weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
                
                # 读取原始重量值
                raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
                
                if raw_weight_data is not None and len(raw_weight_data) > 0:
                    # 重量值需要除以10
                    weight_value = raw_weight_data[0] / 10.0
                    bucket_weights[bucket_id] = weight_value
                else:
                    self._log(f"❌ 读取料斗{bucket_id}重量失败")
                    return None
            
            return bucket_weights
            
        except Exception as e:
            self.logger.error(f"读取料斗重量异常: {e}")
            return None
    
    def _check_cleaning_completion(self) -> bool:
        """
        检查清料完成条件
        
        条件：连续三次读取到6个料斗的：
        1. 实时重量2-实时重量1 的差值都不超过2g
        2. 实时重量3-实时重量2 的差值都不超过2g  
        3. 6个料斗的实时重量3都＜0g
        
        Returns:
            bool: 是否满足清料完成条件
        """
        try:
            if len(self.weight_readings) < self.required_readings:
                return False
            
            # 获取三次重量读取结果
            weight1 = self.weight_readings[0]  # 第1次读取
            weight2 = self.weight_readings[1]  # 第2次读取
            weight3 = self.weight_readings[2]  # 第3次读取
            
            self._log("🔍 检查清料完成条件:")
            self._log(f"   第1次重量: {weight1}")
            self._log(f"   第2次重量: {weight2}")
            self._log(f"   第3次重量: {weight3}")
            
            # 检查所有料斗的条件
            for bucket_id in range(1, 4):
                w1 = weight1[bucket_id]
                w2 = weight2[bucket_id]
                w3 = weight3[bucket_id]
                
                # 条件1: 实时重量2-实时重量1 的差值不超过2g
                diff_2_1 = abs(w2 - w1)
                if diff_2_1 > self.weight_threshold:
                    self._log(f"   料斗{bucket_id}: 重量2-重量1差值 {diff_2_1:.1f}g > {self.weight_threshold}g，不满足条件1")
                    return False
                
                # 条件2: 实时重量3-实时重量2 的差值不超过2g
                diff_3_2 = abs(w3 - w2)
                if diff_3_2 > self.weight_threshold:
                    self._log(f"   料斗{bucket_id}: 重量3-重量2差值 {diff_3_2:.1f}g > {self.weight_threshold}g，不满足条件2")
                    return False
                
                # 条件3: 实时重量3 < 0g
                if w3 >= self.zero_threshold:
                    self._log(f"   料斗{bucket_id}: 重量3 {w3:.1f}g >= {self.zero_threshold}g，不满足条件3")
                    return False
                
                self._log(f"   料斗{bucket_id}: ✓ 差值2-1={diff_2_1:.1f}g, 差值3-2={diff_3_2:.1f}g, 重量3={w3:.1f}g")
            
            self._log("✅ 所有料斗都满足清料完成条件")
            return True
            
        except Exception as e:
            self.logger.error(f"检查清料完成条件异常: {e}")
            return False
    
    def _trigger_cleaning_completed(self):
        """触发清料完成事件"""
        self.is_cleaning = False
        if self.on_cleaning_completed:
            try:
                self.on_cleaning_completed()
            except Exception as e:
                self.logger.error(f"清料完成事件回调异常: {e}")
    
    def _trigger_cleaning_failed(self, error_message: str):
        """触发清料失败事件"""
        self.is_cleaning = False
        if self.on_cleaning_failed:
            try:
                self.on_cleaning_failed(error_message)
            except Exception as e:
                self.logger.error(f"清料失败事件回调异常: {e}")
    
    def _log(self, message: str):
        """记录日志"""
        self.logger.info(message)
        if self.on_log_message:
            try:
                self.on_log_message(message)
            except Exception as e:
                self.logger.error(f"日志事件回调异常: {e}")
    
    def get_cleaning_status(self) -> Dict:
        """
        获取清料状态信息
        
        Returns:
            Dict: 状态信息字典
        """
        return {
            'is_cleaning': self.is_cleaning,
            'start_time': self.cleaning_start_time,
            'readings_count': len(self.weight_readings),
            'last_weights': self.weight_readings[-1] if self.weight_readings else None
        }
    
    def dispose(self):
        """释放资源"""
        try:
            if self.is_cleaning:
                self.stop_cleaning()
            self._log("清料控制器资源已释放")
        except Exception as e:
            self.logger.error(f"释放清料控制器资源异常: {e}")

def create_material_cleaning_controller(modbus_client: ModbusClient) -> MaterialCleaningController:
    """
    创建清料控制器实例的工厂函数
    
    Args:
        modbus_client (ModbusClient): Modbus客户端实例
        
    Returns:
        MaterialCleaningController: 清料控制器实例
    """
    return MaterialCleaningController(modbus_client)