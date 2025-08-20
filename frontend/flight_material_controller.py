"""
飞料值测定控制器

作者：C
创建日期：2025-07-23
"""

import threading
import time
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
from modbus_client import ModbusClient
from bucket_monitoring import BucketMonitoringService, create_bucket_monitoring_service
from clients.flight_material_webapi import analyze_flight_material
from bucket_control_extended import BucketControlExtended, create_bucket_control_extended
from plc_addresses import BUCKET_PARAMETER_ADDRESSES, BUCKET_MONITORING_ADDRESSES

class BucketFlightMaterialState:
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_testing = False
        self.is_completed = False
        self.target_weight = 0.0
        self.current_attempt = 0
        self.max_attempts = 3
        self.recorded_weights = []
        self.start_time = None
        self.error_message = ""
        self.average_flight_material = 0.0
        self.material_name = "未知物料"
        self.root_reference = None
    
    def reset_for_new_test(self, target_weight: float):
        self.is_testing = False
        self.is_completed = False
        self.target_weight = target_weight
        self.current_attempt = 0
        self.recorded_weights = []
        self.start_time = None
        self.error_message = ""
        self.average_flight_material = 0.0
    
    def start_next_attempt(self):
        self.is_testing = True
        self.current_attempt += 1
        if self.start_time is None:
            self.start_time = datetime.now()
    
    def record_weight(self, weight: float):
        self.recorded_weights.append(weight)
        self.is_testing = False
    
    def complete_successfully(self, average_flight_material: float):
        self.is_testing = False
        self.is_completed = True
        self.average_flight_material = average_flight_material
    
    def fail_with_error(self, error_message: str):
        self.is_testing = False
        self.is_completed = True
        self.error_message = error_message

class FlightMaterialTestController:
    
    def __init__(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client
        self.bucket_states: Dict[int, BucketFlightMaterialState] = {}
        self.lock = threading.RLock()
        self.material_name = "未知物料"
        
        self.monitoring_service = create_bucket_monitoring_service(modbus_client)
        self.bucket_control = create_bucket_control_extended(modbus_client)
        
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
        """初始化料斗状态"""
        with self.lock:
            for bucket_id in range(1, 7):
                self.bucket_states[bucket_id] = BucketFlightMaterialState(bucket_id)
                
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
            if stage == "flight_material" and not is_production:
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
            self.stop_bucket_flight_material_test(bucket_id)
            
            with self.lock:
                state = self.bucket_states.get(bucket_id)
                if state:
                    state.fail_with_error("物料不足")
            
        except Exception as e:
            pass
    
    def start_flight_material_test(self, bucket_id: int, target_weight: float) -> bool:
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return False
                
                state = self.bucket_states[bucket_id]
                if state.is_testing or state.is_completed:
                    return True
                
                state.reset_for_new_test(target_weight)
            
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
                                f"正在进行第{state.current_attempt}次飞料值测定...")
            
            def attempt_thread():
                self._execute_single_attempt(bucket_id)
            
            thread = threading.Thread(target=attempt_thread, daemon=True, 
                                    name=f"FlightMaterial-{bucket_id}-{state.current_attempt}")
            thread.start()
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"启动料斗{bucket_id}单次尝试异常: {str(e)}")
    
    def _execute_single_attempt(self, bucket_id: int):
        try:
            success = self._start_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"启动料斗{bucket_id}失败")
                return
            
            self.monitoring_service.start_monitoring([bucket_id], "flight_material")
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"执行料斗{bucket_id}单次尝试异常: {str(e)}")
    
    def _start_bucket_with_mutex_protection(self, bucket_id: int) -> bool:
        try:
            from plc_addresses import get_bucket_control_address
            
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
    
    def _on_target_reached(self, bucket_id: int, coarse_time_ms: int):
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return
                
                state = self.bucket_states[bucket_id]
                if not state.is_testing:
                    return
            
            def process_thread():
                self._process_target_reached_for_flight_material(bucket_id)
            
            thread = threading.Thread(target=process_thread, daemon=True, 
                                    name=f"ProcessFlightTarget-{bucket_id}")
            thread.start()
            
        except Exception as e:
            pass
    
    def _process_target_reached_for_flight_material(self, bucket_id: int):
        try:
            success = self._stop_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"停止料斗{bucket_id}失败")
                return
            
            time.sleep(1)
            
            weight = self._read_bucket_weight(bucket_id)
            if weight is None:
                self._handle_bucket_failure(bucket_id, f"读取料斗{bucket_id}实时重量失败")
                return
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.record_weight(weight)
            
            success = self._discharge_bucket(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}放料操作失败")
                return
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                if state.current_attempt >= state.max_attempts:
                    self._complete_flight_material_test(bucket_id)
                else:
                    time.sleep(1.0)
                    self._start_single_attempt(bucket_id)
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"处理料斗{bucket_id}飞料到重流程异常: {str(e)}")
    
    def _stop_bucket_with_mutex_protection(self, bucket_id: int) -> bool:
        try:
            from plc_addresses import get_bucket_control_address
            
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
    
    def _read_bucket_weight(self, bucket_id: int) -> Optional[float]:
        try:
            if bucket_id not in BUCKET_MONITORING_ADDRESSES:
                return None
            
            weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
            
            raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
            
            if raw_weight_data is not None and len(raw_weight_data) > 0:
                weight_value = raw_weight_data[0] / 10.0
                return weight_value
            else:
                return None
                
        except Exception as e:
            return None
    
    def _discharge_bucket(self, bucket_id: int) -> bool:
        try:
            from plc_addresses import get_bucket_control_address
            
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
    
    def _complete_flight_material_test(self, bucket_id: int):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                recorded_weights = state.recorded_weights[:]
                target_weight = state.target_weight
            
            analysis_success, avg_flight_material, flight_details, message = analyze_flight_material(
                target_weight, recorded_weights)
            
            if analysis_success:
                with self.lock:
                    state.complete_successfully(avg_flight_material)
                
                success_msg = (f"料斗{bucket_id}飞料值测定成功！\n\n"
                             f"测定结果：\n"
                             f"  • 目标重量：{target_weight}g\n"
                             f"  • 3次实时重量：{recorded_weights[0]:.1f}g, {recorded_weights[1]:.1f}g, {recorded_weights[2]:.1f}g\n"
                             f"  • 3次飞料值：{flight_details[0]:.1f}g, {flight_details[1]:.1f}g, {flight_details[2]:.1f}g\n"
                             f"  • 平均飞料值：{avg_flight_material:.1f}g\n\n"
                             f"料斗{bucket_id}飞料值测定完成！")
                
                self._trigger_bucket_completed(bucket_id, True, success_msg)
            else:
                self._handle_bucket_failure(bucket_id, f"WebAPI计算飞料值失败: {message}")
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"完成料斗{bucket_id}飞料值测定异常: {str(e)}")
    
    def _handle_bucket_failure(self, bucket_id: int, error_message: str, failed_stage: str = "flight_material"):
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
    
    def get_bucket_state(self, bucket_id: int) -> Optional[BucketFlightMaterialState]:
        with self.lock:
            return self.bucket_states.get(bucket_id)
    
    def stop_bucket_flight_material_test(self, bucket_id: int):
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
    
    def stop_all_flight_material_test(self):
        try:
            with self.lock:
                for state in self.bucket_states.values():
                    state.is_testing = False
            
            self.monitoring_service.set_material_check_enabled(False)
            
            self.monitoring_service.stop_all_monitoring()
            
        except Exception as e:
            pass
            
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
                target_weight = state.target_weight
            
            restart_success = self.start_flight_material_test(bucket_id, target_weight)
            
            if restart_success:
                success_msg = f"料斗{bucket_id}物料不足已恢复，飞料值测定重新启动成功"
                return True, success_msg
            else:
                error_msg = f"料斗{bucket_id}飞料值测定重新启动失败"
                return False, error_msg
            
        except Exception as e:
            return False, f"处理料斗{bucket_id}物料不足继续操作异常: {str(e)}"
        
    def handle_material_shortage_cancel(self) -> Tuple[bool, str]:
        try:
            self.stop_all_flight_material_test()
            
            cancel_success = self.monitoring_service.handle_material_shortage_cancel()
            
            success_msg = "已取消生产，所有飞料值测定已停止，准备返回AI模式自适应自学习界面"
            
            return cancel_success, success_msg
            
        except Exception as e:
            return False, f"处理取消生产操作异常: {str(e)}"
    
    def _trigger_bucket_completed(self, bucket_id: int, success: bool, message: str):
        if self.on_bucket_completed:
            try:
                with self.lock:
                    state = self.bucket_states[bucket_id]
                    avg_flight_material = state.average_flight_material
                
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
            self.stop_all_flight_material_test()
            self.monitoring_service.dispose()
        except Exception as e:
            pass

def create_flight_material_test_controller(modbus_client: ModbusClient) -> FlightMaterialTestController:
    return FlightMaterialTestController(modbus_client)