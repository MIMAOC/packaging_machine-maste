__version__ = "1.5.1"
__author__ = "L&C"

try:
    from . import health, weight, coarse_time, flight_material, fine_time, adaptive_learning
    
    __all__ = ['health', 'weight', 'coarse_time', 'flight_material', 'fine_time', 'adaptive_learning']
    
except ImportError as e:
    print(f"警告：路由模块导入失败: {e}")
    __all__ = []