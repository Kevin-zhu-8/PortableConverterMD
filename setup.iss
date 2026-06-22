; Inno Setup 安装脚本 — PortableConverterMD

[Setup]
AppName=PortableConverterMD
AppVersion=1.0
AppPublisher=PortableConverterMD
DefaultDirName={autopf}\PortableConverterMD
DefaultGroupName=PortableConverterMD
OutputDir=.\installer
OutputBaseFilename=PortableConverterMD-Setup
SetupIconFile=o.jpg
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\o.jpg
WizardStyle=modern

[Files]
Source: "dist\PortableConverterMD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PortableConverterMD"; Filename: "{app}\PortableConverterMD.exe"; IconFilename: "{app}\o.jpg"
Name: "{group}\卸载 PortableConverterMD"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PortableConverterMD"; Filename: "{app}\PortableConverterMD.exe"; IconFilename: "{app}\o.jpg"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "其他:"

[Run]
Filename: "{app}\PortableConverterMD.exe"; Description: "启动 PortableConverterMD"; Flags: nowait postinstall skipifsilent
