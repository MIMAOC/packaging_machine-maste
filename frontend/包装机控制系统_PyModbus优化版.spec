# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('clients', 'clients'), ('config', 'config'), ('data', 'data'), ('database', 'database'), ('output', 'output')]
binaries = []
hiddenimports = ['pymodbus', 'pymodbus.client', 'pymodbus.client.tcp', 'pymodbus.client.serial', 'pymodbus.client.udp', 'pymodbus.client.sync', 'pymodbus.payload', 'pymodbus.constants', 'pymodbus.exceptions', 'pymodbus.pdu', 'pymodbus.register_read_message', 'pymodbus.register_write_message', 'pymodbus.bit_read_message', 'pymodbus.bit_write_message', 'pymodbus.transaction', 'pymodbus.utilities', 'pymodbus.factory', 'pymodbus.datastore', 'pymodbus.device', 'pymodbus.server', 'serial', 'serial.serialutil', 'serial.tools', 'serial.tools.list_ports', 'socket', 'select', 'threading', 'time', 'struct', 'logging', 'collections', 'itertools', 'functools', 'operator', 'tkinter', 'tkinter.ttk', 'tkinter.font', 'tkinter.messagebox', 'requests', 'tenacity', 'typing', 'modbus_client', 'plc_operations', 'plc_addresses', 'ai_mode_interface', 'traditional_mode_interface', 'logo_handler', 'adaptive_learning_controller', 'bucket_control_extended', 'bucket_learning_state_manager', 'bucket_monitoring', 'coarse_time_controller', 'factory_settings_interface', 'fine_time_controller', 'flight_material_controller', 'manual_mode_interface', 'material_cleaning_controller', 'material_management_interface', 'parameter_setting_interface', 'production_interface', 'production_records_interface', 'system_settings_interface', 'system_setting_interface', 'traditional_plc_addresses', 'virtual_plc', 'weight_calibration_interface', 'config', 'config.api_config', 'clients', 'clients.webapi_client']
hiddenimports += collect_submodules('pymodbus')
hiddenimports += collect_submodules('serial')
tmp_ret = collect_all('pymodbus')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('serial')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pymodbus.client')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pymodbus.payload')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pymodbus.constants')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
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
    name='包装机控制系统_PyModbus优化版',
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
