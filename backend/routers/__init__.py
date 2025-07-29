# backend/routers/__init__.py
"""
API路由包
定义各种API端点的路由处理

模块列表：
- health: 健康检查API
- weight: 重量分析API
- coarse_time: 快加时间分析API
- flight_material: 飞料值分析API
"""

__version__ = "1.5.1"
__author__ = "AI助手"

# 导入主要路由模块
try:
    from . import health, weight, coarse_time, flight_material, fine_time, adaptive_learning
    
    __all__ = ['health', 'weight', 'coarse_time', 'flight_material', 'fine_time', 'adaptive_learning']
    
except ImportError as e:
    print(f"警告：路由模块导入失败: {e}")
    __all__ = []