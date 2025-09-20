#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
慢加时间测定控制器
对飞料值测定成功的料斗进行慢加时间测定，重复测定直至成功或达到15次上限

作者：AI助手
创建日期：2025-07-24
更新日期：2025-07-24（集成自适应学习阶段启动）
修复日期：2025-07-29（修复慢加流速传递问题）
"""

import threading
import time
import logging
from typing import Dict, Optional, Callable, Tuple
from datetime import datetime
from modbus_client import ModbusClient
from bucket_monitoring import BucketMonitoringService, create_bucket_monitoring_service
from clients.fine_time_webapi import analyze_fine_time
from plc_addresses import BUCKET_PARAMETER_ADDRESSES, get_bucket_control_address

from typing import Optional, Union
import tkinter as tk
class BucketFineTimeState:
    """料斗慢加时间测定状态"""
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_testing = False             # 是否正在测定
        self.is_completed = False           # 是否完成测定
        self.current_attempt = 0           # 当前尝试次数
        self.max_attempts = 15             # 最大尝试次数
        self.start_time = None             # 开始时间
        self.target_reached_time = None    # 到量时间
        self.fine_time_ms = 0             # 慢加时间（毫秒）
        self.current_fine_speed = 44      # 当前慢加速度（默认44）
        self.error_message = ""            # 错误消息
        self.average_flight_material = 0.0  # 存储平均飞料值（来自飞料值测定阶段）
        self.fine_flow_rate = None         # 慢加流速（g/s）
        self.material_name = "未知物料"
    
        # 新增：用于跨线程UI操作的root引用
        self.root_reference = None
    
    def reset_for_new_test(self, average_flight_material: float = 0.0):
        """重置状态开始新的测定"""
        self.is_testing = False
        self.is_completed = False
        self.current_attempt = 0
        self.start_time = None
        self.target_reached_time = None
        self.fine_time_ms = 0
        self.current_fine_speed = 44
        self.error_message = ""
        self.average_flight_material = average_flight_material  # 存储平均飞料值为飞料值测定阶段的值
        self.fine_flow_rate = None         # 重置慢加流速
    
    def start_next_attempt(self):
        """开始下一次尝试"""
        self.is_testing = True
        self.current_attempt += 1
        self.start_time = datetime.now()
    
    def record_target_reached(self, reached_time: datetime):
        """记录到量时间"""
        self.target_reached_time = reached_time
        if self.start_time is not None:
            self.fine_time_ms = int((reached_time - self.start_time).total_seconds() * 1000)
        else:
            self.fine_time_ms = 0
        self.is_testing = False
    
    def complete_successfully(self, fine_flow_rate: Optional[float] = None):
        """成功完成测定，同时存储慢加流速"""
        self.is_testing = False
        self.is_completed = True
        # 只有当传入的fine_flow_rate不为None时才更新，否则保持原值
        if fine_flow_rate is not None:
            self.fine_flow_rate = fine_flow_rate
        # 如果传入的是None但self.fine_flow_rate有值，保持不变
        # 如果两者都是None，那就是None
    
    def fail_with_error(self, error_message: str):
        """测定失败"""
        self.is_testing = False
        self.is_completed = True
        self.error_message = error_message

class FineTimeTestController:
    """
    慢加时间测定控制器
    
    负责对飞料值测定成功的料斗进行慢加时间测定
    每个料斗独立运行，重复测定直至成功或达到15次上限
    """
    
    def __init__(self, modbus_client: ModbusClient):
        """
        初始化慢加时间测定控制器
        
        Args:
            modbus_client (ModbusClient): Modbus客户端实例
        """
        root_reference: Optional[Union[tk.Tk, tk.Toplevel]] = None
        self.modbus_client = modbus_client
        self.bucket_states: Dict[int, BucketFineTimeState] = {}
        self.bucket_original_weights: Dict[int, float] = {}  # 存储每个料斗的原始目标重量
        self.lock = threading.RLock()
        self.material_name = "未知物料"  # 存储物料名称

        # 新增：用于跨线程UI操作的root引用
        self.root_reference = None
        
        # 创建服务实例
        self.monitoring_service = create_bucket_monitoring_service(modbus_client)
        
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
            for bucket_id in range(1,4):
                self.bucket_states[bucket_id] = BucketFineTimeState(bucket_id)
    
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
            self._log(f"📝 慢加时间控制器设置物料名称: {material_name}")
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
            # 只处理慢加时间测定阶段的物料不足
            if stage == "fine_time" and not is_production:
                self._log(f"⚠️ 料斗{bucket_id}在慢加时间测定阶段检测到物料不足，停止该料斗测定")
                
                # 停止该料斗的慢加时间测定
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
            # 停止该料斗的慢加时间测定
            self.stop_bucket_fine_time_test(bucket_id)
            
            # 更新料斗状态为失败
            with self.lock:
                state = self.bucket_states.get(bucket_id)
                if state:
                    state.fail_with_error("物料不足")
            
            self._log(f"✅ 料斗{bucket_id}慢加时间测定已因物料不足而停止")
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}物料不足停止逻辑异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def start_fine_time_test(self, bucket_id: int, original_target_weight: float = 200.0, 
                              average_flight_material: float = 0.0) -> bool:
        """
        启动指定料斗的慢加时间测定
        
        Args:
            bucket_id (int): 料斗ID
            original_target_weight (float): 原始目标重量（AI生产时输入的真实重量）
            average_flight_material (float): 平均飞料值（来自飞料值测定）
            
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
                state.reset_for_new_test(average_flight_material)
                
                # 存储原始目标重量
                self.bucket_original_weights[bucket_id] = original_target_weight
            
            # 启用物料监测
            self.monitoring_service.set_material_check_enabled(True)
            self._log(f"🔍 料斗{bucket_id}慢加时间测定物料监测已启用")
            
            self._log(f"🚀 料斗{bucket_id}开始慢加时间测定，原始目标重量: {original_target_weight}g，平均飞料值: {average_flight_material:.1f}g")
            
            # 启动第一次尝试
            self._start_single_attempt(bucket_id)
            
            return True
            
        except Exception as e:
            error_msg = f"启动料斗{bucket_id}慢加时间测定异常: {str(e)}"
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
            
            self._log(f"🔄 料斗{bucket_id}开始第{state.current_attempt}次慢加时间测定")
            
            # 更新进度
            self._update_progress(bucket_id, state.current_attempt, state.max_attempts, 
                                f"正在进行第{state.current_attempt}次慢加时间测定...")
            
            # 在后台线程执行测定流程
            def attempt_thread():
                self._execute_single_attempt(bucket_id)
            
            thread = threading.Thread(target=attempt_thread, daemon=True, 
                                    name=f"FineTime-{bucket_id}-{state.current_attempt}")
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
            # 步骤1: 写入目标重量=6g、快加提前量=6g
            self._log(f"📝 步骤1: 料斗{bucket_id}写入测定参数")
            success = self._write_test_parameters(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}写入测定参数失败")
                return
            
            # 步骤2: 启动料斗（互斥保护）
            self._log(f"📤 步骤2: 启动料斗{bucket_id}（互斥保护）")
            success = self._start_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"启动料斗{bucket_id}失败")
                return
            
            # 步骤3: 启动监测（指定监测类型为fine_time）
            self._log(f"🔍 步骤3: 启动料斗{bucket_id}慢加监测")
            self.monitoring_service.start_monitoring([bucket_id], "fine_time")
            
        except Exception as e:
            error_msg = f"执行料斗{bucket_id}单次尝试异常: {str(e)}"
            self.logger.error(error_msg)
            self._handle_bucket_failure(bucket_id, error_msg)
    
    def _write_test_parameters(self, bucket_id: int) -> bool:
        """
        写入测定参数：目标重量=6g、快加提前量=6g
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            bool: 是否成功
        """
        try:
            bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
            
            # 目标重量6g，写入需要×10
            target_weight_plc = 6 * 10  # 60
            # 快加提前量6g，写入需要×10
            coarse_advance = 6 * 10
            
            # 写入目标重量
            success = self.modbus_client.write_holding_register(
                bucket_addresses['TargetWeight'], target_weight_plc)
            if not success:
                self._log(f"❌ 料斗{bucket_id}目标重量写入失败")
                return False
            
            # 写入快加提前量
            success = self.modbus_client.write_holding_register(
                bucket_addresses['CoarseAdvance'], coarse_advance)
            if not success:
                self._log(f"❌ 料斗{bucket_id}快加提前量写入失败")
                return False
            
            self._log(f"✅ 料斗{bucket_id}测定参数写入成功（目标重量=6g, 快加提前量=6g）")
            return True
            
        except Exception as e:
            error_msg = f"料斗{bucket_id}写入测定参数异常: {str(e)}"
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
    
    def _on_target_reached(self, bucket_id: int, time_ms: int):
        """
        处理料斗到量事件（监测服务回调）
        
        Args:
            bucket_id (int): 料斗ID
            time_ms (int): 时间（毫秒，慢加测定时这就是慢加时间）
        """
        try:
            # 检查该料斗是否在慢加测定中
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return
                
                state = self.bucket_states[bucket_id]
                if not state.is_testing:
                    return
                
                # 记录到量时间
                state.record_target_reached(datetime.now())
            
            self._log(f"📍 料斗{bucket_id}到量，慢加时间: {state.fine_time_ms}ms")
            
            # 在后台线程处理到量事件
            def process_thread():
                self._process_target_reached_for_fine_time(bucket_id)
            
            thread = threading.Thread(target=process_thread, daemon=True, 
                                    name=f"ProcessFineTarget-{bucket_id}")
            thread.start()
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}慢加到量事件异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _process_target_reached_for_fine_time(self, bucket_id: int):
        """
        处理慢加测定的到量流程
        
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
            
            # 步骤3: 延迟600ms后发送放料=1命令
            self._log(f"⏱️ 步骤5: 等待600ms后料斗{bucket_id}开始放料")
            time.sleep(0.6)
            
            success = self._execute_discharge_sequence(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}放料操作失败")
                return
            
            # 步骤4: 获取慢加时间并分析
            with self.lock:
                state = self.bucket_states[bucket_id]
                fine_time_ms = state.fine_time_ms
                current_fine_speed = state.current_fine_speed
                flight_material_value = state.average_flight_material  # 获取平均飞料值
                # 获取存储的原始目标重量
                original_target_weight = self.bucket_original_weights.get(bucket_id, 200.0)
        
            self._log(f"🧠 步骤6: 分析料斗{bucket_id}慢加时间（包含平均飞料值: {flight_material_value:.1f}g）")
        
            # 调用后端API分析（增强返回值处理和调试）
            try:
                api_result = analyze_fine_time(
                    6.0, fine_time_ms, current_fine_speed, original_target_weight, flight_material_value)  # 目标重量固定为6g
                
                # 调试：检查API返回值
                self._log(f"🔍 API返回值调试 - 料斗{bucket_id}: {api_result}")
                
                if isinstance(api_result, (list, tuple)) and len(api_result) >= 6:
                    analysis_success, is_compliant, new_fine_speed, coarse_advance, fine_flow_rate, analysis_msg = api_result
                elif isinstance(api_result, (list, tuple)):
                    # 处理返回值数量不足的情况
                    self._log(f"⚠️ API返回值数量不足，期待6个，实际{len(api_result)}个")
                    analysis_success, is_compliant, new_fine_speed, coarse_advance, fine_flow_rate, analysis_msg = (
                        list(api_result) + [None] * (6 - len(api_result)))[:6]
                else:
                    # 返回值不可迭代，全部赋值为None并记录错误
                    self._log(f"❌ API返回值不可迭代，实际类型: {type(api_result)}，内容: {api_result}")
                    analysis_success, is_compliant, new_fine_speed, coarse_advance, fine_flow_rate, analysis_msg = (None, None, None, None, None, "API返回值不可迭代")
                    
            except Exception as e:
                self._handle_bucket_failure(bucket_id, f"慢加时间API调用异常: {str(e)}")
                return
        
            if not analysis_success:
                self._handle_bucket_failure(bucket_id, f"慢加时间分析失败: {analysis_msg}")
                return
        
            self._log(f"📊 料斗{bucket_id}分析结果: {analysis_msg}")
            
            # 调试：检查fine_flow_rate的值和类型
            self._log(f"🔍 API返回的fine_flow_rate调试 - 值: {fine_flow_rate}, 类型: {type(fine_flow_rate)}")
            
            # 从API分析消息中提取流速值（备用方案）
            extracted_flow_rate = self._extract_flow_rate_from_message(analysis_msg)
            if fine_flow_rate is None and extracted_flow_rate is not None:
                fine_flow_rate = extracted_flow_rate
                self._log(f"🔧 从分析消息中提取慢加流速: {fine_flow_rate:.3f}g/s")
            
            # 记录慢加流速到状态中
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.fine_flow_rate = fine_flow_rate  # 临时存储慢加流速
                self._log(f"💾 料斗{bucket_id}慢加流速已存储到状态: {fine_flow_rate}")
            
            if fine_flow_rate is not None:
                self._log(f"📊 料斗{bucket_id}慢加流速: {fine_flow_rate:.3f}g/s (来自API响应，已存储)")
            else:
                self._log(f"⚠️ 料斗{bucket_id}慢加流速为None，可能影响自适应学习精度")
            
            if coarse_advance is not None:
                self._log(f"📊 料斗{bucket_id}计算快加提前量: {coarse_advance:.1f}g (基于平均飞料值 {flight_material_value:.1f}g)")
                # 立即写入PLC快加提前量
                success = self._write_coarse_advance_to_plc(bucket_id, coarse_advance)
                if success:
                    self._log(f"✅ 料斗{bucket_id}快加提前量已写入PLC: {coarse_advance:.1f}g")
                else:
                    self._log(f"❌ 料斗{bucket_id}快加提前量写入PLC失败")
        
            # 步骤5: 处理分析结果
            if is_compliant:
                # 符合条件，慢加时间测定完成，启动自适应学习阶段
                self._handle_bucket_success(bucket_id, current_fine_speed, analysis_msg)
            else:
                # 不符合条件，需要重测
                if new_fine_speed is None:
                    # 速度异常，测定失败
                    self._handle_bucket_failure(bucket_id, analysis_msg)
                else:
                    # 调整速度并重测
                    self._handle_bucket_retry(bucket_id, new_fine_speed, analysis_msg)
        
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}慢加到量流程异常: {str(e)}"
            self.logger.error(error_msg)
            self._handle_bucket_failure(bucket_id, error_msg)
    
    def _extract_flow_rate_from_message(self, analysis_msg: str) -> Optional[float]:
        """
        从分析消息中提取慢加流速值（备用方案）
        
        Args:
            analysis_msg (str): API分析消息
            
        Returns:
            Optional[float]: 提取的流速值，失败返回None
        """
        try:
            import re
            
            # 尝试多种模式来提取流速
            patterns = [
                r"流速[：:]\s*([\d.]+)\s*g/s",           # 流速：0.649 g/s
                r"流速[：:]\s*([\d.]+)g/s",              # 流速：0.649g/s
                r"流速\s+([\d.]+)\s*g/s",                # 流速 0.649 g/s
                r"速度[：:]\s*([\d.]+)\s*g/s",           # 速度：0.649 g/s
                r"([\d.]+)\s*g/s",                       # 0.649 g/s
            ]
            
            for pattern in patterns:
                match = re.search(pattern, analysis_msg)
                if match:
                    flow_rate = float(match.group(1))
                    self._log(f"🔧 成功从分析消息中提取流速: {flow_rate}g/s (模式: {pattern})")
                    return flow_rate
            
            self._log(f"⚠️ 无法从分析消息中提取流速，消息: {analysis_msg}")
            return None
            
        except Exception as e:
            self._log(f"❌ 提取流速异常: {str(e)}")
            return None

    def _write_coarse_advance_to_plc(self, bucket_id: int, coarse_advance: float) -> bool:
        """
        将快加提前量写入PLC
        
        Args:
            bucket_id (int): 料斗ID
            coarse_advance (float): 快加提前量（克）
            
        Returns:
            bool: 是否写入成功
        """
        try:
            if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                self._log(f"❌ 无效的料斗ID: {bucket_id}")
                return False
            
            # 获取快加提前量的PLC地址
            coarse_advance_address = BUCKET_PARAMETER_ADDRESSES[bucket_id]['CoarseAdvance']
            
            # 快加提前量写入需要×10（根据PLC地址模块的规则）
            coarse_advance_plc = int(coarse_advance * 10)
            
            # 写入到PLC
            success = self.modbus_client.write_holding_register(coarse_advance_address, coarse_advance_plc)
            
            if success:
                self._log(f"📝 料斗{bucket_id}快加提前量写入PLC成功: {coarse_advance}g (PLC值: {coarse_advance_plc})")
                return True
            else:
                self._log(f"❌ 料斗{bucket_id}快加提前量写入PLC失败")
                return False
        
        except Exception as e:
            error_msg = f"料斗{bucket_id}写入快加提前量到PLC异常: {str(e)}"
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
    
    def _handle_bucket_success(self, bucket_id: int, final_fine_speed: int, message: str):
        """
        处理料斗测定成功（修复版本：正确传递慢加流速到自适应学习阶段）
        
        Args:
            bucket_id (int): 料斗ID
            final_fine_speed (int): 最终慢加速度
            message (str): 成功消息
        """
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                # 获取存储的慢加流速
                fine_flow_rate = state.fine_flow_rate
                # 调试：检查状态中的流速值
                self._log(f"🔍 从状态中获取的fine_flow_rate调试 - 值: {fine_flow_rate}, 类型: {type(fine_flow_rate)}")
                # 标记完成并存储慢加流速
                state.complete_successfully(fine_flow_rate)
                # 获取存储的原始目标重量
                original_target_weight = self.bucket_original_weights.get(bucket_id, 200.0)
            
            success_msg = f"🎉 料斗{bucket_id}慢加时间测定成功！最终慢加速度: {final_fine_speed}档（共{state.current_attempt}次尝试）"
            self._log(success_msg)
            
            # 显示慢加流速信息
            if fine_flow_rate is not None:
                self._log(f"💾 料斗{bucket_id}慢加流速已存储: {fine_flow_rate:.3f}g/s")
            else:
                self._log(f"⚠️ 料斗{bucket_id}慢加流速未获取到，将以None传递给自适应学习")
            
            # 不再弹窗显示成功信息，而是启动自适应学习阶段
            self._log(f"🚀 料斗{bucket_id}开始自适应学习阶段...")
            
            # 启动自适应学习阶段（传递存储的慢加流速）
            try:
                from adaptive_learning_controller import create_adaptive_learning_controller
                
                # 创建自适应学习控制器（如果尚未创建）
                if not hasattr(self, 'adaptive_learning_controller'):
                    self.adaptive_learning_controller = create_adaptive_learning_controller(self.modbus_client)
                
                    # 🔥 修复：立即设置物料名称到自适应学习控制器
                    if hasattr(self.adaptive_learning_controller, 'set_material_name'):
                        self.adaptive_learning_controller.set_material_name(self.material_name)
                        self._log(f"📝 已将物料名称'{self.material_name}'传递给自适应学习控制器")
                    else:
                        self._log(f"⚠️ 自适应学习控制器不支持设置物料名称方法")
                    
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
                
                # 调试：在传递之前再次检查流速值
                self._log(f"🔍 即将传递给自适应学习的fine_flow_rate: {fine_flow_rate}, 类型: {type(fine_flow_rate)}")
                
                # 启动自适应学习测定（关键修复：传递存储的慢加流速）
                adaptive_success = False
                if self.adaptive_learning_controller is not None and hasattr(self.adaptive_learning_controller, "start_adaptive_learning_test"):
                    adaptive_success = self.adaptive_learning_controller.start_adaptive_learning_test(
                        bucket_id, original_target_weight, fine_flow_rate)  # 传递存储的慢加流速
                else:
                    self._log("❌ 自适应学习控制器未正确初始化或缺少 start_adaptive_learning_test 方法")
                
                if adaptive_success:
                    # 修复：安全处理fine_flow_rate可能为None的情况
                    if fine_flow_rate is not None:
                        self._log(f"✅ 料斗{bucket_id}自适应学习阶段已启动，慢加流速: {fine_flow_rate:.3f}g/s (已正确传递)")
                    else:
                        self._log(f"⚠️ 料斗{bucket_id}自适应学习阶段已启动，但慢加流速为None")
                else:
                    # 自适应学习启动失败，弹窗显示慢加时间成功信息
                    self._log(f"❌ 料斗{bucket_id}自适应学习启动失败，显示慢加时间结果")
                    self._trigger_bucket_completed(bucket_id, True, success_msg)
                
            except ImportError as e:
                error_msg = f"无法导入自适应学习控制器模块：{str(e)}"
                self._log(f"❌ {error_msg}")
                # 导入失败，弹窗显示慢加时间成功信息
                self._trigger_bucket_completed(bucket_id, True, success_msg)
                
            except Exception as e:
                error_msg = f"自适应学习阶段启动异常：{str(e)}"
                self._log(f"❌ {error_msg}")
                # 异常情况下，弹窗显示慢加时间成功信息
                self._trigger_bucket_completed(bucket_id, True, success_msg)
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}成功状态异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def _handle_bucket_failure(self, bucket_id: int, error_message: str, failed_stage: str = "fine_time"):
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
            
            failure_msg = f"❌ 料斗{bucket_id}慢加时间测定失败: {error_message}（共{state.current_attempt}次尝试）"
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
    
    def _handle_bucket_retry(self, bucket_id: int, new_fine_speed: int, reason: str):
        """
        处理料斗重测
        
        Args:
            bucket_id (int): 料斗ID
            new_fine_speed (int): 新的慢加速度
            reason (str): 重测原因
        """
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                # 检查是否达到最大重试次数
                if state.current_attempt >= state.max_attempts:
                    self._handle_bucket_failure(bucket_id, f"已达最大重试次数({state.max_attempts})，慢加时间测定失败")
                    return
                
                # 更新速度
                state.current_fine_speed = new_fine_speed
            
            self._log(f"🔄 料斗{bucket_id}不符合条件，重测: {reason}")
            self._log(f"📝 更新料斗{bucket_id}慢加速度: {new_fine_speed}档")
            
            # 步骤1: 更新PLC中的慢加速度
            if bucket_id in BUCKET_PARAMETER_ADDRESSES:
                fine_speed_address = BUCKET_PARAMETER_ADDRESSES[bucket_id]['FineSpeed']
                success = self.modbus_client.write_holding_register(fine_speed_address, new_fine_speed)
                if not success:
                    self._handle_bucket_failure(bucket_id, f"更新慢加速度失败，无法继续测定")
                    return
            
            # 步骤2: 等待100ms确保参数写入生效
            time.sleep(0.1)
            
            # 步骤3: 重新开始测定
            self._update_progress(bucket_id, state.current_attempt, state.max_attempts, 
                                f"速度调整为{new_fine_speed}档，准备第{state.current_attempt + 1}次测定...")
            
            # 等待1秒后开始下次尝试
            time.sleep(1.0)
            self._start_single_attempt(bucket_id)
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}重测异常: {str(e)}"
            self.logger.error(error_msg)
            self._handle_bucket_failure(bucket_id, f"{error_msg}，无法继续测定")
            
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
                average_flight_material = state.average_flight_material
                
                # 获取原始目标重量
                original_target_weight = self.bucket_original_weights.get(bucket_id, 200.0)
            
            # 重新启动该料斗的慢加时间测定
            restart_success = self.start_fine_time_test(bucket_id, original_target_weight, average_flight_material)
            
            if restart_success:
                success_msg = f"料斗{bucket_id}物料不足已恢复，慢加时间测定重新启动成功"
                self._log(f"✅ {success_msg}")
                return True, success_msg
            else:
                error_msg = f"料斗{bucket_id}慢加时间测定重新启动失败"
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
            self._log("📢 用户选择取消生产，停止所有慢加时间测定...")
            
            # 停止所有慢加时间测定
            self.stop_all_fine_time_test()
            
            # 调用监测服务的取消方法
            cancel_success = self.monitoring_service.handle_material_shortage_cancel()
            
            success_msg = "✅ 已取消生产，所有慢加时间测定已停止，准备返回AI模式自适应自学习界面"
            self._log(success_msg)
            
            return cancel_success, success_msg
            
        except Exception as e:
            error_msg = f"处理取消生产操作异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
            return False, error_msg
    
    def stop_bucket_fine_time_test(self, bucket_id: int):
        """
        停止指定料斗的慢加时间测定（增强版）
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            with self.lock:
                if bucket_id in self.bucket_states:
                    state = self.bucket_states[bucket_id]
                    if state.is_testing:
                        state.is_testing = False
                        self._log(f"🛑 料斗{bucket_id}慢加时间测定已停止")
            
            # 停止该料斗的监测
            self.monitoring_service.stop_bucket_monitoring(bucket_id)
            
            # 发送该料斗的停止命令（互斥保护）
            success = self._stop_bucket_with_mutex_protection(bucket_id)
            if success:
                self._log(f"✅ 料斗{bucket_id}PLC停止命令发送成功")
            else:
                self._log(f"⚠️ 料斗{bucket_id}PLC停止命令发送失败")
            
        except Exception as e:
            error_msg = f"停止料斗{bucket_id}慢加时间测定异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def stop_all_fine_time_test(self):
        """停止所有料斗的慢加时间测定（增强版 - 禁用物料监测）"""
        try:
            with self.lock:
                for state in self.bucket_states.values():
                    state.is_testing = False
            
            # 🔥 新增：禁用物料监测
            self.monitoring_service.set_material_check_enabled(False)
            self._log("⏸️ 慢加时间测定物料监测已禁用")
            
            # 停止监测服务
            self.monitoring_service.stop_all_monitoring()
            
            self._log("🛑 所有料斗的慢加时间测定已停止")
            
        except Exception as e:
            error_msg = f"停止所有慢加时间测定异常: {str(e)}"
            self.logger.error(error_msg)
            self._log(f"❌ {error_msg}")
    
    def get_bucket_state(self, bucket_id: int) -> Optional[BucketFineTimeState]:
        """
        获取料斗测定状态
        
        Args:
            bucket_id (int): 料斗ID
            
        Returns:
            Optional[BucketFineTimeState]: 料斗状态
        """
        with self.lock:
            return self.bucket_states.get(bucket_id)
    
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
        self._log(f"[慢加监测] {message}")
    
    def dispose(self):
        """释放资源"""
        try:
            self.stop_all_fine_time_test()
            self.monitoring_service.dispose()
            
            # 释放自适应学习控制器资源（如果存在）
            if hasattr(self, 'adaptive_learning_controller') and self.adaptive_learning_controller is not None:
                self.adaptive_learning_controller.dispose()
                self.adaptive_learning_controller = None
            
            self._log("慢加时间测定控制器资源已释放")
        except Exception as e:
            self.logger.error(f"释放控制器资源异常: {e}")

def create_fine_time_test_controller(modbus_client: ModbusClient) -> FineTimeTestController:
    """
    创建慢加时间测定控制器实例的工厂函数
    
    Args:
        modbus_client (ModbusClient): Modbus客户端实例
        
    Returns:
        FineTimeTestController: 控制器实例
    """
    return FineTimeTestController(modbus_client)