; Inno Setup 安装脚本 — PortableConverterMD

[Setup]
AppName=PortableConverterMD
AppVersion=1.0
AppPublisher=PortableConverterMD
DefaultDirName={autopf}\PortableConverterMD
DefaultGroupName=PortableConverterMD
OutputDir=.\installer
OutputBaseFilename=PortableConverterMD-Setup
SetupIconFile=res\PortableConverterMD.png
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\res\PortableConverterMD.png
WizardStyle=modern

[Files]
Source: "dist\PortableConverterMD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PortableConverterMD"; Filename: "{app}\PortableConverterMD.exe"; IconFilename: "{app}\res\PortableConverterMD.png"
Name: "{group}\卸载 PortableConverterMD"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PortableConverterMD"; Filename: "{app}\PortableConverterMD.exe"; IconFilename: "{app}\res\PortableConverterMD.png"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "其他:"
Name: "contextmenu"; Description: "添加右键菜单「转换为 Markdown」"; GroupDescription: "其他:"; Flags: checkedonce

[Registry]
Root: HKCR; Subkey: "*\shell\ConvertToMarkdown"; ValueType: string; ValueName: ""; ValueData: "转换为 Markdown"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCR; Subkey: "*\shell\ConvertToMarkdown"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\res\PortableConverterMD.png"; Tasks: contextmenu
Root: HKCR; Subkey: "*\shell\ConvertToMarkdown\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PortableConverterMD.exe"" ""%1"""; Tasks: contextmenu

[Run]
Filename: "{app}\PortableConverterMD.exe"; Description: "启动 PortableConverterMD"; Flags: nowait postinstall skipifsilent
