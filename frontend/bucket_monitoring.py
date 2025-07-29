#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
料斗监测模块（重命名自coarse_time_monitoring.py）
监测6个料斗的到量状态，支持快加时间测定、飞料值测定和自适应学习阶段

作者：AI助手
创建日期：2025-07-23
更新日期：2025-07-29（修复快加状态监测的初始状态问题）
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from modbus_client import ModbusClient
from plc_addresses import (
    BUCKET_MONITORING_ADDRESSES,
    get_all_bucket_target_reached_addresses,
    get_all_bucket_coarse_add_addresses
)

class BucketMonitoringState:
    """料斗监测状态"""
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_monitoring = False          # 是否正在监测
        self.start_time = None             # 开始时间
        self.target_reached_time = None    # 到量时间
        self.coarse_time_ms = 0           # 快加时间（毫秒）
        self.last_target_reached = False  # 上次到量状态
        self.last_coarse_active = None    # 🔥 修复：初始值改为None，表示未知状态
        self.monitoring_type = "coarse_time"  # 监测类型：coarse_time 或 flight_material 或 adaptive_learning
        self.coarse_active_initialized = False  # 🔥 新增：标记快加状态是否已初始化
    
    def reset(self):
        """重置状态"""
        self.is_monitoring = False
        self.start_time = None
        self.target_reached_time = None
        self.coarse_time_ms = 0
        self.last_target_reached = False
        self.last_coarse_active = None  # 🔥 修复：重置为None
        self.monitoring_type = "coarse_time"
        self.coarse_active_initialized = False  # 🔥 新增：重置初始化标记
    
    def start_monitoring(self, monitoring_type: str = "coarse_time"):
        """开始监测"""
        self.reset()
        self.is_monitoring = True
        self.start_time = datetime.now()
        self.monitoring_type = monitoring_type

class BucketMonitoringService:
    """
    料斗监测服务
    负责监测6个料斗的到量状态并记录时间，支持多种监测类型
    """
    
    def __init__(self, modbus_client: ModbusClient):
        """
        初始化监测服务
        
        Args:
            modbus_client (ModbusClient): Modbus客户端实例
        """
        self.modbus_client = modbus_client
        self.monitoring_states: Dict[int, BucketMonitoringState] = {}
        self.monitoring_thread = None
        self.stop_monitoring_flag = threading.Event()
        self.lock = threading.RLock()
        
        # 监测参数
        self.monitoring_interval = 0.1  # 100ms监测间隔
        
        # 事件回调
        self.on_target_reached: Optional[Callable[[int, int], None]] = None  # (bucket_id, coarse_time_ms)
        self.on_coarse_status_changed: Optional[Callable[[int, bool], None]] = None  # (bucket_id, coarse_active) 新增回调
        self.on_monitoring_log: Optional[Callable[[str], None]] = None
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # 初始化料斗状态
        self._initialize_bucket_states()
    
    def _initialize_bucket_states(self):
        """初始化料斗监测状态"""
        with self.lock:
            for bucket_id in range(1, 7):
                self.monitoring_states[bucket_id] = BucketMonitoringState(bucket_id)
    
    def start_monitoring(self, bucket_ids: List[int], monitoring_type: str = "coarse_time"):
        """
        开始监测指定的料斗
        
        Args:
            bucket_ids (List[int]): 要监测的料斗ID列表
            monitoring_type (str): 监测类型 ("coarse_time" 或 "flight_material" 或 "adaptive_learning")
        """
        try:
            with self.lock:
                # 停止现有监测
                if self.monitoring_thread and self.monitoring_thread.is_alive():
                    self.stop_monitoring_flag.set()
                    self.monitoring_thread.join(timeout=1.0)
                
                # 重置并启动指定料斗的监测
                for bucket_id in bucket_ids:
                    if bucket_id in self.monitoring_states:
                        self.monitoring_states[bucket_id].start_monitoring(monitoring_type)
                        self._log(f"料斗{bucket_id}开始{monitoring_type}监测")
                
                # 启动监测线程
                self.stop_monitoring_flag.clear()
                self.monitoring_thread = threading.Thread(
                    target=self._monitoring_thread_func,
                    daemon=True,
                    name="BucketMonitoring"
                )
                self.monitoring_thread.start()
                
                self._log(f"料斗监测服务已启动，监测料斗: {bucket_ids}，类型: {monitoring_type}")
                
        except Exception as e:
            error_msg = f"启动料斗监测失败: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
    
    def restart_bucket_monitoring(self, bucket_id: int, monitoring_type: str = "coarse_time"):
        """
        重新启动单个料斗的监测
        
        Args:
            bucket_id (int): 料斗ID
            monitoring_type (str): 监测类型
        """
        try:
            with self.lock:
                if bucket_id in self.monitoring_states:
                    self.monitoring_states[bucket_id].start_monitoring(monitoring_type)
                    self._log(f"料斗{bucket_id}重新开始{monitoring_type}监测")
                else:
                    self._log(f"无效的料斗ID: {bucket_id}")
        except Exception as e:
            error_msg = f"重新启动料斗{bucket_id}监测失败: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
    
    def stop_bucket_monitoring(self, bucket_id: int):
        """
        停止单个料斗的监测
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            with self.lock:
                if bucket_id in self.monitoring_states:
                    state = self.monitoring_states[bucket_id]
                    if state.is_monitoring:
                        state.is_monitoring = False
                        self._log(f"料斗{bucket_id}监测已停止")
        except Exception as e:
            error_msg = f"停止料斗{bucket_id}监测失败: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
    
    def stop_all_monitoring(self):
        """停止所有料斗的监测"""
        try:
            with self.lock:
                # 设置停止标志
                self.stop_monitoring_flag.set()
                
                # 停止所有料斗监测
                for state in self.monitoring_states.values():
                    state.is_monitoring = False
                
                # 等待监测线程结束
                if self.monitoring_thread and self.monitoring_thread.is_alive():
                    self.monitoring_thread.join(timeout=1.0)
                
                self._log("料斗监测服务已停止")
                
        except Exception as e:
            error_msg = f"停止料斗监测失败: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
    
    def _monitoring_thread_func(self):
        """监测线程主函数"""
        self.logger.info("料斗监测线程已启动")
        
        try:
            while not self.stop_monitoring_flag.is_set():
                # 获取当前需要监测的料斗列表
                monitoring_buckets = []
                with self.lock:
                    for bucket_id, state in self.monitoring_states.items():
                        if state.is_monitoring:
                            monitoring_buckets.append(bucket_id)
                
                if monitoring_buckets:
                    # 批量读取所有料斗的到量状态和快加状态
                    self._check_target_reached_status(monitoring_buckets)
                else:
                    # 没有料斗需要监测，可以适当延长休眠时间
                    time.sleep(0.5)
                    continue
                
                # 等待下次监测
                time.sleep(self.monitoring_interval)
                
        except Exception as e:
            error_msg = f"料斗监测线程异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
        finally:
            self.logger.info("料斗监测线程已结束")
    
    def _check_target_reached_status(self, monitoring_buckets: List[int]):
        """
        检查料斗到量状态和快加状态（扩展）
        
        Args:
            monitoring_buckets (List[int]): 需要监测的料斗ID列表
        """
        try:
            # 获取所有到量线圈地址
            target_reached_addresses = get_all_bucket_target_reached_addresses()
            
            # 批量读取到量线圈状态
            coil_states = self.modbus_client.read_coils(
                target_reached_addresses[0], len(target_reached_addresses))
            
            if coil_states is None:
                self._log("读取到量线圈状态失败")
                return
            
            # 对于自适应学习监测，还需要读取快加状态
            coarse_states = None
            if any(self.monitoring_states[bid].monitoring_type == "adaptive_learning" 
                   for bid in monitoring_buckets if bid in self.monitoring_states):
                
                # 获取所有快加线圈地址
                coarse_add_addresses = get_all_bucket_coarse_add_addresses()
                
                # 批量读取快加线圈状态
                coarse_states = self.modbus_client.read_coils(
                    coarse_add_addresses[0], len(coarse_add_addresses))
                
                if coarse_states is None:
                    self._log("读取快加线圈状态失败")
                    # 继续处理到量状态，不中断
            
            current_time = datetime.now()
            
            # 检查每个料斗的状态
            with self.lock:
                for i, bucket_id in enumerate(range(1, 7)):
                    if bucket_id not in monitoring_buckets:
                        continue
                    
                    state = self.monitoring_states[bucket_id]
                    if not state.is_monitoring:
                        continue
                    
                    current_target_reached = coil_states[i] if i < len(coil_states) else False
                    
                    # 检测到量状态的上升沿（从False变为True）
                    if current_target_reached and not state.last_target_reached:
                        # 第一次到量
                        state.target_reached_time = current_time
                        state.coarse_time_ms = int((current_time - state.start_time).total_seconds() * 1000)
                        state.is_monitoring = False  # 停止该料斗的监测
                        
                        self._log(f"料斗{bucket_id}到量，时间: {state.coarse_time_ms}ms，类型: {state.monitoring_type}")
                        
                        # 触发到量事件
                        if self.on_target_reached:
                            try:
                                self.on_target_reached(bucket_id, state.coarse_time_ms)
                            except Exception as e:
                                self.logger.error(f"处理料斗{bucket_id}到量事件异常: {e}")
                    
                    # 🔥 修复：改进快加状态检测逻辑
                    if (state.monitoring_type == "adaptive_learning" and 
                        coarse_states is not None and i < len(coarse_states)):
                        
                        current_coarse_active = coarse_states[i]
                        
                        # 🔥 修复：处理初始状态
                        if not state.coarse_active_initialized:
                            # 第一次读取，初始化状态
                            state.last_coarse_active = current_coarse_active
                            state.coarse_active_initialized = True
                            self._log(f"料斗{bucket_id}快加状态初始化: {current_coarse_active}")
                        else:
                            # 🔥 修复：检测状态变化（包括上升沿和下降沿）
                            if state.last_coarse_active != current_coarse_active:
                                if current_coarse_active:
                                    # 上升沿：快加开始
                                    self._log(f"料斗{bucket_id}快加开始（0→1）")
                                else:
                                    # 下降沿：快加结束
                                    self._log(f"料斗{bucket_id}快加结束（1→0）")
                                    
                                    # 触发快加状态变化事件（快加结束）
                                    if self.on_coarse_status_changed:
                                        try:
                                            self.on_coarse_status_changed(bucket_id, current_coarse_active)
                                        except Exception as e:
                                            self.logger.error(f"处理料斗{bucket_id}快加状态变化事件异常: {e}")
                                
                                # 更新状态
                                state.last_coarse_active = current_coarse_active
                    
                    # 更新上次到量状态
                    state.last_target_reached = current_target_reached
                    
        except Exception as e:
            error_msg = f"检查状态异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
    
    def get_bucket_monitoring_state(self, bucket_id: int) -> Optional[BucketMonitoringState]:
        """
        获取料斗监测状态
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            Optional[BucketMonitoringState]: 监测状态，如果料斗ID无效则返回None
        """
        with self.lock:
            return self.monitoring_states.get(bucket_id)
    
    def get_all_monitoring_states(self) -> Dict[int, BucketMonitoringState]:
        """
        获取所有料斗的监测状态
        
        Returns:
            Dict[int, BucketMonitoringState]: 所有料斗的监测状态
        """
        with self.lock:
            return self.monitoring_states.copy()
    
    def is_any_bucket_monitoring(self) -> bool:
        """
        检查是否有任何料斗正在监测
        
        Returns:
            bool: 是否有料斗正在监测
        """
        with self.lock:
            return any(state.is_monitoring for state in self.monitoring_states.values())
    
    def _log(self, message: str):
        """记录日志"""
        self.logger.info(message)
        if self.on_monitoring_log:
            try:
                self.on_monitoring_log(message)
            except Exception as e:
                self.logger.error(f"日志回调异常: {e}")
    
    def dispose(self):
        """释放资源"""
        try:
            self.stop_all_monitoring()
        except Exception as e:
            self.logger.error(f"释放监测服务资源异常: {e}")

def create_bucket_monitoring_service(modbus_client: ModbusClient) -> BucketMonitoringService:
    """
    创建料斗监测服务实例的工厂函数
    
    Args:
        modbus_client (ModbusClient): Modbus客户端实例
        
    Returns:
        BucketMonitoringService: 监测服务实例
    """
    return BucketMonitoringService(modbus_client)

# 示例使用
if __name__ == "__main__":
    from modbus_client import create_modbus_client
    
    # 创建Modbus客户端并连接
    client = create_modbus_client()
    success, message = client.connect()
    print(f"连接状态: {success} - {message}")
    
    if success:
        # 创建监测服务
        monitoring_service = create_bucket_monitoring_service(client)
        
        # 设置事件回调
        def on_target_reached(bucket_id: int, coarse_time_ms: int):
            print(f"[事件] 料斗{bucket_id}到量，时间: {coarse_time_ms}ms")
        
        def on_coarse_status_changed(bucket_id: int, coarse_active: bool):
            print(f"[事件] 料斗{bucket_id}快加状态变化: {coarse_active}")
        
        def on_monitoring_log(message: str):
            print(f"[日志] {message}")
        
        monitoring_service.on_target_reached = on_target_reached
        monitoring_service.on_coarse_status_changed = on_coarse_status_changed
        monitoring_service.on_monitoring_log = on_monitoring_log
        
        # 开始监测
        print("开始监测料斗1-6（自适应学习模式）...")
        monitoring_service.start_monitoring([1, 2, 3, 4, 5, 6], "adaptive_learning")
        
        # 运行一段时间后停止
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            pass
        
        print("停止监测...")
        monitoring_service.stop_all_monitoring()
        monitoring_service.dispose()
        
        # 断开连接
        client.disconnect()