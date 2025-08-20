"""
慢加时间测定控制器

作者：C
创建日期：2025-07-24
更新日期：2025-08-19
"""

import threading
import time
from typing import Dict, Optional, Callable, Tuple
from datetime import datetime
from modbus_client import ModbusClient
from bucket_monitoring import BucketMonitoringService, create_bucket_monitoring_service
from clients.fine_time_webapi import analyze_fine_time
from plc_addresses import BUCKET_PARAMETER_ADDRESSES, get_bucket_control_address

class BucketFineTimeState:
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_testing = False
        self.is_completed = False
        self.current_attempt = 0
        self.max_attempts = 15
        self.start_time = None
        self.target_reached_time = None
        self.fine_time_ms = 0
        self.current_fine_speed = 44
        self.error_message = ""
        self.average_flight_material = 0.0
        self.fine_flow_rate = None
        self.material_name = "未知物料"
        self.root_reference = None
    
    def reset_for_new_test(self, average_flight_material: float = 0.0):
        self.is_testing = False
        self.is_completed = False
        self.current_attempt = 0
        self.start_time = None
        self.target_reached_time = None
        self.fine_time_ms = 0
        self.current_fine_speed = 44
        self.error_message = ""
        self.average_flight_material = average_flight_material
        self.fine_flow_rate = None
    
    def start_next_attempt(self):
        self.is_testing = True
        self.current_attempt += 1
        self.start_time = datetime.now()
    
    def record_target_reached(self, reached_time: datetime):
        self.target_reached_time = reached_time
        self.fine_time_ms = int((reached_time - self.start_time).total_seconds() * 1000)
        self.is_testing = False
    
    def complete_successfully(self, fine_flow_rate: Optional[float] = None):
        self.is_testing = False
        self.is_completed = True
        if fine_flow_rate is not None:
            self.fine_flow_rate = fine_flow_rate
    
    def fail_with_error(self, error_message: str):
        self.is_testing = False
        self.is_completed = True
        self.error_message = error_message

class FineTimeTestController:
    
    def __init__(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client
        self.bucket_states: Dict[int, BucketFineTimeState] = {}
        self.bucket_original_weights: Dict[int, float] = {}
        self.lock = threading.RLock()
        self.material_name = "未知物料"
        
        self.monitoring_service = create_bucket_monitoring_service(modbus_client)
        
        self.on_bucket_completed: Optional[Callable[[int, bool, str], None]] = None
        self.on_bucket_failed: Optional[Callable[[int, str, str], None]] = None
        self.on_progress_update: Optional[Callable[[int, int, int, str], None]] = None
        self.on_log_message: Optional[Callable[[str], None]] = None
        
        self.on_material_shortage: Optional[Callable[[int, str, bool], None]] = None
        
        self._initialize_bucket_states()
        
        self.monitoring_service.on_target_reached = self._on_target_reached
        self.monitoring_service.on_monitoring_log = self._on_monitoring_log
        
        self.monitoring_service.on_material_shortage_detected = self._on_material_shortage_detected
    
    def _initialize_bucket_states(self):
        with self.lock:
            for bucket_id in range(1, 7):
                self.bucket_states[bucket_id] = BucketFineTimeState(bucket_id)
    
    def set_material_name(self, material_name: str):
        try:
            self.material_name = material_name
            with self.lock:
                for state in self.bucket_states.values():
                    state.material_name = material_name
        except Exception as e:
            pass
                
    def _on_material_shortage_detected(self, bucket_id: int, stage: str, is_production: bool):
        try:
            if stage == "fine_time" and not is_production:
                self._handle_material_shortage_for_bucket(bucket_id)
                
                def trigger_shortage_failure():
                    error_message = "料斗物料低于最低水平线或闭合不正常"
                    self._handle_bucket_failure(bucket_id, error_message, stage)
                
                import threading
                threading.Timer(0.2 * bucket_id, trigger_shortage_failure).start()
            
        except Exception as e:
            pass
    
    def _handle_material_shortage_for_bucket(self, bucket_id: int):
        try:
            self.stop_bucket_fine_time_test(bucket_id)
            
            with self.lock:
                state = self.bucket_states.get(bucket_id)
                if state:
                    state.fail_with_error("物料不足")
            
        except Exception as e:
            pass
    
    def start_fine_time_test(self, bucket_id: int, original_target_weight: float = 200.0, 
                              average_flight_material: float = 0.0) -> bool:
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return False
                
                state = self.bucket_states[bucket_id]
                if state.is_testing or state.is_completed:
                    return True
                
                state.reset_for_new_test(average_flight_material)
                
                self.bucket_original_weights[bucket_id] = original_target_weight
            
            self.monitoring_service.set_material_check_enabled(True)
            
            self._start_single_attempt(bucket_id)
            
            return True
            
        except Exception as e:
            return False
    
    def _start_single_attempt(self, bucket_id: int):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.start_next_attempt()
            
            self._update_progress(bucket_id, state.current_attempt, state.max_attempts, 
                                f"正在进行第{state.current_attempt}次慢加时间测定...")
            
            def attempt_thread():
                self._execute_single_attempt(bucket_id)
            
            thread = threading.Thread(target=attempt_thread, daemon=True, 
                                    name=f"FineTime-{bucket_id}-{state.current_attempt}")
            thread.start()
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"启动料斗{bucket_id}单次尝试异常: {str(e)}")
    
    def _execute_single_attempt(self, bucket_id: int):
        try:
            success = self._write_test_parameters(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}写入测定参数失败")
                return
            
            success = self._start_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"启动料斗{bucket_id}失败")
                return
            
            self.monitoring_service.start_monitoring([bucket_id], "fine_time")
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"执行料斗{bucket_id}单次尝试异常: {str(e)}")
    
    def _write_test_parameters(self, bucket_id: int) -> bool:
        try:
            bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
            
            target_weight_plc = 6 * 10
            coarse_advance = 6 * 10
            
            success = self.modbus_client.write_holding_register(
                bucket_addresses['TargetWeight'], target_weight_plc)
            if not success:
                return False
            
            success = self.modbus_client.write_holding_register(
                bucket_addresses['CoarseAdvance'], coarse_advance)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _start_bucket_with_mutex_protection(self, bucket_id: int) -> bool:
        try:
            start_address = get_bucket_control_address(bucket_id, 'StartAddress')
            stop_address = get_bucket_control_address(bucket_id, 'StopAddress')
            
            success = self.modbus_client.write_coil(stop_address, False)
            if not success:
                return False
            
            time.sleep(0.05)
            
            success = self.modbus_client.write_coil(start_address, True)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _on_target_reached(self, bucket_id: int, time_ms: int):
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return
                
                state = self.bucket_states[bucket_id]
                if not state.is_testing:
                    return
                
                state.record_target_reached(datetime.now())
            
            def process_thread():
                self._process_target_reached_for_fine_time(bucket_id)
            
            thread = threading.Thread(target=process_thread, daemon=True, 
                                    name=f"ProcessFineTarget-{bucket_id}")
            thread.start()
            
        except Exception as e:
            pass
    
    def _process_target_reached_for_fine_time(self, bucket_id: int):
        try:
            self.monitoring_service.stop_bucket_monitoring(bucket_id)
            
            success = self._stop_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"停止料斗{bucket_id}失败")
                return
            
            time.sleep(0.6)
            
            success = self._execute_discharge_sequence(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}放料操作失败")
                return
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                fine_time_ms = state.fine_time_ms
                current_fine_speed = state.current_fine_speed
                flight_material_value = state.average_flight_material
                
                original_target_weight = self.bucket_original_weights.get(bucket_id, 200.0)
            
            try:
                api_result = analyze_fine_time(
                    6.0, fine_time_ms, current_fine_speed, original_target_weight, flight_material_value)
                
                if len(api_result) >= 6:
                    analysis_success, is_compliant, new_fine_speed, coarse_advance, fine_flow_rate, analysis_msg = api_result
                else:
                    analysis_success, is_compliant, new_fine_speed, coarse_advance, fine_flow_rate, analysis_msg = (
                        api_result + [None] * (6 - len(api_result)))[:6]
                    
            except Exception as e:
                self._handle_bucket_failure(bucket_id, f"慢加时间API调用异常: {str(e)}")
                return
        
            if not analysis_success:
                self._handle_bucket_failure(bucket_id, f"慢加时间分析失败: {analysis_msg}")
                return
            
            extracted_flow_rate = self._extract_flow_rate_from_message(analysis_msg)
            if fine_flow_rate is None and extracted_flow_rate is not None:
                fine_flow_rate = extracted_flow_rate
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.fine_flow_rate = fine_flow_rate
            
            if coarse_advance is not None:
                success = self._write_coarse_advance_to_plc(bucket_id, coarse_advance)
            
            if is_compliant:
                self._handle_bucket_success(bucket_id, current_fine_speed, analysis_msg)
            else:
                if new_fine_speed is None:
                    self._handle_bucket_failure(bucket_id, analysis_msg)
                else:
                    self._handle_bucket_retry(bucket_id, new_fine_speed, analysis_msg)
        
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"处理料斗{bucket_id}慢加到重流程异常: {str(e)}")
    
    def _extract_flow_rate_from_message(self, analysis_msg: str) -> Optional[float]:
        try:
            import re
            
            patterns = [
                r"流速[：:]\s*([\d.]+)\s*g/s",
                r"流速[：:]\s*([\d.]+)g/s",
                r"流速\s+([\d.]+)\s*g/s",
                r"速度[：:]\s*([\d.]+)\s*g/s",
                r"([\d.]+)\s*g/s",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, analysis_msg)
                if match:
                    flow_rate = float(match.group(1))
                    return flow_rate
            
            return None
            
        except Exception as e:
            return None

    def _write_coarse_advance_to_plc(self, bucket_id: int, coarse_advance: float) -> bool:
        try:
            if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                return False
            
            coarse_advance_address = BUCKET_PARAMETER_ADDRESSES[bucket_id]['CoarseAdvance']
            
            coarse_advance_plc = int(coarse_advance * 10)
            
            success = self.modbus_client.write_holding_register(coarse_advance_address, coarse_advance_plc)
            
            return success
        
        except Exception as e:
            return False
        
    def _stop_bucket_with_mutex_protection(self, bucket_id: int) -> bool:
        try:
            start_address = get_bucket_control_address(bucket_id, 'StartAddress')
            stop_address = get_bucket_control_address(bucket_id, 'StopAddress')
            
            success = self.modbus_client.write_coil(start_address, False)
            if not success:
                return False
            
            time.sleep(0.05)
            
            success = self.modbus_client.write_coil(stop_address, True)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _execute_discharge_sequence(self, bucket_id: int) -> bool:
        try:
            discharge_address = get_bucket_control_address(bucket_id, 'DischargeAddress')
            
            success = self.modbus_client.write_coil(discharge_address, True)
            if not success:
                return False
            
            time.sleep(1.5)
            
            success = self.modbus_client.write_coil(discharge_address, False)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _handle_bucket_success(self, bucket_id: int, final_fine_speed: int, message: str):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                fine_flow_rate = state.fine_flow_rate
                state.complete_successfully(fine_flow_rate)
                original_target_weight = self.bucket_original_weights.get(bucket_id, 200.0)
            
            success_msg = f"料斗{bucket_id}慢加时间测定成功！最终慢加速度: {final_fine_speed}档（共{state.current_attempt}次尝试）"
            
            try:
                from adaptive_learning_controller import create_adaptive_learning_controller
                
                if not hasattr(self, 'adaptive_learning_controller'):
                    self.adaptive_learning_controller = create_adaptive_learning_controller(self.modbus_client)
                    
                    if hasattr(self.adaptive_learning_controller, 'set_material_name'):
                        self.adaptive_learning_controller.set_material_name(self.material_name)
                    
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
                    
                    def on_adaptive_log(message: str):
                        pass
                    
                    self.adaptive_learning_controller.on_bucket_completed = on_adaptive_bucket_completed
                    self.adaptive_learning_controller.on_bucket_failed = on_adaptive_bucket_failed
                    self.adaptive_learning_controller.on_progress_update = on_adaptive_progress
                    self.adaptive_learning_controller.on_log_message = on_adaptive_log
                
                adaptive_success = self.adaptive_learning_controller.start_adaptive_learning_test(
                    bucket_id, original_target_weight, fine_flow_rate)
                
                if not adaptive_success:
                    self._trigger_bucket_completed(bucket_id, True, success_msg)
                
            except ImportError as e:
                self._trigger_bucket_completed(bucket_id, True, success_msg)
                
            except Exception as e:
                self._trigger_bucket_completed(bucket_id, True, success_msg)
            
        except Exception as e:
            pass
    
    def _handle_bucket_failure(self, bucket_id: int, error_message: str, failed_stage: str = "fine_time"):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.fail_with_error(error_message)
            
            def trigger_failure_callback():
                if self.on_bucket_failed:
                    try:
                        self.on_bucket_failed(bucket_id, error_message, failed_stage)
                    except Exception as e:
                        pass
            
            if self.root_reference:
                self.root_reference.after(100, trigger_failure_callback)
            
        except Exception as e:
            pass
    
    def _handle_bucket_retry(self, bucket_id: int, new_fine_speed: int, reason: str):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                if state.current_attempt >= state.max_attempts:
                    self._handle_bucket_failure(bucket_id, f"已达最大重试次数({state.max_attempts})，慢加时间测定失败")
                    return
                
                state.current_fine_speed = new_fine_speed
            
            if bucket_id in BUCKET_PARAMETER_ADDRESSES:
                fine_speed_address = BUCKET_PARAMETER_ADDRESSES[bucket_id]['FineSpeed']
                success = self.modbus_client.write_holding_register(fine_speed_address, new_fine_speed)
                if not success:
                    self._handle_bucket_failure(bucket_id, f"更新慢加速度失败，无法继续测定")
                    return
            
            time.sleep(0.1)
            
            self._update_progress(bucket_id, state.current_attempt, state.max_attempts, 
                                f"速度调整为{new_fine_speed}档，准备第{state.current_attempt + 1}次测定...")
            
            time.sleep(1.0)
            self._start_single_attempt(bucket_id)
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"处理料斗{bucket_id}重测异常: {str(e)}，无法继续测定")
            
    def handle_material_shortage_continue(self, bucket_id: int) -> Tuple[bool, str]:
        try:
            self.monitoring_service.handle_material_shortage_continue(bucket_id, False)
            
            with self.lock:
                state = self.bucket_states.get(bucket_id)
                if not state:
                    return False, f"无效的料斗ID: {bucket_id}"
                
                state.is_testing = False
                state.is_completed = False
                state.error_message = ""
                average_flight_material = state.average_flight_material
                
                original_target_weight = self.bucket_original_weights.get(bucket_id, 200.0)
            
            restart_success = self.start_fine_time_test(bucket_id, original_target_weight, average_flight_material)
            
            if restart_success:
                success_msg = f"料斗{bucket_id}物料不足已恢复，慢加时间测定重新启动成功"
                return True, success_msg
            else:
                error_msg = f"料斗{bucket_id}慢加时间测定重新启动失败"
                return False, error_msg
            
        except Exception as e:
            return False, f"处理料斗{bucket_id}物料不足继续操作异常: {str(e)}"
    
    def handle_material_shortage_cancel(self) -> Tuple[bool, str]:
        try:
            self.stop_all_fine_time_test()
            
            cancel_success = self.monitoring_service.handle_material_shortage_cancel()
            
            success_msg = "已取消生产，所有慢加时间测定已停止，准备返回AI模式自适应自学习界面"
            
            return cancel_success, success_msg
            
        except Exception as e:
            return False, f"处理取消生产操作异常: {str(e)}"
    
    def stop_bucket_fine_time_test(self, bucket_id: int):
        try:
            with self.lock:
                if bucket_id in self.bucket_states:
                    state = self.bucket_states[bucket_id]
                    if state.is_testing:
                        state.is_testing = False
            
            self.monitoring_service.stop_bucket_monitoring(bucket_id)
            
            success = self._stop_bucket_with_mutex_protection(bucket_id)
            
        except Exception as e:
            pass
    
    def stop_all_fine_time_test(self):
        try:
            with self.lock:
                for state in self.bucket_states.values():
                    state.is_testing = False
            
            self.monitoring_service.set_material_check_enabled(False)
            
            self.monitoring_service.stop_all_monitoring()
            
        except Exception as e:
            pass
    
    def get_bucket_state(self, bucket_id: int) -> Optional[BucketFineTimeState]:
        with self.lock:
            return self.bucket_states.get(bucket_id)
    
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
    
    def _log(self, message: str):
        pass
    
    def _on_monitoring_log(self, message: str):
        pass
    
    def dispose(self):
        try:
            self.stop_all_fine_time_test()
            self.monitoring_service.dispose()
            
            if hasattr(self, 'adaptive_learning_controller'):
                self.adaptive_learning_controller.dispose()
                self.adaptive_learning_controller = None
            
        except Exception as e:
            pass

def create_fine_time_test_controller(modbus_client: ModbusClient) -> FineTimeTestController:
    return FineTimeTestController(modbus_client)