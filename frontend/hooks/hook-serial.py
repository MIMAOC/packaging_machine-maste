
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
