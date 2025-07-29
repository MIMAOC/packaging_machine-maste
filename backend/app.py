#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多斗颗粒称重包装机 - 后端API服务
基于FastAPI的分析服务，提供重量分析、快加时间分析、飞料值分析、慢加时间分析、自适应学习分析等功能

依赖库安装：
pip install fastapi uvicorn python-multipart

作者：AI助手
创建日期：2025-07-23
更新日期：2025-07-24（添加慢加时间分析和自适应学习分析功能）
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import traceback
from datetime import datetime
import uvicorn

# 导入路由模块
from routers import health, weight, coarse_time, flight_material, fine_time, adaptive_learning

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="包装机分析API服务",
    description="多斗颗粒称重包装机数据分析API服务",
    version="1.5.1",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, prefix="/api", tags=["健康检查"])
app.include_router(weight.router, prefix="/api/weight", tags=["重量分析"])
app.include_router(coarse_time.router, prefix="/api/coarse_time", tags=["快加时间分析"])
app.include_router(flight_material.router, prefix="/api/flight_material", tags=["飞料值分析"])
app.include_router(fine_time.router, prefix="/api/fine_time", tags=["慢加时间分析"])
app.include_router(adaptive_learning.router, prefix="/api/adaptive_learning", tags=["自适应学习分析"])

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "服务器内部错误",
            "timestamp": datetime.now().isoformat()
        }
    )

# 根路径
@app.get("/")
async def root():
    """根路径，返回API基本信息"""
    return {
        "name": "包装机分析API服务",
        "version": "1.5.1",
        "description": "多斗颗粒称重包装机数据分析API服务",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": {
            "weight_analysis": "/api/weight/analyze",
            "coarse_time_analysis": "/api/coarse_time/analyze", 
            "flight_material_analysis": "/api/flight_material/analyze",
            "fine_time_analysis": "/api/fine_time/analyze",
            "adaptive_learning_analysis": "/api/adaptive_learning/analyze"
        },
        "timestamp": datetime.now().isoformat()
    }

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    logger.info("=" * 60)
    logger.info("🚀 包装机分析API服务启动中...")
    logger.info("=" * 60)
    logger.info(f"📊 服务名称: 包装机分析API服务")
    logger.info(f"📈 版本号: 1.5.1")
    logger.info(f"🌐 文档地址: /docs")
    logger.info(f"💊 健康检查: /api/health")
    logger.info("=" * 60)
    logger.info("✅ 服务启动完成！")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    logger.info("👋 包装机分析API服务正在关闭...")
    logger.info("✅ 服务已安全关闭")

if __name__ == "__main__":
    # 直接运行时的配置
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,  # 开发模式下启用热重载
        log_level="info"
    )