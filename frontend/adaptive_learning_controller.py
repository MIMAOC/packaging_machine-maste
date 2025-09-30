#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应学习阶段控制器 - 修复版本
对慢加时间测定成功的料斗进行自适应学习阶段测定，直至连续3次符合条件或超出3轮各15次测定失败

修复内容：
1. 修复连续成功次数的重置逻辑
2. 修复轮次管理逻辑
3. 确保不符合条件时正确重置成功计数
4. 修改为单个料斗完成事件（不再合并）

作者：AI助手
创建日期：2025-07-24
更新日期：2025-08-07（修改为单个料斗完成事件）
"""

import threading
import time
import logging
from typing import Dict, Optional, Callable, Tuple
from datetime import datetime
from modbus_client import ModbusClient
from bucket_monitoring import BucketMonitoringService, create_bucket_monitoring_service
from clients.adaptive_learning_webapi import analyze_adaptive_learning_parameters
from plc_addresses import BUCKET_PARAMETER_ADDRESSES, BUCKET_MONITORING_ADDRESSES, get_bucket_control_address

try:
    from database.intelligent_learning_dao import IntelligentLearningDAO
    INTELLIGENT_LEARNING_DAO_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入智能学习DAO模块: {e}")
    INTELLIGENT_LEARNING_DAO_AVAILABLE = False

class BucketAdaptiveLearningState:
    """料斗自适应学习阶段状态"""
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_testing = False             # 是否正在测定
        self.is_completed = False           # 是否完成测定
        self.original_target_weight = 0.0  # 原始目标重量
        self.current_round = 1             # 当前轮次（1-3轮）
        self.current_attempt = 0           # 当前轮次内的尝试次数
        self.max_rounds = 3                # 最大轮次
        self.max_attempts_per_round = 15   # 每轮最大尝试次数
        self.consecutive_success_count = 0 # 连续成功次数
        self.consecutive_success_required = 3  # 需要连续成功3次
        self.parameters_initialized = False  # 标记目标重量和落差值是否已初始化
        self.material_name = "未知物料"    # 物料名称（新增）
        
        # 测定过程变量
        self.start_time = None             # 启动时间
        self.coarse_end_time = None        # 快加结束时间
        self.target_reached_time = None    # 到量时间
        self.actual_total_cycle_ms = 0     # 实际总周期
        self.actual_coarse_time_ms = 0     # 实际快加时间
        self.error_value = 0.0             # 误差值
        self.error_message = ""            # 错误消息
        
        # 当前测定使用的参数（从PLC读取的实际值）
        self.current_coarse_advance = 0.0  # 当前快加提前量（从PLC读取）
        self.current_fall_value = 0.4      # 当前落差值（从PLC读取）
        
        # 存储每个料斗的慢加流速值
        self.bucket_fine_flow_rates: Dict[int, float] = {}
        
        # 最终结果存储（测定成功时的参数）
        self.is_success = False            # 最终是否成功
        self.final_coarse_speed = 0        # 最终快加速度
        self.final_fine_speed = 44         # 最终慢加速度
        self.final_coarse_advance = 0.0    # 最终快加提前量
        self.final_fall_value = 0.4        # 最终落差值
        self.failure_stage = ""            # 失败阶段
        self.failure_reason = ""           # 失败原因
    
    def reset_for_new_test(self, original_target_weight: float):
        """重置状态开始新的测定"""
        self.is_testing = False
        self.is_completed = False
        self.original_target_weight = original_target_weight
        self.current_round = 1
        self.current_attempt = 0
        self.consecutive_success_count = 0
        self.parameters_initialized = False
        self.start_time = None
        self.coarse_end_time = None
        self.target_reached_time = None
        self.actual_total_cycle_ms = 0
        self.actual_coarse_time_ms = 0
        self.error_value = 0.0
        self.error_message = ""
        # 🔥 修复：重置为默认值，稍后会从PLC读取实际值
        self.current_coarse_advance = 0.0  # 默认值，稍后从PLC读取
        self.current_fall_value = 0.4      # 默认值，稍后从PLC读取
        # 重置最终结果
        self.is_success = False
        self.final_coarse_speed = 0
        self.final_fine_speed = 44
        self.final_coarse_advance = 0.0
        self.final_fall_value = 0.4
        self.failure_stage = ""
        self.failure_reason = ""
    
    def start_new_round(self):
        """开始新一轮测定"""
        self.current_round += 1
        self.current_attempt = 0
        # 注意：这里不重置连续成功次数，因为连续成功是跨轮次的概念
    
    def start_next_attempt(self):
        """开始下一次尝试"""
        self.is_testing = True
        self.current_attempt += 1
        self.start_time = datetime.now()
        self.coarse_end_time = None
        self.target_reached_time = None
    
    def record_coarse_end(self, coarse_end_time: datetime):
        """记录快加结束时间"""
        self.coarse_end_time = coarse_end_time
        if self.start_time is not None:
            self.actual_coarse_time_ms = int((coarse_end_time - self.start_time).total_seconds() * 1000)
        else:
            self.actual_coarse_time_ms = 0
        self.is_testing = False

    def record_target_reached(self, reached_time: datetime):
        """记录到量时间"""
        self.target_reached_time = reached_time
        if self.start_time is not None:
            self.actual_total_cycle_ms = int((reached_time - self.start_time).total_seconds() * 1000)
        else:
            self.actual_coarse_time_ms=0
        self.is_testing = False
    
    def record_error_value(self, error_value: float):
        """记录误差值"""
        self.error_value = error_value
    
    def record_success(self):
        """记录一次成功"""
        self.consecutive_success_count += 1
    
    def reset_consecutive_success(self):
        """重置连续成功次数"""
        self.consecutive_success_count = 0
    
    def is_current_round_exhausted(self) -> bool:
        """检查当前轮次的尝试次数是否已用完"""
        return self.current_attempt >= self.max_attempts_per_round
    
    def has_reached_max_rounds(self) -> bool:
        """检查是否已达到最大轮次数"""
        return self.current_round >= self.max_rounds
    
    def is_learning_successful(self) -> bool:
        """检查学习是否成功（连续成功3次）"""
        return self.consecutive_success_count >= self.consecutive_success_required
    
    def complete_successfully(self, coarse_speed: int, fine_speed: int):
        """成功完成测定"""
        self.is_testing = False
        self.is_completed = True
        self.is_success = True
        self.final_coarse_speed = coarse_speed
        self.final_fine_speed = fine_speed
        self.final_coarse_advance = self.current_coarse_advance  # 保存当前参数作为最终参数
        self.final_fall_value = self.current_fall_value
    
    def fail_with_error(self, error_message: str, failure_stage: str = "自适应学习阶段"):
        """测定失败"""
        self.is_testing = False
        self.is_completed = True
        self.is_success = False
        self.error_message = error_message
        self.failure_stage = failure_stage
        self.failure_reason = error_message

class AdaptiveLearningController:
    """
    自适应学习阶段控制器
    
    负责对慢加时间测定成功的料斗进行自适应学习阶段测定
    每个料斗独立运行，直至连续3次符合条件或超出3轮各15次测定失败
    
    修复的逻辑：
    1. 符合条件：连续成功次数+1，如果达到3次则成功完成
    2. 不符合条件：连续成功次数重置为0，继续在当前轮次内重试
    3. 当前轮次尝试次数用完：开始新一轮（如果未超过最大轮次）
    4. 超过最大轮次：判定为失败
    """
    
    def __init__(self, modbus_client: ModbusClient):
        """
        初始化自适应学习控制器
        
        Args:
            modbus_client (ModbusClient): Modbus客户端实例
        """
        self.modbus_client = modbus_client
        self.bucket_states: Dict[int, BucketAdaptiveLearningState] = {}
        self.lock = threading.RLock()
    
        # 新增：用于跨线程UI操作的root引用
        self.root_reference = None
        
        # 创建服务实例
        self.monitoring_service = create_bucket_monitoring_service(modbus_client)
        
        # 🔥 修改：移除合并完成事件，改用单个料斗完成事件
        self.on_bucket_completed: Optional[Callable[[int, bool, str], None]] = None  # 单个料斗完成
        self.on_bucket_failed: Optional[Callable[[int, str, str], None]] = None      # (bucket_id, error_message, failed_stage) - 失败回调
        self.on_progress_update: Optional[Callable[[int, int, int, str], None]] = None  # (bucket_id, current_attempt, max_attempts, message)
        self.on_log_message: Optional[Callable[[str], None]] = None
        
        # 物料不足相关回调
        self.on_material_shortage: Optional[Callable[[int, str, bool], None]] = None  # (bucket_id, stage, is_production)
        
        # 新增：跟踪活跃料斗
        self.active_buckets: set = set()  # 正在进行自适应学习的料斗集合
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # 初始化料斗状态
        self._initialize_bucket_states()
        
        # 设置监测服务事件回调
        self.monitoring_service.on_target_reached = self._on_target_reached
        self.monitoring_service.on_coarse_status_changed = self._on_coarse_status_changed
        self.monitoring_service.on_monitoring_log = self._on_monitoring_log
        
        # 设置物料不足回调
        self.monitoring_service.on_material_shortage_detected = self._on_material_shortage_detected
    
    def _initialize_bucket_states(self):
        """初始化料斗状态"""
        with self.lock:
            for bucket_id in range(1, 7):
                self.bucket_states[bucket_id] = BucketAdaptiveLearningState(bucket_id)
                
    def _on_material_shortage_detected(self, bucket_id: int, stage: str, is_production: bool):
        """
        处理物料不足检测事件
        
        Args:
            bucket_id (int): 料斗ID
            stage (str): 当前阶段
            is_production (bool): 是否为生产阶段
        """
        try:
            # 只处理自适应学习阶段的物料不足
            if stage == "adaptive_learning" and not is_production:
                self._log(f"⚠️ 料斗{bucket_id}在自适应学习阶段检测到物料不足，停止该料斗测定")

                # 停止该料斗的自适应学习测定
                self._handle_material_shortage_for_bucket(bucket_id)
            
                # 延迟触发失败回调，避免多个料斗同时触发
                def trigger_shortage_failure():
                    error_message = "料斗物料低于最低水平线或闭合不正常"
                    self._handle_bucket_failure(bucket_id, error_message, stage)
                
                # 延迟200ms * bucket_id，避免多个料斗同时触发
                import threading
                threading.Timer(0.2 * bucket_id, trigger_shortage_failure).start()

        except Exception as e:
            error_msg = f"处理料斗{bucket_id}物料不足事件异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _handle_material_shortage_for_bucket(self, bucket_id: int):
        """
        处理单个料斗的物料不足
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            # 停止该料斗的自适应学习测定
            self.stop_bucket_adaptive_learning_test(bucket_id)
            
            # 更新料斗状态为失败
            with self.lock:
                state = self.bucket_states.get(bucket_id)
                if state:
                    state.fail_with_error("物料不足", "自适应学习阶段")
            
            self._log(f"✅ 料斗{bucket_id}自适应学习测定已因物料不足而停止")
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}物料不足停止逻辑异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def start_adaptive_learning_test(self, bucket_id: int, original_target_weight: float, 
                                    fine_flow_rate: Optional[float] = None) -> bool:
        """
        启动指定料斗的自适应学习阶段测定
        
        Args:
            bucket_id (int): 料斗ID
            original_target_weight (float): 原始目标重量（AI生产时输入的真实重量）
            fine_flow_rate (float): 慢加流速（g/s），来自慢加时间测定结果
            
        Returns:
            bool: 是否成功启动
        """
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    self._log(f"❌ 无效的料斗ID: {bucket_id}")
                    return False
                
                state = self.bucket_states[bucket_id]
                if state.is_testing or state.is_completed:
                    self._log(f"⚠️ 料斗{bucket_id}已在测定中或已完成，跳过")
                    return True
                
                # 将料斗添加到活跃料斗集合
                self.active_buckets.add(bucket_id)
                
                # 重置状态并开始测定
                state.reset_for_new_test(original_target_weight)
                
                # 调试日志：显示传入的慢加流速值
                self._log(f"🔍 调试信息 - 传入的fine_flow_rate: {fine_flow_rate} (类型: {type(fine_flow_rate)})")
                
                # 改进慢加流速验证和存储逻辑
                if fine_flow_rate is not None and fine_flow_rate > 0:
                    state.bucket_fine_flow_rates[bucket_id] = fine_flow_rate
                    self._log(f"📊 料斗{bucket_id}慢加流速: {fine_flow_rate:.3f}g/s (来自慢加时间测定)")
                else:
                    # 提供更详细的错误信息
                    if fine_flow_rate is None:
                        self._log(f"⚠️ 料斗{bucket_id}慢加流速为None，自适应学习分析可能不准确")
                    elif fine_flow_rate <= 0:
                        self._log(f"⚠️ 料斗{bucket_id}慢加流速为无效值: {fine_flow_rate}g/s，自适应学习分析可能不准确")
                    else:
                        self._log(f"⚠️ 料斗{bucket_id}慢加流速验证失败: {fine_flow_rate}，自适应学习分析可能不准确")
            
            # 启用物料监测
            self.monitoring_service.set_material_check_enabled(True)
            self._log(f"🔍 料斗{bucket_id}自适应学习阶段物料监测已启用")
            
            self._log(f"🚀 料斗{bucket_id}开始自适应学习阶段测定，原始目标重量: {original_target_weight}g")
            
            # 启动第一次尝试
            self._start_single_attempt(bucket_id)
            
            return True
            
        except Exception as e:
            error_msg = f"启动料斗{bucket_id}自适应学习测定异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False
    
    def _read_current_parameters_from_plc(self, bucket_id: int) -> bool:
        """
        🔥 从PLC读取当前的快加提前量和落差值（在API分析前调用，确保使用最新参数）
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            bool: 是否成功读取
        """
        try:
            if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                return False
            
            bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
            state = self.bucket_states[bucket_id]
            
            # 读取快加提前量
            coarse_advance_data = self.modbus_client.read_holding_registers(
                bucket_addresses['CoarseAdvance'], 1)
            if coarse_advance_data and len(coarse_advance_data) > 0:
                # 读取需要除以10
                state.current_coarse_advance = coarse_advance_data[0] / 10.0
                self._log(f"📖 料斗{bucket_id}从PLC读取快加提前量: {state.current_coarse_advance}g")
            else:
                self._log(f"❌ 料斗{bucket_id}读取快加提前量失败")
                return False
            
            # 读取落差值
            fall_value_data = self.modbus_client.read_holding_registers(
                bucket_addresses['FallValue'], 1)
            if fall_value_data and len(fall_value_data) > 0:
                # 读取需要除以10
                state.current_fall_value = fall_value_data[0] / 10.0
                self._log(f"📖 料斗{bucket_id}从PLC读取落差值: {state.current_fall_value}g")
            else:
                self._log(f"❌ 料斗{bucket_id}读取落差值失败")
                return False
            
            return True
            
        except Exception as e:
            error_msg = f"料斗{bucket_id}从PLC读取当前参数异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False
    
    def _start_single_attempt(self, bucket_id: int):
        """
        启动单次尝试
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.start_next_attempt()
            
            self._log(f"🔄 料斗{bucket_id}开始第{state.current_round}轮第{state.current_attempt}次自适应学习测定")
            
            # 修复：改进进度计算，确保不会出现负数
            total_progress = max(0, (state.current_round - 1) * state.max_attempts_per_round + state.current_attempt)
            total_max = state.max_rounds * state.max_attempts_per_round
            self._update_progress(bucket_id, total_progress, total_max, 
                                f"第{state.current_round}轮第{state.current_attempt}次测定（连续成功{state.consecutive_success_count}次）")
            
            # 在后台线程执行测定流程
            def attempt_thread():
                self._execute_single_attempt(bucket_id)
            
            thread = threading.Thread(target=attempt_thread, daemon=True, 
                                    name=f"AdaptiveLearning-{bucket_id}-{state.current_round}-{state.current_attempt}")
            thread.start()
            
        except Exception as e:
            error_msg = f"启动料斗{bucket_id}单次尝试异常: {str(e)}"
            self.logger.error(error_msg)
            self._handle_bucket_failure(bucket_id, error_msg)
    
    def _execute_single_attempt(self, bucket_id: int):
        """
        执行单次尝试的完整流程
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            # 步骤1: 写入参数到PLC
            with self.lock:
                state = self.bucket_states[bucket_id]
                is_first_attempt = not state.parameters_initialized
            
            if is_first_attempt:
                # 第一次尝试时，初始化所有参数
                self._log(f"📝 步骤1: 料斗{bucket_id}初始化自适应学习参数（第一次）")
                success = self._write_adaptive_learning_parameters(bucket_id)
                if not success:
                    self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}初始化自适应学习参数失败")
                    return
                
                # 标记为已初始化
                with self.lock:
                    state.parameters_initialized = True
            else:
                # 后续尝试时，不写入目标重量和落差值
                self._log(f"📝 步骤1: 料斗{bucket_id}准备开始测定（第{state.current_round}轮第{state.current_attempt}次）")
                # 不需要写入参数，直接进入下一步
            
            # 步骤2: 启动料斗（互斥保护）
            self._log(f"📤 步骤2: 启动料斗{bucket_id}（互斥保护）")
            success = self._start_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"启动料斗{bucket_id}失败")
                return
            
            # 步骤3: 启动监测（指定监测类型为adaptive_learning）
            self._log(f"🔍 步骤3: 启动料斗{bucket_id}自适应学习监测")
            self.monitoring_service.start_monitoring([bucket_id], "adaptive_learning")
            
        except Exception as e:
            error_msg = f"执行料斗{bucket_id}单次尝试异常: {str(e)}"
            self.logger.error(error_msg)
            self._handle_bucket_failure(bucket_id, error_msg)
    
    def _write_adaptive_learning_parameters(self, bucket_id: int) -> bool:
        """
        写入自适应学习参数：目标重量=原始目标重量、落差值=当前落差值
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            bool: 是否成功
        """
        try:            
            with self.lock:
                state = self.bucket_states[bucket_id]
                original_target_weight = state.original_target_weight
                fall_value = state.current_fall_value
            
            bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
            
            # 目标重量，写入需要×10
            target_weight_plc = int(original_target_weight * 10)
            # 落差值，写入需要×10
            fall_value_plc = int(fall_value * 10)
            
            # 写入目标重量
            success = self.modbus_client.write_holding_register(
                bucket_addresses['TargetWeight'], target_weight_plc)
            if not success:
                self._log(f"❌ 料斗{bucket_id}目标重量写入失败")
                return False
            
            # 写入落差值
            success = self.modbus_client.write_holding_register(
                bucket_addresses['FallValue'], fall_value_plc)
            if not success:
                self._log(f"❌ 料斗{bucket_id}落差值写入失败")
                return False
            
            self._log(f"✅ 料斗{bucket_id}自适应学习参数写入成功（目标重量={original_target_weight}g, 落差值={fall_value}g）")
            return True
            
        except Exception as e:
            error_msg = f"料斗{bucket_id}写入自适应学习参数异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False
    
    def _start_bucket_with_mutex_protection(self, bucket_id: int) -> bool:
        """
        启动料斗（互斥保护）
        先写入停止=0，然后写入启动=1
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            bool: 是否成功
        """
        try:
            start_address = get_bucket_control_address(bucket_id, 'StartAddress')
            stop_address = get_bucket_control_address(bucket_id, 'StopAddress')
            
            # 步骤1: 先发送停止=0命令（互斥保护）
            success = self.modbus_client.write_coil(stop_address, False)
            if not success:
                self._log(f"❌ 料斗{bucket_id}发送停止=0命令（互斥保护）失败")
                return False
            
            # 步骤2: 等待50ms确保互斥保护生效
            time.sleep(0.05)
            
            # 步骤3: 发送启动=1命令
            success = self.modbus_client.write_coil(start_address, True)
            if not success:
                self._log(f"❌ 料斗{bucket_id}发送启动=1命令失败")
                return False
            
            self._log(f"✅ 料斗{bucket_id}启动成功（互斥保护）")
            return True
            
        except Exception as e:
            error_msg = f"启动料斗{bucket_id}异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False
    
    def _on_coarse_status_changed(self, bucket_id: int, coarse_active: bool):
        """
        处理快加状态变化事件（监测服务回调）
        
        Args:
            bucket_id (int): 料斗ID
            coarse_active (bool): 快加状态（True=快加中, False=快加结束）
        """
        try:
            # 检查该料斗是否在自适应学习测定中
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return
                
                state = self.bucket_states[bucket_id]
                if not state.is_testing:
                    return
                
                # 只关心快加从True变为False的时刻（快加结束）
                if not coarse_active and state.coarse_end_time is None:
                    state.record_coarse_end(datetime.now())
                    self._log(f"📍 料斗{bucket_id}快加结束，快加时间: {state.actual_coarse_time_ms}ms")
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}快加状态变化异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _on_target_reached(self, bucket_id: int, time_ms: int):
        """
        处理料斗到量事件（监测服务回调）
        
        Args:
            bucket_id (int): 料斗ID
            time_ms (int): 时间（毫秒，自适应学习测定时这就是总周期时间）
        """
        try:
            # 检查该料斗是否在自适应学习测定中
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return
                
                state = self.bucket_states[bucket_id]
                if not state.is_testing:
                    return
                
                # 记录到量时间
                state.record_target_reached(datetime.now())
            
            self._log(f"📍 料斗{bucket_id}到量，总周期时间: {state.actual_total_cycle_ms}ms")
            
            # 在后台线程处理到量事件
            def process_thread():
                self._process_target_reached_for_adaptive_learning(bucket_id)
            
            thread = threading.Thread(target=process_thread, daemon=True, 
                                    name=f"ProcessAdaptiveTarget-{bucket_id}")
            thread.start()
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}自适应学习到量事件异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _process_target_reached_for_adaptive_learning(self, bucket_id: int):
        """
        处理自适应学习测定的到量流程 - 增强调试版本
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            # 步骤1: 停止监测
            self.monitoring_service.stop_bucket_monitoring(bucket_id)
            
            # 步骤2: 停止料斗（互斥保护）
            self._log(f"🛑 步骤4: 停止料斗{bucket_id}（互斥保护）")
            success = self._stop_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"停止料斗{bucket_id}失败")
                return
            
            # 步骤3: 延迟1000ms后读取实时重量
            self._log(f"⏱️ 步骤5: 等待1000ms后读取料斗{bucket_id}实时重量")
            time.sleep(1)
            
            real_weight = self._read_bucket_weight(bucket_id)
            if real_weight is None:
                self._handle_bucket_failure(bucket_id, f"读取料斗{bucket_id}实时重量失败")
                return
            
            # 计算误差值
            with self.lock:
                state = self.bucket_states[bucket_id]
                original_target_weight = state.original_target_weight
                error_value = real_weight - original_target_weight
                state.record_error_value(error_value)
            
            self._log(f"📊 料斗{bucket_id}实时重量: {real_weight}g, 目标重量: {original_target_weight}g, 误差值: {error_value}g")
            
            # 步骤4: 放料操作
            self._log(f"📤 步骤6: 料斗{bucket_id}执行放料操作")
            success = self._execute_discharge_sequence(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}放料操作失败")
                return
            
            # 步骤5: WebAPI分析参数是否符合条件
            self._log(f"🧠 步骤7: 分析料斗{bucket_id}自适应学习参数")
            
            # 🔥 修复：在API分析前读取最新的PLC参数
            self._log(f"📖 步骤7.1: 从PLC读取料斗{bucket_id}当前参数")
            success = self._read_current_parameters_from_plc(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}读取当前PLC参数失败")
                return
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                # 获取存储的慢加流速
                fine_flow_rate = state.bucket_fine_flow_rates.get(bucket_id)
                
                # 🔥 调试日志：打印所有分析参数
                self.logger.info("=" * 60)
                self.logger.info(f"🔍 料斗{bucket_id}自适应学习分析参数:")
                self.logger.info(f"  original_target_weight: {original_target_weight}")
                self.logger.info(f"  actual_total_cycle_ms: {state.actual_total_cycle_ms}")
                self.logger.info(f"  actual_coarse_time_ms: {state.actual_coarse_time_ms}")
                self.logger.info(f"  error_value: {error_value}")
                self.logger.info(f"  current_coarse_advance: {state.current_coarse_advance} (从PLC读取)")
                self.logger.info(f"  current_fall_value: {state.current_fall_value} (从PLC读取)")
                self.logger.info(f"  fine_flow_rate: {fine_flow_rate}")
                self.logger.info("=" * 60)
                
                analysis_params = {
                    'target_weight': original_target_weight,
                    'actual_total_cycle_ms': state.actual_total_cycle_ms,
                    'actual_coarse_time_ms': state.actual_coarse_time_ms,
                    'error_value': error_value,
                    'current_coarse_advance': state.current_coarse_advance,
                    'current_fall_value': state.current_fall_value,
                    'fine_flow_rate': fine_flow_rate  # 添加慢加流速参数
                }
            
            # 🔥 调试：验证所有参数都不为None
            none_params = [key for key, value in analysis_params.items() if value is None and key != 'fine_flow_rate']
            if none_params:
                error_msg = f"料斗{bucket_id}分析参数中包含None值: {none_params}"
                self.logger.error(f"❌ {error_msg}")
                self._handle_bucket_failure(bucket_id, error_msg)
                return
            
            analysis_success, is_compliant, new_params, analysis_msg = analyze_adaptive_learning_parameters(**analysis_params)
            
            # 🔥 调试日志：打印API分析结果
            self.logger.info("=" * 60)
            self.logger.info(f"🔍 料斗{bucket_id}API分析结果:")
            self.logger.info(f"  analysis_success: {analysis_success}")
            self.logger.info(f"  is_compliant: {is_compliant}")
            self.logger.info(f"  new_params: {new_params}")
            self.logger.info(f"  analysis_msg: {analysis_msg}")
            self.logger.info("=" * 60)
            
            # 步骤6: 处理分析结果
            if not analysis_success:
                # API调用失败
                error_msg = f"料斗{bucket_id}自适应学习参数分析API调用失败: {analysis_msg}"
                self.logger.error(f"❌ {error_msg}")
                self._handle_bucket_failure(bucket_id, error_msg)
                return
            
            if is_compliant:
                # 符合条件，记录一次成功
                with self.lock:
                    state.record_success()
                    consecutive_count = state.consecutive_success_count
                
                self._log(f"✅ 料斗{bucket_id}第{consecutive_count}次符合条件")
                
                # 检查是否达到连续成功要求
                if state.is_learning_successful():
                    # 连续3次成功，自适应学习完成
                    self._handle_bucket_success(bucket_id)
                else:
                    # 还需要继续测定
                    self._log(f"📈 料斗{bucket_id}需连续{state.consecutive_success_required}次成功，当前已成功{consecutive_count}次")
                    time.sleep(1.0)  # 等待1秒后开始下次尝试
                    self._start_single_attempt(bucket_id)
            else:
                # 不符合条件，处理失败或重测
                self._handle_adaptive_learning_not_compliant(bucket_id, new_params, analysis_msg)
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}自适应学习到量流程异常: {str(e)}"
            self.logger.error(error_msg)
            self.logger.exception("🔍 完整异常堆栈:")
            self._handle_bucket_failure(bucket_id, error_msg)
    
    def _handle_adaptive_learning_not_compliant(self, bucket_id: int, new_params: Optional[dict], reason: str):
        """
        处理自适应学习不符合条件的情况
        
        逻辑说明：
        1. 重置连续成功次数为0（这是关键修复）
        2. 检查当前轮次是否已用完尝试次数
        3. 如果当前轮次未用完，继续在当前轮次内重试
        4. 如果当前轮次已用完，开始新一轮（如果未超过最大轮次）
        5. 如果已超过最大轮次，判定为失败
        
        Args:
            bucket_id (int): 料斗ID
            new_params (dict): 新的参数
            reason (str): 不符合的原因
        """
        try:
            # 调试日志：打印输入参数
            self.logger.info("=" * 60)
            self.logger.info(f"🔍 处理料斗{bucket_id}不符合条件 - 输入参数调试:")
            self.logger.info(f"  bucket_id: {bucket_id}")
            self.logger.info(f"  new_params: {new_params} (类型: {type(new_params)})")
            self.logger.info(f"  reason: {reason}")
            self.logger.info("=" * 60)
            
            # 🔥 修复：检查new_params是否为None
            if new_params is None:
                error_msg = f"料斗{bucket_id}API分析失败，未返回调整参数，无法继续测定"
                self.logger.error(f"❌ {error_msg}")
                self._handle_bucket_failure(bucket_id, error_msg)
                return
            
            # 🔥 修复：检查new_params是否为字典类型
            if not isinstance(new_params, dict):
                error_msg = f"料斗{bucket_id}API返回的调整参数格式错误（期望dict，实际{type(new_params)}），无法继续测定"
                self.logger.error(f"❌ {error_msg}")
                self._handle_bucket_failure(bucket_id, error_msg)
                return
            
            # 🔥 修复：检查new_params是否为空字典
            if not new_params:
                error_msg = f"料斗{bucket_id}API返回空的调整参数，可能是参数超出边界范围，无法继续测定"
                self.logger.error(f"❌ {error_msg}")
                self._handle_bucket_failure(bucket_id, error_msg)
                return
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                # 重置连续成功次数
                old_consecutive_count = state.consecutive_success_count
                state.reset_consecutive_success()
                self._log(f"🔄 料斗{bucket_id}不符合条件，连续成功次数从{old_consecutive_count}重置为0")
                
                # 记录调整前的参数值
                old_coarse_advance = state.current_coarse_advance
                old_fall_value = state.current_fall_value
                
                # 更新参数
                params_updated = []
                if 'coarse_advance' in new_params:
                    state.current_coarse_advance = new_params['coarse_advance']
                    params_updated.append(f"快加提前量: {old_coarse_advance}g → {new_params['coarse_advance']}g")
                    self.logger.info(f"📝 料斗{bucket_id}快加提前量更新: {old_coarse_advance}g → {new_params['coarse_advance']}g")
                    
                if 'fall_value' in new_params:
                    state.current_fall_value = new_params['fall_value']
                    params_updated.append(f"落差值: {old_fall_value}g → {new_params['fall_value']}g")
                    self.logger.info(f"📝 料斗{bucket_id}落差值更新: {old_fall_value}g → {new_params['fall_value']}g")
                
                # 检查当前轮次是否已用完尝试次数
                current_round = state.current_round
                current_attempt = state.current_attempt
                is_round_exhausted = state.is_current_round_exhausted()
                has_reached_max_rounds = state.has_reached_max_rounds()
                
                self._log(f"📊 料斗{bucket_id}状态检查: 第{current_round}轮第{current_attempt}次尝试，轮次用完={is_round_exhausted}，达到最大轮次={has_reached_max_rounds}")
        
            self._log(f"🔄 料斗{bucket_id}不符合条件，原因: {reason}")
            if params_updated:
                self._log(f"📝 参数更新: {'; '.join(params_updated)}")
            
            # 步骤1: 更新PLC中的参数
            success = self._update_bucket_parameters(bucket_id, new_params)
            if not success:
                self._handle_bucket_failure(bucket_id, f"更新料斗{bucket_id}参数失败，无法继续测定")
                return
            
            # 步骤2: 等待100ms确保参数写入生效
            time.sleep(0.1)
            
            # 步骤3: 决定下一步行动
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                if is_round_exhausted:
                    # 当前轮次已用完，需要开始新一轮
                    if has_reached_max_rounds:
                        # 已达到最大轮次，测定失败
                        self._handle_bucket_failure(bucket_id, 
                            f"已达最大轮次({state.max_rounds})且连续成功次数未达到要求，自适应学习测定失败")
                        return
                    else:
                        # 开始新一轮
                        state.start_new_round()
                        self._log(f"🔄 料斗{bucket_id}当前轮次已用完，开始第{state.current_round}轮测定")
                
                # 在当前轮次内继续尝试（无论是新轮次的第一次还是当前轮次的继续）
                time.sleep(1.0)  # 等待1秒后开始下次尝试
                self._start_single_attempt(bucket_id)
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}不符合条件异常: {str(e)}"
            self.logger.error(error_msg)
            self.logger.exception("🔍 完整异常堆栈:")
            self._handle_bucket_failure(bucket_id, f"{error_msg}，无法继续测定")
    
    def _update_bucket_parameters(self, bucket_id: int, new_params: dict) -> bool:
        """
        更新料斗PLC参数
        
        Args:
            bucket_id (int): 料斗ID
            new_params (dict): 新的参数
            
        Returns:
            bool: 是否成功
        """
        try:
            bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
            
            # 更新快加提前量
            if 'coarse_advance' in new_params:
                coarse_advance_plc = int(new_params['coarse_advance'] * 10)  # 写入需要×10
                success = self.modbus_client.write_holding_register(
                    bucket_addresses['CoarseAdvance'], coarse_advance_plc)
                if not success:
                    self._log(f"❌ 料斗{bucket_id}快加提前量更新失败")
                    return False
                self._log(f"📝 更新料斗{bucket_id}快加提前量: {new_params['coarse_advance']}g")
            
            # 更新落差值
            if 'fall_value' in new_params:
                fall_value_plc = int(new_params['fall_value'] * 10)  # 写入需要×10
                success = self.modbus_client.write_holding_register(
                    bucket_addresses['FallValue'], fall_value_plc)
                if not success:
                    self._log(f"❌ 料斗{bucket_id}落差值更新失败")
                    return False
                self._log(f"📝 更新料斗{bucket_id}落差值: {new_params['fall_value']}g")
            
            return True
            
        except Exception as e:
            error_msg = f"更新料斗{bucket_id}参数异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False
    
    def _stop_bucket_with_mutex_protection(self, bucket_id: int) -> bool:
        """
        停止料斗（互斥保护）
        先发送启动=0，然后发送停止=1
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            bool: 是否成功
        """
        try:
            start_address = get_bucket_control_address(bucket_id, 'StartAddress')
            stop_address = get_bucket_control_address(bucket_id, 'StopAddress')
            
            # 步骤1: 先发送启动=0命令（互斥保护）
            success = self.modbus_client.write_coil(start_address, False)
            if not success:
                self._log(f"❌ 料斗{bucket_id}发送启动=0命令（互斥保护）失败")
                return False
            
            # 步骤2: 等待50ms确保互斥保护生效
            time.sleep(0.05)
            
            # 步骤3: 发送停止=1命令
            success = self.modbus_client.write_coil(stop_address, True)
            if not success:
                self._log(f"❌ 料斗{bucket_id}发送停止=1命令失败")
                return False
            
            self._log(f"✅ 料斗{bucket_id}停止成功（互斥保护）")
            return True
            
        except Exception as e:
            error_msg = f"停止料斗{bucket_id}异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False
    
    def _read_bucket_weight(self, bucket_id: int) -> Optional[float]:
        """
        读取料斗实时重量
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            Optional[float]: 重量值（克），失败返回None
        """
        try:
            if bucket_id not in BUCKET_MONITORING_ADDRESSES:
                return None
            
            weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
            
            # 读取原始重量值
            raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
            
            if raw_weight_data is not None and len(raw_weight_data) > 0:
                # 重量值需要除以10
                weight_value = raw_weight_data[0] / 10.0
                return weight_value
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"读取料斗{bucket_id}重量异常: {e}")
            return None
    
    def _execute_discharge_sequence(self, bucket_id: int) -> bool:
        """
        执行放料序列：放料=1，延迟1.5s后放料=0
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            bool: 是否成功
        """
        try:
            discharge_address = get_bucket_control_address(bucket_id, 'DischargeAddress')
            
            # 步骤1: 发送放料=1命令
            success = self.modbus_client.write_coil(discharge_address, True)
            if not success:
                self._log(f"❌ 料斗{bucket_id}发送放料=1命令失败")
                return False
            
            self._log(f"💧 料斗{bucket_id}开始放料，等待1.5秒...")
            
            # 步骤2: 延迟1.5秒
            time.sleep(1.5)
            
            # 步骤3: 发送放料=0命令
            success = self.modbus_client.write_coil(discharge_address, False)
            if not success:
                self._log(f"❌ 料斗{bucket_id}发送放料=0命令失败")
                return False
            
            self._log(f"✅ 料斗{bucket_id}放料操作完成")
            return True
            
        except Exception as e:
            error_msg = f"料斗{bucket_id}放料操作异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False
    
    def _handle_bucket_success(self, bucket_id: int):
        """
        处理料斗测定成功（🔥 修改：立即触发单个完成事件）
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                # 获取当前参数作为最终参数
                coarse_speed = self._get_current_coarse_speed(bucket_id)
                fine_speed = self._get_current_fine_speed(bucket_id)
                
                # 标记为成功完成
                state.complete_successfully(coarse_speed, fine_speed)
                
                # 从活跃料斗集合中移除
                self.active_buckets.discard(bucket_id)
                
                # 保存智能学习结果到数据库
                self._save_learning_result_to_database(bucket_id, state)
            
            success_msg = f"🎉 料斗{bucket_id}自适应学习阶段测定成功！连续成功{state.consecutive_success_count}次"
            self._log(success_msg)
            
            # 🔥 修改：立即触发单个料斗完成事件，不再等待所有料斗
            if self.on_bucket_completed:
                try:
                    self.on_bucket_completed(bucket_id, True, success_msg)
                    self._log(f"✅ 料斗{bucket_id}完成事件已触发")
                except Exception as e:
                    self.logger.error(f"料斗{bucket_id}完成事件回调异常: {e}")
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}成功状态异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            
    def _save_learning_result_to_database(self, bucket_id: int, state):
        """
        保存智能学习结果到数据库
        
        Args:
            bucket_id (int): 料斗ID
            state: 料斗状态对象
        """
        try:
            if not INTELLIGENT_LEARNING_DAO_AVAILABLE:
                self._log(f"⚠️ 智能学习DAO不可用，无法保存料斗{bucket_id}的学习结果")
                return
            
            # 获取物料名称（需要从外部传入或存储）
            material_name = getattr(state, 'material_name', '未知物料')
            
            # 保存学习结果
            success, message = IntelligentLearningDAO.save_learning_result(
                material_name=material_name,
                target_weight=state.original_target_weight,
                bucket_id=bucket_id,
                coarse_speed=state.final_coarse_speed,
                fine_speed=state.final_fine_speed,
                coarse_advance=state.final_coarse_advance,
                fall_value=state.final_fall_value
            )
            
            if success:
                self._log(f"✅ 料斗{bucket_id}智能学习结果已保存到数据库: {message}")
                
                # 更新物料状态为"已学习"
                self._update_material_ai_status(material_name)
            else:
                self._log(f"❌ 料斗{bucket_id}智能学习结果保存失败: {message}")
                
        except Exception as e:
            error_msg = f"保存料斗{bucket_id}智能学习结果到数据库异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            
    def _update_material_ai_status(self, material_name: str):
        """
        更新物料AI状态为"已学习"
        
        Args:
            material_name (str): 物料名称
        """
        try:
            from database.material_dao import MaterialDAO
            success, message = MaterialDAO.update_material_ai_status_by_name(material_name, "已学习")
            if success:
                self._log(f"✅ 物料'{material_name}'状态已更新为'已学习'")
            else:
                self._log(f"⚠️ 更新物料'{material_name}'状态失败: {message}")
        except Exception as e:
            self._log(f"⚠️ 更新物料AI状态异常: {str(e)}")
            
    def set_material_name(self, material_name: str):
        """
        设置物料名称（供外部调用）
        
        Args:
            material_name (str): 物料名称
        """
        try:
            # 🔥 修复：立即设置到所有料斗状态中
            with self.lock:
                for state in self.bucket_states.values():
                    state.material_name = material_name
            self._log(f"📝 设置物料名称到所有料斗状态: {material_name}")
            
            # 也保存到实例变量中
            self.current_material_name = material_name
            self._log(f"📝 已保存当前物料名称到实例变量: {material_name}")
            
        except Exception as e:
            self._log(f"❌ 设置物料名称异常: {str(e)}")
    
    def _handle_bucket_failure(self, bucket_id: int, error_message: str, failed_stage: str = "adaptive_learning"):
        """
        处理料斗测定失败（不立即弹窗，收集结果）
        
        Args:
            bucket_id (int): 料斗ID
            error_message (str): 错误消息
        """
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.fail_with_error(error_message, "自适应学习阶段")
                
                # 从活跃料斗集合中移除
                self.active_buckets.discard(bucket_id)
            
            total_attempts = (state.current_round-1) * state.max_attempts_per_round + state.current_attempt
            failure_msg = f"❌ 料斗{bucket_id}自适应学习阶段测定失败: {error_message}（共{state.current_round}轮{total_attempts}次尝试）"
            self._log(failure_msg)
        
            # 修复：使用root.after确保在主线程中执行UI操作
            def trigger_failure_callback():
                if self.on_bucket_failed:
                    try:
                        self.on_bucket_failed(bucket_id, error_message, failed_stage)
                    except Exception as e:
                        self.logger.error(f"失败事件回调异常: {e}")
            
            # 延迟100ms执行，避免同时触发多个弹窗
            if self.root_reference:
                self.root_reference.after(100, trigger_failure_callback)
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}失败状态异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _get_current_coarse_speed(self, bucket_id: int) -> int:
        """
        获取料斗当前快加速度
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            int: 快加速度，失败返回0
        """
        try:
            if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                return 0
            
            coarse_speed_address = BUCKET_PARAMETER_ADDRESSES[bucket_id]['CoarseSpeed']
            data = self.modbus_client.read_holding_registers(coarse_speed_address, 1)
            
            if data and len(data) > 0:
                return data[0]
            else:
                return 0
                
        except Exception as e:
            self.logger.error(f"读取料斗{bucket_id}快加速度异常: {e}")
            return 0
    
    def _get_current_fine_speed(self, bucket_id: int) -> int:
        """
        获取料斗当前慢加速度
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            int: 慢加速度，失败返回44
        """
        try:
            if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                return 44
            
            fine_speed_address = BUCKET_PARAMETER_ADDRESSES[bucket_id]['FineSpeed']
            data = self.modbus_client.read_holding_registers(fine_speed_address, 1)
            
            if data and len(data) > 0:
                return data[0]
            else:
                return 44
                
        except Exception as e:
            self.logger.error(f"读取料斗{bucket_id}慢加速度异常: {e}")
            return 44
    
    def handle_material_shortage_continue(self, bucket_id: int) -> Tuple[bool, str]:
        """
        处理物料不足继续操作
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            # 调用监测服务的继续方法
            self.monitoring_service.handle_material_shortage_continue(bucket_id, False)  # 非生产阶段
            
            # 获取料斗状态
            with self.lock:
                state = self.bucket_states.get(bucket_id)
                if not state:
                    return False, f"无效的料斗ID: {bucket_id}"
                
                # 重置失败状态，准备重新启动
                state.is_testing = False
                state.is_completed = False
                state.error_message = ""
                state.failure_stage = ""
                state.failure_reason = ""
                original_target_weight = state.original_target_weight
                fine_flow_rate = state.bucket_fine_flow_rates.get(bucket_id)
                
                # 重新添加到活跃料斗集合
                self.active_buckets.add(bucket_id)
            
            # 重新启动该料斗的自适应学习测定
            restart_success = self.start_adaptive_learning_test(bucket_id, original_target_weight, fine_flow_rate)
            
            if restart_success:
                success_msg = f"料斗{bucket_id}物料不足已恢复，自适应学习测定重新启动成功"
                self._log(f"✅ {success_msg}")
                return True, success_msg
            else:
                error_msg = f"料斗{bucket_id}自适应学习测定重新启动失败"
                self._log(f"❌ {error_msg}")
                return False, error_msg
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}物料不足继续操作异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False, error_msg
    
    def handle_material_shortage_cancel(self) -> Tuple[bool, str]:
        """
        处理物料不足取消生产操作
        
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            self._log("📢 用户选择取消生产，停止所有自适应学习测定...")
            
            # 停止所有自适应学习测定
            self.stop_all_adaptive_learning_test()
            
            # 调用监测服务的取消方法
            cancel_success = self.monitoring_service.handle_material_shortage_cancel()
            
            success_msg = "✅ 已取消生产，所有自适应学习测定已停止，准备返回AI模式自适应自学习界面"
            self._log(success_msg)
            
            return cancel_success, success_msg
            
        except Exception as e:
            error_msg = f"处理取消生产操作异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False, error_msg
    
    def stop_bucket_adaptive_learning_test(self, bucket_id: int):
        """
        停止指定料斗的自适应学习测定
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            with self.lock:
                if bucket_id in self.bucket_states:
                    state = self.bucket_states[bucket_id]
                    if state.is_testing:
                        state.is_testing = False
                        self._log(f"🛑 料斗{bucket_id}自适应学习测定已停止")
                
                # 从活跃料斗集合中移除
                self.active_buckets.discard(bucket_id)
            
            # 停止该料斗的监测
            self.monitoring_service.stop_bucket_monitoring(bucket_id)
            
            # 发送该料斗的停止命令（互斥保护）
            success = self._stop_bucket_with_mutex_protection(bucket_id)
            if success:
                self._log(f"✅ 料斗{bucket_id}PLC停止命令发送成功")
            else:
                self._log(f"⚠️ 料斗{bucket_id}PLC停止命令发送失败")
            
        except Exception as e:
            error_msg = f"停止料斗{bucket_id}自适应学习测定异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def stop_all_adaptive_learning_test(self):
        """停止所有料斗的自适应学习测定"""
        try:
            with self.lock:
                for state in self.bucket_states.values():
                    state.is_testing = False
                
                # 清空活跃料斗集合
                self.active_buckets.clear()
            
            # 禁用物料监测
            self.monitoring_service.set_material_check_enabled(False)
            self._log("⏸️ 自适应学习阶段物料监测已禁用")
            
            # 停止监测服务
            self.monitoring_service.stop_all_monitoring()
            
            self._log("🛑 所有料斗的自适应学习测定已停止")
            
        except Exception as e:
            error_msg = f"停止所有自适应学习测定异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def get_bucket_state(self, bucket_id: int) -> Optional[BucketAdaptiveLearningState]:
        """
        获取料斗测定状态
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            Optional[BucketAdaptiveLearningState]: 料斗状态
        """
        with self.lock:
            return self.bucket_states.get(bucket_id)
    
    def _update_progress(self, bucket_id: int, current_progress: int, max_progress: int, message: str):
        """更新进度"""
        if self.on_progress_update:
            try:
                self.on_progress_update(bucket_id, current_progress, max_progress, message)
            except Exception as e:
                self.logger.error(f"进度更新事件回调异常: {e}")
    
    def _log(self, message: str):
        """记录日志"""
        self.logger.info(message)
        if self.on_log_message:
            try:
                self.on_log_message(message)
            except Exception as e:
                self.logger.error(f"日志事件回调异常: {e}")
    
    def _on_monitoring_log(self, message: str):
        """监测服务日志回调"""
        self._log(f"[自适应学习监测] {message}")
    
    def dispose(self):
        """释放资源"""
        try:
            self.stop_all_adaptive_learning_test()
            self.monitoring_service.dispose()
            self._log("自适应学习控制器资源已释放")
        except Exception as e:
            self.logger.error(f"释放控制器资源异常: {e}")

def create_adaptive_learning_controller(modbus_client: ModbusClient) -> AdaptiveLearningController:
    """
    创建自适应学习控制器实例的工厂函数
    
    Args:
        modbus_client (ModbusClient): Modbus客户端实例
        
    Returns:
        AdaptiveLearningController: 控制器实例
    """
    return AdaptiveLearningController(modbus_client)