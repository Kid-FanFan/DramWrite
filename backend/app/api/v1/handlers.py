"""
全局异常处理器
"""
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ScriptMasterException


async def scriptmaster_exception_handler(request: Request, exc: ScriptMasterException):
    """处理应用自定义异常"""
    return JSONResponse(
        status_code=exc.code // 100,  # 将业务码转为 HTTP 状态码
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None
        }
    )
