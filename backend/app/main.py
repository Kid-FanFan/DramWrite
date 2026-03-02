"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import ScriptMasterException
from app.api.v1.handlers import scriptmaster_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(f"🎬 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    logger.info(f"📡 服务器地址: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"🔧 调试模式: {settings.DEBUG}")

    # 数据库会在第一次导入 app.core.database 时自动初始化
    logger.info("✅ 数据库初始化完成")

    yield

    # 关闭时
    logger.info("👋 应用关闭中...")


def create_application() -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI驱动的短剧剧本创作工具",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册异常处理器
    app.add_exception_handler(ScriptMasterException, scriptmaster_exception_handler)

    # 注册路由
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_application()


@app.get("/")
async def root():
    """根路径 - 服务状态检查"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "code": 200,
        "message": "healthy",
        "data": {
            "status": "ok",
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }
    }
