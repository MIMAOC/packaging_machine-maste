# backend/analysis/__init__.py
"""
分析模块包
提供各种数据分析功能

模块列表：
- weight_analysis: 重量分析逻辑
- coarse_time_analysis: 快加时间分析逻辑
- flight_material_analysis: 飞料值分析逻辑
"""

__version__ = "1.5.1"
__author__ = "AI助手"

# 导入主要分析函数
try:
    from .weight_analysis import analyze_target_weight_for_coarse_speed, get_all_speed_rules
    from .coarse_time_analysis import analyze_coarse_time_compliance
    from .flight_material_analysis import analyze_flight_material_values
    
    __all__ = [
        'analyze_target_weight_for_coarse_speed', 'get_all_speed_rules',
        'analyze_coarse_time_compliance',
        'analyze_flight_material_values'
    ]
    
except ImportError as e:
    print(f"警告：分析模块导入失败: {e}")
    __all__ = []