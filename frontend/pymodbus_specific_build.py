#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门针对PyModbus问题的打包脚本
"""

import os
import sys
import subprocess
import importlib.util

def check_pymodbus_installation():
    """检查pymodbus安装情况"""
    print("检查PyModbus安装情况...")
    
    try:
        import pymodbus
        print(f"✓ PyModbus版本: {pymodbus.__version__}")
        print(f"✓ PyModbus位置: {pymodbus.__file__}")
        
        # 检查关键子模块
        submodules = [
            'pymodbus.client',
            'pymodbus.payload', 
            'pymodbus.constants',
            'pymodbus.exceptions'
        ]
        
        for submodule in submodules:
            try:
                __import__(submodule)
                print(f"✓ {submodule} 可用")
            except ImportError as e:
                print(f"✗ {submodule} 不可用: {e}")
        
        return True
    except ImportError as e:
        print(f"✗ PyModbus未安装或有问题: {e}")
        return False

def create_pymodbus_hook():
    """创建PyModbus的PyInstaller hook文件"""
    hook_content = '''
"""
PyInstaller hook for pymodbus
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集所有pymodbus相关内容
datas, binaries, hiddenimports = collect_all('pymodbus')

# 额外的隐藏导入
additional_imports = [
    'pymodbus.client',
    'pymodbus.client.tcp',
    'pymodbus.client.serial', 
    'pymodbus.client.udp',
    'pymodbus.client.sync',
    'pymodbus.payload',
    'pymodbus.constants',
    'pymodbus.exceptions',
    'pymodbus.pdu',
    'pymodbus.register_read_message',
    'pymodbus.register_write_message',
    'pymodbus.bit_read_message',
    'pymodbus.bit_write_message',
    'pymodbus.transaction',
    'pymodbus.utilities',
    'pymodbus.factory',
    'pymodbus.datastore',
    'pymodbus.device',
]

# 收集所有子模块
hiddenimports.extend(collect_submodules('pymodbus'))
hiddenimports.extend(additional_imports)

# 去重
hiddenimports = list(set(hiddenimports))
'''
    
    # 创建hooks目录
    if not os.path.exists('hooks'):
        os.makedirs('hooks')
    
    # 写入hook文件
    with open('hooks/hook-pymodbus.py', 'w', encoding='utf-8') as f:
        f.write(hook_content)
    
    print("✓ 创建了PyModbus hook文件: hooks/hook-pymodbus.py")

def create_serial_hook():
    """创建serial的PyInstaller hook文件"""
    hook_content = '''
"""
PyInstaller hook for serial (pyserial)
"""

from PyInstaller.utils.hooks import collect_all

# 收集所有serial相关内容
datas, binaries, hiddenimports = collect_all('serial')

# 额外的隐藏导入
additional_imports = [
    'serial',
    'serial.serialutil',
    'serial.tools',
    'serial.tools.list_ports',
    'serial.tools.miniterm',
]

hiddenimports.extend(additional_imports)
hiddenimports = list(set(hiddenimports))
'''
    
    with open('hooks/hook-serial.py', 'w', encoding='utf-8') as f:
        f.write(hook_content)
    
    print("✓ 创建了Serial hook文件: hooks/hook-serial.py")

def pymodbus_optimized_build():
    """PyModbus优化打包"""
    print("\n开始PyModbus优化打包...")
    
    # 检查安装
    if not check_pymodbus_installation():
        print("请先安装pymodbus: pip install pymodbus")
        return
    
    # 创建hook文件
    create_pymodbus_hook()
    create_serial_hook()
    
    # 扫描子目录
    subdirs = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.') and d not in ['build', 'dist', '__pycache__', 'hooks']]
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--console',  # 显示控制台以便调试
        '--name=包装机控制系统_PyModbus优化版',
        '--distpath=dist',
        '--workpath=build',
        '--specpath=.',
        
        # 使用自定义hooks
        '--additional-hooks-dir=hooks',
        
        # 强制收集pymodbus和serial的所有内容
        '--collect-all=pymodbus',
        '--collect-all=serial',
        '--collect-submodules=pymodbus',
        '--collect-submodules=serial',
        
        # 递归收集所有依赖
        '--collect-all=pymodbus.client',
        '--collect-all=pymodbus.payload',
        '--collect-all=pymodbus.constants',
        
        # 不优化导入（保留所有模块）
        '--noconfirm',
        '--clean',
    ]
    
    # 添加数据目录
    for subdir in subdirs:
        if os.path.exists(subdir):
            cmd.extend(['--add-data', f'{subdir};{subdir}'])
            print(f"添加目录: {subdir}")
    
    # 大量的隐藏导入
    hidden_imports = [
        # PyModbus相关
        'pymodbus', 'pymodbus.client', 'pymodbus.client.tcp', 'pymodbus.client.serial',
        'pymodbus.client.udp', 'pymodbus.client.sync', 'pymodbus.payload',
        'pymodbus.constants', 'pymodbus.exceptions', 'pymodbus.pdu',
        'pymodbus.register_read_message', 'pymodbus.register_write_message',
        'pymodbus.bit_read_message', 'pymodbus.bit_write_message',
        'pymodbus.transaction', 'pymodbus.utilities', 'pymodbus.factory',
        'pymodbus.datastore', 'pymodbus.device', 'pymodbus.server',
        
        # Serial相关  
        'serial', 'serial.serialutil', 'serial.tools', 'serial.tools.list_ports',
        
        # 系统模块
        'socket', 'select', 'threading', 'time', 'struct', 'logging',
        'collections', 'itertools', 'functools', 'operator',
        
        # GUI相关
        'tkinter', 'tkinter.ttk', 'tkinter.font', 'tkinter.messagebox',
        
        # 其他依赖
        'requests', 'tenacity', 'typing',
        
        # 你的自定义模块
        'modbus_client', 'plc_operations', 'plc_addresses',
        'ai_mode_interface', 'traditional_mode_interface', 'logo_handler',
        'adaptive_learning_controller', 'bucket_control_extended',
        'bucket_learning_state_manager', 'bucket_monitoring',
        'coarse_time_controller', 'factory_settings_interface',
        'fine_time_controller', 'flight_material_controller',
        'manual_mode_interface', 'material_cleaning_controller',
        'material_management_interface', 'parameter_setting_interface',
        'production_interface', 'production_records_interface',
        'system_settings_interface', 'system_setting_interface',
        'traditional_plc_addresses', 'virtual_plc', 'weight_calibration_interface',
        'config', 'config.api_config', 'clients', 'clients.webapi_client',
    ]
    
    for module in hidden_imports:
        cmd.extend(['--hidden-import', module])
    
    cmd.append('main.py')
    
    # 执行打包
    try:
        print(f"\n执行命令:")
        for i, arg in enumerate(cmd):
            if i % 4 == 0:
                print()
            print(f"{arg} ", end="")
        print("\n")
        
        print("打包进行中，请稍候...")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("PyInstaller输出:")
        print(result.stdout)
        
        if result.stderr:
            print("错误信息:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✓ 打包成功!")
            
            # 检查输出文件
            exe_path = "dist/包装机控制系统_PyModbus优化版.exe"
            if os.path.exists(exe_path):
                file_size = os.path.getsize(exe_path)
                print(f"Exe文件: {exe_path}")
                print(f"文件大小: {file_size / (1024*1024):.1f} MB")
            else:
                print("警告: 未找到输出的exe文件")
        else:
            print(f"\n✗ 打包失败，退出码: {result.returncode}")
            
    except Exception as e:
        print(f"✗ 打包过程中发生错误: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("PyModbus专用打包工具")
    print("=" * 60)
    
    pymodbus_optimized_build()
    
    print("\n完成！请运行生成的exe文件并检查pymodbus是否正常工作。")