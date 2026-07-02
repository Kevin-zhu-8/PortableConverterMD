"""PortableConverterMD 核心转换模块的单元测试"""
import os
import tempfile
import pytest

# 待实现
from converter import convert_file


def test_convert_txt_to_markdown():
    """纯文本文件应成功转换为 .md"""
    with tempfile.TemporaryDirectory() as tmpdir:
        txt_path = os.path.join(tmpdir, "hello.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Hello World")

        out_dir = os.path.join(tmpdir, "md_output")
        result = convert_file(txt_path, out_dir)

        assert os.path.exists(result)
        assert result.endswith(".md")
        with open(result, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Hello World" in content


def test_convert_creates_output_dir():
    """输出目录不存在时应自动创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        txt_path = os.path.join(tmpdir, "test.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("content")

        out_dir = os.path.join(tmpdir, "nonexistent", "md_output")
        result = convert_file(txt_path, out_dir)

        assert os.path.isdir(out_dir)
        assert os.path.exists(result)


def test_convert_same_filename_md_extension():
    """输出文件名应与输入同名，扩展名变为 .md"""
    with tempfile.TemporaryDirectory() as tmpdir:
        txt_path = os.path.join(tmpdir, "myfile.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("test")

        out_dir = os.path.join(tmpdir, "md_output")
        result = convert_file(txt_path, out_dir)

        assert os.path.basename(result) == "myfile.md"


def test_empty_pdf_falls_back_to_ocr():
    """空内容 PDF 应尝试 OCR 回退（空白页导致识别失败）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "empty.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
                    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
                    b"0000000058 00000 n \n0000000115 00000 n \n"
                    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF")

        out_dir = os.path.join(tmpdir, "md_output")

        # 内置 Tesseract 可用但空白 PDF 无法 OCR
        with pytest.raises(RuntimeError, match="未能从 PDF 中识别"):
            convert_file(pdf_path, out_dir)
