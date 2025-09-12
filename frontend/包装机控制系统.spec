# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('clients', 'clients'), ('config', 'config'), ('data', 'data'), ('database', 'database'), ('output', 'output')],
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.font', 'tkinter.messagebox', 'requests', 'tenacity', 'pymodbus', 'pymodbus.client.tcp', 'pymodbus.client.sync', 'threading', 'time', 'functools', 'typing', 'modbus_client', 'ai_mode_interface', 'traditional_mode_interface', 'logo_handler', 'plc_addresses', 'adaptive_learning_controller', 'bucket_control_extended', 'bucket_learning_state_manager', 'bucket_monitoring', 'coarse_time_controller', 'factory_settings_interface', 'fine_time_controller', 'flight_material_controller', 'manual_mode_interface', 'material_cleaning_controller', 'material_management_interface', 'parameter_setting_interface', 'plc_operations', 'production_interface', 'production_records_interface', 'system_settings_interface', 'system_setting_interface', 'traditional_plc_addresses', 'virtual_plc', 'weight_calibration_interface', 'config', 'config.api_config', 'clients', 'clients.webapi_client'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='包装机控制系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
