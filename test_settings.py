"""设置与类型判定测试"""
import os

import pytest

import settings
from main import split_supported


@pytest.fixture(autouse=True)
def _clean_settings():
    """每个用例前后都回到默认设置，避免互相影响。"""
    settings.set_custom_dir("")
    settings.set_output_mode(settings.MODE_SUBFOLDER)
    yield
    settings.set_custom_dir("")
    settings.set_output_mode(settings.MODE_SUBFOLDER)


# ------------------------------------------------------------ 输出位置

def test_output_dir_same_dir(tmp_path):
    src = tmp_path / "report.docx"
    assert settings.output_dir_for(str(src), mode=settings.MODE_SAME_DIR) == str(tmp_path)


def test_output_dir_subfolder(tmp_path):
    src = tmp_path / "report.docx"
    expected = str(tmp_path / settings.SUBFOLDER_NAME)
    assert settings.output_dir_for(str(src), mode=settings.MODE_SUBFOLDER) == expected
    assert settings.SUBFOLDER_NAME == "output"


def test_output_dir_custom_overrides_mode(tmp_path):
    src = tmp_path / "report.docx"
    custom = str(tmp_path / "elsewhere")
    assert settings.output_dir_for(str(src), mode=settings.MODE_SAME_DIR, custom=custom) == custom
    assert settings.output_dir_for(str(src), mode=settings.MODE_SUBFOLDER, custom=custom) == custom


def test_output_mode_persists():
    settings.set_output_mode(settings.MODE_SAME_DIR)
    assert settings.output_mode() == settings.MODE_SAME_DIR
    settings.set_output_mode(settings.MODE_SUBFOLDER)
    assert settings.output_mode() == settings.MODE_SUBFOLDER


def test_invalid_mode_falls_back_to_subfolder():
    settings.set_output_mode("nonsense")
    assert settings.output_mode() == settings.MODE_SUBFOLDER


def test_mode_labels_are_readable():
    assert "同目录" in settings.mode_label(settings.MODE_SAME_DIR)
    assert settings.SUBFOLDER_NAME in settings.mode_label(settings.MODE_SUBFOLDER)


# ------------------------------------------------------------ 开关持久化

def test_switches_round_trip():
    settings.set_keep_in_background(True)
    assert settings.keep_in_background() is True
    settings.set_keep_in_background(False)
    assert settings.keep_in_background() is False

    settings.set_logging_enabled(False)
    assert settings.logging_enabled() is False
    settings.set_logging_enabled(True)
    assert settings.logging_enabled() is True


def test_autostart_command_points_to_this_app():
    cmd = settings.autostart_command()
    assert cmd.startswith('"')
    assert "main.py" in cmd or cmd.endswith('.exe"')


# ------------------------------------------------------------ 右键类型判定

def test_split_supported_separates_types(tmp_path):
    good = [str(tmp_path / "a.docx"), str(tmp_path / "b.pdf"), str(tmp_path / "c.png")]
    bad = [str(tmp_path / "d.mp3"), str(tmp_path / "e.doc"), str(tmp_path / "f.exe")]
    supported, unsupported = split_supported(good + bad)
    assert supported == good
    assert unsupported == bad


def test_split_supported_handles_empty_and_extensionless(tmp_path):
    supported, unsupported = split_supported([])
    assert supported == [] and unsupported == []
    supported, unsupported = split_supported([str(tmp_path / "noext")])
    assert supported == [] and len(unsupported) == 1


def test_supported_extensions_cover_office_and_pdf():
    import engine
    for ext in (".docx", ".xlsx", ".pptx", ".pdf", ".txt", ".csv", ".json", ".html", ".zip"):
        assert engine.supports("x" + ext)
    for ext in (".doc", ".xls", ".ppt", ".mp3", ".exe", ""):
        assert not engine.supports("x" + ext)


# ------------------------------------------------------------ 安装脚本一致性

def _read_iss() -> str:
    import pathlib
    return (pathlib.Path(__file__).resolve().parent / "setup.iss").read_text(encoding="utf-8")


def test_iss_registers_context_menu_for_every_supported_extension():
    """右键菜单按类型注册，且必须覆盖 engine.SUPPORTED_EXT 里的每个扩展名。"""
    import engine

    iss = _read_iss()
    missing = [e for e in engine.SUPPORTED_EXT
               if f"SystemFileAssociations\\{e}\\shell" not in iss]
    assert not missing, f"setup.iss 缺少这些扩展名的右键菜单注册：{missing}"


def test_iss_does_not_use_wildcard_context_menu():
    """不能再出现对所有文件都生效的 *\\shell 注册项。"""
    iss = _read_iss()
    for line in iss.splitlines():
        stripped = line.strip()
        if stripped.startswith("Root:") and "\\*\\shell" in stripped:
            raise AssertionError(f"setup.iss 仍存在通配右键项：{stripped}")
    assert "[Code]" in iss and "RegDeleteKeyIncludingSubkeys" in iss


def test_iss_has_command_for_each_verb():
    import engine

    iss = _read_iss()
    for ext in engine.SUPPORTED_EXT:
        assert f"SystemFileAssociations\\{ext}\\shell\\{{#VerbKey}}\\command" in iss


def test_iss_declares_non_admin_and_min_version():
    iss = _read_iss()
    assert "PrivilegesRequiredOverridesAllowed=dialog" in iss   # 允许非管理员按用户安装
    assert "ChangesAssociations=yes" in iss                     # 外壳立即刷新
    assert "MinVersion=10.0.17763" in iss                        # Windows OCR 要求
    assert "ArchitecturesInstallIn64BitMode=x64compatible" in iss
