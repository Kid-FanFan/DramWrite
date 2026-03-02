"""
导出功能 API
"""
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from loguru import logger

from app.services.export import ExportService

router = APIRouter()


class ExportRequest(BaseModel):
    """导出请求"""
    format: str = Field(..., description="格式: docx/pdf/zip")
    contents: List[str] = Field(default=["synopsis", "characters", "outline", "scripts"])
    episodes: str = Field(default="all", description="集数范围: all/1-30/[1,2,3]")


@router.post("/{project_id}/export", response_model=dict)
async def export_project(project_id: str, request: ExportRequest):
    """
    导出剧本包

    Args:
        project_id: 项目ID
        request: 导出请求
    """
    try:
        if request.format == "docx":
            filepath = ExportService.export_to_docx(
                project_id, request.contents, request.episodes
            )
        elif request.format == "pdf":
            filepath = ExportService.export_to_pdf(
                project_id, request.contents, request.episodes
            )
        elif request.format == "zip":
            filepath = ExportService.export_to_zip(
                project_id, request.contents, request.episodes
            )
        else:
            raise HTTPException(status_code=400, detail="不支持的导出格式")

        # 生成导出ID（使用文件名）
        export_id = os.path.basename(filepath)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "export_id": export_id,
                "status": "completed",
                "download_url": f"/api/v1/projects/exports/{export_id}/download",
                "filename": export_id
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"导出失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.get("/exports/{export_id}/download")
async def download_export(export_id: str):
    """
    下载导出文件

    Args:
        export_id: 导出任务ID（文件名）
    """
    export_dir = os.path.join(os.getcwd(), "exports")
    filepath = os.path.join(export_dir, export_id)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件不存在")

    # 确定MIME类型
    if export_id.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif export_id.endswith(".pdf"):
        media_type = "application/pdf"
    elif export_id.endswith(".zip"):
        media_type = "application/zip"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        filepath,
        media_type=media_type,
        filename=export_id
    )
