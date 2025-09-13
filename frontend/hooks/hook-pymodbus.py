
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
