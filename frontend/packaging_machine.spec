# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],  # 如果主入口不是main.py，请改为实际入口文件名
    pathex=['.'],  # 指定当前目录为搜索路径
    binaries=[],
    datas=[
        ('clients/*', 'clients'),
        ('config/*', 'config'),
        ('data/*', 'data'),
        ('database/*', 'database'),
        ('output/*', 'output'),
        # 如有其它资源文件夹可继续添加
    ],
    hiddenimports=[
        'tkinter', 'tkinter.ttk', 'tkinter.font', 'tkinter.messagebox',
        'requests', 'tenacity', 'pymodbus', 'pymodbus.client.tcp', 'pymodbus.client.sync',
        'threading', 'time', 'functools', 'typing',
        'modbus_client', 'ai_mode_interface', 'traditional_mode_interface', 'logo_handler',
        'plc_addresses', 'adaptive_learning_controller', 'bucket_control_extended',
        'bucket_learning_state_manager', 'bucket_monitoring', 'coarse_time_controller',
        'factory_settings_interface', 'fine_time_controller', 'flight_material_controller',
        'manual_mode_interface', 'material_cleaning_controller', 'material_management_interface',
        'parameter_setting_interface', 'plc_operations', 'production_interface',
        'production_records_interface', 'system_settings_interface', 'system_setting_interface',
        'traditional_plc_addresses', 'virtual_plc', 'weight_calibration_interface',
        'config', 'config.api_config', 'clients', 'clients.webapi_client'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='包装机控制系统',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 改为False，打包为无控制台窗口的GUI程序
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    
)
