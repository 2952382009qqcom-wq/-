"""文档解析 - 支持 TXT / PDF / DOCX"""

from __future__ import annotations
import io


def parse_txt(content: bytes) -> str:
    """解析纯文本"""
    for encoding in ["utf-8", "gbk", "gb2312", "gb18030"]:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def parse_pdf(content: bytes) -> str:
    """解析 PDF 提取文字"""
    from PyPDF2 import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def parse_docx(content: bytes) -> str:
    """解析 DOCX 提取文字"""
    from docx import Document

    doc = Document(io.BytesIO(content))
    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)
    return "\n".join(paragraphs)


def parse_file(filename: str, content: bytes) -> str:
    """根据文件扩展名自动选择解析器"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("txt", "md", ""):
        return parse_txt(content)
    elif ext == "pdf":
        return parse_pdf(content)
    elif ext == "docx":
        return parse_docx(content)
    else:
        # 不支持的格式，尝试按文本解析
        return parse_txt(content)


def parse_upload(file_storage) -> tuple[str, str]:
    """解析 Flask FileStorage，返回 (filename, text)"""
    filename = file_storage.filename or "upload.txt"
    content = file_storage.read()
    text = parse_file(filename, content)
    return filename, text
