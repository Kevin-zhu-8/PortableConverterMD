<p align="center">
  <img src="ZENO.png" width="128" alt="PortableConverterMD">
</p>

<h1 align="center">PortableConverterMD</h1>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6.svg">
  <img src="https://img.shields.io/badge/license-MIT-green.svg">
  <img src="https://img.shields.io/badge/PySide6-6.5+-41CD52.svg">
</p>

<p align="center">
  拖拽文件 → 一键转 Markdown<br>
  基于 <a href="https://github.com/microsoft/markitdown">Microsoft MarkItDown</a> 的 Windows 桌面工具
</p>

---

## 特性

- **拖拽即用** — 拖入文件或点击选择，批量转换
- **全格式覆盖** — Office（Word/Excel/PPT）、PDF、图片、HTML、CSV、JSON、XML、音频、ZIP
- **后台转换** — 多线程处理，界面不卡顿
- **进度可见** — 实时进度条 + 状态提示
- **错误追踪** — 失败文件弹窗提示原因，详细日志输出到 `logs/conversion.log`

## 界面

```
┌─────────────────────────────────────┐
│    拖拽文件到此处（或点击选择）        │
├─────────────────────────────────────┤
│  [x] report.docx         123KB     │
│  [x] slides.pptx         5.2MB     │
├─────────────────────────────────────┤
│  状态：已转换 2/2                   │
│  [========================] 100%   │
│  [ 开始转换 ]  [ 打开输出目录 ]      │
└─────────────────────────────────────┘
```

## 使用

```bash
# 安装依赖
pip install -r requirements.txt

# 直接运行
python main.py
```

## 打包

```bash
# 绿色免安装版（文件夹，启动快）
pyinstaller portable_converter_md.spec
```

`dist/PortableConverterMD/` 文件夹双击 `PortableConverterMD.exe` 即用。

## 项目结构

```
├── main.py                          # 全部源码（单文件）
├── requirements.txt                 # Python 依赖
├── portable_converter_md.spec       # PyInstaller 打包配置
├── setup.iss                        # Inno Setup 安装包配置
├── ZENO.png                         # 应用图标
├── test_converter.py                # 单元测试
└── docs/                            # 设计文档
```

## 依赖

| 包 | 用途 |
|---|---|
| [markitdown](https://github.com/microsoft/markitdown) | 文件 → Markdown 核心引擎 |
| [PySide6](https://pypi.org/project/PySide6/) | Qt 桌面框架 |
| [pyinstaller](https://pyinstaller.org/) | 打包为独立程序 |

## 许可证

MIT
