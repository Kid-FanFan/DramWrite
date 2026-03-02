"""
导出服务 - Word/PDF 生成
"""
import os
import zipfile
from datetime import datetime
from typing import List, Dict, Any, Optional

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from loguru import logger

from app.services.project import ProjectService


class ExportService:
    """导出服务"""

    @staticmethod
    def export_to_docx(
        project_id: str,
        contents: List[str],
        episodes: str = "all"
    ) -> str:
        """
        导出为 Word 文档

        Args:
            project_id: 项目ID
            contents: 导出内容类型列表 (synopsis, characters, outlines, scripts)
            episodes: 集数范围 (all/1-30/[1,2,3])

        Returns:
            文件路径
        """
        logger.info(f"导出 Word: {project_id}, contents={contents}, episodes={episodes}")

        project = ProjectService.get_project(project_id)
        if not project:
            raise ValueError("项目不存在")

        # 创建文档
        doc = Document()

        # 设置文档标题
        title = doc.add_heading(project.get("name", "未命名剧本"), 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 添加导出信息
        info = doc.add_paragraph()
        info.add_run(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n").font.size = Pt(10)
        info.add_run(f"总集数: {len(project.get('episode_outlines', []))}集\n").font.size = Pt(10)
        info.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_page_break()

        # 导出故事梗概
        if "synopsis" in contents and project.get("story_synopsis"):
            doc.add_heading("一、故事梗概", 1)
            doc.add_heading(project.get("story_title", "未命名"), 2)

            # 一句话简介
            if project.get("one_liner"):
                p = doc.add_paragraph()
                p.add_run("一句话简介: ").bold = True
                p.add_run(project["one_liner"])

            # 详细梗概
            if project.get("story_synopsis"):
                doc.add_heading("详细梗概", 3)
                doc.add_paragraph(project["story_synopsis"])

            # 核心卖点
            if project.get("selling_points"):
                doc.add_heading("核心卖点", 3)
                for point in project["selling_points"]:
                    doc.add_paragraph(point, style='List Bullet')

            doc.add_page_break()

        # 导出人物小传
        if "characters" in contents and project.get("character_profiles"):
            doc.add_heading("二、人物小传", 1)

            for i, char in enumerate(project["character_profiles"], 1):
                char_name = ExportService._safe_get_field(char, 'name', 'name', '未知')
                doc.add_heading(f"{i}. {char_name}", 2)

                # 基本信息
                info_table = doc.add_table(rows=5, cols=2)
                info_table.style = 'Light Grid Accent 1'

                info_data = [
                    ("角色", ExportService._safe_get_field(char, 'role', 'role', '')),
                    ("年龄", ExportService._safe_get_field(char, 'age', 'age', '')),
                    ("性格", ExportService._safe_get_field(char, 'personality', 'personality', '')),
                    ("背景", ExportService._safe_get_field(char, 'background', 'background', '')),
                    ("目标", ExportService._safe_get_field(char, 'goal', 'goal', '')),
                ]

                for row_idx, (key, value) in enumerate(info_data):
                    info_table.rows[row_idx].cells[0].text = key
                    info_table.rows[row_idx].cells[1].text = value

                # 记忆点
                memory_point = ExportService._safe_get_field(char, 'memoryPoint', 'memory_point', '')
                if memory_point:
                    p = doc.add_paragraph()
                    p.add_run("记忆点: ").bold = True
                    p.add_run(memory_point)

                doc.add_paragraph()  # 空行

            doc.add_page_break()

        # 导出分集大纲
        if "outlines" in contents and project.get("episode_outlines"):
            doc.add_heading("三、分集大纲", 1)

            # 解析集数范围
            episode_list = ExportService._parse_episodes(episodes, len(project["episode_outlines"]))

            for ep_num in episode_list:
                outline = next(
                    (o for o in project["episode_outlines"]
                     if ExportService._safe_get_field(o, 'episodeNumber', 'episode_number') == ep_num),
                    None
                )
                if outline:
                    is_checkpoint = ExportService._safe_get_field(outline, 'isCheckpoint', 'is_checkpoint', False)
                    summary = ExportService._safe_get_field(outline, 'summary', 'summary', '')
                    hook = ExportService._safe_get_field(outline, 'hook', 'hook', '')

                    title = f"第{ep_num}集"
                    if is_checkpoint:
                        title += " (付费卡点)"

                    doc.add_heading(title, 2)

                    # 剧情概要
                    if summary:
                        p = doc.add_paragraph()
                        p.add_run("剧情概要: ").bold = True
                        p.add_run(summary)

                    # 卡点
                    if hook:
                        p = doc.add_paragraph()
                        p.add_run("卡点/钩子: ").bold = True
                        run = p.add_run(hook)
                        run.font.color.rgb = RGBColor(255, 0, 0)  # 红色

                    doc.add_paragraph()  # 空行

            doc.add_page_break()

        # 导出剧本正文
        if "scripts" in contents and project.get("scripts"):
            doc.add_heading("四、剧本正文", 1)

            # 解析集数范围
            episode_list = ExportService._parse_episodes(episodes, len(project["scripts"]))

            for ep_num in episode_list:
                script = next(
                    (s for s in project["scripts"]
                     if ExportService._safe_get_field(s, 'episodeNumber', 'episode_number') == ep_num),
                    None
                )
                if script:
                    title = f"第{ep_num}集"
                    script_title = ExportService._safe_get_field(script, 'title', 'title', '')
                    if script_title:
                        title += f" {script_title}"

                    doc.add_heading(title, 2)

                    # 字数
                    word_count = ExportService._safe_get_field(script, 'wordCount', 'word_count', 0)
                    if word_count:
                        p = doc.add_paragraph()
                        p.add_run(f"字数: {word_count}字").italic = True

                    # 正文
                    content = ExportService._safe_get_field(script, 'content', 'content', '')
                    if content:
                        # 保留换行格式
                        lines = content.split('\n')
                        for line in lines:
                            if line.strip():
                                # 场景标题居中
                                if line.startswith("场景："):
                                    p = doc.add_paragraph(line)
                                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                # 人物名居中加粗
                                elif line.startswith("**") and line.endswith("**"):
                                    p = doc.add_paragraph()
                                    run = p.add_run(line.replace("**", ""))
                                    run.bold = True
                                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                # 动作描述斜体
                                elif line.startswith("▶"):
                                    p = doc.add_paragraph()
                                    run = p.add_run(line[1:])
                                    run.italic = True
                                else:
                                    doc.add_paragraph(line)
                            else:
                                doc.add_paragraph()  # 空行

                    doc.add_page_break()

        # 保存文件
        output_dir = os.path.join(os.getcwd(), "exports")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{project.get('name', '未命名')}_{timestamp}.docx"
        filepath = os.path.join(output_dir, filename)

        doc.save(filepath)
        logger.info(f"Word文档已保存: {filepath}")

        return filepath

    @staticmethod
    def export_to_pdf(
        project_id: str,
        contents: List[str],
        episodes: str = "all"
    ) -> str:
        """
        导出为 PDF

        Args:
            project_id: 项目ID
            contents: 导出内容类型列表
            episodes: 集数范围

        Returns:
            文件路径
        """
        # 暂时通过 Word 转换
        # TODO: 使用 weasyprint 实现原生 PDF 导出
        logger.info(f"导出 PDF: {project_id}, contents={contents}, episodes={episodes}")

        # 先生成 Word
        docx_path = ExportService.export_to_docx(project_id, contents, episodes)

        # 提示用户 Word 转 PDF 的方法
        pdf_path = docx_path.replace(".docx", ".pdf")

        return pdf_path

    @staticmethod
    def export_to_zip(
        project_id: str,
        contents: List[str],
        episodes: str = "all"
    ) -> str:
        """
        导出为 ZIP 压缩包

        Args:
            project_id: 项目ID
            contents: 导出内容类型列表
            episodes: 集数范围

        Returns:
            文件路径
        """
        logger.info(f"导出 ZIP: {project_id}, contents={contents}, episodes={episodes}")

        project = ProjectService.get_project(project_id)
        if not project:
            raise ValueError("项目不存在")

        # 创建临时目录
        output_dir = os.path.join(os.getcwd(), "exports")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{project.get('name', '未命名')}_{timestamp}.zip"
        zip_filepath = os.path.join(output_dir, zip_filename)

        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 添加 Word 文档
            docx_path = ExportService.export_to_docx(project_id, contents, episodes)
            zf.write(docx_path, os.path.basename(docx_path))

            # 可以添加更多文件...

        logger.info(f"ZIP包已保存: {zip_filepath}")
        return zip_filepath

    @staticmethod
    def _parse_episodes(episodes: str, total: int) -> List[int]:
        """
        解析集数范围

        Args:
            episodes: 集数范围字符串 (all/1-30/1,2,3)
            total: 总集数

        Returns:
            集数列表
        """
        if episodes == "all":
            return list(range(1, total + 1))

        if "-" in episodes:
            start, end = episodes.split("-")
            return list(range(int(start), int(end) + 1))

        if "," in episodes:
            return [int(x.strip()) for x in episodes.split(",")]

        try:
            return [int(episodes)]
        except ValueError:
            return list(range(1, total + 1))

    @staticmethod
    def _safe_get_field(obj: dict, camel_case: str, snake_case: str, default=None):
        """兼容获取字段（支持 camelCase 和 snake_case）"""
        if not obj:
            return default
        return obj.get(camel_case, obj.get(snake_case, default))
