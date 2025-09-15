#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞料值测定控制器
对快加时间测定成功的料斗进行飞料值测定，重复3次并计算平均飞料值

作者：AI助手
创建日期：2025-07-23
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
from modbus_client import ModbusClient
from bucket_monitoring import BucketMonitoringService, create_bucket_monitoring_service
from clients.flight_material_webapi import analyze_flight_material
from bucket_control_extended import BucketControlExtended, create_bucket_control_extended
from plc_addresses import BUCKET_PARAMETER_ADDRESSES, BUCKET_MONITORING_ADDRESSES

class BucketFlightMaterialState:
    """料斗飞料值测定状态"""
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_testing = False             # 是否正在测定
        self.is_completed = False           # 是否完成测定
        self.target_weight = 0.0           # 目标重量
        self.current_attempt = 0           # 当前尝试次数
        self.max_attempts = 3              # 最大尝试次数（3次）
        self.recorded_weights = []         # 记录的实时重量列表
        self.start_time = None             # 开始时间
        self.error_message = ""            # 错误消息
        self.average_flight_material = 0.0 # 平均飞料值
        self.material_name = "未知物料"
    
        # 新增：用于跨线程UI操作的root引用
        self.root_reference = None
    
    def reset_for_new_test(self, target_weight: float):
        """重置状态开始新的测定"""
        self.is_testing = False
        self.is_completed = False
        self.target_weight = target_weight
        self.current_attempt = 0
        self.recorded_weights = []
        self.start_time = None
        self.error_message = ""
        self.average_flight_material = 0.0
    
    def start_next_attempt(self):
        """开始下一次尝试"""
        self.is_testing = True
        self.current_attempt += 1
        if self.start_time is None:
            self.start_time = datetime.now()
    
    def record_weight(self, weight: float):
        """记录一次重量"""
        self.recorded_weights.append(weight)
        self.is_testing = False  # 该次尝试完成
    
    def complete_successfully(self, average_flight_material: float):
        """成功完成测定"""
        self.is_testing = False
        self.is_completed = True
        self.average_flight_material = average_flight_material
    
    def fail_with_error(self, error_message: str):
        """测定失败"""
        self.is_testing = False
        self.is_completed = True
        self.error_message = error_message

class FlightMaterialTestController:
    """
    飞料值测定控制器
    
    负责对快加时间测定成功的料斗进行飞料值测定
    每个料斗独立运行，重复3次，计算平均飞料值
    """
    
    def __init__(self, modbus_client: ModbusClient):
        """
        初始化飞料值测定控制器
        
        Args:
            modbus_client (ModbusClient): Modbus客户端实例
        """
        self.modbus_client = modbus_client
        self.bucket_states: Dict[int, BucketFlightMaterialState] = {}
        self.lock = threading.RLock()
        self.material_name = "未知物料"  # 存储物料名称
        
        # 创建服务实例
        self.monitoring_service = create_bucket_monitoring_service(modbus_client)
        self.bucket_control = create_bucket_control_extended(modbus_client)
        
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
    
    def _initialize_bucket_states(self):
        """初始化料斗状态"""
        with self.lock:
            for bucket_id in range(1, 4):
                self.bucket_states[bucket_id] = BucketFlightMaterialState(bucket_id)
                
    def set_material_name(self, material_name: str):
        """
        设置物料名称（新增方法）
        
        Args:
            material_name (str): 物料名称
        """
        try:
            self.material_name = material_name
            with self.lock:
                for state in self.bucket_states.values():
                    state.material_name = material_name
            self._log(f"📝 飞料值控制器设置物料名称: {material_name}")
        except Exception as e:
            self._log(f"❌ 设置物料名称异常: {str(e)}")
                
    def _on_material_shortage_detected(self, bucket_id: int, stage: str, is_production: bool):
        """
        处理物料不足检测事件
        
        Args:
            bucket_id (int): 料斗ID
            stage (str): 当前阶段
            is_production (bool): 是否为生产阶段
        """
        try:
            # 只处理飞料值测定阶段的物料不足
            if stage == "flight_material" and not is_production:
                self._log(f"⚠️ 料斗{bucket_id}在飞料值测定阶段检测到物料不足，停止该料斗测定")

                # 停止该料斗的飞料值测定
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
            # 停止该料斗的飞料值测定
            self.stop_bucket_flight_material_test(bucket_id)
            
            # 更新料斗状态为失败
            with self.lock:
                state = self.bucket_states.get(bucket_id)
                if state:
                    state.fail_with_error("物料不足")
            
            self._log(f"✅ 料斗{bucket_id}飞料值测定已因物料不足而停止")
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}物料不足停止逻辑异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def start_flight_material_test(self, bucket_id: int, target_weight: float) -> bool:
        """
        启动指定料斗的飞料值测定
        
        Args:
            bucket_id (int): 料斗ID
            target_weight (float): 目标重量（克）
            
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
                
                # 重置状态并开始测定
                state.reset_for_new_test(target_weight)
            
            # 启用物料监测
            self.monitoring_service.set_material_check_enabled(True)
            self._log(f"🔍 料斗{bucket_id}飞料值测定物料监测已启用")
            
            self._log(f"🚀 料斗{bucket_id}开始飞料值测定，目标重量: {target_weight}g")
            
            # 启动第一次尝试
            self._start_single_attempt(bucket_id)
            
            return True
            
        except Exception as e:
            error_msg = f"启动料斗{bucket_id}飞料值测定异常: {str(e)}"
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
            
            self._log(f"🔄 料斗{bucket_id}开始第{state.current_attempt}次飞料值测定")
            
            # 更新进度
            self._update_progress(bucket_id, state.current_attempt, state.max_attempts, 
                                f"正在进行第{state.current_attempt}次飞料值测定...")
            
            # 在后台线程执行启动和监测流程
            def attempt_thread():
                self._execute_single_attempt(bucket_id)
            
            thread = threading.Thread(target=attempt_thread, daemon=True, 
                                    name=f"FlightMaterial-{bucket_id}-{state.current_attempt}")
            thread.start()
            
        except Exception as e:
            error_msg = f"启动料斗{bucket_id}单次尝试异常: {str(e)}"
            self.logger.error(error_msg)
            self._handle_bucket_failure(bucket_id, error_msg)
    
    def _execute_single_attempt(self, bucket_id: int):
        """
        执行单次尝试的完整流程（增强版 - 监测类型为flight_material）
        """
        try:
            # 步骤1: 启动料斗（互斥保护）
            self._log(f"📤 步骤1: 启动料斗{bucket_id}（互斥保护）")
            success = self._start_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"启动料斗{bucket_id}失败")
                return
            
            # 步骤2: 启动监测并等待到量（指定监测类型为flight_material）
            self._log(f"🔍 步骤2: 启动料斗{bucket_id}飞料监测")
            self.monitoring_service.start_monitoring([bucket_id], "flight_material")
            
        except Exception as e:
            error_msg = f"执行料斗{bucket_id}单次尝试异常: {str(e)}"
            self.logger.error(error_msg)
            self._handle_bucket_failure(bucket_id, error_msg)
    
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
            # 获取该料斗的控制地址
            from plc_addresses import get_bucket_control_address
            
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
    
    def _on_target_reached(self, bucket_id: int, coarse_time_ms: int):
        """
        处理料斗到量事件（监测服务回调）
        
        Args:
            bucket_id (int): 料斗ID
            coarse_time_ms (int): 时间（毫秒，飞料测定时不关注此值）
        """
        try:
            # 检查该料斗是否在飞料测定中
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return
                
                state = self.bucket_states[bucket_id]
                if not state.is_testing:
                    return
            
            self._log(f"📍 料斗{bucket_id}到量，开始处理飞料流程")
            
            # 在后台线程处理到量事件
            def process_thread():
                self._process_target_reached_for_flight_material(bucket_id)
            
            thread = threading.Thread(target=process_thread, daemon=True, 
                                    name=f"ProcessFlightTarget-{bucket_id}")
            thread.start()
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}飞料到量事件异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _process_target_reached_for_flight_material(self, bucket_id: int):
        """
        处理飞料测定的到量流程
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            # 步骤1: 停止料斗（互斥保护）
            self._log(f"🛑 步骤3: 停止料斗{bucket_id}（互斥保护）")
            success = self._stop_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"停止料斗{bucket_id}失败")
                return
            
            # 步骤2: 延迟1000ms后读取实时重量
            self._log(f"⏱️ 步骤4: 等待1000ms后读取料斗{bucket_id}实时重量")
            time.sleep(1)
            
            weight = self._read_bucket_weight(bucket_id)
            if weight is None:
                self._handle_bucket_failure(bucket_id, f"读取料斗{bucket_id}实时重量失败")
                return
            
            # 记录重量
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.record_weight(weight)
            
            self._log(f"📊 料斗{bucket_id}第{state.current_attempt}次实时重量: {weight}g")
            
            # 步骤3: 放料操作
            self._log(f"📤 步骤5: 料斗{bucket_id}执行放料操作")
            success = self._discharge_bucket(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}放料操作失败")
                return
            
            # 步骤4: 检查是否完成3次测定
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                if state.current_attempt >= state.max_attempts:
                    # 完成3次测定，计算平均飞料值
                    self._complete_flight_material_test(bucket_id)
                else:
                    # 继续下一次尝试
                    time.sleep(1.0)  # 等待1秒后开始下次尝试
                    self._start_single_attempt(bucket_id)
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}飞料到量流程异常: {str(e)}"
            self.logger.error(error_msg)
            self._handle_bucket_failure(bucket_id, error_msg)
    
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
            from plc_addresses import get_bucket_control_address
            
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
    
    def _discharge_bucket(self, bucket_id: int) -> bool:
        """
        料斗放料操作
        发送放料=1，延迟1.5s后发送放料=0
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            bool: 是否成功
        """
        try:
            from plc_addresses import get_bucket_control_address
            
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
    
    def _complete_flight_material_test(self, bucket_id: int):
        """
        完成飞料值测定并计算结果
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                recorded_weights = state.recorded_weights[:]
                target_weight = state.target_weight
            
            self._log(f"🧮 料斗{bucket_id}完成3次测定，记录重量: {recorded_weights}")
            
            # 调用WebAPI计算飞料值
            analysis_success, avg_flight_material, flight_details, message = analyze_flight_material(
                target_weight, recorded_weights)
            
            if analysis_success:
                # 计算成功
                with self.lock:
                    state.complete_successfully(avg_flight_material)
                
                success_msg = (f"🎉 料斗{bucket_id}飞料值测定成功！\n\n"
                             f"📊 测定结果：\n"
                             f"  • 目标重量：{target_weight}g\n"
                             f"  • 3次实时重量：{recorded_weights[0]:.1f}g, {recorded_weights[1]:.1f}g, {recorded_weights[2]:.1f}g\n"
                             f"  • 3次飞料值：{flight_details[0]:.1f}g, {flight_details[1]:.1f}g, {flight_details[2]:.1f}g\n"
                             f"  • 平均飞料值：{avg_flight_material:.1f}g\n\n"
                             f"✅ 料斗{bucket_id}飞料值测定完成！")
                
                self._log(success_msg)
                self._trigger_bucket_completed(bucket_id, True, success_msg)
            else:
                # 计算失败
                self._handle_bucket_failure(bucket_id, f"WebAPI计算飞料值失败: {message}")
            
        except Exception as e:
            error_msg = f"完成料斗{bucket_id}飞料值测定异常: {str(e)}"
            self.logger.error(error_msg)
            self._handle_bucket_failure(bucket_id, error_msg)
    
    def _handle_bucket_failure(self, bucket_id: int, error_message: str, failed_stage: str = "flight_material"):
        """
        处理料斗测定失败
        
        Args:
            bucket_id (int): 料斗ID
            error_message (str): 错误消息
        """
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.fail_with_error(error_message)

            failure_msg = f"❌ 料斗{bucket_id}飞料值测定失败: {error_message}"
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
    
    def get_bucket_state(self, bucket_id: int) -> Optional[BucketFlightMaterialState]:
        """
        获取料斗测定状态
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            Optional[BucketFlightMaterialState]: 料斗状态
        """
        with self.lock:
            return self.bucket_states.get(bucket_id)
    
    def stop_bucket_flight_material_test(self, bucket_id: int):
        """
        停止指定料斗的飞料值测定（增强版）
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            with self.lock:
                if bucket_id in self.bucket_states:
                    state = self.bucket_states[bucket_id]
                    if state.is_testing:
                        state.is_testing = False
                        self._log(f"🛑 料斗{bucket_id}飞料值测定已停止")
            
            # 停止该料斗的监测
            self.monitoring_service.stop_bucket_monitoring(bucket_id)
            
            # 发送该料斗的停止命令（互斥保护）
            success = self._stop_bucket_with_mutex_protection(bucket_id)
            if success:
                self._log(f"✅ 料斗{bucket_id}PLC停止命令发送成功")
            else:
                self._log(f"⚠️ 料斗{bucket_id}PLC停止命令发送失败")
            
        except Exception as e:
            error_msg = f"停止料斗{bucket_id}飞料值测定异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def stop_all_flight_material_test(self):
        """停止所有料斗的飞料值测定（增强版 - 禁用物料监测）"""
        try:
            with self.lock:
                for state in self.bucket_states.values():
                    state.is_testing = False
            
            # 禁用物料监测
            self.monitoring_service.set_material_check_enabled(False)
            self._log("⏸️ 飞料值测定物料监测已禁用")
            
            # 停止监测服务
            self.monitoring_service.stop_all_monitoring()
            
            self._log("🛑 所有料斗的飞料值测定已停止")
            
        except Exception as e:
            error_msg = f"停止所有飞料值测定异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            
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
                target_weight = state.target_weight
            
            # 重新启动该料斗的飞料值测定
            restart_success = self.start_flight_material_test(bucket_id, target_weight)
            
            if restart_success:
                success_msg = f"料斗{bucket_id}物料不足已恢复，飞料值测定重新启动成功"
                self._log(f"✅ {success_msg}")
                return True, success_msg
            else:
                error_msg = f"料斗{bucket_id}飞料值测定重新启动失败"
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
            self._log("📢 用户选择取消生产，停止所有飞料值测定...")
            
            # 停止所有飞料值测定
            self.stop_all_flight_material_test()
            
            # 调用监测服务的取消方法
            cancel_success = self.monitoring_service.handle_material_shortage_cancel()
            
            success_msg = "✅ 已取消生产，所有飞料值测定已停止，准备返回AI模式自适应自学习界面"
            self._log(success_msg)
            
            return cancel_success, success_msg
            
        except Exception as e:
            error_msg = f"处理取消生产操作异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False, error_msg
    
    def _trigger_bucket_completed(self, bucket_id: int, success: bool, message: str):
        """触发料斗完成事件"""
        if self.on_bucket_completed:
            try:
                # 获取平均飞料值用于后续阶段
                with self.lock:
                    state = self.bucket_states[bucket_id]
                    avg_flight_material = state.average_flight_material
                
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
        self._log(f"[飞料监测] {message}")
    
    def dispose(self):
        """释放资源"""
        try:
            self.stop_all_flight_material_test()
            self.monitoring_service.dispose()
            self._log("飞料值测定控制器资源已释放")
        except Exception as e:
            self.logger.error(f"释放控制器资源异常: {e}")

def create_flight_material_test_controller(modbus_client: ModbusClient) -> FlightMaterialTestController:
    """
    创建飞料值测定控制器实例的工厂函数
    
    Args:
        modbus_client (ModbusClient): Modbus客户端实例
        
    Returns:
        FlightMaterialTestController: 控制器实例
    """
    return FlightMaterialTestController(modbus_client)