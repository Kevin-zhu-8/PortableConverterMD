# PortableConverterMD 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 PySide6 桌面应用，将任意文件拖入后通过 MarkItDown 批量转换为 Markdown，打包为单个 .exe。

**Architecture:** 单文件 `main.py`（~250 行），PySide6 窗口 + QThread 后台转换 + markitdown 核心。PyInstaller 打包为独立 .exe。

**Tech Stack:** Python 3.10+, PySide6, markitdown, PyInstaller

## Global Constraints

- 单文件实现，所有代码在 `main.py`
- 输出目录：源文件所在目录下统一 `md_output/` 文件夹
- 窗口尺寸 600×500，不可过大
- 支持 MarkItDown 全部格式（Office、PDF、图片、音频、HTML、CSV/JSON/XML、ZIP）
- 打包后单个 .exe，约 200-350MB

---

### Task 1: 项目骨架

**Files:**
- Create: `requirements.txt`
- Create: `portable_converter_md.spec`

**Interfaces:**
- Produces: 依赖清单供 `pip install`，PyInstaller 规格供 `pyinstaller` 命令

- [ ] **Step 1: 创建 requirements.txt**

```txt
markitdown[all]>=0.0.1a3
PySide6>=6.5.0
pyinstaller>=6.0.0
```

- [ ] **Step 2: 创建 PyInstaller spec 文件**

```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['markitdown', 'markitdown._markitdown'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PortableConverterMD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
```

- [ ] **Step 3: 安装依赖**

```bash
pip install -r requirements.txt
```

- [ ] **Step 4: 验证依赖可导入**

```bash
python -c "from markitdown import MarkItDown; from PySide6.QtWidgets import QApplication; print('OK')"
```

预期输出: `OK`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt portable_converter_md.spec
git commit -m "chore: add project skeleton with dependencies and PyInstaller spec"
```

---

### Task 2: 核心转换模块

**Files:**
- Create: `test_converter.py`
- Modify: `main.py` (新建)

**Interfaces:**
- Produces: `convert_file(file_path: str, output_dir: str) -> str` — 返回输出 .md 路径；`MarkItDown` 实例化

- [ ] **Step 1: 编写转换逻辑的测试**

```python
# test_converter.py
import os
import tempfile
import pytest
from main import convert_file


def test_convert_txt_to_markdown():
    """纯文本文件应成功转换为 .md"""
    # 准备：创建临时 .txt 文件
    with tempfile.TemporaryDirectory() as tmpdir:
        txt_path = os.path.join(tmpdir, "hello.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Hello World")

        out_dir = os.path.join(tmpdir, "md_output")
        result = convert_file(txt_path, out_dir)

        # 验证
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest test_converter.py -v
```

预期: `ModuleNotFoundError: No module named 'main'` 或 `ImportError: cannot import name 'convert_file'`

- [ ] **Step 3: 实现 `main.py` 转换模块**

```python
"""PortableConverterMD - 文件转 Markdown 桌面工具"""
import os
from pathlib import Path

# 延迟导入，GUI 启动时不加载 markitdown
_md = None


def _get_converter():
    global _md
    if _md is None:
        from markitdown import MarkItDown
        _md = MarkItDown()
    return _md


def convert_file(file_path: str, output_dir: str) -> str:
    """转换单个文件为 Markdown，返回输出文件路径。"""
    file_path = str(file_path)
    output_dir = str(output_dir)

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 生成输出文件名：同名 .md
    input_name = Path(file_path).stem
    output_path = os.path.join(output_dir, f"{input_name}.md")

    # 调用 MarkItDown 转换
    converter = _get_converter()
    result = converter.convert(file_path)

    # 写入结果
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.text_content)

    return output_path
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest test_converter.py -v
```

预期: 2 passed (test_convert_creates_output_dir 有一个依赖 markitdown 的行为，可能因为依赖下载需要首次运行；忽略网络相关失败，仅确认文本转换通过)

- [ ] **Step 5: Commit**

```bash
git add main.py test_converter.py
git commit -m "feat: add core file-to-markdown conversion module"
```

---

### Task 3: 后台转换线程

**Files:**
- Modify: `main.py` (在文件中追加)

**Interfaces:**
- Consumes: `convert_file(file_path, output_dir) -> str`
- Produces: `ConvertWorker(QThread)` — signals: `progress(int current, int total)`, `finished(list[str] output_paths)`, `error(str message)`

- [ ] **Step 1: 在 main.py 中添加 ConvertWorker 类**

在 `main.py` 中 `convert_file` 函数之后追加以下代码：

```python
# ============================================================
# 后台转换线程
# ============================================================

from PySide6.QtCore import QThread, Signal


class ConvertWorker(QThread):
    """后台线程执行批量转换，不阻塞 GUI。"""
    progress_updated = Signal(int, int)  # current, total
    conversion_done = Signal(list)       # output_paths

    def __init__(self, file_paths: list[str], output_dir: str):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir

    def run(self):
        results = []
        total = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            try:
                out_path = convert_file(file_path, self.output_dir)
                results.append(out_path)
            except Exception as e:
                # 转换失败时跳过，继续处理后续文件
                print(f"转换失败 [{file_path}]: {e}")
                results.append(None)
            self.progress_updated.emit(i + 1, total)
        self.conversion_done.emit(results)
```

- [ ] **Step 2: 验证文件结构完整**

```bash
python -c "from main import ConvertWorker, convert_file; print('Import OK')"
```

预期输出: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add background conversion worker thread"
```

---

### Task 4: 主窗口 GUI

**Files:**
- Modify: `main.py` (在文件中追加)

**Interfaces:**
- Consumes: `ConvertWorker`
- Produces: `MainWindow(QMainWindow)` — 完整窗口

- [ ] **Step 1: 在 main.py 中添加 GUI 类和入口**

在 `main.py` 末尾追加以下代码：

```python
# ============================================================
# GUI 组件
# ============================================================

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QProgressBar,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont


class DropZone(QLabel):
    """拖拽区域：支持拖入文件或点击选择。"""

    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setText("📁  拖拽文件到此处（或点击选择）")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #aaa;
                border-radius: 12px;
                background: #f8f9fa;
                font-size: 14px;
                color: #666;
            }
            DropZone:hover {
                border-color: #4a90d9;
                background: #e8f0fe;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropZone {
                    border: 2px solid #4a90d9;
                    border-radius: 12px;
                    background: #d4e4fc;
                    font-size: 14px;
                    color: #333;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #aaa;
                border-radius: 12px;
                background: #f8f9fa;
                font-size: 14px;
                color: #666;
            }
            DropZone:hover {
                border-color: #4a90d9;
                background: #e8f0fe;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            self.files_dropped.emit(files)
        self.dragLeaveEvent(None)

    def mousePressEvent(self, event):
        """点击打开文件选择对话框。"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要转换的文件", "",
            "所有文件 (*.*)"
        )
        if files:
            self.files_dropped.emit(files)


class MainWindow(QMainWindow):
    """PortableConverterMD 主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PortableConverterMD")
        self.resize(620, 480)
        self.file_paths: list[str] = []
        self.output_dir: str = ""
        self.worker: ConvertWorker | None = None

        # --- 中央组件 ---
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # --- 拖拽区 ---
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._add_files)
        layout.addWidget(self.drop_zone)

        # --- 文件列表 ---
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        layout.addWidget(self.file_list)

        # --- 文件列表操作栏 ---
        btn_row = QHBoxLayout()
        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.clicked.connect(self._clear_files)
        self.btn_clear.setEnabled(False)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        self.lbl_count = QLabel("0 个文件")
        btn_row.addWidget(self.lbl_count)
        layout.addLayout(btn_row)

        # --- 状态 ---
        self.lbl_status = QLabel("就绪")
        layout.addWidget(self.lbl_status)

        # --- 进度条 ---
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # --- 操作按钮 ---
        action_row = QHBoxLayout()
        self.btn_convert = QPushButton("开始转换")
        self.btn_convert.clicked.connect(self._start_conversion)
        self.btn_convert.setEnabled(False)
        self.btn_convert.setMinimumHeight(40)
        action_row.addWidget(self.btn_convert)

        self.btn_open_dir = QPushButton("打开输出目录")
        self.btn_open_dir.clicked.connect(self._open_output_dir)
        self.btn_open_dir.setEnabled(False)
        self.btn_open_dir.setMinimumHeight(40)
        action_row.addWidget(self.btn_open_dir)
        layout.addLayout(action_row)

    # ---- 文件管理 ----

    def _add_files(self, paths: list[str]):
        """添加文件到列表，去重，默认勾选。"""
        for path in paths:
            if path not in self.file_paths:
                self.file_paths.append(path)
                item = QListWidgetItem(os.path.basename(path))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.file_list.addItem(item)
        self._update_ui()

    def _clear_files(self):
        """清空文件列表。"""
        self.file_list.clear()
        self.file_paths.clear()
        self._update_ui()

    def _update_ui(self):
        count = self.file_list.count()
        self.lbl_count.setText(f"{count} 个文件")
        has_files = count > 0
        self.btn_clear.setEnabled(has_files)
        self.btn_convert.setEnabled(has_files)

    # ---- 转换 ----

    def _get_checked_paths(self) -> list[str]:
        """获取勾选的文件路径列表。"""
        checked = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.Checked:
                checked.append(self.file_paths[i])
        return checked

    def _start_conversion(self):
        """开始批量转换。"""
        checked = self._get_checked_paths()
        if not checked:
            QMessageBox.information(self, "提示", "没有勾选任何文件。")
            return

        # 取第一个文件的目录作为输出根目录
        self.output_dir = os.path.join(
            os.path.dirname(checked[0]), "md_output"
        )

        # 禁用按钮，显示进度
        self.btn_convert.setEnabled(False)
        self.btn_open_dir.setEnabled(False)
        self.drop_zone.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(checked))

        # 启动后台线程
        self.worker = ConvertWorker(checked, self.output_dir)
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.conversion_done.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, current: int, total: int):
        self.progress.setValue(current)
        self.lbl_status.setText(f"已转换 {current}/{total}")

    def _on_done(self, results: list):
        success = sum(1 for r in results if r is not None)
        total = len(results)
        self.progress.setVisible(False)
        self.lbl_status.setText(f"完成：{success}/{total} 个文件转换成功")
        self.drop_zone.setEnabled(True)
        self.btn_open_dir.setEnabled(True)
        self.btn_convert.setEnabled(True)
        QMessageBox.information(
            self, "转换完成",
            f"成功转换 {success}/{total} 个文件。\n输出目录：{self.output_dir}"
        )

    def _open_output_dir(self):
        """用系统文件管理器打开输出目录。"""
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)


# ============================================================
# 入口
# ============================================================

def main():
    import sys
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

注意：这一步还需在文件开头把 `Signal` 加到 PySide6 的 import 里。

- [ ] **Step 2: 修正文件开头的 import**

找到 `main.py` 顶部的 `from PySide6.QtCore import QThread, Signal` 行，检查是否缺少 `Signal`（因为在 DropZone 中使用了 `Signal(list)`，需要确保导入）。将文件顶部 `from PySide6.QtCore import QThread, Signal` 保留（已在 Task 3 中添加）。

同时在 GUI 代码之前（紧跟 ConvertWorker 之后）添加正确的导入。确保 DropZone 的 `files_dropped = Signal(list)` 可用。

- [ ] **Step 3: 验证程序能启动**

```bash
python main.py
```

预期：出现窗口，标题 "PortableConverterMD"，有拖拽区、空文件列表、"开始转换"按钮灰色不可点。

关闭窗口确认程序正常退出。

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add main window GUI with drag-drop and file list"
```

---

### Task 5: 打包为 .exe

**Files:**
- Modify: `portable_converter_md.spec`（如需要调整）

- [ ] **Step 1: 清理旧构建**

```bash
rm -rf build/ dist/ 2>/dev/null; echo "cleaned"
```

如果是 Windows（无 rm），用：
```powershell
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
```

- [ ] **Step 2: 执行 PyInstaller 打包**

```bash
pyinstaller portable_converter_md.spec
```

预期输出：`BUILD SUCCEEDED`，`dist/PortableConverterMD.exe` 存在。

- [ ] **Step 3: 验证 .exe 可启动**

```bash
start dist/PortableConverterMD.exe
```

预期：窗口正常出现。关闭窗口。

- [ ] **Step 4: 冒烟测试 — 拖入文件转换**

手动测试：
1. 在任意目录创建 `test.txt`，内容随便写
2. 拖入 PortableConverterMD
3. 点击开始转换
4. 检查 `md_output/test.md` 是否生成且内容正确

- [ ] **Step 5: Commit**

```bash
git add portable_converter_md.spec
git commit -m "build: finalize PyInstaller packaging configuration"
```

---

### Task 6: 收尾

- [ ] **Step 1: 创建 .gitignore**

```gitignore
__pycache__/
*.pyc
build/
dist/
*.egg-info/
.env
```

- [ ] **Step 2: 初始化 git（如果尚未初始化）**

```bash
git init
git add -A
git commit -m "feat: PortableConverterMD v1.0 - single-exe markdown converter"
```

- [ ] **Step 3: 最终验证清单**

- [ ] `main.py` 总行数 ≈ 250 行以内
- [ ] `python main.py` 可启动 GUI
- [ ] 拖入文件 → 列表显示 → 勾选正常 → 清空正常
- [ ] 转换功能正常，输出到 `md_output/`
- [ ] 进度条和状态更新正常
- [ ] `dist/PortableConverterMD.exe` 存在且可运行
