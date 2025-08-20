__version__ = "1.5.1"
__author__ = "L&C"

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