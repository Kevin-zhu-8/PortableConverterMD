"""OCR 模块测试：文本清理 + Windows OCR 集成（无可用后端时自动跳过）"""
import os

import pytest

import ocr


# ------------------------------------------------------------ 纯函数

def test_clean_text_removes_spaces_between_cjk():
    """Windows OCR 会在汉字间插空格，必须还原（实测 "扫 描 件" -> "扫描件"）。"""
    assert ocr.clean_text("扫 描 件 中 文 识 别") == "扫描件中文识别"


def test_clean_text_keeps_latin_spacing_and_lines():
    raw = "Page 1 line 1: hello world\r\n\r\nPage 2 line 1: hello"
    out = ocr.clean_text(raw)
    assert out.splitlines()[0] == "Page 1 line 1: hello world"
    assert "Page 2 line 1: hello" in out
    assert "\r" not in out


def test_clean_text_collapses_repeated_spaces_and_blank_lines():
    assert ocr.clean_text("a    b\n\n\n   \nc") == "a b\nc"


def test_backend_label_is_readable():
    label = ocr.backend_label()
    assert label in ("不可用",) or "OCR" in label or "Tesseract" in label


# ------------------------------------------------------------ 集成（需要系统 OCR）

needs_ocr = pytest.mark.skipif(ocr.backend() == "", reason="本机没有可用的 OCR 后端")


@needs_ocr
def test_ocr_reads_english_text(tmp_path):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (900, 200), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 36)
    draw.text((30, 60), "Hello OCR engine 12345", fill="black", font=font)
    path = tmp_path / "en.png"
    img.save(path)

    text = ocr.recognize(Image.open(path))
    assert "Hello" in text and "12345" in text


@needs_ocr
def test_ocr_reads_chinese_without_inner_spaces(tmp_path):
    from PIL import Image, ImageDraw, ImageFont

    if not os.path.exists(r"C:\Windows\Fonts\msyh.ttc"):
        pytest.skip("缺少中文字体")
    img = Image.new("RGB", (1000, 200), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 40)
    draw.text((30, 60), "扫描件中文识别测试", fill="black", font=font)
    path = tmp_path / "cn.png"
    img.save(path)

    text = ocr.recognize(Image.open(path))
    assert "扫描件中文识别测试" in text          # 中间不应有空格
