"""PortableConverterMD 核心转换模块的单元测试"""
import os
import tempfile
import pytest

# 待实现
from main import convert_file


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
