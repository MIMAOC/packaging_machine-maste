"""
扩展的料斗控制模块

作者：C
创建日期：2025-07-23
"""

import time
from typing import List, Tuple
from modbus_client import ModbusClient
from plc_addresses import (
    BUCKET_CONTROL_ADDRESSES,
    COARSE_TIME_MONITORING_ADDRESSES,
    get_bucket_control_address,
    get_coarse_time_monitoring_address
)

class BucketControlExtended:
    def __init__(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client
    
    def start_all_buckets_with_mutex_protection(self) -> Tuple[bool, str]:
        try:
            stop_coil_start_address = get_coarse_time_monitoring_address('STOP_COIL_START_ADDRESS')
            stop_commands = [False] * 6
            
            success = self.modbus_client.write_multiple_coils(stop_coil_start_address, stop_commands)
            if not success:
                error_msg = "发送停止=0命令（互斥保护）失败"
                return False, error_msg
            
            time.sleep(0.05)
            
            start_coil_start_address = get_coarse_time_monitoring_address('START_COIL_START_ADDRESS')
            start_commands = [True] * 6
            
            success = self.modbus_client.write_multiple_coils(start_coil_start_address, start_commands)
            if not success:
                error_msg = "发送启动=1命令失败"
                return False, error_msg
            
            success_msg = "✅ 6个料斗批量启动成功（带互斥保护）"
            return True, success_msg
            
        except Exception as e:
            error_msg = f"6个料斗批量启动异常: {str(e)}"
            return False, error_msg
    
    def stop_single_bucket_with_mutex_protection(self, bucket_id: int) -> Tuple[bool, str]:
        try:
            if bucket_id < 1 or bucket_id > 6:
                return False, f"无效的料斗ID: {bucket_id}，有效范围: 1-6"
            
            start_address = get_bucket_control_address(bucket_id, 'StartAddress')
            stop_address = get_bucket_control_address(bucket_id, 'StopAddress')
            
            success = self.modbus_client.write_coil(start_address, False)
            if not success:
                error_msg = f"料斗{bucket_id}发送启动=0命令（互斥保护）失败"
                return False, error_msg
            
            time.sleep(0.05)
            
            success = self.modbus_client.write_coil(stop_address, True)
            if not success:
                error_msg = f"料斗{bucket_id}发送停止=1命令失败"
                return False, error_msg
            
            success_msg = f"✅ 料斗{bucket_id}停止成功（带互斥保护）"
            return True, success_msg
            
        except Exception as e:
            error_msg = f"停止料斗{bucket_id}异常: {str(e)}"
            return False, error_msg
    
    def discharge_single_bucket(self, bucket_id: int) -> Tuple[bool, str]:
        try:
            if bucket_id < 1 or bucket_id > 6:
                return False, f"无效的料斗ID: {bucket_id}，有效范围: 1-6"
            
            discharge_address = get_bucket_control_address(bucket_id, 'DischargeAddress')
            
            success = self.modbus_client.write_coil(discharge_address, True)
            if not success:
                error_msg = f"料斗{bucket_id}发送放料=1命令失败"
                return False, error_msg
            
            time.sleep(1.5)
            
            success = self.modbus_client.write_coil(discharge_address, False)
            if not success:
                error_msg = f"料斗{bucket_id}发送放料=0命令失败"
                return False, error_msg
            
            success_msg = f"✅ 料斗{bucket_id}放料操作完成"
            return True, success_msg
            
        except Exception as e:
            error_msg = f"料斗{bucket_id}放料操作异常: {str(e)}"
            return False, error_msg
    
    def restart_single_bucket(self, bucket_id: int) -> Tuple[bool, str]:
        try:
            if bucket_id < 1 or bucket_id > 6:
                return False, f"无效的料斗ID: {bucket_id}，有效范围: 1-6"
            
            start_address = get_bucket_control_address(bucket_id, 'StartAddress')
            stop_address = get_bucket_control_address(bucket_id, 'StopAddress')
            
            success = self.modbus_client.write_coil(stop_address, False)
            if not success:
                error_msg = f"料斗{bucket_id}设置停止=0失败"
                return False, error_msg
            
            time.sleep(0.05)
            
            success = self.modbus_client.write_coil(start_address, True)
            if not success:
                error_msg = f"料斗{bucket_id}发送启动=1命令失败"
                return False, error_msg
            
            success_msg = f"✅ 料斗{bucket_id}重新启动成功"
            return True, success_msg
            
        except Exception as e:
            error_msg = f"重新启动料斗{bucket_id}异常: {str(e)}"
            return False, error_msg
    
    def stop_all_buckets(self) -> Tuple[bool, str]:
        try:
            start_coil_start_address = get_coarse_time_monitoring_address('START_COIL_START_ADDRESS')
            start_commands = [False] * 6
            
            success = self.modbus_client.write_multiple_coils(start_coil_start_address, start_commands)
            if not success:
                error_msg = "发送启动=0命令（互斥保护）失败"
                return False, error_msg
            
            time.sleep(0.05)
            
            stop_coil_start_address = get_coarse_time_monitoring_address('STOP_COIL_START_ADDRESS')
            stop_commands = [True] * 6
            
            success = self.modbus_client.write_multiple_coils(stop_coil_start_address, stop_commands)
            if not success:
                error_msg = "发送停止=1命令失败"
                return False, error_msg
            
            success_msg = "✅ 所有料斗停止操作完成"
            return True, success_msg
            
        except Exception as e:
            error_msg = f"停止所有料斗异常: {str(e)}"
            return False, error_msg
    
    def execute_bucket_stop_and_discharge_sequence(self, bucket_id: int) -> Tuple[bool, str]:
        try:
            stop_success, stop_msg = self.stop_single_bucket_with_mutex_protection(bucket_id)
            if not stop_success:
                return False, f"停止料斗失败: {stop_msg}"
            
            time.sleep(0.5)
            
            discharge_success, discharge_msg = self.discharge_single_bucket(bucket_id)
            if not discharge_success:
                return False, f"放料操作失败: {discharge_msg}"
            
            success_msg = f"✅ 料斗{bucket_id}停止和放料序列操作完成"
            return True, success_msg
            
        except Exception as e:
            error_msg = f"料斗{bucket_id}停止和放料序列异常: {str(e)}"
            return False, error_msg

def create_bucket_control_extended(modbus_client: ModbusClient) -> BucketControlExtended:
    return BucketControlExtended(modbus_client)