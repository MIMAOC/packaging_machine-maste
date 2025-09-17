#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速打包脚本 - 跳过依赖检查，直接执行打包
"""

import os
import sys
import subprocess

def main():
    print("=" * 60)
    print("快速打包工具")
    print("=" * 60)
    
    # 检查main.py是否存在
    if not os.path.exists('main.py'):
        print("✗ 找不到 main.py 文件")
        print("请确保在包含 main.py 的目录中运行此脚本")
        return
    
    print("✓ 发现 main.py 文件")
    
    # 扫描当前目录的子目录
    subdirs = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.') and d not in ['build', 'dist', '__pycache__']]
    print(f"发现子目录: {subdirs}")
    
    print("\n选择打包方式:")
    print("1. 基础打包（只包含基本依赖）")
    print("2. 完整打包（包含所有子目录和隐藏导入）")
    print("3. 退出")
    
    choice = input("\n请选择 (1-3): ").strip()
    
    if choice == '1':
        basic_build()
    elif choice == '2':
        full_build(subdirs)
    elif choice == '3':
        print("退出")
        return
    else:
        print("无效选择")

def basic_build():
    """基础打包"""
    print("\n开始基础打包...")
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',  # 使用当前Python环境
        '--onefile',
        '--windowed',
        '--name=包装机控制系统',
        '--distpath=dist',
        '--workpath=build',
        '--specpath=.',
        'main.py'
    ]
    
    execute_build(cmd)

def full_build(subdirs):
    """完整打包"""
    print("\n开始完整打包...")
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',  # 使用当前Python环境
        '--onefile',
        '--windowed', 
        '--name=包装机控制系统',
        '--distpath=dist',
        '--workpath=build',
        '--specpath=.',
    ]
    
    # 添加子目录
    for subdir in subdirs:
        cmd.extend(['--add-data', f'{subdir};{subdir}'])
        print(f"添加目录: {subdir}")
    
    # 添加隐藏导入
    hidden_imports = [
        'tkinter',
        'tkinter.ttk',
        'tkinter.font', 
        'tkinter.messagebox',
        'requests',
        'tenacity',
        'pymodbus',
        'pymodbus.client.tcp',
        'pymodbus.client.sync',
        'threading',
        'time',
        'functools',
        'typing',
        # 你的自定义模块
        'modbus_client',
        'ai_mode_interface',
        'traditional_mode_interface', 
        'logo_handler',
        'plc_addresses',
        'adaptive_learning_controller',
        'bucket_control_extended',
        'bucket_learning_state_manager',
        'bucket_monitoring',
        'coarse_time_controller',
        'factory_settings_interface',
        'fine_time_controller',
        'flight_material_controller',
        'manual_mode_interface',
        'material_cleaning_controller',
        'material_management_interface',
        'parameter_setting_interface',
        'plc_operations',
        'production_interface',
        'production_records_interface',
        'system_settings_interface',
        'system_setting_interface',
        'traditional_plc_addresses',
        'virtual_plc',
        'weight_calibration_interface',
    ]
    
    # 检查config和clients目录
    if 'config' in subdirs:
        hidden_imports.extend(['config', 'config.api_config'])
    if 'clients' in subdirs:
        hidden_imports.extend(['clients', 'clients.webapi_client'])
    
    for module in hidden_imports:
        cmd.extend(['--hidden-import', module])
    
    cmd.append('main.py')
    
    execute_build(cmd)

def execute_build(cmd):
    """执行打包命令"""
    try:
        print(f"\n执行命令: {' '.join(cmd)}")
        print("\n打包进行中，请稍候...")
        
        # 使用更好的进程管理
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            universal_newlines=True
        )
        
        # 实时显示输出
        if process.stdout is not None:
            for line in process.stdout:
                print(line.rstrip())
        else:
            print("无法获取子进程输出流。")
        
        process.wait()
        
        if process.returncode == 0:
            print("\n" + "=" * 50)
            print("✓ 打包成功!")
            print("=" * 50)
            
            # 检查输出文件
            if os.path.exists('dist'):
                exe_files = [f for f in os.listdir('dist') if f.endswith('.exe')]
                if exe_files:
                    print(f"\nExe文件: dist/{exe_files[0]}")
                    file_size = os.path.getsize(f"dist/{exe_files[0]}")
                    print(f"文件大小: {file_size / (1024*1024):.1f} MB")
                else:
                    print("\n警告: 在dist目录中未找到exe文件")
            else:
                print("\n警告: 未找到dist目录")
                
        else:
            print(f"\n✗ 打包失败，退出码: {process.returncode}")
            
    except FileNotFoundError:
        print("✗ 错误: PyInstaller未找到")
        print("请尝试运行: pip install pyinstaller")
        
    except Exception as e:
        print(f"✗ 打包过程中发生错误: {e}")

if __name__ == "__main__":
    main()