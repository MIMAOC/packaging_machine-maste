#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frontend包装机程序打包脚本
用于将frontend目录下的包装机程序打包成exe可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """检查必要的依赖是否已安装"""
    required_packages = [
        'pyinstaller',
        'requests', 
        'tenacity',
        'pymodbus'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} 未安装")
    
    if missing_packages:
        print("\n缺少以下依赖包:")
        for pkg in missing_packages:
            print(f"  - {pkg}")
        print("\n请运行: pip install " + " ".join(missing_packages))
        return False
    
    return True

def scan_python_files():
    """扫描当前目录下的Python文件"""
    python_files = []
    for file in os.listdir('.'):
        if file.endswith('.py') and file != 'build_frontend.py':
            python_files.append(file)
    
    print("\n发现的Python文件:")
    for file in python_files:
        print(f"  - {file}")
    
    return python_files

def create_spec_file():
    """创建PyInstaller的spec文件"""
    
    # 扫描当前目录的子目录
    subdirs = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.') and d not in ['build', 'dist', '__pycache__']]
    
    # 构建datas列表
    datas_list = []
    for subdir in subdirs:
        datas_list.append(f"('{subdir}', '{subdir}'),")
    
    datas_str = "\n    ".join(datas_list) if datas_list else "# 没有发现子目录"
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 定义需要包含的数据文件和目录
datas = [
    {datas_str}
]

# 定义需要包含的隐藏导入
hiddenimports = [
    'tkinter',
    'tkinter.ttk', 
    'tkinter.font',
    'tkinter.messagebox',
    'requests',
    'tenacity',
    'pymodbus',
    'pymodbus.client.tcp',
    'pymodbus.client.sync',
    'pymodbus.client',
    'threading',
    'time',
    'functools',
    'typing',
    # 根据你的实际模块添加
    'modbus_client',
    'ai_mode_interface', 
    'traditional_mode_interface',
    'logo_handler',
    'plc_addresses',
]

# 检查config目录是否存在，如果存在则添加相关模块
try:
    import config.api_config
    hiddenimports.extend([
        'config',
        'config.api_config',
    ])
except ImportError:
    pass

# 检查clients目录是否存在，如果存在则添加相关模块  
try:
    import clients.webapi_client
    hiddenimports.extend([
        'clients',
        'clients.webapi_client',
    ])
except ImportError:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='包装机控制系统-前端',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设为False隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 如果有图标文件，在这里指定路径
)
"""
    
    with open('packaging_machine_frontend.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content.strip())
    
    print("✓ 已创建 packaging_machine_frontend.spec 文件")

def build_exe_with_spec():
    """使用spec文件打包"""
    print("\n开始使用spec文件打包...")
    
    cmd = [
        'pyinstaller',
        '--clean',  # 清理临时文件
        'packaging_machine_frontend.spec'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ 打包成功!")
        print(f"exe文件位置: dist/包装机控制系统-前端.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def build_exe_simple():
    """简单的打包方法"""
    print("\n使用简单方法打包...")
    
    # 扫描子目录
    subdirs = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.') and d not in ['build', 'dist', '__pycache__']]
    
    cmd = [
        'pyinstaller',
        '--onefile',                          # 打包成单个exe文件
        '--windowed',                         # 不显示控制台窗口
        '--name=包装机控制系统-前端',            # 指定exe文件名
        '--distpath=dist',                    # 指定输出目录
        '--workpath=build',                   # 指定临时工作目录  
        '--specpath=.',                       # 指定spec文件位置
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=tkinter.font',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=requests',
        '--hidden-import=tenacity',
        '--hidden-import=pymodbus',
        '--hidden-import=pymodbus.client.tcp',
        '--hidden-import=threading',
        '--hidden-import=time',
        '--hidden-import=functools',
    ]
    
    # 添加子目录
    for subdir in subdirs:
        cmd.append(f'--add-data={subdir};{subdir}')
        print(f"添加目录: {subdir}")
    
    # 添加可能的隐藏导入
    possible_modules = [
        'modbus_client',
        'ai_mode_interface', 
        'traditional_mode_interface',
        'logo_handler',
        'plc_addresses',
        'config.api_config',
        'clients.webapi_client',
    ]
    
    for module in possible_modules:
        cmd.append(f'--hidden-import={module}')
    
    cmd.append('main.py')
    
    try:
        print("执行命令:", ' '.join(cmd))
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ 简单打包成功!")
        print(f"exe文件位置: dist/包装机控制系统-前端.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 简单打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        print(f"标准输出: {e.stdout}")
        return False

def clean_build_files():
    """清理构建文件"""
    dirs_to_clean = ['build', '__pycache__']
    files_to_clean = ['*.spec']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ 已清理 {dir_name} 目录")
    
    import glob
    for pattern in files_to_clean:
        for file in glob.glob(pattern):
            os.remove(file)
            print(f"✓ 已清理 {file}")

def main():
    """主函数"""
    print("=" * 60)
    print("包装机程序打包工具 - Frontend版本")
    print("=" * 60)
    
    # 检查是否在正确的目录
    if not os.path.exists('main.py'):
        print("✗ 找不到 main.py 文件")
        print("请确保在frontend目录中运行此脚本")
        return
    
    print("✓ 发现 main.py 文件")
    
    # 扫描Python文件
    python_files = scan_python_files()
    
    # 检查依赖
    if not check_dependencies():
        print("\n请先安装缺少的依赖包")
        return
    
    print("\n选择打包方式:")
    print("1. 使用spec文件打包 (推荐，更可控)")
    print("2. 简单快速打包")
    print("3. 清理构建文件")
    print("4. 退出")
    
    choice = input("\n请选择 (1-4): ").strip()
    
    if choice == '1':
        create_spec_file()
        if build_exe_with_spec():
            print("\n✓ 打包完成! 请检查 dist 目录中的exe文件")
            print("可以将整个dist目录复制到目标机器上运行")
        else:
            print("\n✗ 打包失败，请检查错误信息")
    
    elif choice == '2':
        if build_exe_simple():
            print("\n✓ 打包完成! 请检查 dist 目录中的exe文件")
            print("可以将exe文件复制到目标机器上运行")
        else:
            print("\n✗ 打包失败，请检查错误信息")
    
    elif choice == '3':
        clean_build_files()
        print("\n✓ 清理完成")
    
    elif choice == '4':
        print("退出")
        return
    
    else:
        print("无效选择")

if __name__ == "__main__":
    main()