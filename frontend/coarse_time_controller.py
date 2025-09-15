#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快加时间测定控制器 - 支持重新学习功能
整合快加时间监测、分析和控制功能，实现6个料斗独立的快加时间测定

作者：AI助手
创建日期：2025-07-23
更新日期：2025-08-04（增加重新学习功能）
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
from modbus_client import ModbusClient
from bucket_monitoring import BucketMonitoringService, create_bucket_monitoring_service
from clients.coarse_time_webapi import analyze_coarse_time
from bucket_control_extended import BucketControlExtended, create_bucket_control_extended
from flight_material_controller import FlightMaterialTestController, create_flight_material_test_controller
from fine_time_controller import FineTimeTestController, create_fine_time_test_controller
from plc_addresses import BUCKET_PARAMETER_ADDRESSES

class BucketCoarseTimeState:
    """料斗快加时间测定状态"""
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_testing = False             # 是否正在测定
        self.is_completed = False           # 是否完成测定
        self.target_weight = 0.0           # 目标重量
        self.current_coarse_speed = 0      # 当前快加速度
        self.attempt_count = 0             # 尝试次数
        self.max_attempts = 15             # 最大尝试次数
        self.start_time = None             # 开始时间
        self.last_coarse_time_ms = 0       # 最后一次快加时间
        self.error_message = ""            # 错误消息
        self.original_target_weight = 0.0  # 保存原始目标重量（AI生产时输入的）
        self.failed_stage = None           # 失败的阶段 ("coarse_time", "flight_material", "fine_time", "adaptive_learning")
        self.last_flight_material_value = 0.0  # 最后一次成功的飞料值
    
    def reset_for_new_test(self, target_weight: float, coarse_speed: int):
        """重置状态开始新的测定"""
        self.is_testing = False
        self.is_completed = False
        self.target_weight = target_weight
        self.original_target_weight = target_weight  # 保存原始目标重量
        self.current_coarse_speed = coarse_speed
        self.attempt_count = 0
        self.start_time = None
        self.last_coarse_time_ms = 0
        self.error_message = ""
        self.failed_stage = None
        # 保留上次成功的飞料值，用于重新学习
        # self.last_flight_material_value = 0.0  # 不重置，保留历史值
    
    def start_attempt(self):
        """开始一次尝试"""
        self.is_testing = True
        self.attempt_count += 1
        self.start_time = datetime.now()
    
    def complete_successfully(self):
        """成功完成测定"""
        self.is_testing = False
        self.is_completed = True
        self.failed_stage = None
    
    def fail_with_error(self, error_message: str, failed_stage: str = None):
        """测定失败"""
        self.is_testing = False
        self.is_completed = True
        self.error_message = error_message
        self.failed_stage = failed_stage

class CoarseTimeTestController:
    """
    快加时间测定控制器
    
    负责协调监测服务、WebAPI分析服务和料斗控制服务
    实现6个料斗独立的快加时间测定流程
    支持重新学习功能
    """
    
    def __init__(self, modbus_client: ModbusClient):
        """
        初始化快加时间测定控制器
        
        Args:
            modbus_client (ModbusClient): Modbus客户端实例
        """
        self.modbus_client = modbus_client
        self.bucket_states: Dict[int, BucketCoarseTimeState] = {}
        self.lock = threading.RLock()
        
        # 创建服务实例
        self.monitoring_service = create_bucket_monitoring_service(modbus_client)
        self.bucket_control = create_bucket_control_extended(modbus_client)
        
        # 创建飞料值测定控制器
        self.flight_material_controller = create_flight_material_test_controller(modbus_client)
        
        # 创建慢加时间测定控制器
        self.fine_time_controller = create_fine_time_test_controller(modbus_client)
        
        # 事件回调
        self.on_bucket_completed: Optional[Callable[[int, bool, str], None]] = None  # (bucket_id, success, message)
        self.on_bucket_failed: Optional[Callable[[int, str, str], None]] = None      # (bucket_id, error_message, failed_stage) - 新增失败回调
        self.on_progress_update: Optional[Callable[[int, int, int, str], None]] = None  # (bucket_id, current_attempt, max_attempts, message)
        self.on_log_message: Optional[Callable[[str], None]] = None
        
        # 物料不足相关回调
        self.on_material_shortage: Optional[Callable[[int, str, bool], None]] = None  # (bucket_id, stage, is_production)
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # 初始化料斗状态
        self._initialize_bucket_states()
        
        # 设置监测服务事件回调
        self.monitoring_service.on_target_reached = self._on_target_reached
        self.monitoring_service.on_monitoring_log = self._on_monitoring_log
        
        # 设置物料不足回调
        self.monitoring_service.on_material_shortage_detected = self._on_material_shortage_detected
        
        # 设置飞料值测定控制器事件回调
        self.flight_material_controller.on_bucket_completed = self._on_flight_material_completed
        self.flight_material_controller.on_progress_update = self._on_flight_material_progress_update
        self.flight_material_controller.on_log_message = self._on_flight_material_log
        
        # 设置慢加时间测定控制器事件回调
        self.fine_time_controller.on_bucket_completed = self._on_fine_time_completed
        self.fine_time_controller.on_progress_update = self._on_fine_time_progress_update
        self.fine_time_controller.on_log_message = self._on_fine_time_log
        
        self.material_name = "未知物料"  # 默认值
        self.current_material_name = "未知物料"  # 兼容性
    
    def _initialize_bucket_states(self):
        """初始化料斗状态"""
        with self.lock:
            for bucket_id in range(1, 4):
                self.bucket_states[bucket_id] = BucketCoarseTimeState(bucket_id)
    
    def set_material_name(self, material_name: str):
        """
        设置物料名称
        
        Args:
            material_name (str): 物料名称
        """
        try:
            self.material_name = material_name
            self.current_material_name = material_name
            
            # 传递给飞料值控制器
            if hasattr(self.flight_material_controller, 'set_material_name'):
                self.flight_material_controller.set_material_name(material_name)
                self._log(f"📝 已将物料名称'{material_name}'传递给飞料值控制器")
            
            # 传递给慢加时间控制器
            if hasattr(self.fine_time_controller, 'set_material_name'):
                self.fine_time_controller.set_material_name(material_name)
                self._log(f"📝 已将物料名称'{material_name}'传递给慢加时间控制器")
            
            # 如果自适应学习控制器已创建，也传递给它
            if hasattr(self, 'adaptive_learning_controller') and self.adaptive_learning_controller:
                if hasattr(self.adaptive_learning_controller, 'set_material_name'):
                    self.adaptive_learning_controller.set_material_name(material_name)
                    self._log(f"📝 已将物料名称'{material_name}'传递给自适应学习控制器")
            
            self._log(f"📝 快加时间控制器设置物料名称: {material_name}")
            
        except Exception as e:
            error_msg = f"设置物料名称异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
        
    def get_current_material_name(self) -> str:
        """
        获取当前物料名称
        
        Returns:
            str: 当前物料名称
        """
        return getattr(self, 'material_name', '未知物料')
    
    def start_coarse_time_test_after_parameter_writing(self, target_weight: float, coarse_speed: int) -> Tuple[bool, str]:
        """
        在参数写入完成后启动快加时间测定
        这是在AI模式的步骤3（写入参数到所有料斗）后调用的新功能
        
        Args:
            target_weight (float): 目标重量（克）
            coarse_speed (int): 快加速度
            
        Returns:
            Tuple[bool, str]: (是否成功启动, 操作消息)
        """
        try:
            self._log("=" * 60)
            self._log("🚀 开始快加时间测定流程")
            self._log("=" * 60)
            
            # 步骤1: 重置所有料斗状态
            with self.lock:
                for bucket_id in range(1, 4):
                    state = self.bucket_states[bucket_id]
                    state.reset_for_new_test(target_weight, coarse_speed)
            
            self._log(f"📊 测定参数: 目标重量={target_weight}g, 快加速度={coarse_speed}档")
            
            # 启用物料监测
            self.monitoring_service.set_material_check_enabled(True)
            self._log("🔍 物料不足监测已启用")
            
            # 步骤2: 一次性启动所有6个料斗（带互斥保护）
            self._log("🔄 步骤1: 启动所有6个料斗...")
            start_success, start_msg = self.bucket_control.start_all_buckets_with_mutex_protection()
            if not start_success:
                error_msg = f"启动所有料斗失败: {start_msg}"
                self._log(f"❌ {error_msg}")
                return False, error_msg
            
            self._log(f"✅ {start_msg}")
            
            # 步骤3: 标记所有料斗开始尝试并启动监测
            with self.lock:
                for bucket_id in range(1, 4):
                    state = self.bucket_states[bucket_id]
                    state.start_attempt()
            
            # 步骤4: 启动快加时间监测服务
            self._log("🔍 步骤2: 启动快加时间监测服务...")
            bucket_ids = list(range(1, 7))
            self.monitoring_service.start_monitoring(bucket_ids, "coarse_time")
            
            # 步骤5: 更新进度
            for bucket_id in range(1, 4):
                self._update_progress(bucket_id, 1, 15, "正在进行快加时间测定...")
            
            success_msg = "✅ 快加时间测定流程已启动，正在监测6个料斗的到量状态"
            self._log(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"启动快加时间测定流程异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False, error_msg
        
    def _on_material_shortage_detected(self, bucket_id: int, stage: str, is_production: bool):
        """
        处理物料不足检测事件
        
        Args:
            bucket_id (int): 料斗ID
            stage (str): 当前阶段
            is_production (bool): 是否为生产阶段
        """
        try:
            stage_name = self._get_stage_name(stage)

            # 非生产阶段（快加时间测定、飞料值测定、慢加时间测定、自适应学习）
            if not is_production:
                self._log(f"⚠️ 料斗{bucket_id}在{stage_name}阶段检测到物料不足，停止该料斗")

                # 停止该料斗的相关测定流程
                self._handle_material_shortage_for_bucket(bucket_id, stage)

                # 直接触发失败回调，使用指定的错误信息
                error_message = "料斗物料低于最低水平线或闭合不正常"
                self._handle_bucket_failure(bucket_id, error_message, stage)

            else:
                # 生产阶段的处理在生产控制器中处理
                self._log(f"⚠️ 生产阶段检测到物料不足，应由生产控制器处理")
        
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}物料不足事件异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            
    def _handle_material_shortage_for_bucket(self, bucket_id: int, stage: str):
        """
        处理单个料斗的物料不足
        
        Args:
            bucket_id (int): 料斗ID
            stage (str): 当前阶段
        """
        try:
            # 根据不同阶段停止相应的测定流程
            if stage == "coarse_time":
                # 快加时间测定阶段：停止该料斗的监测
                self.monitoring_service.stop_bucket_monitoring(bucket_id)
                
                # 更新料斗状态为失败
                with self.lock:
                    state = self.bucket_states.get(bucket_id)
                    if state:
                        state.fail_with_error("物料不足", "coarse_time")
                
            elif stage == "flight_material":
                # 飞料值测定阶段：停止该料斗的飞料值测定
                if hasattr(self.flight_material_controller, 'stop_bucket_flight_material_test'):
                    self.flight_material_controller.stop_bucket_flight_material_test(bucket_id)
                
            elif stage == "fine_time":
                # 慢加时间测定阶段：停止该料斗的慢加时间测定
                if hasattr(self.fine_time_controller, 'stop_bucket_fine_time_test'):
                    self.fine_time_controller.stop_bucket_fine_time_test(bucket_id)
                
            elif stage == "adaptive_learning":
                # 自适应学习阶段：停止该料斗的监测
                self.monitoring_service.stop_bucket_monitoring(bucket_id)
            
            self._log(f"✅ 料斗{bucket_id}在{self._get_stage_name(stage)}阶段的测定已停止")
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}物料不足停止逻辑异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            
    def handle_material_shortage_continue(self, bucket_id: int, stage: str) -> Tuple[bool, str]:
        """
        处理物料不足继续操作
        
        Args:
            bucket_id (int): 料斗ID
            stage (str): 当前阶段
            
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            # 调用监测服务的继续方法
            self.monitoring_service.handle_material_shortage_continue(bucket_id, False)  # 非生产阶段
            
            # 根据不同阶段重新启动相应的测定流程
            if stage == "coarse_time":
                # 快加时间测定阶段：重新启动该料斗
                with self.lock:
                    state = self.bucket_states.get(bucket_id)
                    if not state:
                        return False, f"无效的料斗ID: {bucket_id}"
                    
                    # 重置失败状态
                    state.is_testing = True
                    state.is_completed = False
                    state.error_message = ""
                    state.failed_stage = None
                
                # 重新启动该料斗的监测
                self.monitoring_service.restart_bucket_monitoring(bucket_id, "coarse_time")
                
                # 更新进度
                self._update_progress(bucket_id, state.attempt_count, state.max_attempts, 
                                    "物料不足已恢复，继续快加时间测定...")
                
            elif stage == "flight_material":
                # 飞料值测定阶段：重新启动飞料值测定
                with self.lock:
                    state = self.bucket_states.get(bucket_id)
                    target_weight = state.target_weight if state else 200.0
                
                flight_success = self.flight_material_controller.start_flight_material_test(bucket_id, target_weight)
                if not flight_success:
                    return False, f"料斗{bucket_id}飞料值测定重新启动失败"
                
            elif stage == "fine_time":
                # 慢加时间测定阶段：重新启动慢加时间测定
                with self.lock:
                    state = self.bucket_states.get(bucket_id)
                    if not state:
                        return False, f"无效的料斗ID: {bucket_id}"
                    target_weight = state.target_weight
                    flight_material_value = state.last_flight_material_value
                
                fine_time_success = self.fine_time_controller.start_fine_time_test(
                    bucket_id, target_weight, flight_material_value)
                if not fine_time_success:
                    return False, f"料斗{bucket_id}慢加时间测定重新启动失败"
                
            elif stage == "adaptive_learning":
                # 自适应学习阶段：重新启动监测
                self.monitoring_service.restart_bucket_monitoring(bucket_id, "adaptive_learning")
            
            success_msg = f"料斗{bucket_id}物料不足已恢复，{self._get_stage_name(stage)}继续进行"
            self._log(f"✅ {success_msg}")
            return True, success_msg
            
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
            self._log("📢 用户选择取消生产，停止所有测定流程...")
            
            # 停止所有测定流程
            self.stop_all_coarse_time_test()
            
            # 调用监测服务的取消方法
            cancel_success = self.monitoring_service.handle_material_shortage_cancel()
            
            success_msg = "✅ 已取消生产，所有测定流程已停止，准备返回AI模式自适应自学习界面"
            self._log(success_msg)
            
            return cancel_success, success_msg
            
        except Exception as e:
            error_msg = f"处理取消生产操作异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False, error_msg
    
    def restart_bucket_learning(self, bucket_id: int, restart_mode: str = "from_beginning") -> Tuple[bool, str]:
        """
        重新开始指定料斗的学习流程
        
        Args:
            bucket_id (int): 料斗ID
            restart_mode (str): 重新学习模式
                - "from_beginning": 从头开始学习（从快加时间测定开始）
                - "from_current_stage": 从当前失败阶段开始学习
                
        Returns:
            Tuple[bool, str]: (是否成功启动, 操作消息)
        """
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return False, f"无效的料斗ID: {bucket_id}"
                
                state = self.bucket_states[bucket_id]
                target_weight = state.original_target_weight
                coarse_speed = state.current_coarse_speed
                failed_stage = state.failed_stage
            
            self._log(f"🔄 料斗{bucket_id}重新学习: 模式={restart_mode}, 失败阶段={failed_stage}")
            
            # 重新启用物料监测（如果之前被禁用）
            self.monitoring_service.set_material_check_enabled(True)
            
            if restart_mode == "from_beginning":
                # 从头开始学习：重置状态，从快加时间测定开始
                with self.lock:
                    state.reset_for_new_test(target_weight, coarse_speed)
                
                return self._restart_single_bucket_coarse_time(bucket_id, target_weight, coarse_speed)
                
            elif restart_mode == "from_current_stage":
                # 从当前失败阶段开始学习
                if not failed_stage:
                    return False, f"料斗{bucket_id}没有失败阶段信息，无法从当前阶段重新学习"
                
                if failed_stage == "coarse_time":
                    # 快加时间测定失败，重新开始快加时间测定
                    with self.lock:
                        state.reset_for_new_test(target_weight, coarse_speed)
                    return self._restart_single_bucket_coarse_time(bucket_id, target_weight, coarse_speed)
                    
                elif failed_stage == "flight_material":
                    # 飞料值测定失败，重新开始飞料值测定
                    flight_success = self.flight_material_controller.start_flight_material_test(bucket_id, target_weight)
                    if flight_success:
                        with self.lock:
                            state.is_testing = True
                            state.failed_stage = None
                        return True, f"料斗{bucket_id}飞料值测定重新启动成功"
                    else:
                        return False, f"料斗{bucket_id}飞料值测定重新启动失败"
                        
                elif failed_stage == "fine_time":
                    # 慢加时间测定失败，重新开始慢加时间测定
                    flight_material_value = state.last_flight_material_value if state.last_flight_material_value > 0 else 0.0
                    fine_time_success = self.fine_time_controller.start_fine_time_test(
                        bucket_id, target_weight, flight_material_value)
                    if fine_time_success:
                        with self.lock:
                            state.is_testing = True
                            state.failed_stage = None
                        return True, f"料斗{bucket_id}慢加时间测定重新启动成功"
                    else:
                        return False, f"料斗{bucket_id}慢加时间测定重新启动失败"
                        
                elif failed_stage == "adaptive_learning":
                    # 自适应学习失败，这通常意味着需要从头开始
                    with self.lock:
                        state.reset_for_new_test(target_weight, coarse_speed)
                    return self._restart_single_bucket_coarse_time(bucket_id, target_weight, coarse_speed)
                
                else:
                    return False, f"未知的失败阶段: {failed_stage}"
            
            else:
                return False, f"未知的重新学习模式: {restart_mode}"
                
        except Exception as e:
            error_msg = f"料斗{bucket_id}重新学习异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _restart_single_bucket_coarse_time(self, bucket_id: int, target_weight: float, coarse_speed: int) -> Tuple[bool, str]:
        """
        重新启动单个料斗的快加时间测定
        
        Args:
            bucket_id (int): 料斗ID
            target_weight (float): 目标重量
            coarse_speed (int): 快加速度
            
        Returns:
            Tuple[bool, str]: (是否成功启动, 操作消息)
        """
        try:
            # 更新PLC中的参数
            if bucket_id in BUCKET_PARAMETER_ADDRESSES:
                addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
                
                # 更新目标重量
                target_weight_plc = int(target_weight * 10)
                if not self.modbus_client.write_holding_register(addresses['TargetWeight'], target_weight_plc):
                    return False, f"料斗{bucket_id}目标重量参数写入失败"
                
                # 更新快加速度
                if not self.modbus_client.write_holding_register(addresses['CoarseSpeed'], coarse_speed):
                    return False, f"料斗{bucket_id}快加速度参数写入失败"
            
            # 等待参数写入生效
            time.sleep(0.1)
            
            # 重新启动该料斗
            restart_success, restart_msg = self.bucket_control.restart_single_bucket(bucket_id)
            if not restart_success:
                return False, f"重新启动料斗{bucket_id}失败: {restart_msg}"
            
            # 更新状态
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.start_attempt()
            
            # 重新启动该料斗的监测
            self.monitoring_service.restart_bucket_monitoring(bucket_id, "coarse_time")
            
            # 更新进度
            self._update_progress(bucket_id, 1, 15, "重新开始快加时间测定...")
            
            success_msg = f"料斗{bucket_id}快加时间测定重新启动成功"
            self._log(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"重新启动料斗{bucket_id}快加时间测定异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _on_target_reached(self, bucket_id: int, coarse_time_ms: int):
        """
        处理料斗到量事件（监测服务回调）
        
        Args:
            bucket_id (int): 料斗ID
            coarse_time_ms (int): 快加时间（毫秒）
        """
        try:
            self._log(f"📍 料斗{bucket_id}到量，快加时间: {coarse_time_ms}ms")
            
            # 获取料斗状态
            with self.lock:
                if bucket_id not in self.bucket_states:
                    self._log(f"❌ 无效的料斗ID: {bucket_id}")
                    return
                
                state = self.bucket_states[bucket_id]
                if not state.is_testing:
                    self._log(f"⚠️ 料斗{bucket_id}不在测定状态，忽略到量事件")
                    return
                
                state.last_coarse_time_ms = coarse_time_ms
            
            # 在后台线程处理到量事件，避免阻塞监测服务
            def process_target_reached():
                self._process_bucket_target_reached(bucket_id, coarse_time_ms)
            
            processing_thread = threading.Thread(
                target=process_target_reached,
                daemon=True,
                name=f"ProcessTargetReached-{bucket_id}"
            )
            processing_thread.start()
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}到量事件异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _process_bucket_target_reached(self, bucket_id: int, coarse_time_ms: int):
        """
        处理料斗到量的完整流程
        
        Args:
            bucket_id (int): 料斗ID
            coarse_time_ms (int): 快加时间（毫秒）
        """
        try:
            # 步骤1: 停止料斗并放料
            self._log(f"🛑 步骤1: 停止料斗{bucket_id}并执行放料...")
            stop_success, stop_msg = self.bucket_control.execute_bucket_stop_and_discharge_sequence(bucket_id)
            if not stop_success:
                self._handle_bucket_failure(bucket_id, f"停止和放料失败: {stop_msg}", "coarse_time")
                return
            
            self._log(f"✅ 料斗{bucket_id}停止和放料完成")
            
            # 步骤2: 获取当前状态
            with self.lock:
                state = self.bucket_states[bucket_id]
                target_weight = state.target_weight
                current_speed = state.current_coarse_speed
            
            # 步骤3: 通过WebAPI分析快加时间
            self._log(f"🧠 步骤2: 分析料斗{bucket_id}快加时间...")
            analysis_success, is_compliant, new_speed, analysis_msg = analyze_coarse_time(
                target_weight, coarse_time_ms, current_speed)
            
            if not analysis_success:
                self._handle_bucket_failure(bucket_id, f"快加时间分析失败: {analysis_msg}", "coarse_time")
                return
            
            self._log(f"📊 料斗{bucket_id}分析结果: {analysis_msg}")
            
            # 步骤4: 处理分析结果
            if is_compliant:
                # 符合条件，快加时间测定完成，启动飞料值测定
                self._handle_bucket_success(bucket_id, current_speed, analysis_msg)
            else:
                # 不符合条件，需要重测
                if new_speed is None:
                    # 速度异常，测定失败
                    self._handle_bucket_failure(bucket_id, analysis_msg, "coarse_time")
                else:
                    # 调整速度并重测
                    self._handle_bucket_retry(bucket_id, new_speed, analysis_msg)
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}到量流程异常: {str(e)}"
            self.logger.error(error_msg)
            self._handle_bucket_failure(bucket_id, error_msg, "coarse_time")
    
    def _handle_bucket_success(self, bucket_id: int, final_speed: int, message: str):
        """
        处理料斗测定成功（不再弹窗，而是启动飞料值测定）
        
        Args:
            bucket_id (int): 料斗ID
            final_speed (int): 最终快加速度
            message (str): 成功消息
        """
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.complete_successfully()
                target_weight = state.target_weight
            
            success_msg = f"🎉 料斗{bucket_id}快加时间测定完成！最终快加速度: {final_speed}档（共{state.attempt_count}次尝试）"
            self._log(success_msg)
        
            # 🔥 修复：在启动飞料值测定前设置物料名称
            current_material_name = self.get_current_material_name()
            if hasattr(self.flight_material_controller, 'set_material_name'):
                self.flight_material_controller.set_material_name(current_material_name)
                self._log(f"📝 已将物料名称'{current_material_name}'传递给飞料值控制器")
            
            # 不再弹窗显示成功信息，而是启动飞料值测定
            self._log(f"🚀 料斗{bucket_id}开始飞料值测定流程...")
            
            # 启动飞料值测定
            flight_success = self.flight_material_controller.start_flight_material_test(bucket_id, target_weight)
            
            if flight_success:
                self._log(f"✅ 料斗{bucket_id}飞料值测定已启动")
            else:
                # 飞料值测定启动失败，仍然触发完成事件（但不弹窗）
                self._log(f"❌ 料斗{bucket_id}飞料值测定启动失败，但快加时间测定已完成")
                # 这里不调用 _trigger_bucket_completed，因为我们不希望弹窗
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}成功状态异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _handle_bucket_failure(self, bucket_id: int, error_message: str, failed_stage: str = "coarse_time"):
        """
        处理料斗测定失败（修改：不直接弹窗，而是触发失败回调）
        
        Args:
            bucket_id (int): 料斗ID
            error_message (str): 错误消息
            failed_stage (str): 失败的阶段
        """
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.fail_with_error(error_message, failed_stage)
            
            failure_msg = f"❌ 料斗{bucket_id}{self._get_stage_name(failed_stage)}失败: {error_message}（共{state.attempt_count}次尝试）"
            self._log(failure_msg)
        
            # 修复：使用root.after确保在主线程中执行UI操作
            def trigger_failure_callback():
                if self.on_bucket_failed:
                    try:
                        self.on_bucket_failed(bucket_id, error_message, failed_stage)
                    except Exception as e:
                        self.logger.error(f"失败事件回调异常: {e}")
            
            # 延迟100ms执行，避免同时触发多个弹窗
            if hasattr(self, 'root_reference') and self.root_reference:
                self.root_reference.after(100, trigger_failure_callback)
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}失败状态异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _get_stage_name(self, stage: str) -> str:
        """获取阶段的中文名称"""
        stage_names = {
            "coarse_time": "快加时间测定",
            "flight_material": "飞料值测定",
            "fine_time": "慢加时间测定",
            "adaptive_learning": "自适应学习"
        }
        return stage_names.get(stage, stage)
    
    def _handle_bucket_retry(self, bucket_id: int, new_speed: int, reason: str):
        """
        处理料斗重测（不符合条件时自动重测，不触发完成事件）
        
        Args:
            bucket_id (int): 料斗ID
            new_speed (int): 新的快加速度
            reason (str): 重测原因
        """
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                # 检查是否达到最大重试次数
                if state.attempt_count >= state.max_attempts:
                    # 达到最大重试次数，判定为最终失败，触发失败事件
                    self._handle_bucket_failure(bucket_id, f"已达最大重试次数({state.max_attempts})，快加时间测定失败", "coarse_time")
                    return
                
                # 更新速度（不触发完成事件，继续测定）
                state.current_coarse_speed = new_speed
            
            self._log(f"🔄 料斗{bucket_id}不符合条件，自动重测: {reason}")
            self._log(f"📝 更新料斗{bucket_id}快加速度: {new_speed}档")
            
            # 步骤1: 更新PLC中的快加速度
            if bucket_id in BUCKET_PARAMETER_ADDRESSES:
                speed_address = BUCKET_PARAMETER_ADDRESSES[bucket_id]['CoarseSpeed']
                success = self.modbus_client.write_holding_register(speed_address, new_speed)
                if not success:
                    # 更新速度失败，判定为真正的失败
                    self._handle_bucket_failure(bucket_id, f"更新快加速度失败，无法继续测定", "coarse_time")
                    return
            
            # 步骤2: 等待100ms确保参数写入生效
            time.sleep(0.1)
            
            # 步骤3: 重新启动该料斗
            restart_success, restart_msg = self.bucket_control.restart_single_bucket(bucket_id)
            if not restart_success:
                # 重新启动失败，判定为真正的失败
                self._handle_bucket_failure(bucket_id, f"重新启动失败: {restart_msg}，无法继续测定", "coarse_time")
                return
            
            # 步骤4: 更新状态并重新开始监测
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.start_attempt()
            
            # 步骤5: 重新启动该料斗的监测
            self.monitoring_service.restart_bucket_monitoring(bucket_id, "coarse_time")
            
            # 步骤6: 更新进度（显示重测进度，但不触发完成事件）
            self._update_progress(bucket_id, state.attempt_count, state.max_attempts, 
                                f"第{state.attempt_count}次测定（速度调整为{new_speed}档，自动重测中...）")
            
            self._log(f"✅ 料斗{bucket_id}已重新启动，开始第{state.attempt_count}次测定（自动重测）")
            
            # 注意：这里不触发完成事件，继续后台自动测定
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}重测异常: {str(e)}"
            self.logger.error(error_msg)
            # 重测过程中的异常视为真正的失败
            self._handle_bucket_failure(bucket_id, f"{error_msg}，无法继续测定", "coarse_time")
    
    def _on_flight_material_completed(self, bucket_id: int, success: bool, message: str):
        """
        处理飞料值测定完成事件
        
        Args:
            bucket_id (int): 料斗ID
            success (bool): 是否成功
            message (str): 消息
        """
        try:
            if success:
                self._log(f"🎉 料斗{bucket_id}飞料值测定完成，开始慢加时间测定")
                
                # 从消息中提取平均飞料值
                flight_material_value = self._extract_flight_material_value_from_message(message)
                
                # 保存飞料值到状态中，用于重新学习
                with self.lock:
                    state = self.bucket_states[bucket_id]
                    original_target_weight = state.original_target_weight
                    state.last_flight_material_value = flight_material_value
                    
                self._log(f"📊 料斗{bucket_id}参数: 原始目标重量={original_target_weight}g, 平均飞料值={flight_material_value:.1f}g")
                
                # 🔥 修复：在启动慢加时间测定前设置物料名称
                current_material_name = self.get_current_material_name()
                if hasattr(self.fine_time_controller, 'set_material_name'):
                    self.fine_time_controller.set_material_name(current_material_name)
                    self._log(f"📝 已将物料名称'{current_material_name}'传递给慢加时间控制器")
                
                # 飞料值测定成功，启动慢加时间测定
                fine_time_success = self.fine_time_controller.start_fine_time_test(
                    bucket_id, original_target_weight, flight_material_value)
                
                if fine_time_success:
                    self._log(f"✅ 料斗{bucket_id}慢加时间测定已启动（包含平均飞料值 {flight_material_value:.1f}g）")
                else:
                    # 慢加时间测定启动失败，触发失败回调
                    self._log(f"❌ 料斗{bucket_id}慢加时间测定启动失败")
                    self._handle_bucket_failure(bucket_id, "慢加时间测定启动失败", "fine_time")
            else:
                self._log(f"❌ 料斗{bucket_id}飞料值测定失败: {message}")
                # 飞料值测定失败，触发失败回调
                self._handle_bucket_failure(bucket_id, message, "flight_material")
                    
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}飞料值完成事件异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            # 异常情况下，触发失败回调
            self._handle_bucket_failure(bucket_id, error_msg, "flight_material")
    
    def _extract_flight_material_value_from_message(self, message: str) -> float:
        """
        从飞料值测定成功消息中提取平均飞料值
        """
        try:
            # 查找"平均飞料值："字符串
            import re
            
            # 尝试多种模式来提取平均飞料值
            patterns = [
                r"平均飞料值：([\d.]+)g",           # 中文冒号
                r"平均飞料值:([\d.]+)g",            # 中文冒号无空格
                r"平均飞料值：\s*([\d.]+)g",        # 中文冒号带空格
                r"平均飞料值:\s*([\d.]+)g",         # 英文冒号带空格
                r"• 平均飞料值：([\d.]+)g",         # 带bullet point
                r"平均飞料值.*?([\d.]+)g"           # 更宽泛的匹配
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message)
                if match:
                    flight_material_value = float(match.group(1))
                    self._log(f"从消息中成功提取平均飞料值: {flight_material_value}g (使用模式: {pattern})")
                    return flight_material_value

            # 如果所有模式都匹配失败，尝试从消息末尾提取数字
            number_match = re.findall(r'([\d.]+)g', message)
            if number_match:
                # 取最后一个匹配的数字作为平均飞料值
                last_value = float(number_match[-1])
                self._log(f"从消息末尾提取平均飞料值: {last_value}g")
                return last_value

            self._log(f"警告：无法从飞料值测定消息中提取平均飞料值，使用默认值0.0")
            self._log(f"原始消息: {message}")
            return 0.0
        
        except Exception as e:
            self._log(f"错误：提取飞料值异常: {str(e)}")
            return 0.0
    
    def _on_fine_time_completed(self, bucket_id: int, success: bool, message: str):
        """
        处理慢加时间测定完成事件
        
        Args:
            bucket_id (int): 料斗ID
            success (bool): 是否成功
            message (str): 消息
        """
        try:
            if success:
                self._log(f"🎉 料斗{bucket_id}慢加时间测定完成，准备启动自适应学习")
                
                # 如果还没有自适应学习控制器，创建它
                if not hasattr(self, 'adaptive_learning_controller') or not self.adaptive_learning_controller:
                    try:
                        from adaptive_learning_controller import create_adaptive_learning_controller
                        self.adaptive_learning_controller = create_adaptive_learning_controller(self.modbus_client)
                        
                        # 设置物料名称
                        current_material_name = self.get_current_material_name()
                        if hasattr(self.adaptive_learning_controller, 'set_material_name'):
                            self.adaptive_learning_controller.set_material_name(current_material_name)
                            self._log(f"📝 自适应学习控制器已创建并设置物料名称: {current_material_name}")
                        
                        # 🔥 修改：设置单个料斗完成事件回调，移除合并完成事件
                        def on_adaptive_bucket_completed(bucket_id: int, success: bool, message: str):
                            """处理单个料斗自适应学习完成"""
                            self._log(f"🎉 料斗{bucket_id}自适应学习{'成功' if success else '失败'}: {message}")
                            
                            # 直接转发单个料斗完成事件
                            if self.on_bucket_completed:
                                try:
                                    self.on_bucket_completed(bucket_id, success, message)
                                except Exception as e:
                                    self.logger.error(f"自适应学习完成事件转发异常: {e}")
                        
                        def on_adaptive_bucket_failed(bucket_id: int, error_message: str, failed_stage: str):
                            """处理单个料斗自适应学习失败"""
                            self._log(f"❌ 料斗{bucket_id}自适应学习失败: {error_message}")
                            
                            # 转发失败事件
                            if self.on_bucket_failed:
                                try:
                                    self.on_bucket_failed(bucket_id, error_message, failed_stage)
                                except Exception as e:
                                    self.logger.error(f"自适应学习失败事件转发异常: {e}")
                        
                        def on_adaptive_progress(bucket_id: int, current: int, max_progress: int, message: str):
                            # 转发自适应学习进度更新
                            self._update_progress(bucket_id, current, max_progress, f"[自适应学习] {message}")
                        
                        def on_adaptive_log(message: str):
                            self._log(f"[自适应学习] {message}")
                        
                        # 🔥 修改：设置单个料斗事件回调，移除合并完成事件
                        self.adaptive_learning_controller.on_bucket_completed = on_adaptive_bucket_completed
                        self.adaptive_learning_controller.on_bucket_failed = on_adaptive_bucket_failed
                        self.adaptive_learning_controller.on_progress_update = on_adaptive_progress
                        self.adaptive_learning_controller.on_log_message = on_adaptive_log
                        
                        self._log("✅ 自适应学习控制器已创建并配置（单个料斗事件模式）")
                        
                    except ImportError as e:
                        self._log(f"❌ 无法导入自适应学习控制器: {e}")
                        self._trigger_bucket_completed(bucket_id, True, message)
                        return
                    except Exception as e:
                        self._log(f"❌ 创建自适应学习控制器异常: {e}")
                        self._trigger_bucket_completed(bucket_id, True, message)
                        return
                
                # 启动自适应学习（这里需要实现自适应学习启动逻辑）
                # 暂时先触发完成事件
                self._trigger_bucket_completed(bucket_id, True, message)
                
            else:
                self._log(f"❌ 料斗{bucket_id}慢加时间测定失败: {message}")
                # 慢加时间测定失败，触发失败回调
                self._handle_bucket_failure(bucket_id, message, "fine_time")
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}慢加时间完成事件异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            
    def _on_adaptive_learning_all_completed(self, all_states):
        """
        处理所有料斗自适应学习完成事件
        
        Args:
            all_states: 所有料斗的自适应学习状态字典
        """
        try:
            self._log("🎉 所有料斗自适应学习阶段完成！")
            
            # 调试：检查传入的状态字典
            self._log(f"[调试] 收到的状态字典类型: {type(all_states)}")
            self._log(f"[调试] 状态字典内容: {list(all_states.keys()) if all_states else 'Empty'}")
            
            for bucket_id, state in all_states.items():
                self._log(f"[调试] 料斗{bucket_id}: 类型={type(state)}, is_success={getattr(state, 'is_success', 'N/A')}, is_completed={getattr(state, 'is_completed', 'N/A')}")
            
            # 触发合并的完成事件，传递所有状态
            if self.on_bucket_completed:
                try:
                    self._log(f"[调试] 触发合并完成事件，bucket_id=0, success=True, 状态数量={len(all_states)}")
                    # 使用特殊的bucket_id=0来标识这是合并结果
                    self.on_bucket_completed(0, True, all_states)
                except Exception as e:
                    self.logger.error(f"自适应学习完成事件回调异常: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                self._log("[警告] on_bucket_completed 回调函数未设置")
            
        except Exception as e:
            error_msg = f"处理所有料斗自适应学习完成事件异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
    
    def _on_adaptive_learning_bucket_failed(self, bucket_id: int, error_message: str, failed_stage: str):
        """
        处理自适应学习料斗失败事件
        
        Args:
            bucket_id (int): 料斗ID
            error_message (str): 错误消息
            failed_stage (str): 失败阶段
        """
        try:
            self._log(f"❌ 料斗{bucket_id}自适应学习失败: {error_message}")
            
            # 转发失败事件
            if self.on_bucket_failed:
                try:
                    self.on_bucket_failed(bucket_id, error_message, failed_stage)
                except Exception as e:
                    self.logger.error(f"自适应学习失败事件回调异常: {e}")
                    
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}自适应学习失败事件异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _on_fine_time_progress_update(self, bucket_id: int, current_attempt: int, max_attempts: int, message: str):
        """
        处理慢加时间测定进度更新事件
        
        Args:
            bucket_id (int): 料斗ID
            current_attempt (int): 当前尝试次数  
            max_attempts (int): 最大尝试次数
            message (str): 消息
        """
        try:
            # 转发慢加时间测定的进度更新
            self._update_progress(bucket_id, current_attempt, max_attempts, f"[慢加时间测定] {message}")
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}慢加时间进度更新异常: {str(e)}"
            self.logger.error(error_msg)
    
    def _on_fine_time_log(self, message: str):
        """
        处理慢加时间测定日志事件
        
        Args:
            message (str): 日志消息
        """
        try:
            self._log(f"[慢加时间] {message}")
            
        except Exception as e:
            error_msg = f"处理慢加时间日志异常: {str(e)}"
            self.logger.error(error_msg)
    
    def _on_flight_material_progress_update(self, bucket_id: int, current_attempt: int, max_attempts: int, message: str):
        """
        处理飞料值测定进度更新事件
        
        Args:
            bucket_id (int): 料斗ID
            current_attempt (int): 当前尝试次数  
            max_attempts (int): 最大尝试次数
            message (str): 消息
        """
        try:
            # 转发飞料值测定的进度更新
            self._update_progress(bucket_id, current_attempt, max_attempts, f"[飞料值测定] {message}")
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}飞料值进度更新异常: {str(e)}"
            self.logger.error(error_msg)
    
    def _on_flight_material_log(self, message: str):
        """
        处理飞料值测定日志事件
        
        Args:
            message (str): 日志消息
        """
        try:
            self._log(f"[飞料值] {message}")
            
        except Exception as e:
            error_msg = f"处理飞料值日志异常: {str(e)}"
            self.logger.error(error_msg)
    
    def stop_all_coarse_time_test(self) -> Tuple[bool, str]:
        """
        停止所有料斗的快加时间测定
        
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            self._log("🛑 停止所有料斗的快加时间测定...")
            
            # 🔥 新增：禁用物料监测
            self.monitoring_service.set_material_check_enabled(False)
            self._log("⏸️ 物料不足监测已禁用")
            
            # 停止监测服务
            self.monitoring_service.stop_all_monitoring()
            
            # 停止飞料值测定
            self.flight_material_controller.stop_all_flight_material_test()
            
            # 停止慢加时间测定
            self.fine_time_controller.stop_all_fine_time_test()
            
            # 停止所有料斗
            stop_success, stop_msg = self.bucket_control.stop_all_buckets()
            
            # 重置状态
            with self.lock:
                for state in self.bucket_states.values():
                    state.is_testing = False
            
            if stop_success:
                success_msg = "✅ 所有料斗的快加时间测定已停止"
                self._log(success_msg)
                return True, success_msg
            else:
                error_msg = f"停止料斗失败: {stop_msg}"
                self._log(f"❌ {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"停止快加时间测定异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False, error_msg
    
    def get_bucket_state(self, bucket_id: int) -> Optional[BucketCoarseTimeState]:
        """
        获取料斗测定状态
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            Optional[BucketCoarseTimeState]: 料斗状态
        """
        with self.lock:
            return self.bucket_states.get(bucket_id)
    
    def get_all_bucket_states(self) -> Dict[int, BucketCoarseTimeState]:
        """
        获取所有料斗的测定状态
        
        Returns:
            Dict[int, BucketCoarseTimeState]: 所有料斗状态
        """
        with self.lock:
            return self.bucket_states.copy()
    
    def _trigger_bucket_completed(self, bucket_id: int, success: bool, message: str):
        """触发料斗完成事件"""
        if self.on_bucket_completed:
            try:
                self.on_bucket_completed(bucket_id, success, message)
            except Exception as e:
                self.logger.error(f"料斗完成事件回调异常: {e}")
    
    def _update_progress(self, bucket_id: int, current_attempt: int, max_attempts: int, message: str):
        """更新进度"""
        if self.on_progress_update:
            try:
                self.on_progress_update(bucket_id, current_attempt, max_attempts, message)
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
        self._log(f"[监测] {message}")
    
    def dispose(self):
        """释放资源"""
        try:
            self.monitoring_service.dispose()
            self.flight_material_controller.dispose()
            self.fine_time_controller.dispose()
            self._log("快加时间测定控制器资源已释放")
        except Exception as e:
            self.logger.error(f"释放控制器资源异常: {e}")

def create_coarse_time_test_controller(modbus_client: ModbusClient) -> CoarseTimeTestController:
    """
    创建快加时间测定控制器实例的工厂函数
    
    Args:
        modbus_client (ModbusClient): Modbus客户端实例
        
    Returns:
        CoarseTimeTestController: 控制器实例
    """
    return CoarseTimeTestController(modbus_client)

# 示例使用
if __name__ == "__main__":
    from modbus_client import create_modbus_client
    
    # 创建Modbus客户端并连接
    client = create_modbus_client()
    success, message = client.connect()
    print(f"连接状态: {success} - {message}")
    
    if success:
        # 创建快加时间测定控制器
        controller = create_coarse_time_test_controller(client)
        
        # 设置事件回调
        def on_bucket_completed(bucket_id: int, success: bool, message: str):
            print(f"[完成事件] 料斗{bucket_id}: {'成功' if success else '失败'} - {message}")
        
        def on_bucket_failed(bucket_id: int, error_message: str, failed_stage: str):
            print(f"[失败事件] 料斗{bucket_id} {failed_stage}失败: {error_message}")
        
        def on_progress_update(bucket_id: int, current_attempt: int, max_attempts: int, message: str):
            print(f"[进度更新] 料斗{bucket_id}: {current_attempt}/{max_attempts} - {message}")
        
        def on_log_message(message: str):
            print(f"[日志] {message}")
        
        controller.on_bucket_completed = on_bucket_completed
        controller.on_bucket_failed = on_bucket_failed
        controller.on_progress_update = on_progress_update
        controller.on_log_message = on_log_message
        
        # 启动快加时间测定
        print("启动快加时间测定...")
        success, msg = controller.start_coarse_time_test_after_parameter_writing(200.0, 72)
        print(f"启动结果: {success} - {msg}")
        
        # 运行一段时间后停止
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            pass
        
        print("停止快加时间测定...")
        controller.stop_all_coarse_time_test()
        controller.dispose()
        
        # 断开连接
        client.disconnect()