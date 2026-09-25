"""GUI + 后台线程集成测试

覆盖旧实现最危险的一类问题：后台线程异常导致 conversion_done 不发射、
按钮永久禁用。测试用 offscreen 平台跑真实 MainWindow + ConvertWorker。
"""
import os

import pytest

pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QThread, QTimer, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import ui  # noqa: E402
import settings  # noqa: E402
from ui import ROLE_STATE  # noqa: E402
from worker import ConvertWorker  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _run_conversion(window, monkeypatch, timeout_ms=60000):
    """走真实的 _start_conversion 装配流程，再启动线程并等待 conversion_done。

    先把 ConvertWorker.start 打桩，避免「线程已跑完但监听还没接上」的竞态。
    """
    loop = QEventLoop()
    result = {}

    def _done(results):
        result["results"] = results
        loop.quit()

    monkeypatch.setattr(ConvertWorker, "start", lambda self: None)
    window._start_conversion()
    assert window.worker is not None, "worker not created"
    window.worker.conversion_done.connect(_done)
    QTimer.singleShot(timeout_ms, loop.quit)
    QThread.start(window.worker)          # 装配完成后再真正启动线程
    loop.exec()
    assert "results" in result, "timeout: conversion_done never emitted"
    return result["results"]


def test_conversion_releases_ui_on_success(qapp, tmp_path, monkeypatch):
    """成功路径：转换完成、按钮复位、输出落盘。"""
    monkeypatch.setattr(ui._CompletionDialog, "exec", lambda self: 0)

    src = tmp_path / "a.txt"
    src.write_text("hello", encoding="utf-8")
    window = ui.MainWindow()
    window._add_files([str(src)])

    results = _run_conversion(window, monkeypatch)

    assert len(results) == 1 and results[0]["error"] is None
    assert os.path.exists(results[0]["output"])
    assert window.btn_convert.isEnabled() and window.drop_zone.isEnabled()
    window.close()


def test_conversion_releases_ui_on_failure(qapp, tmp_path, monkeypatch):
    """失败路径：线程必须仍然通知 UI 复位（旧实现在这里会永久卡死）。"""
    monkeypatch.setattr(ui._CompletionDialog, "exec", lambda self: 0)

    bad = tmp_path / "broken.xyz"
    bad.write_bytes(b"\x00\x01")
    window = ui.MainWindow()
    window._add_files([str(bad)])

    results = _run_conversion(window, monkeypatch)

    assert len(results) == 1 and results[0]["error"] is not None
    assert "暂不支持的文件类型" in results[0]["error"]
    assert window.btn_convert.isEnabled() and window.drop_zone.isEnabled()
    assert not os.path.exists(tmp_path / "md_output" / "broken.md")   # 不留空文件
    window.close()


def test_same_basename_rows_do_not_cross_talk(qapp, tmp_path, monkeypatch):
    """同名文件（不同目录）必须各自更新自己那一行。"""
    monkeypatch.setattr(ui._CompletionDialog, "exec", lambda self: 0)

    d1, d2 = tmp_path / "one", tmp_path / "two"
    d1.mkdir(); d2.mkdir()
    (d1 / "report.txt").write_text("first", encoding="utf-8")
    (d2 / "report.txt").write_text("second", encoding="utf-8")

    window = ui.MainWindow()
    window._add_files([str(d1 / "report.txt"), str(d2 / "report.txt")])
    results = _run_conversion(window, monkeypatch)

    assert len(results) == 2
    heads = [open(r["output"], encoding="utf-8").read() for r in results]
    assert heads == ["first", "second"]
    assert all(window.file_list.item(i).data(ROLE_STATE) == "done" for i in range(2))
    window.close()


def test_worker_uses_per_file_output_dir(qapp, tmp_path, monkeypatch):
    """默认（output 文件夹）：每个文件写到各自目录旁的 output 文件夹。"""
    monkeypatch.setattr(ui._CompletionDialog, "exec", lambda self: 0)
    settings.set_custom_dir("")
    settings.set_output_mode(settings.MODE_SUBFOLDER)

    d1, d2 = tmp_path / "x", tmp_path / "y"
    d1.mkdir(); d2.mkdir()
    (d1 / "a.txt").write_text("A", encoding="utf-8")
    (d2 / "b.txt").write_text("B", encoding="utf-8")

    window = ui.MainWindow()
    window._add_files([str(d1 / "a.txt"), str(d2 / "b.txt")])
    results = _run_conversion(window, monkeypatch)

    outs = sorted(os.path.dirname(r["output"]) for r in results)
    assert outs == sorted([str(d1 / settings.SUBFOLDER_NAME),
                           str(d2 / settings.SUBFOLDER_NAME)])
    window.close()


def test_worker_same_dir_mode_writes_next_to_source(qapp, tmp_path, monkeypatch):
    """设置为「与源文件同目录」时，.md 直接落在源文件旁。"""
    monkeypatch.setattr(ui._CompletionDialog, "exec", lambda self: 0)
    settings.set_custom_dir("")
    settings.set_output_mode(settings.MODE_SAME_DIR)
    try:
        src = tmp_path / "same.txt"
        src.write_text("hello", encoding="utf-8")
        window = ui.MainWindow()
        window._add_files([str(src)])
        results = _run_conversion(window, monkeypatch)

        assert results[0]["output"] == str(tmp_path / "same.md")
        window.close()
    finally:
        settings.set_output_mode(settings.MODE_SUBFOLDER)


def test_custom_dir_overrides_mode(qapp, tmp_path, monkeypatch):
    """设置了自定义目录时，两种模式都让位给自定义目录。"""
    monkeypatch.setattr(ui._CompletionDialog, "exec", lambda self: 0)
    target = tmp_path / "custom"
    settings.set_custom_dir(str(target))
    try:
        src = tmp_path / "c.txt"
        src.write_text("x", encoding="utf-8")
        window = ui.MainWindow()
        window._add_files([str(src)])
        results = _run_conversion(window, monkeypatch)

        assert os.path.dirname(results[0]["output"]) == str(target)
        window.close()
    finally:
        settings.set_custom_dir("")


# ------------------------------------------------------------ 新交互

def test_delete_key_removes_selected_row(qapp, tmp_path):
    """Delete 移除选中行，列表与内部路径保持同步。"""
    paths = []
    for i in range(3):
        p = tmp_path / f"f{i}.txt"
        p.write_text("x", encoding="utf-8")
        paths.append(str(p))

    window = ui.MainWindow()
    window._add_files(paths)
    assert window.file_list.count() == 3

    window.file_list.setCurrentRow(1)
    QTest.keyClick(window.file_list, Qt.Key.Key_Delete)

    assert window.file_list.count() == 2
    assert len(window.file_paths) == 2
    assert paths[1] not in window.file_paths
    assert window.lbl_status.text().startswith("2 个文件")
    window.close()


def test_space_toggles_checkbox(qapp, tmp_path):
    """空格切换勾选状态（自绘复选框的键盘可达性）。"""
    p = tmp_path / "k.txt"
    p.write_text("x", encoding="utf-8")

    window = ui.MainWindow()
    window._add_files([str(p)])
    window.file_list.setCurrentRow(0)
    assert window._get_checked_items(), "新加入的文件默认勾选"

    QTest.keyClick(window.file_list, Qt.Key.Key_Space)
    assert not window._get_checked_items(), "空格应取消勾选"

    QTest.keyClick(window.file_list, Qt.Key.Key_Space)
    assert len(window._get_checked_items()) == 1, "空格应重新勾选"
    window.close()


def test_folder_drop_expands_supported_files_only(qapp, tmp_path):
    """拖入文件夹时展开一层，只收支持的类型。"""
    folder = tmp_path / "batch"
    folder.mkdir()
    (folder / "a.txt").write_text("A", encoding="utf-8")
    (folder / "b.docx").write_bytes(b"fake")
    (folder / "c.bin").write_bytes(b"\x00\x01")
    (folder / "d.md").write_text("D", encoding="utf-8")

    window = ui.MainWindow()
    window._add_files([str(folder)])

    names = sorted(os.path.basename(p) for p in window.file_paths)
    assert names == ["a.txt", "b.docx", "d.md"]
    window.close()


def test_drop_zone_adapts_to_file_count(qapp, tmp_path):
    """空态拖放区展开，有文件时收成细条（小巧的关键）。"""
    p = tmp_path / "z.txt"
    p.write_text("x", encoding="utf-8")

    window = ui.MainWindow()
    window.show()
    qapp.processEvents()
    assert window.drop_zone.height() >= ui.DropZone.EXPANDED_MIN_H
    assert window.file_list.isHidden()

    window._add_files([str(p)])
    qapp.processEvents()
    assert window.drop_zone.height() == ui.DropZone.COMPACT_H
    assert window.file_list.isVisible()
    window.close()


# ------------------------------------------------------------ 标题栏与设置面板

def test_title_bar_buttons_emit_signals(qapp):
    from widgets import TitleBar

    bar = TitleBar()
    clicks = []
    bar.settings_clicked.connect(lambda: clicks.append("settings"))
    bar.minimize_clicked.connect(lambda: clicks.append("min"))
    bar.maximize_clicked.connect(lambda: clicks.append("max"))
    bar.close_clicked.connect(lambda: clicks.append("close"))

    bar.btn_settings.click()
    bar.btn_min.click()
    bar.btn_max.click()
    bar.btn_close.click()
    assert clicks == ["settings", "min", "max", "close"]


def test_title_bar_supports_drag_and_double_click(qapp):
    from PySide6.QtCore import QPoint

    from widgets import TitleBar

    bar = TitleBar()
    events = []
    bar.drag_started.connect(lambda: events.append("drag"))
    bar.double_clicked.connect(lambda: events.append("dbl"))

    QTest.mousePress(bar, Qt.MouseButton.LeftButton, pos=QPoint(240, 20))
    QTest.mouseDClick(bar, Qt.MouseButton.LeftButton, pos=QPoint(240, 20))
    assert "drag" in events and "dbl" in events


def test_main_window_has_settings_button_on_title_bar(qapp):
    window = ui.MainWindow()
    assert window.title_bar.btn_settings.isVisible() or not window.isVisible()
    assert window.windowTitle() == "PortableConverterMD"
    window.close()


def test_settings_panel_switches_output_mode_and_logging(qapp):
    from settings_panel import SettingsPanel

    panel = SettingsPanel()
    panel.seg_mode.set_index(0, animate=False)
    assert settings.output_mode() == settings.MODE_SAME_DIR
    panel.seg_mode.set_index(1, animate=False)
    assert settings.output_mode() == settings.MODE_SUBFOLDER

    panel.sw_log.setChecked(False)
    assert settings.logging_enabled() is False
    panel.sw_log.setChecked(True)
    assert settings.logging_enabled() is True
    panel.close()


def test_settings_panel_background_toggle_persists(qapp):
    from settings_panel import SettingsPanel

    panel = SettingsPanel()
    panel.sw_background.setChecked(True)
    assert settings.keep_in_background() is True
    panel.sw_background.setChecked(False)
    assert settings.keep_in_background() is False
    panel.close()
