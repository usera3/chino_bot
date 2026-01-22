"""
文档处理工具
支持读取和创建 Word、PDF、Excel 等文档
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
import os


# ==================== 读取 PDF 工具 ====================
class ReadPDFInput(BaseModel):
    """读取 PDF 输入"""
    file_path: str = Field(description="PDF 文件路径")
    max_pages: Optional[int] = Field(default=None, description="最多读取的页数，默认读取全部")


class ReadPDFTool(BaseTool):
    """读取 PDF 文件内容"""
    name: str = "read_pdf"
    description: str = """读取 PDF 文件的文本内容。

使用场景：
- 用户发送 PDF 文件并询问内容
- 用户说"读一下这个 PDF"
- 用户问"这个 PDF 讲的是什么"

参数：
- file_path: PDF 文件路径（必需）
- max_pages: 最多读取的页数（可选，默认全部）

返回：PDF 的文本内容"""
    args_schema: type[BaseModel] = ReadPDFInput
    
    def _run(self, file_path: str, max_pages: Optional[int] = None) -> str:
        """执行工具"""
        try:
            from PyPDF2 import PdfReader
            
            if not os.path.exists(file_path):
                return f"❌ 文件不存在: {file_path}"
            
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            
            # 确定要读取的页数
            pages_to_read = min(max_pages, total_pages) if max_pages else total_pages
            
            # 提取文本
            text_content = []
            for i in range(pages_to_read):
                page = reader.pages[i]
                text = page.extract_text()
                if text.strip():
                    text_content.append(f"[第 {i+1} 页]\n{text}")
            
            if not text_content:
                return f"❌ 无法从 PDF 中提取文本（可能是扫描版或图片 PDF）"
            
            result = "\n\n".join(text_content)
            
            # 添加摘要信息
            summary = f"📄 PDF 文档信息\n"
            summary += f"📁 文件：{os.path.basename(file_path)}\n"
            summary += f"📊 总页数：{total_pages}\n"
            summary += f"📖 已读取：{pages_to_read} 页\n"
            summary += f"{'='*50}\n\n"
            
            return summary + result
            
        except Exception as e:
            return f"❌ 读取 PDF 失败：{str(e)}"
    
    async def _arun(self, file_path: str, max_pages: Optional[int] = None) -> str:
        """异步执行"""
        return self._run(file_path, max_pages)


# ==================== 读取 Word 工具 ====================
class ReadWordInput(BaseModel):
    """读取 Word 输入"""
    file_path: str = Field(description="Word 文件路径（.docx）")


class ReadWordTool(BaseTool):
    """读取 Word 文档内容"""
    name: str = "read_word"
    description: str = """读取 Word 文档的文本内容。

使用场景：
- 用户发送 Word 文件并询问内容
- 用户说"读一下这个 Word"
- 用户问"这个文档写了什么"

参数：
- file_path: Word 文件路径（必需，.docx 格式）

返回：Word 的文本内容"""
    args_schema: type[BaseModel] = ReadWordInput
    
    def _run(self, file_path: str) -> str:
        """执行工具"""
        try:
            from docx import Document
            
            if not os.path.exists(file_path):
                return f"❌ 文件不存在: {file_path}"
            
            doc = Document(file_path)
            
            # 提取所有段落
            paragraphs = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            
            if not paragraphs:
                return f"❌ Word 文档为空或无法读取"
            
            # 添加摘要信息
            summary = f"📝 Word 文档信息\n"
            summary += f"📁 文件：{os.path.basename(file_path)}\n"
            summary += f"📊 段落数：{len(paragraphs)}\n"
            summary += f"{'='*50}\n\n"
            
            content = "\n\n".join(paragraphs)
            
            return summary + content
            
        except Exception as e:
            return f"❌ 读取 Word 失败：{str(e)}"
    
    async def _arun(self, file_path: str) -> str:
        """异步执行"""
        return self._run(file_path)


# ==================== 创建 Word 工具 ====================
class CreateWordInput(BaseModel):
    """创建 Word 输入"""
    file_path: str = Field(description="保存的文件路径")
    title: str = Field(description="文档标题")
    content: str = Field(description="文档内容（支持多段落，用 \\n\\n 分隔）")


class CreateWordTool(BaseTool):
    """创建 Word 文档"""
    name: str = "create_word"
    description: str = """创建一个新的 Word 文档。

使用场景：
- 用户说"创建一个 Word 文档"
- 用户说"帮我写个文档"
- 用户说"把这些内容保存成 Word"

参数：
- file_path: 保存的文件路径（必需）
- title: 文档标题（必需）
- content: 文档内容（必需，多段落用 \\n\\n 分隔）

返回：创建结果"""
    args_schema: type[BaseModel] = CreateWordInput
    
    def _run(self, file_path: str, title: str, content: str) -> str:
        """执行工具"""
        try:
            from docx import Document
            from docx.shared import Pt, RGBColor
            from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
            
            # 强制使用 Downloads 目录（NapCat 可以访问）
            # 无论传入什么路径，都只使用文件名，保存到 Downloads
            file_name = os.path.basename(file_path)
            downloads_dir = os.path.expanduser("~/Downloads")
            file_path = os.path.join(downloads_dir, file_name)
            print(f"⚠️ 文件将保存到: {file_path}")
            
            doc = Document()
            
            # 添加标题
            heading = doc.add_heading(title, level=1)
            heading.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            
            # 添加内容（按段落分割）
            paragraphs = content.split('\n\n')
            for para_text in paragraphs:
                if para_text.strip():
                    para = doc.add_paragraph(para_text.strip())
                    # 设置字体
                    for run in para.runs:
                        run.font.size = Pt(12)
            
            # 保存文档
            doc.save(file_path)
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            file_size_kb = file_size / 1024
            
            return f"✅ Word 文档创建成功！\n📁 文件：{file_path}\n📊 大小：{file_size_kb:.2f} KB\n📝 段落数：{len(paragraphs)}"
            
        except Exception as e:
            return f"❌ 创建 Word 失败：{str(e)}"
    
    async def _arun(self, file_path: str, title: str, content: str) -> str:
        """异步执行"""
        return self._run(file_path, title, content)


# ==================== 读取 Excel 工具 ====================
class ReadExcelInput(BaseModel):
    """读取 Excel 输入"""
    file_path: str = Field(description="Excel 文件路径")
    sheet_name: Optional[str] = Field(default=None, description="工作表名称，默认读取第一个")
    max_rows: Optional[int] = Field(default=100, description="最多读取的行数，默认 100")


class ReadExcelTool(BaseTool):
    """读取 Excel 表格内容"""
    name: str = "read_excel"
    description: str = """读取 Excel 表格的内容。

使用场景：
- 用户发送 Excel 文件并询问内容
- 用户说"读一下这个表格"
- 用户问"这个 Excel 有什么数据"

参数：
- file_path: Excel 文件路径（必需）
- sheet_name: 工作表名称（可选，默认第一个）
- max_rows: 最多读取的行数（可选，默认 100）

返回：Excel 的表格内容"""
    args_schema: type[BaseModel] = ReadExcelInput
    
    def _run(self, file_path: str, sheet_name: Optional[str] = None, max_rows: int = 100) -> str:
        """执行工具"""
        try:
            import pandas as pd
            
            if not os.path.exists(file_path):
                return f"❌ 文件不存在: {file_path}"
            
            # 读取 Excel
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=max_rows)
            else:
                df = pd.read_excel(file_path, nrows=max_rows)
            
            # 获取工作表信息
            xl_file = pd.ExcelFile(file_path)
            sheet_names = xl_file.sheet_names
            
            # 添加摘要信息
            summary = f"📊 Excel 表格信息\n"
            summary += f"📁 文件：{os.path.basename(file_path)}\n"
            summary += f"📋 工作表：{', '.join(sheet_names)}\n"
            summary += f"📏 当前表：{sheet_name or sheet_names[0]}\n"
            summary += f"📊 行数：{len(df)} / 列数：{len(df.columns)}\n"
            summary += f"{'='*50}\n\n"
            
            # 转换为字符串表格
            table_str = df.to_string(index=False, max_rows=max_rows)
            
            return summary + table_str
            
        except Exception as e:
            return f"❌ 读取 Excel 失败：{str(e)}"
    
    async def _arun(self, file_path: str, sheet_name: Optional[str] = None, max_rows: int = 100) -> str:
        """异步执行"""
        return self._run(file_path, sheet_name, max_rows)


# ==================== 创建 Excel 工具 ====================
class CreateExcelInput(BaseModel):
    """创建 Excel 输入"""
    file_path: str = Field(description="保存的文件路径")
    data: str = Field(description="表格数据（JSON 格式字符串，如：[{'姓名': '张三', '年龄': 25}, ...]）")
    sheet_name: Optional[str] = Field(default="Sheet1", description="工作表名称")


class CreateExcelTool(BaseTool):
    """创建 Excel 表格"""
    name: str = "create_excel"
    description: str = """创建一个新的 Excel 表格。

使用场景：
- 用户说"创建一个 Excel 表格"
- 用户说"把这些数据保存成表格"
- 用户提供表格数据要求保存

参数：
- file_path: 保存的文件路径（必需）
- data: 表格数据（必需，JSON 格式字符串）
- sheet_name: 工作表名称（可选，默认 Sheet1）

示例数据格式：
[
  {"姓名": "张三", "年龄": 25, "职位": "工程师"},
  {"姓名": "李四", "年龄": 30, "职位": "经理"}
]

返回：创建结果"""
    args_schema: type[BaseModel] = CreateExcelInput
    
    def _run(self, file_path: str, data: str, sheet_name: str = "Sheet1") -> str:
        """执行工具"""
        try:
            import pandas as pd
            import json
            
            # 强制使用 Downloads 目录（NapCat 可以访问）
            # 无论传入什么路径，都只使用文件名，保存到 Downloads
            file_name = os.path.basename(file_path)
            downloads_dir = os.path.expanduser("~/Downloads")
            file_path = os.path.join(downloads_dir, file_name)
            print(f"⚠️ 文件将保存到: {file_path}")
            
            # 解析 JSON 数据
            data_list = json.loads(data)
            
            if not isinstance(data_list, list):
                return f"❌ 数据格式错误：必须是列表格式"
            
            # 创建 DataFrame
            df = pd.DataFrame(data_list)
            
            # 保存为 Excel
            df.to_excel(file_path, sheet_name=sheet_name, index=False)
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            file_size_kb = file_size / 1024
            
            return f"✅ Excel 表格创建成功！\n📁 文件：{file_path}\n📊 大小：{file_size_kb:.2f} KB\n📏 行数：{len(df)} / 列数：{len(df.columns)}"
            
        except json.JSONDecodeError as e:
            return f"❌ JSON 解析失败：{str(e)}\n请确保数据格式正确"
        except Exception as e:
            return f"❌ 创建 Excel 失败：{str(e)}"
    
    async def _arun(self, file_path: str, data: str, sheet_name: str = "Sheet1") -> str:
        """异步执行"""
        return self._run(file_path, data, sheet_name)


# ==================== Word 转 PDF 工具 ====================
class ConvertWordToPDFInput(BaseModel):
    """Word 转 PDF 输入"""
    word_path: str = Field(description="Word 文件路径（.docx）")
    pdf_path: Optional[str] = Field(default=None, description="PDF 保存路径（可选，默认同名）")


class ConvertWordToPDFTool(BaseTool):
    """将 Word 文档转换为 PDF"""
    name: str = "convert_word_to_pdf"
    description: str = """将 Word 文档转换为 PDF 格式。

使用场景：
- 用户说"把这个 Word 转成 PDF"
- 用户说"转换成 PDF 格式"
- 用户说"生成 PDF 版本"

参数：
- word_path: Word 文件路径（必需，.docx 格式）
- pdf_path: PDF 保存路径（可选，默认同名同目录）

返回：转换结果"""
    args_schema: type[BaseModel] = ConvertWordToPDFInput
    
    def _run(self, word_path: str, pdf_path: Optional[str] = None) -> str:
        """执行工具"""
        try:
            from docx import Document
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
            
            # 检查 Word 文件是否存在
            if not os.path.exists(word_path):
                return f"❌ Word 文件不存在: {word_path}"
            
            # 如果没有指定 PDF 路径，使用同名文件
            if not pdf_path:
                pdf_path = os.path.splitext(word_path)[0] + ".pdf"
            
            # 确保 PDF 保存在 Downloads 目录（NapCat 可以访问）
            pdf_name = os.path.basename(pdf_path)
            downloads_dir = os.path.expanduser("~/Downloads")
            pdf_path = os.path.join(downloads_dir, pdf_name)
            
            print(f"⚠️ 正在转换: {word_path} -> {pdf_path}")
            
            # 注册中文字体（使用系统自带的中文字体）
            # macOS 系统字体路径
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",  # macOS 苹方字体
                "/System/Library/Fonts/STHeiti Light.ttc",  # 华文黑体
                "/System/Library/Fonts/Supplemental/Songti.ttc",  # 宋体
            ]
            
            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                        font_registered = True
                        print(f"✅ 已注册中文字体: {font_path}")
                        break
                    except Exception as e:
                        print(f"⚠️ 注册字体失败 {font_path}: {e}")
                        continue
            
            if not font_registered:
                return f"❌ 无法找到中文字体，PDF 转换可能出现乱码"
            
            # 读取 Word 文档
            doc = Document(word_path)
            
            # 创建 PDF
            pdf = SimpleDocTemplate(pdf_path, pagesize=A4)
            story = []
            
            # 创建支持中文的样式
            styles = getSampleStyleSheet()
            
            # 正文样式
            normal_style = ParagraphStyle(
                'ChineseNormal',
                parent=styles['Normal'],
                fontName='ChineseFont',
                fontSize=12,
                leading=18,
                alignment=TA_LEFT
            )
            
            # 标题样式
            heading_style = ParagraphStyle(
                'ChineseHeading',
                parent=styles['Heading1'],
                fontName='ChineseFont',
                fontSize=18,
                leading=24,
                alignment=TA_CENTER,
                spaceAfter=12
            )
            
            # 提取 Word 内容并添加到 PDF
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    # 判断是否是标题
                    if para.style.name.startswith('Heading'):
                        p = Paragraph(text, heading_style)
                    else:
                        p = Paragraph(text, normal_style)
                    story.append(p)
                    story.append(Spacer(1, 0.2*inch))
            
            # 如果没有内容
            if not story:
                return f"❌ Word 文档为空，无法转换"
            
            # 生成 PDF
            pdf.build(story)
            
            # 检查转换是否成功
            if not os.path.exists(pdf_path):
                return f"❌ PDF 转换失败：文件未生成"
            
            # 获取文件大小
            file_size = os.path.getsize(pdf_path)
            file_size_kb = file_size / 1024
            
            return f"""✅ Word 转 PDF 成功！
📁 原文件：{os.path.basename(word_path)}
📄 PDF 文件：{pdf_path}
📊 大小：{file_size_kb:.2f} KB
✨ 已支持中文显示"""
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ Word 转 PDF 失败：{str(e)}"
    
    async def _arun(self, word_path: str, pdf_path: Optional[str] = None) -> str:
        """异步执行"""
        return self._run(word_path, pdf_path)


# ==================== PDF 转 Word 工具 ====================
class ConvertPDFToWordInput(BaseModel):
    """PDF 转 Word 输入"""
    pdf_path: str = Field(description="PDF 文件路径")
    word_path: Optional[str] = Field(default=None, description="Word 保存路径（可选，默认同名）")


class ConvertPDFToWordTool(BaseTool):
    """将 PDF 转换为 Word 文档"""
    name: str = "convert_pdf_to_word"
    description: str = """将 PDF 文件转换为可编辑的 Word 文档。

使用场景：
- 用户说"把这个 PDF 转成 Word"
- 用户说"转换成 Word 格式"
- 用户说"生成可编辑的文档"

参数：
- pdf_path: PDF 文件路径（必需）
- word_path: Word 保存路径（可选，默认同名同目录）

返回：转换结果"""
    args_schema: type[BaseModel] = ConvertPDFToWordInput
    
    def _run(self, pdf_path: str, word_path: Optional[str] = None) -> str:
        """执行工具"""
        try:
            from pdf2docx import Converter
            
            # 检查 PDF 文件是否存在
            if not os.path.exists(pdf_path):
                return f"❌ PDF 文件不存在: {pdf_path}"
            
            # 如果没有指定 Word 路径，使用同名文件
            if not word_path:
                word_path = os.path.splitext(pdf_path)[0] + ".docx"
            
            # 确保 Word 保存在 Downloads 目录（NapCat 可以访问）
            word_name = os.path.basename(word_path)
            downloads_dir = os.path.expanduser("~/Downloads")
            word_path = os.path.join(downloads_dir, word_name)
            
            print(f"⚠️ 正在转换: {pdf_path} -> {word_path}")
            
            # 转换 PDF 到 Word
            cv = Converter(pdf_path)
            cv.convert(word_path)
            cv.close()
            
            # 检查转换是否成功
            if not os.path.exists(word_path):
                return f"❌ Word 转换失败：文件未生成"
            
            # 获取文件大小
            file_size = os.path.getsize(word_path)
            file_size_kb = file_size / 1024
            
            return f"""✅ PDF 转 Word 成功！
📁 原文件：{os.path.basename(pdf_path)}
📝 Word 文件：{word_path}
📊 大小：{file_size_kb:.2f} KB
✨ 已转换为可编辑格式"""
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ PDF 转 Word 失败：{str(e)}"
    
    async def _arun(self, pdf_path: str, word_path: Optional[str] = None) -> str:
        """异步执行"""
        return self._run(pdf_path, word_path)


# ==================== 工具列表 ====================
def get_all_document_tools():
    """获取所有文档处理工具"""
    return [
        ReadPDFTool(),
        ReadWordTool(),
        CreateWordTool(),
        ReadExcelTool(),
        CreateExcelTool(),
        ConvertWordToPDFTool(),
        ConvertPDFToWordTool(),
    ]
