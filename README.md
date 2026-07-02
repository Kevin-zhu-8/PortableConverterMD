<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6.svg">
  <img src="https://img.shields.io/badge/license-MIT-green.svg">
  <img src="https://img.shields.io/badge/PySide6-6.5+-41CD52.svg">
</p>

<h1 align="center">PortableConverterMD</h1>

<p align="center">
  <strong>拖拽文件，一键转 Markdown</strong><br><br>
  一个基于 <a href="https://github.com/microsoft/markitdown">Microsoft MarkItDown</a> 的 Windows 桌面工具<br>
  将 Office 文档、PDF、HTML、图片等任意文件批量转换为 Markdown 格式
</p>

<p align="center">
  <img src="res/screenshot.png" width="560" alt="截图">
</p>

## 特性

- **拖拽即用** — 拖入或点击选择，批量转换
- **全格式支持** — Word、Excel、PPT、PDF、图片（OCR）、HTML、CSV、JSON、XML、音频、ZIP
- **扫描件 OCR** — 内置 Tesseract 引擎，扫描版 PDF 自动识别（中英双语）
- **右键菜单** — 安装后右键任意文件直达转换
- **实时状态** — 逐个显示转换进度，成功/失败一目了然
- **自定义输出** — 可选指定输出目录，默认源文件旁 `md_output`
- **命令行支持** — 支持传文件路径直接转换，无需打开 GUI

## 安装

从 [Releases]() 下载安装包，双击安装。

或下载绿色免安装版，解压即用。

## 使用

### GUI 模式

启动后拖入文件 → 勾选需要的 → 点"开始转换"。

### 右键菜单

安装后，在任意文件上右键 → **转换为 Markdown**。

### 命令行

```bash
PortableConverterMD.exe "C:\path\to\file.pdf"
```

## 从源码运行

```bash
# 1. 克隆
git clone https://github.com/your-org/PortableConverterMD.git
cd PortableConverterMD

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

## 从源码打包

```bash
# 绿色免安装版（onedir）
pyinstaller portable_converter_md.spec

# 安装包（需要 Inno Setup）
# 用 Inno Setup 打开 setup.iss → 编译
```

## 原理

```
文件 → markitdown 文本提取
         ├─ Office / HTML / CSV / JSON … → 直接输出 .md
         └─ PDF →  文本层有内容 → 直接输出 .md
                   文本层为空 → 逐页渲染 → Tesseract OCR → 输出 .md
```

## 项目结构

```
├── main.py               # 入口（GUI + CLI）
├── converter.py          # 转换引擎 + OCR
├── worker.py             # 后台线程
├── ui.py                 # GUI 界面
├── test_converter.py     # 单元测试
├── requirements.txt      # Python 依赖
├── portable_converter_md.spec  # PyInstaller 配置
├── setup.iss             # Inno Setup 安装包配置
├── res/                  # 图标和截图
├── tesseract/            # OCR 引擎（内置，不进 Git）
└── docs/                 # 设计文档
```

## 致谢

本项目基于以下开源项目构建：

| 项目 | 用途 | 许可证 |
|------|------|--------|
| [MarkItDown](https://github.com/microsoft/markitdown) | 文件格式转换引擎 | MIT |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | 扫描件文字识别 | Apache 2.0 |
| [PySide6](https://pypi.org/project/PySide6/) | GUI 框架 | LGPL |

## 许可证

[MIT](LICENSE)
