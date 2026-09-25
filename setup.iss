; Inno Setup 安装脚本 — PortableConverterMD
; 设计要点：
;  1. 右键菜单按「文件类型」注册（SystemFileAssociations\<.ext>），只对支持的类型出现，
;     不再使用 `*\shell` 那种对所有文件都出现的写法
;  2. 用 HKA 根键：管理员安装写 HKLM（全机生效），非管理员安装写 HKCU（当前用户生效），
;     因此不强制管理员权限，也不会出现"装到 Program Files 后普通用户没有写权限"的问题
;  3. ChangesAssociations=yes 让外壳立即刷新，右键菜单无需重启资源管理器
;  4. MinVersion 限定 Windows 10 1809+（内置 OCR 的 Windows.Media.Ocr 需要）
;  5. MultiSelectModel=Player：多选文件时只调用一次、一次传入所有文件

#define AppName "PortableConverterMD"
#define AppVersion "2.1"
#define AppExe "PortableConverterMD.exe"
#define AppURL "https://github.com/your-org/PortableConverterMD"
#define VerbKey "ConvertToMarkdown"
#define VerbName "转换为 Markdown"

[Setup]
AppId={{8E1B7C24-3F5A-4C9D-9B6E-7A2D4E5F6A11}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppName}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=.\installer
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
SetupIconFile=res\PortableConverterMD.ico
UninstallDisplayIcon={app}\_internal\res\PortableConverterMD.ico
LicenseFile=LICENSE
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
SetupLogging=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes
CloseApplications=yes
RestartApplications=no
DisableWelcomePage=no

[Languages]
Name: "chinese"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "其他:"
Name: "contextmenu"; Description: "添加右键菜单「{#VerbName}」（仅对支持的文件类型显示）"; GroupDescription: "其他:"; Flags: checkedonce

[Files]
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "NOTICE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\_internal\res\PortableConverterMD.ico"
Name: "{autoprograms}\卸载 {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent

; ---------------------------------------------------------------------------
; 右键菜单：逐个「支持的文件类型」注册，因此菜单只在相关文件上出现。
; 扩展名列表必须与 engine.SUPPORTED_EXT 保持一致。
; ---------------------------------------------------------------------------

[Registry]
; ---- 文本 / 数据 ----
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tsv\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tsv\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tsv\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tsv\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.json\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.json\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.json\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.json\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xml\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xml\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xml\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xml\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
; ---- 代码 / 配置（纯文本，同样支持转换） ----
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.py\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.py\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.py\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.py\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ini\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ini\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ini\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ini\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.cfg\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.cfg\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.cfg\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.cfg\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.conf\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.conf\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.conf\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.conf\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.yaml\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.yaml\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.yaml\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.yaml\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.yml\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.yml\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.yml\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.yml\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
; ---- 网页 ----
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
; ---- Office ----
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pptx\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
; ---- PDF ----
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
; ---- 图片（OCR） ----
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
; ---- 压缩包 ----
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\{#VerbKey}"; ValueType: string; ValueName: ""; ValueData: "{#VerbName}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\{#VerbKey}"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\_internal\res\PortableConverterMD.ico"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\{#VerbKey}"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\{#VerbKey}\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu

[Code]
{ v1 用的是对所有文件都出现的 *\shell 项，升级时清掉，避免菜单里残留一条无效项 }
procedure RemoveLegacyContextMenu();
begin
  RegDeleteKeyIncludingSubkeys(HKLM, 'Software\Classes\*\shell\{#VerbKey}');
  RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Classes\*\shell\{#VerbKey}');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RemoveLegacyContextMenu();
end;
