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
from typing import Dict, List, Optional, Callable, Deque
from datetime import datetime
from collections import deque
from modbus_client import ModbusClient
from plc_addresses import (
    BUCKET_MONITORING_ADDRESSES,
    BUCKET_CONTROL_ADDRESSES,
    GLOBAL_CONTROL_ADDRESSES,
    get_all_bucket_target_reached_addresses,
    get_all_bucket_coarse_add_addresses,
    get_all_bucket_weight_addresses,
    get_all_bucket_discharge_addresses
)

# 导入生产明细DAO
try:
    from database.production_detail_dao import ProductionDetailDAO, ProductionDetail
    PRODUCTION_DETAIL_DAO_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入生产明细DAO模块: {e}")
    PRODUCTION_DETAIL_DAO_AVAILABLE = False
class BucketProductionState:
    """料斗生产状态"""
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_monitoring_target = False    # 是否正在监测到量状态
        self.is_monitoring_discharge = False # 是否正在监测放料状态
        self.target_reached_time = None      # 到量时间
        self.discharge_time = None           # 放料时间
        self.last_target_reached = False    # 上次到量状态
        self.last_discharge_state = False   # 上次放料状态
        self.consecutive_unqualified = 0    # 连续不合格次数
        self.waiting_for_restart = False    # 是否等待重新开始监测
        self.restart_time = None             # 重新开始时间
        
    def reset(self):
        """重置状态"""
        self.is_monitoring_target = False
        self.is_monitoring_discharge = False
        self.target_reached_time = None
        self.discharge_time = None
        self.last_target_reached = False
        self.last_discharge_state = False
        self.waiting_for_restart = False
        self.restart_time = None
        # 注意：连续不合格次数不在这里重置

class BucketMonitoringState:
    """料斗监测状态"""
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_monitoring = False          # 是否正在监测
        self.start_time = None             # 开始时间
        self.target_reached_time = None    # 到量时间
        self.coarse_time_ms = 0           # 快加时间（毫秒）
        self.last_target_reached = False  # 上次到量状态
        self.last_coarse_active = None    # 初始值改为None，表示未知状态
        self.monitoring_type = "coarse_time"  # 监测类型：coarse_time 或 flight_material 或 adaptive_learning
        self.coarse_active_initialized = False  # 标记快加状态是否已初始化
        
        self.weight_history: Deque[tuple] = deque(maxlen=150)  # 重量历史记录(时间戳, 重量)，保存15秒数据
        self.last_start_active = None      # 上次启动状态
        self.start_active_initialized = False  # 启动状态是否已初始化
        self.material_shortage_detected = False  # 是否检测到物料不足
        self.material_shortage_time = None  # 物料不足检测时间
    
    def reset(self):
        """重置状态"""
        self.is_monitoring = False
        self.start_time = None
        self.target_reached_time = None
        self.coarse_time_ms = 0
        self.last_target_reached = False
        self.last_coarse_active = None  # 重置为None
        self.monitoring_type = "coarse_time"
        self.coarse_active_initialized = False  # 重置初始化标记
        
        self.weight_history.clear() # 重置物料监测状态
        self.last_start_active = None
        self.start_active_initialized = False
        self.material_shortage_detected = False
        self.material_shortage_time = None
    
    def start_monitoring(self, monitoring_type: str = "coarse_time"):
        """开始监测"""
        self.reset()
        self.is_monitoring = True
        self.start_time = datetime.now()
        self.monitoring_type = monitoring_type
    
    def add_weight_record(self, weight: float):
        """添加重量记录"""
        current_time = time.time()
        self.weight_history.append((current_time, weight))
    
    def get_weight_15s_ago(self) -> Optional[float]:
        """获取15秒前的重量"""
        if not self.weight_history:
            return None
        
        current_time = time.time()
        target_time = current_time - 15.0
        
        # 找到最接近15秒前的重量记录
        for timestamp, weight in self.weight_history:
            if timestamp <= target_time:
                return weight
        
        return None

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
        
        # 物料不足相关回调
        self.on_material_shortage_detected: Optional[Callable[[int, str, bool], None]] = None  # (bucket_id, stage, is_production)
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # 新增：生产监测相关属性
        self.production_states: Dict[int, BucketProductionState] = {}
        self.production_id = ""
        self.target_weight = 0.0
        self.is_production_monitoring = False
        
        # 新增：生产监测回调
        self.on_production_detail_recorded: Optional[Callable[[int, ProductionDetail], None]] = None
        self.on_production_stop_triggered: Optional[Callable[[int, str], None]] = None
        self.on_single_unqualified_triggered: Optional[Callable[[int, float, float], None]] = None  # 新增：单次不合格回调
        
        self.material_check_enabled = False  # 物料检测开关
        self.weight_threshold = 0.3  # 重量变化阈值（克）
        
        # 初始化料斗状态
        self._initialize_bucket_states()
        
        # 初始化生产状态
        self._initialize_production_states()
    
    def _initialize_production_states(self):
        """初始化料斗生产状态"""
        with self.lock:
            for bucket_id in range(1, 7):
                self.production_states[bucket_id] = BucketProductionState(bucket_id)
    
    def _initialize_bucket_states(self):
        """初始化料斗监测状态"""
        with self.lock:
            for bucket_id in range(1, 7):
                self.monitoring_states[bucket_id] = BucketMonitoringState(bucket_id)
    
    def set_material_check_enabled(self, enabled: bool):
        """设置物料监测开关"""
        with self.lock:
            self.material_check_enabled = enabled
            self._log(f"物料监测{'已启用' if enabled else '已禁用'}")
    
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

                # 停止生产监测
                self.stop_production_monitoring()

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
                # 处理原有的料斗监测
                monitoring_buckets = []
                with self.lock:
                    for bucket_id, state in self.monitoring_states.items():
                        if state.is_monitoring:
                            monitoring_buckets.append(bucket_id)
                
                if monitoring_buckets:
                    # 批量读取所有料斗的到量状态和快加状态
                    self._check_target_reached_status(monitoring_buckets)
                
                # 处理生产监测
                if self.is_production_monitoring:
                    self._check_production_states()
                
                # 如果没有任何监测任务，适当延长休眠时间
                if not monitoring_buckets and not self.is_production_monitoring:
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
        检查料斗到量状态和快加状态
        
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
            
            # 读取启动线圈状态（用于物料监测）
            start_states = None
            if self.material_check_enabled:
                start_addresses = [BUCKET_CONTROL_ADDRESSES[i]['StartAddress'] for i in range(1, 7)]
                start_states = self.modbus_client.read_coils(start_addresses[0], len(start_addresses))
                
                if start_states is None:
                    self._log("读取启动线圈状态失败")
            
            # 读取重量数据（用于物料监测）
            weight_data = None
            if self.material_check_enabled:
                weight_addresses = get_all_bucket_weight_addresses()
                weight_registers = []
                for addr in weight_addresses:
                    weight_reg = self.modbus_client.read_holding_registers(addr, 1)
                    if weight_reg:
                        weight_registers.append(weight_reg[0] / 10.0)  # 转换重量单位
                    else:
                        weight_registers.append(0.0)
                weight_data = weight_registers

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
                    
                    # 物料不足检测逻辑
                    if (self.material_check_enabled and start_states and weight_data and 
                        i < len(start_states) and i < len(weight_data)):
                        
                        self._check_material_shortage(bucket_id, state, start_states[i], 
                                                    current_target_reached, weight_data[i])
                    
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
                    
                    # 改进快加状态检测逻辑
                    if (state.monitoring_type == "adaptive_learning" and 
                        coarse_states is not None and i < len(coarse_states)):
                        
                        current_coarse_active = coarse_states[i]
                        
                        # 处理初始状态
                        if not state.coarse_active_initialized:
                            # 第一次读取，初始化状态
                            state.last_coarse_active = current_coarse_active
                            state.coarse_active_initialized = True
                            self._log(f"料斗{bucket_id}快加状态初始化: {current_coarse_active}")
                        else:
                            # 检测状态变化（包括上升沿和下降沿）
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
    
    def _check_material_shortage(self, bucket_id: int, state: BucketMonitoringState, 
                               start_active: bool, target_reached: bool, current_weight: float):
        """
        检查物料不足
        
        Args:
            bucket_id: 料斗ID
            state: 料斗状态
            start_active: 启动状态
            target_reached: 到量状态
            current_weight: 当前重量
        """
        try:
            # 添加重量记录
            state.add_weight_record(current_weight)
            
            # 初始化启动状态
            if not state.start_active_initialized:
                state.last_start_active = start_active
                state.start_active_initialized = True
                return
        
            # 检查是否已监测足够时间（至少15秒）
            if state.start_time:
                monitoring_duration = (datetime.now() - state.start_time).total_seconds()
                if monitoring_duration < 15.0:
                    return  # 监测时间不足15秒，跳过物料不足检测
                
            if len(state.weight_history) < 150:  # 15秒 * 10次/秒 = 150个数据点
                return
            
            # 检查条件：启动=1 且 到量=0
            if start_active and not target_reached:
                # 获取15秒前的重量
                weight_15s_ago = state.get_weight_15s_ago()
                
                if weight_15s_ago is not None:
                    oldest_time = state.weight_history[0][0] if state.weight_history else time.time()
                    if time.time() - oldest_time < 15.0:
                        return  # 数据历史不足15秒，不进行检测
                
                    weight_change = current_weight - weight_15s_ago
                    
                    # 判断是否物料不足（重量变化 < 0.3g）
                    if weight_change < self.weight_threshold and not state.material_shortage_detected:
                        state.material_shortage_detected = True
                        state.material_shortage_time = datetime.now()
                        
                        # 判断是否为生产阶段
                        is_production = (state.monitoring_type == "production")
                        
                        self._log(f"料斗{bucket_id}检测到物料不足！当前重量: {current_weight:.1f}g, "
                                f"15秒前重量: {weight_15s_ago:.1f}g, 重量变化: {weight_change:.1f}g")
                        
                        # 发送停止命令
                        self._handle_material_shortage_stop(bucket_id, is_production)
                    
                        # 延迟触发物料不足事件，避免同时处理多个料斗
                        def trigger_shortage_event():
                            if self.on_material_shortage_detected:
                                try:
                                    self.on_material_shortage_detected(bucket_id, state.monitoring_type, is_production)
                                except Exception as e:
                                    self.logger.error(f"处理料斗{bucket_id}物料不足事件异常: {e}")
                        
                        # 延迟200ms触发，避免多个料斗同时触发
                        import threading
                        threading.Timer(0.2 * bucket_id, trigger_shortage_event).start()
            
            # 更新启动状态
            state.last_start_active = start_active
            
        except Exception as e:
            self.logger.error(f"检查料斗{bucket_id}物料不足异常: {e}")
    
    def _handle_material_shortage_stop(self, bucket_id: int, is_production: bool):
        """
        处理物料不足时的停止命令
        
        Args:
            bucket_id: 料斗ID
            is_production: 是否为生产阶段
        """
        try:
            if is_production:
                # 生产阶段：发送总停止命令
                self._log(f"生产阶段物料不足，发送总停止命令")
                
                # 先发送总启动=0命令
                success1 = self.modbus_client.write_coil(
                    GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                
                # 再发送总停止=1命令
                success2 = self.modbus_client.write_coil(
                    GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True)
                
                if success1 and success2:
                    self._log("总停止命令发送成功")
                else:
                    self._log("总停止命令发送失败")
            else:
                # 非生产阶段：发送该斗停止命令
                self._log(f"非生产阶段料斗{bucket_id}物料不足，发送该斗停止命令")
                
                # 先发送该斗启动=0命令
                success1 = self.modbus_client.write_coil(
                    BUCKET_CONTROL_ADDRESSES[bucket_id]['StartAddress'], False)
                
                # 再发送该斗停止=1命令
                success2 = self.modbus_client.write_coil(
                    BUCKET_CONTROL_ADDRESSES[bucket_id]['StopAddress'], True)
                
                if success1 and success2:
                    self._log(f"料斗{bucket_id}停止命令发送成功")
                else:
                    self._log(f"料斗{bucket_id}停止命令发送失败")
                    
        except Exception as e:
            self.logger.error(f"处理物料不足停止命令异常: {e}")
            
    def handle_material_shortage_continue(self, bucket_id: int, is_production: bool):
        """
        处理物料不足时的继续命令
        
        Args:
            bucket_id: 料斗ID
            is_production: 是否为生产阶段
        """
        try:
            with self.lock:
                state = self.monitoring_states.get(bucket_id)
                if state:
                    state.material_shortage_detected = False
                    state.material_shortage_time = None
            
            if is_production:
                # 生产阶段：发送总启动命令
                self._log("生产阶段物料不足恢复，发送总启动命令")
                
                # 先发送总停止=0命令
                success1 = self.modbus_client.write_coil(
                    GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False)
                
                # 再发送总启动=1命令
                success2 = self.modbus_client.write_coil(
                    GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True)
                
                if success1 and success2:
                    self._log("总启动命令发送成功")
                else:
                    self._log("总启动命令发送失败")
            else:
                # 非生产阶段：发送该斗启动命令
                self._log(f"非生产阶段料斗{bucket_id}物料不足恢复，发送该斗启动命令")
                
                # 先发送该斗停止=0命令
                success1 = self.modbus_client.write_coil(
                    BUCKET_CONTROL_ADDRESSES[bucket_id]['StopAddress'], False)
                
                # 再发送该斗启动=1命令
                success2 = self.modbus_client.write_coil(
                    BUCKET_CONTROL_ADDRESSES[bucket_id]['StartAddress'], True)
                
                if success1 and success2:
                    self._log(f"料斗{bucket_id}启动命令发送成功")
                else:
                    self._log(f"料斗{bucket_id}启动命令发送失败")
                    
        except Exception as e:
            self.logger.error(f"处理物料不足继续命令异常: {e}")
            
    def handle_material_shortage_cancel(self):
        """
        处理物料不足时的取消生产命令
        """
        try:
            self._log("用户选择取消生产，准备返回AI模式自适应自学习界面")
            
            # 停止所有监测
            self.stop_all_monitoring()
            
            # 这里可以添加其他需要的清理逻辑
            
            return True
            
        except Exception as e:
            self.logger.error(f"处理取消生产命令异常: {e}")
            return False
        
    def get_bucket_material_shortage_status(self, bucket_id: int) -> dict:
        """
        获取料斗物料不足状态
        
        Args:
            bucket_id: 料斗ID
            
        Returns:
            dict: 物料不足状态信息
        """
        with self.lock:
            state = self.monitoring_states.get(bucket_id)
            if not state:
                return {'detected': False, 'time': None, 'weight_records': 0}
            
            return {
                'detected': state.material_shortage_detected,
                'time': state.material_shortage_time,
                'weight_records': len(state.weight_history),
                'current_weight': state.weight_history[-1][1] if state.weight_history else 0.0,
                'weight_15s_ago': state.get_weight_15s_ago()
            }
    
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
        
    def start_production_monitoring(self, production_id: str, target_weight: float):
        """
        开始生产监测
        
        Args:
            production_id: 生产编号
            target_weight: 目标重量
        """
        try:
            with self.lock:
                self.production_id = production_id
                self.target_weight = target_weight
                self.is_production_monitoring = True
                
                # 重置所有料斗的生产状态
                for state in self.production_states.values():
                    state.reset()
                    # 开始监测到量状态
                    state.is_monitoring_target = True
                
                self._log(f"开始生产监测，生产编号: {production_id}, 目标重量: {target_weight}g")
                
                # 如果监测线程没有运行，则启动它
                if not self.monitoring_thread or not self.monitoring_thread.is_alive():
                    self.stop_monitoring_flag.clear()
                    self.monitoring_thread = threading.Thread(
                        target=self._monitoring_thread_func,  # 使用现有的监测线程函数
                        daemon=True,
                        name="BucketMonitoring"
                    )
                    self.monitoring_thread.start()
                
        except Exception as e:
            error_msg = f"启动生产监测失败: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
            
    def stop_production_monitoring(self):
        """停止生产监测"""
        try:
            with self.lock:
                self.is_production_monitoring = False
                
                # 重置所有料斗的生产状态
                for state in self.production_states.values():
                    state.reset()
                
                self._log("生产监测已停止")
                
        except Exception as e:
            error_msg = f"停止生产监测失败: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
            
    def _check_production_states(self):
        """检查料斗生产状态"""
        try:
            if not self.is_production_monitoring:
                return
            
            # 批量读取到量状态
            target_reached_addresses = get_all_bucket_target_reached_addresses()
            target_states = self.modbus_client.read_coils(
                target_reached_addresses[0], len(target_reached_addresses))
            
            if target_states is None:
                return
            
            # 批量读取放料状态
            discharge_addresses = get_all_bucket_discharge_addresses()
            discharge_states = self.modbus_client.read_coils(
                discharge_addresses[0], len(discharge_addresses))
            
            if discharge_states is None:
                return
            
            current_time = time.time()
            
            with self.lock:
                for i, bucket_id in enumerate(range(1, 7)):
                    if i >= len(target_states) or i >= len(discharge_states):
                        continue
                    
                    state = self.production_states[bucket_id]
                    current_target = target_states[i]
                    current_discharge = discharge_states[i]
                    
                    # 处理等待重新开始的状态
                    if state.waiting_for_restart:
                        if state.restart_time and current_time >= state.restart_time:
                            # 2秒延迟结束，重新开始监测
                            state.waiting_for_restart = False
                            state.is_monitoring_target = True
                            state.is_monitoring_discharge = False
                            state.target_reached_time = None
                            state.discharge_time = None
                            self._log(f"料斗{bucket_id}重新开始监测")
                        continue
                    
                    # 监测到量状态
                    if state.is_monitoring_target:
                        # 检测到量状态上升沿（从False变为True）
                        if current_target and not state.last_target_reached:
                            state.target_reached_time = current_time
                            state.is_monitoring_target = False
                            state.is_monitoring_discharge = True
                            self._log(f"料斗{bucket_id}检测到到量信号")
                            
                            # 延迟500ms后读取重量并处理
                            threading.Timer(0.5, self._handle_weight_measurement, 
                                          args=(bucket_id,)).start()
                    
                    # 监测放料状态
                    if state.is_monitoring_discharge:
                        # 检测放料状态上升沿（从False变为True）
                        if current_discharge and not state.last_discharge_state:
                            state.discharge_time = current_time
                            state.is_monitoring_discharge = False
                            self._log(f"料斗{bucket_id}检测到放料信号")
                        
                            # 立即读取重量并记录到数据库
                            threading.Timer(0.1, self._handle_weight_measurement_on_discharge, 
                                        args=(bucket_id,)).start()
                            
                            # 延迟0.8s后重新开始监测
                            state.waiting_for_restart = True
                            state.restart_time = current_time + 0.8
                    
                    # 更新上次状态
                    state.last_target_reached = current_target
                    state.last_discharge_state = current_discharge
            
        except Exception as e:
            error_msg = f"检查生产状态异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
            
    def _handle_weight_measurement(self, bucket_id: int):
        """
        处理重量测量和误差计算
        
        Args:
            bucket_id: 料斗ID
        """
        try:
            # 读取实时重量
            weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
            raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)

            if raw_weight_data is None or len(raw_weight_data) == 0:
                self._log(f"料斗{bucket_id}重量读取失败")
                return

            # 处理重量数据
            raw_value = raw_weight_data[0]
            if raw_value > 32767:
                signed_value = raw_value - 65536
            else:
                signed_value = raw_value

            real_weight = signed_value / 10.0
            error_value = real_weight - self.target_weight

            # 获取动态误差阈值（修改这部分）
            lower_error, upper_error = self._get_error_thresholds()

            # 判断是否合格（使用动态阈值）
            is_qualified = lower_error <= error_value <= upper_error

            self._log(f"料斗{bucket_id}重量测量 - 实重: {real_weight:.1f}g, 误差: {error_value:.1f}g, "
                     f"阈值: [{lower_error:+.1f}g, {upper_error:+.1f}g], 合格: {is_qualified}")

            # 处理合格/不合格逻辑
            if is_qualified:
                # 合格：记录有效数据，清零不合格次数
                self._record_production_detail(bucket_id, real_weight, error_value, True, True)
                with self.lock:
                    self.production_states[bucket_id].consecutive_unqualified = 0

            else:
                # 不合格：记录无效数据，累计不合格次数
                self._record_production_detail(bucket_id, real_weight, error_value, False, False)

                with self.lock:
                    state = self.production_states[bucket_id]
                    state.consecutive_unqualified += 1

                    self._log(f"料斗{bucket_id}不合格，连续次数: {state.consecutive_unqualified}")

                    # 发送停止命令
                    self._send_production_stop_commands()

                    # 检查是否连续3次不合格
                    if state.consecutive_unqualified >= 3:
                        self._log(f"料斗{bucket_id}连续3次不合格，触发E002事件")
                        
                        # 触发连续不合格停止事件（E002）
                        if self.on_production_stop_triggered:
                            try:
                                self.on_production_stop_triggered(bucket_id, f"连续{state.consecutive_unqualified}次不合格")
                            except Exception as e:
                                self.logger.error(f"处理生产停止事件异常: {e}")
                    else:
                        self._log(f"料斗{bucket_id}单次不合格，触发取走不合格产品事件")
                        
                        # 触发单次不合格事件
                        if self.on_single_unqualified_triggered:
                            try:
                                self.on_single_unqualified_triggered(bucket_id, real_weight, error_value)
                            except Exception as e:
                                self.logger.error(f"处理单次不合格事件异常: {e}")

        except Exception as e:
            error_msg = f"处理料斗{bucket_id}重量测量异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
            
    def _get_error_thresholds(self) -> tuple:
        """
        获取误差阈值
        
        Returns:
            tuple: (下限误差, 上限误差)
        """
        try:
            # 尝试从出厂设置获取动态阈值
            try:
                from factory_settings_interface import error_config
                lower_error, upper_error = error_config.get_thresholds()
                return lower_error, upper_error
            except ImportError:
                # 如果无法导入，使用默认值
                return -0.2, 0.6
        except Exception as e:
            self.logger.error(f"获取误差阈值异常: {e}")
            return -0.2, 0.6  # 使用默认值
            
    def _record_production_detail(self, bucket_id: int, real_weight: float, 
                                 error_value: float, is_qualified: bool, is_valid: bool):
        """
        记录生产明细到数据库
        
        Args:
            bucket_id: 料斗ID
            real_weight: 实时重量
            error_value: 误差值
            is_qualified: 是否合格
            is_valid: 是否有效
        """
        try:
            if not PRODUCTION_DETAIL_DAO_AVAILABLE:
                self._log("生产明细DAO不可用，无法记录数据")
                return
            
            # 创建生产明细对象
            detail = ProductionDetail(
                production_id=self.production_id,
                bucket_id=bucket_id,
                real_weight=real_weight,
                error_value=error_value,
                is_qualified=is_qualified,
                is_valid=is_valid
            )
            
            # 插入数据库
            success, message, record_id = ProductionDetailDAO.insert_detail(detail)
            
            if success:
                self._log(f"料斗{bucket_id}生产明细已记录，ID: {record_id}")
                
                # 触发记录事件
                if self.on_production_detail_recorded:
                    try:
                        self.on_production_detail_recorded(bucket_id, detail)
                    except Exception as e:
                        self.logger.error(f"处理生产明细记录事件异常: {e}")
            else:
                self._log(f"料斗{bucket_id}生产明细记录失败: {message}")
        
        except Exception as e:
            error_msg = f"记录料斗{bucket_id}生产明细异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
    
    def _send_production_stop_commands(self):
        """发送生产停止命令"""
        try:
            # 在后台线程中执行PLC操作
            def stop_commands_thread():
                try:
                    # 1. 发送总启动=0
                    success1 = self.modbus_client.write_coil(
                        GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                    
                    # 2. 发送总停止=1
                    success2 = self.modbus_client.write_coil(
                        GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True)
                    
                    # 3. 向包装机停止地址70发送0
                    success3 = self.modbus_client.write_coil(
                        GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], False)
                    
                    # 4. 向包装机停止地址70发送1
                    success4 = self.modbus_client.write_coil(
                        GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], True)
                    
                    if success1 and success2 and success3 and success4:
                        self._log("生产停止命令发送成功")
                    else:
                        self._log(f"生产停止命令发送结果: 总启动=0:{success1}, 总停止=1:{success2}, 包装机停止=0:{success3}, 包装机停止=1:{success4}")
                
                except Exception as e:
                    error_msg = f"发送生产停止命令异常: {str(e)}"
                    self.logger.error(error_msg)
                    self._log(error_msg)
            
            # 启动命令发送线程
            threading.Thread(target=stop_commands_thread, daemon=True).start()
            
        except Exception as e:
            error_msg = f"启动生产停止命令线程异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(error_msg)
    
    def get_production_statistics(self) -> Dict:
        """
        获取当前生产的统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            if not PRODUCTION_DETAIL_DAO_AVAILABLE or not self.production_id:
                return {}
            
            return ProductionDetailDAO.get_production_statistics(self.production_id)
            
        except Exception as e:
            error_msg = f"获取生产统计信息异常: {str(e)}"
            self.logger.error(error_msg)
            return {}
    
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