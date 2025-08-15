# exception_handlers.py
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """自定义验证错误处理器"""
    
    try:
        # 获取第一个验证错误（通常最重要）
        first_error = exc.errors()[0] if exc.errors() else None
        
        if first_error:
            # 提取字段名和错误类型
            field_name = first_error['loc'][-1] if first_error['loc'] else 'unknown'
            error_msg = first_error.get('msg', '验证失败')
            
            # 记录详细错误信息
            logger.warning(f"验证失败 - 字段: {field_name}, 错误: {error_msg}")
            
            # 返回统一的错误响应格式
            return JSONResponse(
                status_code=422,
                content={
                    'success': False,
                    'error': error_msg,
                    'field': field_name,
                    'timestamp': str(exc.errors()[0].get('input', ''))
                }
            )
        else:
            return JSONResponse(
                status_code=422,
                content={
                    'success': False,
                    'error': '请求参数验证失败',
                    'details': '未知验证错误'
                }
            )
            
    except Exception as e:
        logger.error(f"异常处理器内部错误: {str(e)}")
        return JSONResponse(
            status_code=422,
            content={
                'success': False,
                'error': '请求参数验证失败',
                'details': '服务器处理验证错误时发生异常'
            }
        )