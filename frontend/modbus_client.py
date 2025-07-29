#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus TCP客户端模块
用于与PLC设备进行Modbus TCP通信

依赖库安装：
pip install pymodbus

作者：C
创建日期：2025-07-22
更新日期：2025-07-23（增加线程安全和批量操作功能，增加快加时间监测相关的读写操作）
更新日期：2025-07-25（修复信捷PLC连接问题，添加slave_id支持）
"""

from pymodbus.client.tcp import ModbusTcpClient
from pymodbus.exceptions import ModbusException, ConnectionException
import logging
import time
import threading
import socket
from typing import Tuple, Optional, Union, List

class ModbusClient:
    """
    Modbus TCP客户端类
    提供与PLC设备的连接、读写操作等功能
    """
    
    def __init__(self, host: str = "192.168.6.6", port: int = 502, timeout: int = 3, slave_id: int = 1):
        """
        初始化Modbus客户端
        
        Args:
            host (str): PLC的IP地址，默认192.168.6.6
            port (int): Modbus TCP端口，默认502
            timeout (int): 连接超时时间（秒），默认3秒
            slave_id (int): PLC从站ID，默认1（信捷PLC默认站号）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.slave_id = slave_id  # 添加从站ID支持
        self.client = None
        self.is_connected = False
        
        # 添加读写锁，确保PLC操作的线程安全
        self._rw_lock = threading.RLock()
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def test_tcp_connection(self) -> bool:
        """
        测试基础TCP连接
        
        Returns:
            bool: TCP连接是否成功
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception as e:
            self.logger.error(f"TCP连接测试失败: {e}")
            return False
    
    def connect(self) -> Tuple[bool, str]:
        """
        连接到PLC设备并验证真实连接
        
        Returns:
            Tuple[bool, str]: (连接状态, 状态消息)
                - True: 连接成功且PLC响应正常
                - False: 连接失败或PLC无响应
        """
        try:
            self.logger.info(f"正在尝试连接到PLC: {self.host}:{self.port}，从站ID: {self.slave_id}")
            
            # 首先测试TCP连接
            if not self.test_tcp_connection():
                error_msg = f"❌ TCP连接失败！\n" \
                           f"PLC地址: {self.host}:{self.port}\n" \
                           f"可能原因：\n" \
                           f"1. IP地址不存在或不可达\n" \
                           f"2. 端口号错误或被占用\n" \
                           f"3. 网络故障或防火墙阻止\n" \
                           f"4. PLC设备未启动"
                self.logger.error("TCP连接失败")
                return False, error_msg
            
            self.logger.info("TCP连接测试成功，正在建立Modbus连接...")
            
            # 创建Modbus TCP客户端
            self.client = ModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout
            )
            
            # 尝试建立Modbus连接
            connection_result = self.client.connect()
            
            if connection_result:
                self.logger.info("Modbus TCP连接建立成功，正在验证通信...")
                
                # 验证真实的Modbus通信
                # 先测试地址0（通常PLC都支持）
                try:
                    result = self.client.read_holding_registers(
                        address=0, count=1, slave=self.slave_id
                    )
                    
                    if not result.isError():
                        self.logger.info(f"地址0读取成功: {result.registers}")
                        communication_verified = True
                        verification_info = f"成功读取地址0数据: {result.registers}"
                    else:
                        # 如果地址0失败，尝试其他常用地址
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
                                    self.logger.info(f"地址 {addr} 读取成功: {result.registers}")
                                    break
                                else:
                                    self.logger.debug(f"地址 {addr} 读取失败: {result}")
                                    
                            except Exception as e:
                                self.logger.debug(f"地址 {addr} 读取异常: {e}")
                                continue
                        
                        if not communication_verified:
                            verification_info = "所有测试地址都无法读取"
                
                except Exception as e:
                    communication_verified = False
                    verification_info = f"通信测试异常: {str(e)}"
                
                if communication_verified:
                    self.is_connected = True
                    success_msg = f"✅ Modbus TCP连接成功！\n" \
                                f"PLC地址: {self.host}:{self.port}\n" \
                                f"从站ID: {self.slave_id}\n" \
                                f"连接时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n" \
                                f"通信验证: {verification_info}"
                    self.logger.info("Modbus TCP连接和通信验证成功")
                    return True, success_msg
                else:
                    # Modbus连接成功但通信失败
                    self.is_connected = False
                    self.client.close()
                    error_msg = f"❌ Modbus通信验证失败！\n" \
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
                    self.logger.error("Modbus通信验证失败")
                    return False, error_msg
            else:
                self.is_connected = False
                error_msg = f"❌ Modbus连接失败！\n" \
                           f"PLC地址: {self.host}:{self.port}\n" \
                           f"TCP连接: 成功\n" \
                           f"Modbus连接: 失败\n" \
                           f"可能原因：\n" \
                           f"1. 端口502被其他服务占用\n" \
                           f"2. PLC不支持Modbus TCP协议\n" \
                           f"3. PLC Modbus服务未启用"
                self.logger.error("Modbus连接失败")
                return False, error_msg
                
        except ConnectionException as e:
            self.is_connected = False
            error_msg = f"❌ 连接异常！\n" \
                       f"PLC地址: {self.host}:{self.port}\n" \
                       f"错误类型: 连接异常\n" \
                       f"错误详情: {str(e)}\n" \
                       f"建议检查：网络连接和目标设备状态"
            self.logger.error(f"连接异常: {e}")
            return False, error_msg
            
        except Exception as e:
            self.is_connected = False
            error_msg = f"❌ 未知错误！\n" \
                       f"PLC地址: {self.host}:{self.port}\n" \
                       f"错误类型: {type(e).__name__}\n" \
                       f"错误详情: {str(e)}"
            self.logger.error(f"未知错误: {e}")
            return False, error_msg
    
    def disconnect(self) -> None:
        """
        断开与PLC的连接
        """
        try:
            if self.client and self.is_connected:
                self.client.close()
                self.is_connected = False
                self.logger.info("Modbus TCP连接已断开")
        except Exception as e:
            self.logger.error(f"断开连接时发生错误: {e}")
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        测试连接状态
        通过读取一个寄存器来验证连接是否正常
        
        Returns:
            Tuple[bool, str]: (测试结果, 状态消息)
        """
        if not self.is_connected or not self.client:
            return False, "未建立连接"
        
        try:
            # 尝试读取保持寄存器地址0（使用slave参数）
            result = self.client.read_holding_registers(address=0, count=1, slave=self.slave_id)
            
            if not result.isError():
                return True, f"连接测试成功，读取数据: {result.registers}"
            else:
                return False, f"连接测试失败: {result}"
                
        except Exception as e:
            return False, f"连接测试异常: {str(e)}"
    
    def read_holding_registers(self, address: int, count: int = 1) -> Optional[list]:
        """
        读取保持寄存器（线程安全）
        
        Args:
            address (int): 寄存器起始地址
            count (int): 读取寄存器数量，默认1个
            
        Returns:
            Optional[list]: 读取的数据列表，失败返回None
        """
        with self._rw_lock:
            if not self.is_connected:
                self.logger.error("未连接到PLC，无法读取数据")
                return None
            
            try:
                # 使用slave参数
                result = self.client.read_holding_registers(
                    address=address, count=count, slave=self.slave_id
                )
                if not result.isError():
                    self.logger.debug(f"成功读取寄存器 {address}，数量: {count}，数据: {result.registers}")
                    return result.registers
                else:
                    self.logger.error(f"读取寄存器失败: {result}")
                    return None
            except Exception as e:
                self.logger.error(f"读取寄存器异常: {e}")
                return None
    
    def write_holding_register(self, address: int, value: int) -> bool:
        """
        写入单个保持寄存器（线程安全）
        
        Args:
            address (int): 寄存器地址
            value (int): 写入的值
            
        Returns:
            bool: 写入是否成功
        """
        with self._rw_lock:
            if not self.is_connected:
                self.logger.error("未连接到PLC，无法写入数据")
                return False
            
            try:
                # 使用slave参数
                result = self.client.write_register(
                    address=address, value=value, slave=self.slave_id
                    )
                if not result.isError():
                    self.logger.info(f"成功写入寄存器 {address}: {value}")
                    return True
                else:
                    self.logger.error(f"写入寄存器失败: {result}")
                    return False
            except Exception as e:
                self.logger.error(f"写入寄存器异常: {e}")
                return False
    
    def write_multiple_registers(self, start_address: int, values: List[int]) -> bool:
        """
        批量写入多个保持寄存器（线程安全）
        
        Args:
            start_address (int): 起始寄存器地址
            values (List[int]): 要写入的值列表
            
        Returns:
            bool: 写入是否成功
        """
        with self._rw_lock:
            if not self.is_connected:
                self.logger.error("未连接到PLC，无法写入数据")
                return False
            
            try:
                # 使用slave参数
                result = self.client.write_registers(
                    start_address=start_address, values=values, slave=self.slave_id
                    )
                if not result.isError():
                    self.logger.info(f"成功批量写入寄存器，起始地址: {start_address}，数量: {len(values)}")
                    return True
                else:
                    self.logger.error(f"批量写入寄存器失败: {result}")
                    return False
            except Exception as e:
                self.logger.error(f"批量写入寄存器异常: {e}")
                return False
    
    def read_coils(self, address: int, count: int = 1) -> Optional[List[bool]]:
        """
        读取线圈状态（线程安全）
        
        Args:
            address (int): 线圈起始地址
            count (int): 读取线圈数量，默认1个
            
        Returns:
            Optional[List[bool]]: 读取的线圈状态列表，失败返回None
        """
        with self._rw_lock:
            if not self.is_connected:
                self.logger.error("未连接到PLC，无法读取线圈")
                return None
            
            try:
                # 使用关键字参数方式调用
                result = self.client.read_coils(
                    address=address, count=count, slave=self.slave_id
                    )
                if not result.isError():
                    self.logger.debug(f"成功读取线圈 {address}，数量: {count}，状态: {result.bits}")
                    return result.bits
                else:
                    self.logger.error(f"读取线圈失败: {result}")
                    return None
            except Exception as e:
                self.logger.error(f"读取线圈异常: {e}")
                return None
    
    def write_coil(self, address: int, value: bool) -> bool:
        """
        写入单个线圈（线程安全）
        
        Args:
            address (int): 线圈地址
            value (bool): 写入的值（True/False）
            
        Returns:
            bool: 写入是否成功
        """
        with self._rw_lock:
            if not self.is_connected:
                self.logger.error("未连接到PLC，无法写入线圈")
                return False
            
            try:
                # 使用关键字参数方式调用
                result = self.client.write_coil(
                    address=address, value=value, slave=self.slave_id
                    )
                if not result.isError():
                    self.logger.info(f"成功写入线圈 {address}: {value}")
                    return True
                else:
                    self.logger.error(f"写入线圈失败: {result}")
                    return False
            except Exception as e:
                self.logger.error(f"写入线圈异常: {e}")
                return False
    
    def write_multiple_coils(self, start_address: int, values: List[bool]) -> bool:
        """
        批量写入多个线圈（线程安全）
        
        Args:
            start_address (int): 起始线圈地址
            values (List[bool]): 要写入的值列表
            
        Returns:
            bool: 写入是否成功
        """
        with self._rw_lock:
            if not self.is_connected:
                self.logger.error("未连接到PLC，无法写入线圈")
                return False
            
            try:
                # 使用关键字参数方式调用
                result = self.client.write_coils(
                    start_address, values, slave=self.slave_id
                    )
                if not result.isError():
                    self.logger.info(f"成功批量写入线圈，起始地址: {start_address}，数量: {len(values)}")
                    return True
                else:
                    self.logger.error(f"批量写入线圈失败: {result}")
                    return False
            except Exception as e:
                self.logger.error(f"批量写入线圈异常: {e}")
                return False
    
    def get_connection_status(self) -> dict:
        """
        获取连接状态信息
        
        Returns:
            dict: 包含连接状态的字典
        """
        return {
            'is_connected': self.is_connected,
            'host': self.host,
            'port': self.port,
            'timeout': self.timeout,
            'slave_id': self.slave_id,  # 添加从站ID信息
            'client_info': str(self.client) if self.client else None
        }
    
    # ==================== 新增快加时间监测相关的读写操作 ====================
    
    def read_multiple_coils_extended(self, start_address: int, count: int) -> Optional[List[bool]]:
        """
        批量读取多个线圈状态（扩展方法，专用于快加时间监测）
        
        Args:
            start_address (int): 起始线圈地址
            count (int): 读取线圈数量
            
        Returns:
            Optional[List[bool]]: 读取的线圈状态列表，失败返回None
        """
        with self._rw_lock:
            if not self.is_connected:
                self.logger.error("未连接到PLC，无法批量读取线圈")
                return None
            
            try:
                # 使用关键字参数方式调用
                result = self.client.read_coils(address=start_address, count=count, slave=self.slave_id)
                if not result.isError():
                    self.logger.debug(f"成功批量读取线圈，起始地址: {start_address}，数量: {count}")
                    return result.bits[:count]  # 确保只返回请求的数量
                else:
                    self.logger.error(f"批量读取线圈失败: {result}")
                    return None
            except Exception as e:
                self.logger.error(f"批量读取线圈异常: {e}")
                return None
    
    def write_multiple_coils_with_validation(self, start_address: int, values: List[bool]) -> Tuple[bool, str]:
        """
        批量写入多个线圈并验证结果（扩展方法，专用于快加时间监测）
        
        Args:
            start_address (int): 起始线圈地址
            values (List[bool]): 要写入的值列表
            
        Returns:
            Tuple[bool, str]: (写入是否成功, 详细消息)
        """
        with self._rw_lock:
            if not self.is_connected:
                error_msg = "未连接到PLC，无法批量写入线圈"
                self.logger.error(error_msg)
                return False, error_msg
            
            if not values:
                error_msg = "写入值列表为空"
                self.logger.error(error_msg)
                return False, error_msg
            
            try:
                # 使用关键字参数方式调用
                result = self.client.write_coils(
                    start_address, values, slave=self.slave_id
                    )
                if not result.isError():
                    success_msg = f"成功批量写入线圈，起始地址: {start_address}，数量: {len(values)}，值: {values}"
                    self.logger.info(success_msg)
                    return True, success_msg
                else:
                    error_msg = f"批量写入线圈失败: {result}"
                    self.logger.error(error_msg)
                    return False, error_msg
            except Exception as e:
                error_msg = f"批量写入线圈异常: {e}"
                self.logger.error(error_msg)
                return False, error_msg
    
    def read_bucket_target_reached_states(self, target_reached_addresses: List[int]) -> Optional[List[bool]]:
        """
        读取料斗到量状态（专用于快加时间监测）
        
        Args:
            target_reached_addresses (List[int]): 到量线圈地址列表
            
        Returns:
            Optional[List[bool]]: 到量状态列表，失败返回None
        """
        with self._rw_lock:
            if not self.is_connected:
                self.logger.error("未连接到PLC，无法读取料斗到量状态")
                return None
            
            try:
                # 如果地址是连续的，可以使用批量读取
                if len(target_reached_addresses) > 1:
                    min_addr = min(target_reached_addresses)
                    max_addr = max(target_reached_addresses)
                    
                    # 检查地址是否连续
                    if max_addr - min_addr + 1 == len(target_reached_addresses):
                        # 地址连续，使用批量读取，添加slave参数
                        result = self.client.read_coils(min_addr, len(target_reached_addresses), slave=self.slave_id)
                        if not result.isError():
                            return result.bits[:len(target_reached_addresses)]
                
                # 地址不连续或只有一个地址，逐个读取
                states = []
                for addr in target_reached_addresses:
                    # 使用slave参数
                    result = self.client.read_coils(addr, 1, slave=self.slave_id)
                    if not result.isError():
                        states.append(result.bits[0])
                    else:
                        self.logger.error(f"读取线圈地址 {addr} 失败: {result}")
                        return None
                
                self.logger.debug(f"成功读取料斗到量状态: {states}")
                return states
                
            except Exception as e:
                self.logger.error(f"读取料斗到量状态异常: {e}")
                return None

def scan_modbus_devices(ip_range: str = "192.168.6", start_ip: int = 1, end_ip: int = 254, 
                       port: int = 502, timeout: int = 1, slave_id: int = 1) -> list:
    """
    扫描指定IP范围内的Modbus设备
    
    Args:
        ip_range (str): IP网段，如 "192.168.6"
        start_ip (int): 起始IP最后一位
        end_ip (int): 结束IP最后一位
        port (int): Modbus端口
        timeout (int): 连接超时时间（秒）
        slave_id (int): 从站ID
        
    Returns:
        list: 找到的Modbus设备列表 [{'ip': 'x.x.x.x', 'status': 'success/failed', 'info': '详细信息'}]
    """
    import threading
    import time
    
    found_devices = []
    scan_threads = []
    
    def test_single_device(ip):
        """测试单个IP地址的Modbus连接"""
        test_client = ModbusClient(ip, port, timeout, slave_id)
        success, message = test_client.connect()
        
        device_info = {
            'ip': ip,
            'port': port,
            'slave_id': slave_id,
            'status': 'success' if success else 'failed',
            'info': message.split('\n')[0] if success else '无响应'
        }
        found_devices.append(device_info)
        
        if success:
            test_client.disconnect()
    
    print(f"正在扫描 {ip_range}.{start_ip}-{end_ip}:{port} 范围内的Modbus设备（从站ID: {slave_id}）...")
    
    # 创建并启动扫描线程
    for i in range(start_ip, end_ip + 1):
        ip = f"{ip_range}.{i}"
        thread = threading.Thread(target=test_single_device, args=(ip,))
        scan_threads.append(thread)
        thread.start()
        
        # 限制并发线程数量
        if len(scan_threads) >= 20:
            for t in scan_threads:
                t.join()
            scan_threads = []
    
    # 等待所有线程完成
    for thread in scan_threads:
        thread.join()
    
    # 按IP排序并只返回成功的设备
    successful_devices = [dev for dev in found_devices if dev['status'] == 'success']
    successful_devices.sort(key=lambda x: int(x['ip'].split('.')[-1]))
    
    return successful_devices

def create_modbus_client(host: str = "192.168.6.6", port: int = 502, timeout: int = 3, slave_id: int = 1) -> ModbusClient:
    """
    创建Modbus客户端实例的工厂函数
    
    Args:
        host (str): PLC的IP地址
        port (int): Modbus TCP端口
        timeout (int): 连接超时时间
        slave_id (int): PLC从站ID
        
    Returns:
        ModbusClient: Modbus客户端实例
    """
    return ModbusClient(host, port, timeout, slave_id)

# 示例使用
if __name__ == "__main__":
    # 创建客户端实例（使用信捷PLC默认从站ID 1）
    modbus_client = create_modbus_client(slave_id=1)
    
    # 尝试连接
    success, message = modbus_client.connect()
    print(f"连接结果: {success}")
    print(f"消息: {message}")
    
    if success:
        # 测试连接
        test_result, test_msg = modbus_client.test_connection()
        print(f"连接测试: {test_result} - {test_msg}")
        
        # 读取数据示例
        data = modbus_client.read_holding_registers(0, 5)
        if data:
            print(f"读取的数据: {data}")
        
        # 测试特定地址读取
        for addr in [20, 22, 24, 26, 28]:
            data = modbus_client.read_holding_registers(addr, 1)
            if data:
                print(f"地址 {addr} 数据: {data}")
        
        # 测试新增的批量线圈读取功能
        coil_states = modbus_client.read_multiple_coils_extended(191, 6)
        if coil_states:
            print(f"读取的线圈状态: {coil_states}")
        
        # 断开连接
        modbus_client.disconnect()