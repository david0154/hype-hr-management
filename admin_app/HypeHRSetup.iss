; ======================================================
; Hype HR Management Installer
; ======================================================

[Setup]
AppId=HypeHRManagement
AppName=Hype HR Management
AppVersion=1.0.0
AppVerName=Hype HR Management 1.0.0
AppPublisher=Hype Technology Ltd
AppPublisherURL=https://github.com/david0154/hype-hr-management
AppSupportURL=https://github.com/david0154/hype-hr-management
AppUpdatesURL=https://github.com/david0154/hype-hr-management

DefaultDirName={autopf}\Hype HR Management
DefaultGroupName=Hype HR Management

OutputDir=dist
OutputBaseFilename=HypeHRManagement-Setup

Compression=lzma2
SolidCompression=yes

WizardStyle=modern

SetupIconFile=logo.ico
UninstallDisplayIcon={app}\logo.ico

PrivilegesRequired=admin

ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

DisableProgramGroupPage=yes

; IMPORTANT
VersionInfoCompany=Hype Technology Ltd
VersionInfoDescription=Hype HR Management Software
VersionInfoVersion=1.0.0
VersionInfoProductName=Hype HR Management
VersionInfoProductVersion=1.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create Desktop Shortcut"; Flags: unchecked

[Files]

; Main EXE
Source: "dist\HypeHRManagement.exe"; DestDir: "{app}"; Flags: ignoreversion

; ICON
Source: "logo.ico"; DestDir: "{app}"; Flags: ignoreversion

; PNG
Source: "logo.png"; DestDir: "{app}"; Flags: ignoreversion

; OTHER FILES
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]

; Start Menu Shortcut
Name: "{group}\Hype HR Management"; \
Filename: "{app}\HypeHRManagement.exe"; \
IconFilename: "{app}\logo.ico"; \
WorkingDir: "{app}"

; Desktop Shortcut
Name: "{autodesktop}\Hype HR Management"; \
Filename: "{app}\HypeHRManagement.exe"; \
IconFilename: "{app}\logo.ico"; \
WorkingDir: "{app}"; \
Tasks: desktopicon

; Uninstall Shortcut
Name: "{group}\Uninstall Hype HR Management"; \
Filename: "{uninstallexe}"

[Run]

Filename: "{app}\HypeHRManagement.exe"; \
Description: "Launch Hype HR Management"; \
Flags: nowait postinstall skipifsilent

[UninstallDelete]

Type: files; Name: "{app}\logo.ico"
Type: files; Name: "{app}\logo.png"
Type: dirifempty; Name: "{app}"