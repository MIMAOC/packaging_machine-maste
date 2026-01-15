"""
料斗监测模块

作者：C
创建日期：2025-07-23
更新日期：2025-08-19
"""

import threading
import time
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

try:
    from database.production_detail_dao import ProductionDetailDAO, ProductionDetail
    PRODUCTION_DETAIL_DAO_AVAILABLE = True
except ImportError as e:
    PRODUCTION_DETAIL_DAO_AVAILABLE = False

class BucketProductionState:
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_monitoring_target = False
        self.is_monitoring_discharge = False
        self.target_reached_time = None
        self.discharge_time = None
        self.last_target_reached = False
        self.last_discharge_state = False
        self.consecutive_unqualified = 0
        self.waiting_for_restart = False
        self.restart_time = None
        
        self.temp_real_weight = 0.0
        self.temp_error_value = 0.0
        self.temp_is_qualified = False
        
    def reset(self):
        self.is_monitoring_target = False
        self.is_monitoring_discharge = False
        self.target_reached_time = None
        self.discharge_time = None
        self.last_target_reached = False
        self.last_discharge_state = False
        self.waiting_for_restart = False
        self.restart_time = None
        self.temp_real_weight = 0.0
        self.temp_error_value = 0.0
        self.temp_is_qualified = False

class BucketMonitoringState:
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_monitoring = False
        self.start_time = None
        self.target_reached_time = None
        self.coarse_time_ms = 0
        self.last_target_reached = False
        self.last_coarse_active = None
        self.monitoring_type = "coarse_time"
        self.coarse_active_initialized = False
        
        self.weight_history: Deque[tuple] = deque(maxlen=150)
        self.last_start_active = None
        self.start_active_initialized = False
        self.material_shortage_detected = False
        self.material_shortage_time = None
    
    def reset(self):
        self.is_monitoring = False
        self.start_time = None
        self.target_reached_time = None
        self.coarse_time_ms = 0
        self.last_target_reached = False
        self.last_coarse_active = None
        self.monitoring_type = "coarse_time"
        self.coarse_active_initialized = False
        
        self.weight_history.clear()
        self.last_start_active = None
        self.start_active_initialized = False
        self.material_shortage_detected = False
        self.material_shortage_time = None
    
    def start_monitoring(self, monitoring_type: str = "coarse_time"):
        self.reset()
        self.is_monitoring = True
        self.start_time = datetime.now()
        self.monitoring_type = monitoring_type
    
    def add_weight_record(self, weight: float):
        current_time = time.time()
        self.weight_history.append((current_time, weight))
    
    def get_weight_15s_ago(self) -> Optional[float]:
        if not self.weight_history:
            return None
        
        current_time = time.time()
        target_time = current_time - 15.0
        
        for timestamp, weight in self.weight_history:
            if timestamp <= target_time:
                return weight
        
        return None

class BucketMonitoringService:
    def __init__(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client
        self.monitoring_states: Dict[int, BucketMonitoringState] = {}
        self.monitoring_thread = None
        self.stop_monitoring_flag = threading.Event()
        self.lock = threading.RLock()
        
        self.monitoring_interval = 0.1
        
        self.on_target_reached: Optional[Callable[[int, int], None]] = None
        self.on_coarse_status_changed: Optional[Callable[[int, bool], None]] = None
        self.on_material_shortage_detected: Optional[Callable[[int, str, bool], None]] = None
        
        self.production_states: Dict[int, BucketProductionState] = {}
        self.production_id = ""
        self.target_weight = 0.0
        self.is_production_monitoring = False
        
        self.on_production_detail_recorded: Optional[Callable[[int, ProductionDetail], None]] = None
        self.on_production_stop_triggered: Optional[Callable[[int, str], None]] = None
        self.on_single_unqualified_triggered: Optional[Callable[[int, float, float], None]] = None
        
        self.material_check_enabled = False
        self.weight_threshold = 0.3
        
        self._initialize_bucket_states()
        
        self._initialize_production_states()
    
    def _initialize_production_states(self):
        with self.lock:
            for bucket_id in range(1, 7):
                self.production_states[bucket_id] = BucketProductionState(bucket_id)
    
    def _initialize_bucket_states(self):
        with self.lock:
            for bucket_id in range(1, 7):
                self.monitoring_states[bucket_id] = BucketMonitoringState(bucket_id)
    
    def set_material_check_enabled(self, enabled: bool):
        with self.lock:
            self.material_check_enabled = enabled
    
    def start_monitoring(self, bucket_ids: List[int], monitoring_type: str = "coarse_time"):
        try:
            with self.lock:
                if self.monitoring_thread and self.monitoring_thread.is_alive():
                    self.stop_monitoring_flag.set()
                    self.monitoring_thread.join(timeout=1.0)
                
                for bucket_id in bucket_ids:
                    if bucket_id in self.monitoring_states:
                        self.monitoring_states[bucket_id].start_monitoring(monitoring_type)
                
                self.stop_monitoring_flag.clear()
                self.monitoring_thread = threading.Thread(
                    target=self._monitoring_thread_func,
                    daemon=True,
                    name="BucketMonitoring"
                )
                self.monitoring_thread.start()
                
        except Exception as e:
            pass
    
    def restart_bucket_monitoring(self, bucket_id: int, monitoring_type: str = "coarse_time"):
        try:
            with self.lock:
                if bucket_id in self.monitoring_states:
                    self.monitoring_states[bucket_id].start_monitoring(monitoring_type)
        except Exception as e:
            pass
    
    def stop_bucket_monitoring(self, bucket_id: int):
        try:
            with self.lock:
                if bucket_id in self.monitoring_states:
                    state = self.monitoring_states[bucket_id]
                    if state.is_monitoring:
                        state.is_monitoring = False
        except Exception as e:
            pass
    
    def stop_all_monitoring(self):
        try:
            with self.lock:
                self.stop_monitoring_flag.set()
                
                self.stop_production_monitoring()
                
                for state in self.monitoring_states.values():
                    state.is_monitoring = False
                    
                if self.monitoring_thread and self.monitoring_thread.is_alive():
                    self.monitoring_thread.join(timeout=1.0)

        except Exception as e:
            pass
    
    def _monitoring_thread_func(self):
        """监测线程主函数"""
        try:
            while not self.stop_monitoring_flag.is_set():
                monitoring_buckets = []
                with self.lock:
                    for bucket_id, state in self.monitoring_states.items():
                        if state.is_monitoring:
                            monitoring_buckets.append(bucket_id)
                
                if monitoring_buckets:
                    self._check_target_reached_status(monitoring_buckets)
                
                if self.is_production_monitoring:
                    self._check_production_states()
                
                if not monitoring_buckets and not self.is_production_monitoring:
                    time.sleep(0.5)
                    continue
                
                time.sleep(self.monitoring_interval)
                
        except Exception as e:
            pass
    
    def _check_target_reached_status(self, monitoring_buckets: List[int]):
        try:
            target_reached_addresses = get_all_bucket_target_reached_addresses()
            
            coil_states = self.modbus_client.read_coils(
                target_reached_addresses[0], len(target_reached_addresses))
            
            if coil_states is None:
                return
            
            start_states = None
            if self.material_check_enabled:
                start_addresses = [BUCKET_CONTROL_ADDRESSES[i]['StartAddress'] for i in range(1, 7)]
                start_states = self.modbus_client.read_coils(start_addresses[0], len(start_addresses))
                
                if start_states is None:
                    pass
            
            weight_data = None
            if self.material_check_enabled:
                weight_addresses = get_all_bucket_weight_addresses()
                weight_registers = []
                for addr in weight_addresses:
                    weight_reg = self.modbus_client.read_holding_registers(addr, 1)
                    if weight_reg:
                        raw_value = weight_reg[0]
                        if raw_value > 32767:
                            signed_value = raw_value - 65536
                        else:
                            signed_value = raw_value
                        weight_registers.append(signed_value / 10.0)
                    else:
                        weight_registers.append(0.0)
                weight_data = weight_registers
                
            coarse_states = None
            if any(self.monitoring_states[bid].monitoring_type == "adaptive_learning" 
                   for bid in monitoring_buckets if bid in self.monitoring_states):
                
                coarse_add_addresses = get_all_bucket_coarse_add_addresses()
                
                coarse_states = self.modbus_client.read_coils(
                    coarse_add_addresses[0], len(coarse_add_addresses))
                
                if coarse_states is None:
                    pass
            
            current_time = datetime.now()
            
            with self.lock:
                for i, bucket_id in enumerate(range(1, 7)):
                    if bucket_id not in monitoring_buckets:
                        continue
                    
                    state = self.monitoring_states[bucket_id]
                    if not state.is_monitoring:
                        continue
                    
                    current_target_reached = coil_states[i] if i < len(coil_states) else False
                    
                    if (self.material_check_enabled and start_states and weight_data and 
                        i < len(start_states) and i < len(weight_data)):
                        
                        self._check_material_shortage(bucket_id, state, start_states[i], 
                                                    current_target_reached, weight_data[i])
                    
                    if current_target_reached and not state.last_target_reached:
                        state.target_reached_time = current_time
                        state.coarse_time_ms = int((current_time - state.start_time).total_seconds() * 1000)
                        state.is_monitoring = False
                        
                        if self.on_target_reached:
                            try:
                                self.on_target_reached(bucket_id, state.coarse_time_ms)
                            except Exception as e:
                                pass
                    
                    if (state.monitoring_type == "adaptive_learning" and 
                        coarse_states is not None and i < len(coarse_states)):
                        
                        current_coarse_active = coarse_states[i]
                        
                        if not state.coarse_active_initialized:
                            state.last_coarse_active = current_coarse_active
                            state.coarse_active_initialized = True
                        else:
                            if state.last_coarse_active != current_coarse_active:
                                if current_coarse_active:
                                    pass
                                else:
                                    pass
                                    
                                    if self.on_coarse_status_changed:
                                        try:
                                            self.on_coarse_status_changed(bucket_id, current_coarse_active)
                                        except Exception as e:
                                            pass
                                
                                state.last_coarse_active = current_coarse_active
                    
                    state.last_target_reached = current_target_reached
                    
        except Exception as e:
            pass
    
    def _check_material_shortage(self, bucket_id: int, state: BucketMonitoringState, 
                               start_active: bool, target_reached: bool, current_weight: float):
        try:
            state.add_weight_record(current_weight)
            
            if not state.start_active_initialized:
                state.last_start_active = start_active
                state.start_active_initialized = True
                return
            
            if state.start_time:
                monitoring_duration = (datetime.now() - state.start_time).total_seconds()
                if monitoring_duration < 15.0:
                    return
                
            if len(state.weight_history) < 150:
                return
            
            if start_active and not target_reached:
                weight_15s_ago = state.get_weight_15s_ago()
                
                if weight_15s_ago is not None:
                    oldest_time = state.weight_history[0][0] if state.weight_history else time.time()
                    if time.time() - oldest_time < 15.0:
                        return
                
                    weight_change = current_weight - weight_15s_ago
                    
                    if weight_change < self.weight_threshold and not state.material_shortage_detected:
                        state.material_shortage_detected = True
                        state.material_shortage_time = datetime.now()
                        
                        is_production = (state.monitoring_type == "production")
                        
                        self._handle_material_shortage_stop(bucket_id, is_production)
                        
                        def trigger_shortage_event():
                            if self.on_material_shortage_detected:
                                try:
                                    self.on_material_shortage_detected(bucket_id, state.monitoring_type, is_production)
                                except Exception as e:
                                    pass
                        
                        import threading
                        threading.Timer(0.2 * bucket_id, trigger_shortage_event).start()
            
            state.last_start_active = start_active
            
        except Exception as e:
            pass
    
    def _handle_material_shortage_stop(self, bucket_id: int, is_production: bool):
        try:
            if is_production:
                success1 = self.modbus_client.write_coil(
                    GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                
                success2 = self.modbus_client.write_coil(
                    GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True)
                
            else:
                success1 = self.modbus_client.write_coil(
                    BUCKET_CONTROL_ADDRESSES[bucket_id]['StartAddress'], False)
                
                success2 = self.modbus_client.write_coil(
                    BUCKET_CONTROL_ADDRESSES[bucket_id]['StopAddress'], True)
                    
        except Exception as e:
            pass
            
    def handle_material_shortage_continue(self, bucket_id: int, is_production: bool):
        try:
            with self.lock:
                state = self.monitoring_states.get(bucket_id)
                if state:
                    state.material_shortage_detected = False
                    state.material_shortage_time = None
            
            if is_production:
                success1 = self.modbus_client.write_coil(
                    GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False)
                
                success2 = self.modbus_client.write_coil(
                    GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True)
                
            else:
                success1 = self.modbus_client.write_coil(
                    BUCKET_CONTROL_ADDRESSES[bucket_id]['StopAddress'], False)
                
                success2 = self.modbus_client.write_coil(
                    BUCKET_CONTROL_ADDRESSES[bucket_id]['StartAddress'], True)
                    
        except Exception as e:
            pass
            
    def handle_material_shortage_cancel(self):
        try:
            self.stop_all_monitoring()
            return True
            
        except Exception as e:
            return False
        
    def get_bucket_material_shortage_status(self, bucket_id: int) -> dict:
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
        with self.lock:
            return self.monitoring_states.get(bucket_id)
    
    def get_all_monitoring_states(self) -> Dict[int, BucketMonitoringState]:
        with self.lock:
            return self.monitoring_states.copy()
    
    def is_any_bucket_monitoring(self) -> bool:
        with self.lock:
            return any(state.is_monitoring for state in self.monitoring_states.values())
        
    def start_production_monitoring(self, production_id: str, target_weight: float):
        try:
            with self.lock:
                self.production_id = production_id
                self.target_weight = target_weight
                self.is_production_monitoring = True
                
                for state in self.production_states.values():
                    state.reset()
                    state.is_monitoring_target = True
                
                if not self.monitoring_thread or not self.monitoring_thread.is_alive():
                    self.stop_monitoring_flag.clear()
                    self.monitoring_thread = threading.Thread(
                        target=self._monitoring_thread_func,
                        daemon=True,
                        name="BucketMonitoring"
                    )
                    self.monitoring_thread.start()
                
        except Exception as e:
            pass
            
    def stop_production_monitoring(self):
        try:
            with self.lock:
                self.is_production_monitoring = False
                
                for state in self.production_states.values():
                    state.reset()
                
        except Exception as e:
            pass
            
    def _check_production_states(self):
        try:
            if not self.is_production_monitoring:
                return
            
            target_reached_addresses = get_all_bucket_target_reached_addresses()
            target_states = self.modbus_client.read_coils(
                target_reached_addresses[0], len(target_reached_addresses))
            
            if target_states is None:
                return
            
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
                    
                    if state.waiting_for_restart:
                        if state.restart_time and current_time >= state.restart_time:
                            state.waiting_for_restart = False
                            state.is_monitoring_target = True
                            state.is_monitoring_discharge = False
                            state.target_reached_time = None
                            state.discharge_time = None
                            state.temp_real_weight = 0.0
                            state.temp_error_value = 0.0
                            state.temp_is_qualified = False
                        continue
                    
                    if state.is_monitoring_target:
                        if current_target and not state.last_target_reached:
                            state.target_reached_time = current_time
                            state.is_monitoring_target = False
                            state.is_monitoring_discharge = True
                            
                            threading.Timer(0.6, self._handle_weight_check_on_target_reached, 
                                        args=(bucket_id,)).start()
                    
                    if state.is_monitoring_discharge:
                        if current_discharge and not state.last_discharge_state:
                            state.discharge_time = current_time
                            state.is_monitoring_discharge = False
                            
                            self._handle_data_record_on_discharge(bucket_id)
                            
                            state.waiting_for_restart = True
                            state.restart_time = current_time + 2.0
                    
                    state.last_target_reached = current_target
                    state.last_discharge_state = current_discharge
            
        except Exception as e:
            pass
            
    def _handle_weight_check_on_target_reached(self, bucket_id: int):
        try:
            weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
            raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)

            if raw_weight_data is None or len(raw_weight_data) == 0:
                return
            
            raw_value = raw_weight_data[0]
            if raw_value > 32767:
                signed_value = raw_value - 65536
            else:
                signed_value = raw_value

            real_weight = signed_value / 10.0
            error_value = real_weight - self.target_weight
            
            error_value = round(error_value, 1)
            
            lower_error, upper_error = self._get_error_thresholds()
            
            is_qualified = lower_error <= error_value <= upper_error
            
            with self.lock:
                state = self.production_states[bucket_id]
                state.temp_real_weight = real_weight
                state.temp_error_value = error_value
                state.temp_is_qualified = is_qualified

        except Exception as e:
            pass
            
    def _handle_data_record_on_discharge(self, bucket_id: int):
        try:
            max_wait_time = 1.0
            wait_interval = 0.1
            waited_time = 0.0
            
            with self.lock:
                state = self.production_states[bucket_id]
                
            while state.temp_real_weight == 0.0 and waited_time < max_wait_time:
                time.sleep(wait_interval)
                waited_time += wait_interval
                with self.lock:
                    state = self.production_states[bucket_id]
            
            with self.lock:
                state = self.production_states[bucket_id]
                real_weight = state.temp_real_weight
                error_value = state.temp_error_value
                is_qualified = state.temp_is_qualified
                
            if is_qualified:
                self._record_production_detail(bucket_id, real_weight, error_value, True, True)
                with self.lock:
                    self.production_states[bucket_id].consecutive_unqualified = 0

            else:
                self._record_production_detail(bucket_id, real_weight, error_value, False, True)

                with self.lock:
                    state = self.production_states[bucket_id]
                    state.consecutive_unqualified += 1
                    
                    self._send_production_stop_commands()
                    
                    if state.consecutive_unqualified >= 3:
                        if self.on_production_stop_triggered:
                            try:
                                self.on_production_stop_triggered(bucket_id, f"连续{state.consecutive_unqualified}次不合格")
                            except Exception as e:
                                pass
                    else:
                        if self.on_single_unqualified_triggered:
                            try:
                                self.on_single_unqualified_triggered(bucket_id, real_weight, error_value)
                            except Exception as e:
                                pass

        except Exception as e:
            pass
            
    def _get_error_thresholds(self) -> tuple:
        try:
            try:
                from factory_settings_interface import error_config
                lower_error, upper_error = error_config.get_thresholds()
                return lower_error, upper_error
            except ImportError:
                return -0.2, 0.6
        except Exception as e:
            return -0.2, 0.6
            
    def _record_production_detail(self, bucket_id: int, real_weight: float, 
                                 error_value: float, is_qualified: bool, is_valid: bool):
        try:
            if not PRODUCTION_DETAIL_DAO_AVAILABLE:
                return
            
            detail = ProductionDetail(
                production_id=self.production_id,
                bucket_id=bucket_id,
                real_weight=real_weight,
                error_value=error_value,
                is_qualified=is_qualified,
                is_valid=is_valid
            )
            
            success, message, record_id = ProductionDetailDAO.insert_detail(detail)
            
            if success:
                if self.on_production_detail_recorded:
                    try:
                        self.on_production_detail_recorded(bucket_id, detail)
                    except Exception as e:
                        pass
        
        except Exception as e:
            pass
    
    def _send_production_stop_commands(self):
        """发送生产停止命令"""
        try:
            def stop_commands_thread():
                try:
                    success3 = self.modbus_client.write_coil(
                        GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], True)
                
                except Exception as e:
                    pass
            
            threading.Thread(target=stop_commands_thread, daemon=True).start()
            
        except Exception as e:
            pass
    
    def get_production_statistics(self) -> Dict:
        try:
            if not PRODUCTION_DETAIL_DAO_AVAILABLE or not self.production_id:
                return {}
            
            return ProductionDetailDAO.get_production_statistics(self.production_id)
            
        except Exception as e:
            return {}
    
    def dispose(self):
        try:
            self.stop_all_monitoring()
        except Exception as e:
            pass

def create_bucket_monitoring_service(modbus_client: ModbusClient) -> BucketMonitoringService:
    return BucketMonitoringService(modbus_client)