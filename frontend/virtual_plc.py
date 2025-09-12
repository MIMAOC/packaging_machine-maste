#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟PLC模拟器
用于在没有真实PLC设备时进行开发和测试

功能特点：
1. 模拟Modbus TCP协议
2. 虚拟寄存器和线圈存储
3. 自动生成模拟数据
4. 支持读写操作
5. 模拟称重和包装过程
6. 可配置的延时和错误模拟
"""

import threading
import time
import random
import json
from typing import Dict, List, Any, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('VirtualPLC')


class VirtualPLCData:
    """虚拟PLC数据存储类"""
    
    def __init__(self):
        # 线圈状态 (0x区域 - 布尔值)
        self.coils: Dict[int, bool] = {}
        
        # 离散输入 (1x区域 - 布尔值)
        self.discrete_inputs: Dict[int, bool] = {}
        
        # 输入寄存器 (3x区域 - 16位整数)
        self.input_registers: Dict[int, int] = {}
        
        # 保持寄存器 (4x区域 - 16位整数)
        self.holding_registers: Dict[int, int] = {}
        
        # 初始化默认值
        self._initialize_default_values()
        
        # 启动数据模拟线程
        self.simulation_running = True
        self.simulation_thread = threading.Thread(target=self._simulate_data, daemon=True)
        self.simulation_thread.start()
    
    def _initialize_default_values(self):
        """初始化默认数据值"""
        # 系统状态线圈
        self.coils[0] = False    # 系统启动
        self.coils[1] = False    # 系统停止
        self.coils[2] = False    # 紧急停止
        self.coils[3] = False    # 自动模式
        self.coils[4] = False    # 手动模式
        self.coils[40] = False   # AI模式
        self.coils[30] = True    # 传统模式（默认）
        
        # 称重头状态线圈
        for i in range(6):  # 6个称重头
            self.coils[100 + i] = False  # 称重头启用状态
            self.coils[200 + i] = False  # 称重头故障状态
        
        # 输入状态
        self.discrete_inputs[0] = True   # 电源状态
        self.discrete_inputs[1] = True   # 压缩空气状态
        self.discrete_inputs[2] = False  # 门开关状态
        
        # 称重数据寄存器
        for i in range(6):  # 6个称重头
            self.holding_registers[1000 + i] = 0  # 当前重量
            self.holding_registers[2000 + i] = 100  # 目标重量
            self.holding_registers[3000 + i] = 5    # 重量误差范围
        
        # 系统参数
        self.holding_registers[5000] = 0    # 当前包装数量
        self.holding_registers[5001] = 1000 # 目标包装数量
        self.holding_registers[5002] = 50   # 包装速度(包/分钟)
        self.holding_registers[5003] = 0    # 错误代码
        
        # 温度传感器数据
        self.input_registers[6000] = 250    # 环境温度(°C * 10)
        self.input_registers[6001] = 600    # 设备温度(°C * 10)
        
        logger.info("虚拟PLC默认数据初始化完成")
    
    def _simulate_data(self):
        """模拟数据变化的后台线程"""
        logger.info("虚拟PLC数据模拟线程启动")
        
        while self.simulation_running:
            try:
                # 模拟称重数据变化
                self._simulate_weighing_data()
                
                # 模拟温度数据变化
                self._simulate_temperature_data()
                
                # 模拟系统运行状态
                self._simulate_system_status()
                
                # 模拟包装计数
                self._simulate_packaging_count()
                
                time.sleep(1)  # 每秒更新一次
                
            except Exception as e:
                logger.error(f"数据模拟线程异常: {e}")
                time.sleep(5)
    
    def _simulate_weighing_data(self):
        """模拟称重数据"""
        for i in range(6):  # 6个称重头
            if self.coils.get(100 + i, False):  # 如果称重头启用
                target_weight = self.holding_registers.get(2000 + i, 100)
                error_range = self.holding_registers.get(3000 + i, 5)
                
                # 生成接近目标重量的随机值
                variation = random.uniform(-error_range/2, error_range/2)
                current_weight = max(0, int(target_weight + variation))
                
                self.holding_registers[1000 + i] = current_weight
    
    def _simulate_temperature_data(self):
        """模拟温度数据"""
        # 环境温度 20-30°C
        base_temp = self.input_registers.get(6000, 250)
        variation = random.randint(-5, 5)
        new_temp = max(200, min(300, base_temp + variation))
        self.input_registers[6000] = new_temp
        
        # 设备温度 50-70°C
        base_device_temp = self.input_registers.get(6001, 600)
        device_variation = random.randint(-10, 10)
        new_device_temp = max(500, min(700, base_device_temp + device_variation))
        self.input_registers[6001] = new_device_temp
    
    def _simulate_system_status(self):
        """模拟系统运行状态"""
        # 如果系统在运行，模拟一些状态变化
        if self.coils.get(0, False):  # 系统启动状态
            # 随机模拟一些状态
            if random.random() < 0.1:  # 10%概率更新状态
                # 模拟称重头状态变化
                for i in range(6):
                    if random.random() < 0.05:  # 5%概率改变状态
                        self.coils[100 + i] = not self.coils.get(100 + i, False)
    
    def _simulate_packaging_count(self):
        """模拟包装计数"""
        if self.coils.get(0, False) and self.coils.get(3, False):  # 系统启动且自动模式
            current_count = self.holding_registers.get(5000, 0)
            target_count = self.holding_registers.get(5001, 1000)
            
            if current_count < target_count:
                # 根据包装速度增加计数
                speed = self.holding_registers.get(5002, 50)  # 包/分钟
                if random.random() < (speed / 60):  # 按速度概率增加
                    self.holding_registers[5000] = current_count + 1
    
    def stop_simulation(self):
        """停止数据模拟"""
        self.simulation_running = False
        if self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=2)
        logger.info("虚拟PLC数据模拟已停止")


class VirtualModbusClient:
    """虚拟Modbus客户端，模拟真实的ModbusClient行为"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 502, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connected = False
        self.data = VirtualPLCData()
        
        logger.info(f"虚拟Modbus客户端创建: {host}:{port}")
    
    # 在VirtualModbusClient类中添加这些方法（在类的末尾，现有方法之后）

    def write_multiple_coils(self, address: int, values: List[bool]) -> bool:
        """
        写入多个线圈（兼容性别名方法）
        
        Args:
            address: 起始地址
            values: 布尔值列表
        
        Returns:
            bool: 写入是否成功
        """
        return self.write_coils(address, values)

    def write_multiple_registers(self, address: int, values: List[int]) -> bool:
        """
        写入多个寄存器（兼容性别名方法）
        
        Args:
            address: 起始地址
            values: 整数值列表
        
        Returns:
            bool: 写入是否成功
        """
        return self.write_registers(address, values)

    def write_holding_register(self, address: int, value: int) -> bool:
        """
        写入单个保持寄存器（兼容性别名方法）
        
        Args:
            address: 寄存器地址
            value: 要写入的值
        
        Returns:
            bool: 写入是否成功
        """
        return self.write_register(address, value)

    def write_holding_registers(self, address: int, values: List[int]) -> bool:
        """
        写入多个保持寄存器（兼容性别名方法）
        
        Args:
            address: 起始地址
            values: 整数值列表
        
        Returns:
            bool: 写入是否成功
        """
        return self.write_registers(address, values)

    def read_input_register(self, address: int) -> tuple[bool, int]:
        """
        读取单个输入寄存器（兼容性别名方法）
        
        Args:
            address: 寄存器地址
        
        Returns:
            tuple[bool, int]: (读取是否成功, 寄存器值)
        """
        success, values = self.read_input_registers(address, 1)
        if success and values:
            return True, values[0]
        return False, 0

    def read_holding_register(self, address: int) -> tuple[bool, int]:
        """
        读取单个保持寄存器（兼容性别名方法）
        
        Args:
            address: 寄存器地址
        
        Returns:
            tuple[bool, int]: (读取是否成功, 寄存器值)
        """
        success, values = self.read_holding_registers(address, 1)
        if success and values:
            return True, values[0]
        return False, 0
    
    def connect(self) -> tuple[bool, str]:
        """模拟连接操作"""
        try:
            # 模拟连接延时
            time.sleep(0.5)
            
            # 95%的成功率
            if random.random() < 0.95:
                self.connected = True
                message = f"虚拟PLC连接成功 {self.host}:{self.port}"
                logger.info(message)
                return True, message
            else:
                message = f"虚拟PLC连接失败 {self.host}:{self.port} - 模拟连接错误"
                logger.warning(message)
                return False, message
                
        except Exception as e:
            message = f"虚拟PLC连接异常: {str(e)}"
            logger.error(message)
            return False, message
    
    def disconnect(self) -> bool:
        """模拟断开连接"""
        if self.connected:
            self.connected = False
            self.data.stop_simulation()
            logger.info("虚拟PLC连接已断开")
            return True
        return False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected
    
    def read_coils(self, address: int, count: int = 1) -> tuple[bool, List[bool]]:
        """读取线圈状态"""
        if not self.connected:
            return False, []
        
        try:
            # 模拟读取延时
            time.sleep(0.01)
            
            result = []
            for i in range(count):
                coil_addr = address + i
                value = self.data.coils.get(coil_addr, False)
                result.append(value)
            
            logger.debug(f"读取线圈 地址:{address} 数量:{count} 结果:{result}")
            return True, result
            
        except Exception as e:
            logger.error(f"读取线圈失败: {e}")
            return False, []
    
    def read_discrete_inputs(self, address: int, count: int = 1) -> tuple[bool, List[bool]]:
        """读取离散输入"""
        if not self.connected:
            return False, []
        
        try:
            time.sleep(0.01)
            
            result = []
            for i in range(count):
                input_addr = address + i
                value = self.data.discrete_inputs.get(input_addr, False)
                result.append(value)
            
            logger.debug(f"读取离散输入 地址:{address} 数量:{count} 结果:{result}")
            return True, result
            
        except Exception as e:
            logger.error(f"读取离散输入失败: {e}")
            return False, []
    
    def read_holding_registers(self, address: int, count: int = 1) -> tuple[bool, List[int]]:
        """读取保持寄存器"""
        if not self.connected:
            return False, []
        
        try:
            time.sleep(0.01)
            
            result = []
            for i in range(count):
                reg_addr = address + i
                value = self.data.holding_registers.get(reg_addr, 0)
                result.append(value)
            
            logger.debug(f"读取保持寄存器 地址:{address} 数量:{count} 结果:{result}")
            return True, result
            
        except Exception as e:
            logger.error(f"读取保持寄存器失败: {e}")
            return False, []
    
    def read_input_registers(self, address: int, count: int = 1) -> tuple[bool, List[int]]:
        """读取输入寄存器"""
        if not self.connected:
            return False, []
        
        try:
            time.sleep(0.01)
            
            result = []
            for i in range(count):
                reg_addr = address + i
                value = self.data.input_registers.get(reg_addr, 0)
                result.append(value)
            
            logger.debug(f"读取输入寄存器 地址:{address} 数量:{count} 结果:{result}")
            return True, result
            
        except Exception as e:
            logger.error(f"读取输入寄存器失败: {e}")
            return False, []
    
    def write_coil(self, address: int, value: bool) -> bool:
        """写入单个线圈"""
        if not self.connected:
            return False
        
        try:
            time.sleep(0.01)
            
            old_value = self.data.coils.get(address, False)
            self.data.coils[address] = value
            
            logger.info(f"写入线圈 地址:{address} 值:{value} (原值:{old_value})")
            
            # 修改特殊处理逻辑，使用地址40
            if address == 40:  # AI模式地址
                if value:
                    logger.info("AI模式已启用")
                else:
                    logger.info("AI模式已关闭")
            
            return True
            
        except Exception as e:
            logger.error(f"写入线圈失败: {e}")
            return False
    
    def write_coils(self, address: int, values: List[bool]) -> bool:
        """写入多个线圈"""
        if not self.connected:
            return False
        
        try:
            time.sleep(0.01)
            
            for i, value in enumerate(values):
                coil_addr = address + i
                self.data.coils[coil_addr] = value
            
            logger.info(f"写入多个线圈 地址:{address} 值:{values}")
            return True
            
        except Exception as e:
            logger.error(f"写入多个线圈失败: {e}")
            return False
    
    def write_register(self, address: int, value: int) -> bool:
        """写入单个寄存器"""
        if not self.connected:
            return False
        
        try:
            time.sleep(0.01)
            
            # 确保值在有效范围内
            value = max(0, min(65535, value))
            
            old_value = self.data.holding_registers.get(address, 0)
            self.data.holding_registers[address] = value
            
            logger.info(f"写入寄存器 地址:{address} 值:{value} (原值:{old_value})")
            return True
            
        except Exception as e:
            logger.error(f"写入寄存器失败: {e}")
            return False
    
    def write_registers(self, address: int, values: List[int]) -> bool:
        """写入多个寄存器"""
        if not self.connected:
            return False
        
        try:
            time.sleep(0.01)
            
            for i, value in enumerate(values):
                reg_addr = address + i
                # 确保值在有效范围内
                value = max(0, min(65535, value))
                self.data.holding_registers[reg_addr] = value
            
            logger.info(f"写入多个寄存器 地址:{address} 值:{values}")
            return True
            
        except Exception as e:
            logger.error(f"写入多个寄存器失败: {e}")
            return False
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取虚拟PLC状态信息"""
        return {
            "type": "Virtual PLC",
            "host": self.host,
            "port": self.port,
            "connected": self.connected,
            "coil_count": len(self.data.coils),
            "discrete_input_count": len(self.data.discrete_inputs),
            "holding_register_count": len(self.data.holding_registers),
            "input_register_count": len(self.data.input_registers),
            "simulation_running": self.data.simulation_running
        }
    
    def export_data(self) -> Dict[str, Any]:
        """导出所有数据（用于调试）"""
        return {
            "coils": dict(self.data.coils),
            "discrete_inputs": dict(self.data.discrete_inputs),
            "holding_registers": dict(self.data.holding_registers),
            "input_registers": dict(self.data.input_registers)
        }
    
    def import_data(self, data: Dict[str, Any]) -> bool:
        """导入数据（用于测试）"""
        try:
            if "coils" in data:
                self.data.coils.update(data["coils"])
            if "discrete_inputs" in data:
                self.data.discrete_inputs.update(data["discrete_inputs"])
            if "holding_registers" in data:
                self.data.holding_registers.update(data["holding_registers"])
            if "input_registers" in data:
                self.data.input_registers.update(data["input_registers"])
            
            logger.info("虚拟PLC数据导入成功")
            return True
        except Exception as e:
            logger.error(f"虚拟PLC数据导入失败: {e}")
            return False


def create_virtual_modbus_client(host: str = "127.0.0.1", port: int = 502, timeout: float = 3.0) -> VirtualModbusClient:
    """
    创建虚拟Modbus客户端实例
    
    Args:
        host: 主机地址（虚拟的）
        port: 端口号（虚拟的）
        timeout: 超时时间
    
    Returns:
        VirtualModbusClient: 虚拟Modbus客户端实例
    """
    return VirtualModbusClient(host, port, timeout)


# 测试代码
if __name__ == "__main__":
    print("🔧 虚拟PLC测试")
    print("=" * 50)
    
    # 创建虚拟客户端
    client = create_virtual_modbus_client()
    
    # 测试连接
    success, message = client.connect()
    print(f"连接结果: {success} - {message}")
    
    if success:
        # 测试读写操作
        print("\n📖 测试读取操作:")
        
        # 读取线圈
        success, coils = client.read_coils(0, 5)
        print(f"读取线圈 0-4: {coils}")
        
        # 读取寄存器
        success, regs = client.read_holding_registers(1000, 6)
        print(f"读取寄存器 1000-1005: {regs}")
        
        print("\n✏️  测试写入操作:")
        
        # 写入线圈
        success = client.write_coil(0, True)
        print(f"写入线圈 0=True: {success}")
        
        # 写入寄存器
        success = client.write_register(2000, 150)
        print(f"写入寄存器 2000=150: {success}")
        
        # 再次读取验证
        success, coils = client.read_coils(0, 1)
        success2, regs = client.read_holding_registers(2000, 1)
        print(f"验证读取 - 线圈0: {coils}, 寄存器2000: {regs}")
        
        print("\n📊 状态信息:")
        status = client.get_status_info()
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # 等待几秒观察数据变化
        print("\n⏰ 等待5秒观察数据变化...")
        time.sleep(5)
        
        success, regs = client.read_input_registers(6000, 2)
        print(f"温度数据更新: {regs}")
        
        # 断开连接
        client.disconnect()
        print("\n✅ 虚拟PLC测试完成")
if __name__ == "__main__":
    try:
        print("测试虚拟PLC模块导入...")
        from virtual_plc import VirtualModbusClient
        print("虚拟PLC模块导入成功")
        
        print("创建虚拟客户端...")
        client = VirtualModbusClient()
        print(f"客户端创建成功: {client}")
        
        print("尝试连接...")
        success, message = client.connect()
        print(f"连接结果: {success} - {message}")
        
        if success:
            print("测试读取...")
            result = client.read_coils(0, 1)
            print(f"读取结果: {result}")
            
            print("测试写入...")
            write_result = client.write_coil(0, True)
            print(f"写入结果: {write_result}")
            
            client.disconnect()
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()