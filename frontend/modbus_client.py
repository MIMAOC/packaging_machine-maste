"""
Modbus TCP客户端模块

作者：C
创建日期：2025-07-22
更新日期：2025-08-19
"""

from pymodbus.client.tcp import ModbusTcpClient
from pymodbus.exceptions import ModbusException, ConnectionException
import time
import threading
import socket
from typing import Tuple, Optional, Union, List

class ModbusClient:
    def __init__(self, host: str = "192.168.6.6", port: int = 502, timeout: int = 3, slave_id: int = 1):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.slave_id = slave_id
        self.client = None
        self.is_connected = False
        
        self._rw_lock = threading.RLock()
    
    def test_tcp_connection(self) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception as e:
            return False
    
    def connect(self) -> Tuple[bool, str]:
        try:
            if not self.test_tcp_connection():
                error_msg = f"TCP连接失败！\n" \
                           f"PLC地址: {self.host}:{self.port}\n" \
                           f"可能原因：\n" \
                           f"1. IP地址不存在或不可达\n" \
                           f"2. 端口号错误或被占用\n" \
                           f"3. 网络故障或防火墙阻止\n" \
                           f"4. PLC设备未启动"
                return False, error_msg
            
            self.client = ModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout
            )
            
            connection_result = self.client.connect()
            
            if connection_result:
                try:
                    result = self.client.read_holding_registers(
                        address=0, count=1, slave=self.slave_id
                    )
                    
                    if not result.isError():
                        communication_verified = True
                        verification_info = f"成功读取地址0数据: {result.registers}"
                    else:
                        communication_verified = False
                        test_addresses = [20, 22, 24, 26, 28]
                        
                        for addr in test_addresses:
                            try:
                                result = self.client.read_holding_registers(
                                    address=addr, count=1, slave=self.slave_id
                                )
                                
                                if not result.isError():
                                    communication_verified = True
                                    verification_info = f"成功读取地址{addr}数据: {result.registers}"
                                    break
                                    
                            except Exception as e:
                                continue
                        
                        if not communication_verified:
                            verification_info = "所有测试地址都无法读取"
                
                except Exception as e:
                    communication_verified = False
                    verification_info = f"通信测试异常: {str(e)}"
                
                if communication_verified:
                    self.is_connected = True
                    success_msg = f"Modbus TCP连接成功！\n" \
                                f"PLC地址: {self.host}:{self.port}\n" \
                                f"从站ID: {self.slave_id}\n" \
                                f"连接时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n" \
                                f"通信验证: {verification_info}"
                    return True, success_msg
                else:
                    self.is_connected = False
                    self.client.close()
                    error_msg = f"Modbus通信验证失败！\n" \
                               f"PLC地址: {self.host}:{self.port}\n" \
                               f"从站ID: {self.slave_id}\n" \
                               f"TCP连接: 成功\n" \
                               f"Modbus连接: 成功\n" \
                               f"数据通信: 失败\n" \
                               f"可能原因：\n" \
                               f"1. 从站ID不正确（当前: {self.slave_id}）\n" \
                               f"2. PLC Modbus服务配置错误\n" \
                               f"3. 寄存器地址权限问题\n" \
                               f"4. PLC正忙或故障\n" \
                               f"详细信息: {verification_info}"
                    return False, error_msg
            else:
                self.is_connected = False
                error_msg = f"Modbus连接失败！\n" \
                           f"PLC地址: {self.host}:{self.port}\n" \
                           f"TCP连接: 成功\n" \
                           f"Modbus连接: 失败\n" \
                           f"可能原因：\n" \
                           f"1. 端口502被其他服务占用\n" \
                           f"2. PLC不支持Modbus TCP协议\n" \
                           f"3. PLC Modbus服务未启用"
                return False, error_msg
                
        except ConnectionException as e:
            self.is_connected = False
            error_msg = f"连接异常！\n" \
                       f"PLC地址: {self.host}:{self.port}\n" \
                       f"错误类型: 连接异常\n" \
                       f"错误详情: {str(e)}\n" \
                       f"建议检查：网络连接和目标设备状态"
            return False, error_msg
            
        except Exception as e:
            self.is_connected = False
            error_msg = f"未知错误！\n" \
                       f"PLC地址: {self.host}:{self.port}\n" \
                       f"错误类型: {type(e).__name__}\n" \
                       f"错误详情: {str(e)}"
            return False, error_msg
    
    def disconnect(self) -> None:
        try:
            if self.client and self.is_connected:
                self.client.close()
                self.is_connected = False
        except Exception as e:
            pass
    
    def test_connection(self) -> Tuple[bool, str]:
        if not self.is_connected or not self.client:
            return False, "未建立连接"
        
        try:
            result = self.client.read_holding_registers(address=0, count=1, slave=self.slave_id)
            
            if not result.isError():
                return True, f"连接测试成功，读取数据: {result.registers}"
            else:
                return False, f"连接测试失败: {result}"
                
        except Exception as e:
            return False, f"连接测试异常: {str(e)}"
    
    def read_holding_registers(self, address: int, count: int = 1) -> Optional[list]:
        with self._rw_lock:
            if not self.is_connected:
                return None
            
            try:
                result = self.client.read_holding_registers(
                    address=address, count=count, slave=self.slave_id
                )
                if not result.isError():
                    return result.registers
                else:
                    return None
            except Exception as e:
                return None
    
    def write_holding_register(self, address: int, value: int) -> bool:
        with self._rw_lock:
            if not self.is_connected:
                return False
            
            try:
                result = self.client.write_register(
                    address=address, value=value, slave=self.slave_id
                    )
                if not result.isError():
                    return True
                else:
                    return False
            except Exception as e:
                return False
    
    def write_multiple_registers(self, start_address: int, values: List[int]) -> bool:
        with self._rw_lock:
            if not self.is_connected:
                return False
            
            try:
                result = self.client.write_registers(
                    start_address=start_address, values=values, slave=self.slave_id
                    )
                if not result.isError():
                    return True
                else:
                    return False
            except Exception as e:
                return False
    
    def read_coils(self, address: int, count: int = 1) -> Optional[List[bool]]:
        with self._rw_lock:
            if not self.is_connected:
                return None
            
            try:
                result = self.client.read_coils(
                    address=address, count=count, slave=self.slave_id
                    )
                if not result.isError():
                    return result.bits
                else:
                    return None
            except Exception as e:
                return None
    
    def write_coil(self, address: int, value: bool) -> bool:
        with self._rw_lock:
            if not self.is_connected:
                return False
            
            try:
                result = self.client.write_coil(
                    address=address, value=value, slave=self.slave_id
                    )
                if not result.isError():
                    return True
                else:
                    return False
            except Exception as e:
                return False
    
    def write_multiple_coils(self, start_address: int, values: List[bool]) -> bool:
        with self._rw_lock:
            if not self.is_connected:
                return False
            
            try:
                result = self.client.write_coils(
                    start_address, values, slave=self.slave_id
                    )
                if not result.isError():
                    return True
                else:
                    return False
            except Exception as e:
                return False
    
    def get_connection_status(self) -> dict:
        return {
            'is_connected': self.is_connected,
            'host': self.host,
            'port': self.port,
            'timeout': self.timeout,
            'slave_id': self.slave_id,
            'client_info': str(self.client) if self.client else None
        }
    
    def read_multiple_coils_extended(self, start_address: int, count: int) -> Optional[List[bool]]:
        with self._rw_lock:
            if not self.is_connected:
                return None
            
            try:
                result = self.client.read_coils(address=start_address, count=count, slave=self.slave_id)
                if not result.isError():
                    return result.bits[:count]
                else:
                    return None
            except Exception as e:
                return None
    
    def write_multiple_coils_with_validation(self, start_address: int, values: List[bool]) -> Tuple[bool, str]:
        with self._rw_lock:
            if not self.is_connected:
                error_msg = "未连接到PLC，无法批量写入线圈"
                return False, error_msg
            
            if not values:
                error_msg = "写入值列表为空"
                return False, error_msg
            
            try:
                result = self.client.write_coils(
                    start_address, values, slave=self.slave_id
                    )
                if not result.isError():
                    success_msg = f"成功批量写入线圈，起始地址: {start_address}，数量: {len(values)}，值: {values}"
                    return True, success_msg
                else:
                    error_msg = f"批量写入线圈失败: {result}"
                    return False, error_msg
            except Exception as e:
                error_msg = f"批量写入线圈异常: {e}"
                return False, error_msg
    
    def read_bucket_target_reached_states(self, target_reached_addresses: List[int]) -> Optional[List[bool]]:
        with self._rw_lock:
            if not self.is_connected:
                return None
            
            try:
                if len(target_reached_addresses) > 1:
                    min_addr = min(target_reached_addresses)
                    max_addr = max(target_reached_addresses)
                    
                    if max_addr - min_addr + 1 == len(target_reached_addresses):
                        result = self.client.read_coils(min_addr, len(target_reached_addresses), slave=self.slave_id)
                        if not result.isError():
                            return result.bits[:len(target_reached_addresses)]
                
                states = []
                for addr in target_reached_addresses:
                    result = self.client.read_coils(addr, 1, slave=self.slave_id)
                    if not result.isError():
                        states.append(result.bits[0])
                    else:
                        return None
                
                return states
                
            except Exception as e:
                return None

def create_modbus_client(host: str = "192.168.6.6", port: int = 502, timeout: int = 3, slave_id: int = 1) -> ModbusClient:
    return ModbusClient(host, port, timeout, slave_id)