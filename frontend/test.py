from pymodbus.client import ModbusTcpClient
import socket
import time

class XinJeModbusClient:
    def __init__(self, host: str = "192.168.6.6", port: int = 502, timeout: int = 3):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client = None
        self.slave_id = 1  # 信捷PLC默认站号
    
    def test_tcp_connection(self):
        """测试基础TCP连接"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception as e:
            print(f"TCP连接测试失败: {e}")
            return False
    
    def connect(self):
        """连接PLC"""
        # 首先测试TCP连接
        if not self.test_tcp_connection():
            print("TCP连接失败，请检查网络和PLC配置")
            return False
        
        # 尝试Modbus连接
        try:
            self.client = ModbusTcpClient(
                host=self.host, 
                port=self.port, 
                timeout=self.timeout
            )
            
            connection = self.client.connect()
            if connection:
                print("Modbus TCP连接成功!")
                
                # 先测试原来的地址0
                print("\n=== 测试地址0 ===")
                result = self.client.read_holding_registers(
                    address=0, count=1, slave=self.slave_id
                )
                
                if not result.isError():
                    print(f"地址0读取成功: {result.registers}")
                else:
                    print(f"地址0读取失败: {result}")
                
                # 测试modbus_client.py中的地址
                test_addresses = [20, 22, 24, 26, 28]
                print(f"\n=== 测试地址 {test_addresses} ===")
                communication_verified = False
                
                for addr in test_addresses:
                    print(f"测试地址 {addr}...")
                    try:
                        result = self.client.read_holding_registers(addr, 1, slave=self.slave_id)
                        
                        if not result.isError():
                            print(f"  地址 {addr} 读取成功: {result.registers}")
                            communication_verified = True
                        else:
                            print(f"  地址 {addr} 读取失败: {result}")
                            
                    except Exception as e:
                        print(f"  地址 {addr} 读取异常: {e}")
                
                if communication_verified:
                    print(f"\n✅ 至少有一个测试地址读取成功")
                    return True
                else:
                    print(f"\n❌ 所有测试地址都读取失败")
                    return False
                    
            return False
            
        except Exception as e:
            print(f"Modbus连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.client:
            self.client.close()
            print("连接已断开")
            from pymodbus.client import ModbusTcpClient
import socket
import time

class XinJeModbusClient:
    def __init__(self, host: str = "192.168.6.6", port: int = 502, timeout: int = 3):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client = None
        self.slave_id = 1  # 信捷PLC默认站号
    
    def test_tcp_connection(self):
        """测试基础TCP连接"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception as e:
            print(f"TCP连接测试失败: {e}")
            return False
    
    def connect(self):
        """连接PLC"""
        # 首先测试TCP连接
        if not self.test_tcp_connection():
            print("TCP连接失败，请检查网络和PLC配置")
            return False
        
        # 尝试Modbus连接
        try:
            self.client = ModbusTcpClient(
                host=self.host, 
                port=self.port, 
                timeout=self.timeout
            )
            
            connection = self.client.connect()
            if connection:
                print("Modbus TCP连接成功!")
                
                # 先测试原来的地址0
                print("\n=== 测试地址0 ===")
                result = self.client.read_holding_registers(
                    address=0, count=1, slave=self.slave_id
                )
                
                if not result.isError():
                    print(f"地址0读取成功: {result.registers}")
                else:
                    print(f"地址0读取失败: {result}")
                
                # 测试modbus_client.py中的地址
                test_addresses = [20, 22, 24, 26, 28]
                print(f"\n=== 测试地址 {test_addresses} ===")
                communication_verified = False
                
                for addr in test_addresses:
                    print(f"测试地址 {addr}...")
                    try:
                        # 修复：使用关键字参数，与地址0的调用方式一致
                        result = self.client.read_holding_registers(address=addr, count=1, slave=self.slave_id)
                        
                        if not result.isError():
                            print(f"  地址 {addr} 读取成功: {result.registers}")
                            communication_verified = True
                        else:
                            print(f"  地址 {addr} 读取失败: {result}")
                            
                    except Exception as e:
                        print(f"  地址 {addr} 读取异常: {e}")
                
                if communication_verified:
                    print(f"\n✅ 至少有一个测试地址读取成功")
                    return True
                else:
                    print(f"\n❌ 所有测试地址都读取失败")
                    return False
                    
            return False
            
        except Exception as e:
            print(f"Modbus连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.client:
            self.client.close()
            print("连接已断开")

# 使用示例
if __name__ == "__main__":
    plc = XinJeModbusClient()
    if plc.connect():
        print("PLC连接成功，可以进行数据通信")
        plc.disconnect()
    else:
        print("PLC连接失败，请检查配置")

# 使用示例
if __name__ == "__main__":
    plc = XinJeModbusClient()
    if plc.connect():
        print("PLC连接成功，可以进行数据通信")
        plc.disconnect()
    else:
        print("PLC连接失败，请检查配置")