# PortableConverterMD

将任意文件转换为 Markdown 的 Windows 桌面工具，基于 Microsoft [MarkItDown](https://github.com/microsoft/markitdown)。

## 功能

- 拖拽或点击选择文件，批量转换为 `.md`
- 支持全部格式：Office（Word/Excel/PPT）、PDF、图片（OCR）、HTML、CSV、JSON、XML、音频、ZIP
- 后台线程转换，不卡界面
- 转换失败时弹窗提示具体错误，日志写入 `logs/conversion.log`

## 使用

### 方式一：直接运行源码

```bash
pip install -r requirements.txt
python main.py
```

### 方式二：打包成绿色免安装版

```bash
pyinstaller portable_converter_md.spec
```

`dist\PortableConverterMD\` 文件夹即为可运行的程序，双击 `PortableConverterMD.exe`。

### 方式三：打包成安装包

1. 安装 [Inno Setup](https://jrsoftware.org/isinfo.php)
2. 先执行方式二生成 `dist\`
3. 用 Inno Setup 编译 `setup.iss`
4. 在 `installer\` 下得到 `PortableConverterMD-Setup.exe`

## 文件结构

```
├── main.py                          # 全部源码（单文件）
├── requirements.txt                 # 依赖
├── portable_converter_md.spec       # PyInstaller 打包配置
├── setup.iss                        # Inno Setup 安装包配置
├── ZENO.png                         # 应用图标
├── test_converter.py                # 核心转换单元测试
└── docs/                            # 设计文档
```

## 依赖

- Python 3.10+
- PySide6
- markitdown[all]
- pyinstaller（仅打包时）
