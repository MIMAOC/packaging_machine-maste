"""
快加时间测定控制器

作者：C
创建日期：2025-07-23
更新日期：2025-08-19
"""

import threading
import time
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
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_testing = False
        self.is_completed = False
        self.target_weight = 0.0
        self.current_coarse_speed = 0
        self.attempt_count = 0
        self.max_attempts = 15
        self.start_time = None
        self.last_coarse_time_ms = 0
        self.error_message = ""
        self.original_target_weight = 0.0
        self.failed_stage = None
        self.last_flight_material_value = 0.0
    
    def reset_for_new_test(self, target_weight: float, coarse_speed: int):
        self.is_testing = False
        self.is_completed = False
        self.target_weight = target_weight
        self.original_target_weight = target_weight
        self.current_coarse_speed = coarse_speed
        self.attempt_count = 0
        self.start_time = None
        self.last_coarse_time_ms = 0
        self.error_message = ""
        self.failed_stage = None
    
    def start_attempt(self):
        self.is_testing = True
        self.attempt_count += 1
        self.start_time = datetime.now()
    
    def complete_successfully(self):
        self.is_testing = False
        self.is_completed = True
        self.failed_stage = None
    
    def fail_with_error(self, error_message: str, failed_stage: str = None):
        self.is_testing = False
        self.is_completed = True
        self.error_message = error_message
        self.failed_stage = failed_stage

class CoarseTimeTestController:
    
    def __init__(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client
        self.bucket_states: Dict[int, BucketCoarseTimeState] = {}
        self.lock = threading.RLock()
        
        self.monitoring_service = create_bucket_monitoring_service(modbus_client)
        self.bucket_control = create_bucket_control_extended(modbus_client)
        
        self.flight_material_controller = create_flight_material_test_controller(modbus_client)
        
        self.fine_time_controller = create_fine_time_test_controller(modbus_client)
        
        self.on_bucket_completed: Optional[Callable[[int, bool, str], None]] = None
        self.on_bucket_failed: Optional[Callable[[int, str, str], None]] = None
        self.on_progress_update: Optional[Callable[[int, int, int, str], None]] = None
        self.on_material_shortage: Optional[Callable[[int, str, bool], None]] = None
        
        self._initialize_bucket_states()
        
        self.monitoring_service.on_target_reached = self._on_target_reached
        
        self.monitoring_service.on_material_shortage_detected = self._on_material_shortage_detected
        
        self.flight_material_controller.on_bucket_completed = self._on_flight_material_completed
        self.flight_material_controller.on_progress_update = self._on_flight_material_progress_update
        
        self.fine_time_controller.on_bucket_completed = self._on_fine_time_completed
        self.fine_time_controller.on_progress_update = self._on_fine_time_progress_update
        
        self.material_name = "未知物料"
        self.current_material_name = "未知物料"
    
    def _initialize_bucket_states(self):
        with self.lock:
            for bucket_id in range(1, 7):
                self.bucket_states[bucket_id] = BucketCoarseTimeState(bucket_id)
    
    def set_material_name(self, material_name: str):
        try:
            self.material_name = material_name
            self.current_material_name = material_name
            
            if hasattr(self.flight_material_controller, 'set_material_name'):
                self.flight_material_controller.set_material_name(material_name)
            
            if hasattr(self.fine_time_controller, 'set_material_name'):
                self.fine_time_controller.set_material_name(material_name)
            
            if hasattr(self, 'adaptive_learning_controller') and self.adaptive_learning_controller:
                if hasattr(self.adaptive_learning_controller, 'set_material_name'):
                    self.adaptive_learning_controller.set_material_name(material_name)
            
        except Exception as e:
            pass
        
    def get_current_material_name(self) -> str:
        return getattr(self, 'material_name', '未知物料')
    
    def start_coarse_time_test_after_parameter_writing(self, target_weight: float, coarse_speed: int) -> Tuple[bool, str]:
        try:
            with self.lock:
                for bucket_id in range(1, 7):
                    state = self.bucket_states[bucket_id]
                    state.reset_for_new_test(target_weight, coarse_speed)
            
            self.monitoring_service.set_material_check_enabled(True)
            
            start_success, start_msg = self.bucket_control.start_all_buckets_with_mutex_protection()
            if not start_success:
                return False, f"启动所有料斗失败: {start_msg}"
            
            with self.lock:
                for bucket_id in range(1, 7):
                    state = self.bucket_states[bucket_id]
                    state.start_attempt()
            
            bucket_ids = list(range(1, 7))
            self.monitoring_service.start_monitoring(bucket_ids, "coarse_time")
            
            for bucket_id in range(1, 7):
                self._update_progress(bucket_id, 1, 15, "正在进行快加时间测定...")
            
            return True, "快加时间测定流程已启动，正在监测6个料斗的到量状态"
            
        except Exception as e:
            return False, f"启动快加时间测定流程异常: {str(e)}"
        
    def _on_material_shortage_detected(self, bucket_id: int, stage: str, is_production: bool):
        try:
            stage_name = self._get_stage_name(stage)
            
            if not is_production:
                self._handle_material_shortage_for_bucket(bucket_id, stage)
                
                error_message = "料斗物料低于最低水平线或闭合不正常"
                self._handle_bucket_failure(bucket_id, error_message, stage)

            else:
                pass
        
        except Exception as e:
            pass
            
    def _handle_material_shortage_for_bucket(self, bucket_id: int, stage: str):
        try:
            if stage == "coarse_time":
                self.monitoring_service.stop_bucket_monitoring(bucket_id)
                
                with self.lock:
                    state = self.bucket_states.get(bucket_id)
                    if state:
                        state.fail_with_error("物料不足", "coarse_time")
                
            elif stage == "flight_material":
                if hasattr(self.flight_material_controller, 'stop_bucket_flight_material_test'):
                    self.flight_material_controller.stop_bucket_flight_material_test(bucket_id)
                
            elif stage == "fine_time":
                if hasattr(self.fine_time_controller, 'stop_bucket_fine_time_test'):
                    self.fine_time_controller.stop_bucket_fine_time_test(bucket_id)
                
            elif stage == "adaptive_learning":
                self.monitoring_service.stop_bucket_monitoring(bucket_id)
            
        except Exception as e:
            pass
            
    def handle_material_shortage_continue(self, bucket_id: int, stage: str) -> Tuple[bool, str]:
        try:
            self.monitoring_service.handle_material_shortage_continue(bucket_id, False)
            
            if stage == "coarse_time":
                with self.lock:
                    state = self.bucket_states.get(bucket_id)
                    if not state:
                        return False, f"无效的料斗ID: {bucket_id}"
                    
                    state.is_testing = True
                    state.is_completed = False
                    state.error_message = ""
                    state.failed_stage = None
                
                self.monitoring_service.restart_bucket_monitoring(bucket_id, "coarse_time")
                
                self._update_progress(bucket_id, state.attempt_count, state.max_attempts, 
                                    "物料不足已恢复，继续快加时间测定...")
                
            elif stage == "flight_material":
                with self.lock:
                    state = self.bucket_states.get(bucket_id)
                    target_weight = state.target_weight if state else 200.0
                
                flight_success = self.flight_material_controller.start_flight_material_test(bucket_id, target_weight)
                if not flight_success:
                    return False, f"料斗{bucket_id}飞料值测定重新启动失败"
                
            elif stage == "fine_time":
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
                self.monitoring_service.restart_bucket_monitoring(bucket_id, "adaptive_learning")
            
            success_msg = f"料斗{bucket_id}物料不足已恢复，{self._get_stage_name(stage)}继续进行"
            return True, success_msg
            
        except Exception as e:
            return False, f"处理料斗{bucket_id}物料不足继续操作异常: {str(e)}"
        
    def handle_material_shortage_cancel(self) -> Tuple[bool, str]:
        try:
            self.stop_all_coarse_time_test()
            
            cancel_success = self.monitoring_service.handle_material_shortage_cancel()
            
            success_msg = "已取消生产，所有测定流程已停止，准备返回AI模式自适应自学习界面"
            
            return cancel_success, success_msg
            
        except Exception as e:
            return False, f"处理取消生产操作异常: {str(e)}"
    
    def restart_bucket_learning(self, bucket_id: int, restart_mode: str = "from_beginning") -> Tuple[bool, str]:
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return False, f"无效的料斗ID: {bucket_id}"
                
                state = self.bucket_states[bucket_id]
                target_weight = state.original_target_weight
                coarse_speed = state.current_coarse_speed
                failed_stage = state.failed_stage
            
            self.monitoring_service.set_material_check_enabled(True)
            
            if restart_mode == "from_beginning":
                with self.lock:
                    state.reset_for_new_test(target_weight, coarse_speed)
                
                return self._restart_single_bucket_coarse_time(bucket_id, target_weight, coarse_speed)
                
            elif restart_mode == "from_current_stage":
                if not failed_stage:
                    return False, f"料斗{bucket_id}没有失败阶段信息，无法从当前阶段重新学习"
                
                if failed_stage == "coarse_time":
                    with self.lock:
                        state.reset_for_new_test(target_weight, coarse_speed)
                    return self._restart_single_bucket_coarse_time(bucket_id, target_weight, coarse_speed)
                    
                elif failed_stage == "flight_material":
                    flight_success = self.flight_material_controller.start_flight_material_test(bucket_id, target_weight)
                    if flight_success:
                        with self.lock:
                            state.is_testing = True
                            state.failed_stage = None
                        return True, f"料斗{bucket_id}飞料值测定重新启动成功"
                    else:
                        return False, f"料斗{bucket_id}飞料值测定重新启动失败"
                        
                elif failed_stage == "fine_time":
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
                    with self.lock:
                        state.reset_for_new_test(target_weight, coarse_speed)
                    return self._restart_single_bucket_coarse_time(bucket_id, target_weight, coarse_speed)
                
                else:
                    return False, f"未知的失败阶段: {failed_stage}"
            
            else:
                return False, f"未知的重新学习模式: {restart_mode}"
                
        except Exception as e:
            return False, f"料斗{bucket_id}重新学习异常: {str(e)}"
    
    def _restart_single_bucket_coarse_time(self, bucket_id: int, target_weight: float, coarse_speed: int) -> Tuple[bool, str]:
        try:
            if bucket_id in BUCKET_PARAMETER_ADDRESSES:
                addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
                
                target_weight_plc = int(target_weight * 10)
                if not self.modbus_client.write_holding_register(addresses['TargetWeight'], target_weight_plc):
                    return False, f"料斗{bucket_id}目标重量参数写入失败"
                
                if not self.modbus_client.write_holding_register(addresses['CoarseSpeed'], coarse_speed):
                    return False, f"料斗{bucket_id}快加速度参数写入失败"
            
            time.sleep(0.1)
            
            restart_success, restart_msg = self.bucket_control.restart_single_bucket(bucket_id)
            if not restart_success:
                return False, f"重新启动料斗{bucket_id}失败: {restart_msg}"
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.start_attempt()
            
            self.monitoring_service.restart_bucket_monitoring(bucket_id, "coarse_time")
            
            self._update_progress(bucket_id, 1, 15, "重新开始快加时间测定...")
            
            success_msg = f"料斗{bucket_id}快加时间测定重新启动成功"
            return True, success_msg
            
        except Exception as e:
            return False, f"重新启动料斗{bucket_id}快加时间测定异常: {str(e)}"
    
    def _on_target_reached(self, bucket_id: int, coarse_time_ms: int):
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return
                
                state = self.bucket_states[bucket_id]
                if not state.is_testing:
                    return
                
                state.last_coarse_time_ms = coarse_time_ms
            
            def process_target_reached():
                self._process_bucket_target_reached(bucket_id, coarse_time_ms)
            
            processing_thread = threading.Thread(
                target=process_target_reached,
                daemon=True,
                name=f"ProcessTargetReached-{bucket_id}"
            )
            processing_thread.start()
            
        except Exception as e:
            pass
    
    def _process_bucket_target_reached(self, bucket_id: int, coarse_time_ms: int):
        try:
            stop_success, stop_msg = self.bucket_control.execute_bucket_stop_and_discharge_sequence(bucket_id)
            if not stop_success:
                self._handle_bucket_failure(bucket_id, f"停止和放料失败: {stop_msg}", "coarse_time")
                return
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                target_weight = state.target_weight
                current_speed = state.current_coarse_speed
            
            analysis_success, is_compliant, new_speed, analysis_msg = analyze_coarse_time(
                target_weight, coarse_time_ms, current_speed)
            
            if not analysis_success:
                self._handle_bucket_failure(bucket_id, f"快加时间分析失败: {analysis_msg}", "coarse_time")
                return
            
            if is_compliant:
                self._handle_bucket_success(bucket_id, current_speed, analysis_msg)
            else:
                if new_speed is None:
                    self._handle_bucket_failure(bucket_id, analysis_msg, "coarse_time")
                else:
                    self._handle_bucket_retry(bucket_id, new_speed, analysis_msg)
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"处理料斗{bucket_id}到量流程异常: {str(e)}", "coarse_time")
    
    def _handle_bucket_success(self, bucket_id: int, final_speed: int, message: str):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.complete_successfully()
                target_weight = state.target_weight
                
            current_material_name = self.get_current_material_name()
            if hasattr(self.flight_material_controller, 'set_material_name'):
                self.flight_material_controller.set_material_name(current_material_name)
            
            flight_success = self.flight_material_controller.start_flight_material_test(bucket_id, target_weight)
            
            if not flight_success:
                pass
            
        except Exception as e:
            pass
    
    def _handle_bucket_failure(self, bucket_id: int, error_message: str, failed_stage: str = "coarse_time"):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.fail_with_error(error_message, failed_stage)
                
            def trigger_failure_callback():
                if self.on_bucket_failed:
                    try:
                        self.on_bucket_failed(bucket_id, error_message, failed_stage)
                    except Exception as e:
                        pass
            
            if hasattr(self, 'root_reference') and self.root_reference:
                self.root_reference.after(100, trigger_failure_callback)
            
        except Exception as e:
            pass
    
    def _get_stage_name(self, stage: str) -> str:
        stage_names = {
            "coarse_time": "快加时间测定",
            "flight_material": "飞料值测定",
            "fine_time": "慢加时间测定",
            "adaptive_learning": "自适应学习"
        }
        return stage_names.get(stage, stage)
    
    def _handle_bucket_retry(self, bucket_id: int, new_speed: int, reason: str):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                if state.attempt_count >= state.max_attempts:
                    self._handle_bucket_failure(bucket_id, f"已达最大重试次数({state.max_attempts})，快加时间测定失败", "coarse_time")
                    return
                
                state.current_coarse_speed = new_speed
            
            if bucket_id in BUCKET_PARAMETER_ADDRESSES:
                speed_address = BUCKET_PARAMETER_ADDRESSES[bucket_id]['CoarseSpeed']
                success = self.modbus_client.write_holding_register(speed_address, new_speed)
                if not success:
                    self._handle_bucket_failure(bucket_id, f"更新快加速度失败，无法继续测定", "coarse_time")
                    return
            
            time.sleep(0.1)
            
            restart_success, restart_msg = self.bucket_control.restart_single_bucket(bucket_id)
            if not restart_success:
                self._handle_bucket_failure(bucket_id, f"重新启动失败: {restart_msg}，无法继续测定", "coarse_time")
                return
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.start_attempt()
            
            self.monitoring_service.restart_bucket_monitoring(bucket_id, "coarse_time")
            
            self._update_progress(bucket_id, state.attempt_count, state.max_attempts, 
                                f"第{state.attempt_count}次测定（速度调整为{new_speed}档，自动重测中...）")
            
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"处理料斗{bucket_id}重测异常: {str(e)}，无法继续测定", "coarse_time")
    
    def _on_flight_material_completed(self, bucket_id: int, success: bool, message: str):
        try:
            if success:
                flight_material_value = self._extract_flight_material_value_from_message(message)
                
                with self.lock:
                    state = self.bucket_states[bucket_id]
                    original_target_weight = state.original_target_weight
                    state.last_flight_material_value = flight_material_value
                
                current_material_name = self.get_current_material_name()
                if hasattr(self.fine_time_controller, 'set_material_name'):
                    self.fine_time_controller.set_material_name(current_material_name)
                
                fine_time_success = self.fine_time_controller.start_fine_time_test(
                    bucket_id, original_target_weight, flight_material_value)
                
                if not fine_time_success:
                    self._handle_bucket_failure(bucket_id, "慢加时间测定启动失败", "fine_time")
            else:
                self._handle_bucket_failure(bucket_id, message, "flight_material")
                    
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"处理料斗{bucket_id}飞料值完成事件异常: {str(e)}", "flight_material")
    
    def _extract_flight_material_value_from_message(self, message: str) -> float:
        try:
            import re
            
            patterns = [
                r"平均飞料值：([\d.]+)g",
                r"平均飞料值:([\d.]+)g",
                r"平均飞料值：\s*([\d.]+)g",
                r"平均飞料值:\s*([\d.]+)g",
                r"• 平均飞料值：([\d.]+)g",
                r"平均飞料值.*?([\d.]+)g"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message)
                if match:
                    flight_material_value = float(match.group(1))
                    return flight_material_value
                
            number_match = re.findall(r'([\d.]+)g', message)
            if number_match:
                last_value = float(number_match[-1])
                return last_value

            return 0.0
        
        except Exception as e:
            return 0.0
    
    def _on_fine_time_completed(self, bucket_id: int, success: bool, message: str):
        try:
            if success:
                if not hasattr(self, 'adaptive_learning_controller') or not self.adaptive_learning_controller:
                    try:
                        from adaptive_learning_controller import create_adaptive_learning_controller
                        self.adaptive_learning_controller = create_adaptive_learning_controller(self.modbus_client)
                        
                        current_material_name = self.get_current_material_name()
                        if hasattr(self.adaptive_learning_controller, 'set_material_name'):
                            self.adaptive_learning_controller.set_material_name(current_material_name)
                        
                        def on_adaptive_bucket_completed(bucket_id: int, success: bool, message: str):
                            if self.on_bucket_completed:
                                try:
                                    self.on_bucket_completed(bucket_id, success, message)
                                except Exception as e:
                                    pass
                        
                        def on_adaptive_bucket_failed(bucket_id: int, error_message: str, failed_stage: str):
                            if self.on_bucket_failed:
                                try:
                                    self.on_bucket_failed(bucket_id, error_message, failed_stage)
                                except Exception as e:
                                    pass
                        
                        def on_adaptive_progress(bucket_id: int, current: int, max_progress: int, message: str):
                            self._update_progress(bucket_id, current, max_progress, f"[自适应学习] {message}")
                        
                        self.adaptive_learning_controller.on_bucket_completed = on_adaptive_bucket_completed
                        self.adaptive_learning_controller.on_bucket_failed = on_adaptive_bucket_failed
                        self.adaptive_learning_controller.on_progress_update = on_adaptive_progress
                        
                    except ImportError as e:
                        self._trigger_bucket_completed(bucket_id, True, message)
                        return
                    except Exception as e:
                        self._trigger_bucket_completed(bucket_id, True, message)
                        return
                
                self._trigger_bucket_completed(bucket_id, True, message)
                
            else:
                self._handle_bucket_failure(bucket_id, message, "fine_time")
            
        except Exception as e:
            pass
            
    def _on_adaptive_learning_all_completed(self, all_states):
        try:
            if self.on_bucket_completed:
                try:
                    self.on_bucket_completed(0, True, all_states)
                except Exception as e:
                    pass
            
        except Exception as e:
            pass
    
    def _on_adaptive_learning_bucket_failed(self, bucket_id: int, error_message: str, failed_stage: str):
        try:
            if self.on_bucket_failed:
                try:
                    self.on_bucket_failed(bucket_id, error_message, failed_stage)
                except Exception as e:
                    pass
                    
        except Exception as e:
            pass
    
    def _on_fine_time_progress_update(self, bucket_id: int, current_attempt: int, max_attempts: int, message: str):
        try:
            self._update_progress(bucket_id, current_attempt, max_attempts, f"[慢加时间测定] {message}")
            
        except Exception as e:
            pass
    
    def _on_flight_material_progress_update(self, bucket_id: int, current_attempt: int, max_attempts: int, message: str):
        try:
            self._update_progress(bucket_id, current_attempt, max_attempts, f"[飞料值测定] {message}")
            
        except Exception as e:
            pass
    
    def stop_all_coarse_time_test(self) -> Tuple[bool, str]:
        try:
            self.monitoring_service.set_material_check_enabled(False)
            
            self.monitoring_service.stop_all_monitoring()
            
            self.flight_material_controller.stop_all_flight_material_test()
            
            self.fine_time_controller.stop_all_fine_time_test()
            
            stop_success, stop_msg = self.bucket_control.stop_all_buckets()
            
            with self.lock:
                for state in self.bucket_states.values():
                    state.is_testing = False
            
            if stop_success:
                return True, "所有料斗的快加时间测定已停止"
            else:
                return False, f"停止料斗失败: {stop_msg}"
                
        except Exception as e:
            return False, f"停止快加时间测定异常: {str(e)}"
    
    def get_bucket_state(self, bucket_id: int) -> Optional[BucketCoarseTimeState]:
        with self.lock:
            return self.bucket_states.get(bucket_id)
    
    def get_all_bucket_states(self) -> Dict[int, BucketCoarseTimeState]:
        with self.lock:
            return self.bucket_states.copy()
    
    def _trigger_bucket_completed(self, bucket_id: int, success: bool, message: str):
        if self.on_bucket_completed:
            try:
                self.on_bucket_completed(bucket_id, success, message)
            except Exception as e:
                pass
    
    def _update_progress(self, bucket_id: int, current_attempt: int, max_attempts: int, message: str):
        if self.on_progress_update:
            try:
                self.on_progress_update(bucket_id, current_attempt, max_attempts, message)
            except Exception as e:
                pass
    
    def dispose(self):
        try:
            self.monitoring_service.dispose()
            self.flight_material_controller.dispose()
            self.fine_time_controller.dispose()
        except Exception as e:
            pass

def create_coarse_time_test_controller(modbus_client: ModbusClient) -> CoarseTimeTestController:
    return CoarseTimeTestController(modbus_client)