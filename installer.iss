; Inno Setup Script for Stock JSON Clipper V3.0
; Produces a professional Windows installer (.exe)

#define MyAppName "Stock JSON Clipper"
#define MyAppVersion "3.0"
#define MyAppPublisher "Stock JSON Clipper"
#define MyAppURL "https://github.com/ABLingss/Stock-JSON-Clipper"
#define MyAppExeName "StockJSONClipper.exe"

[Setup]
AppId={{A8B3C5D7-1234-4567-89AB-CDEF01234567}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\StockJSONClipper
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=StockJSONClipper-Setup-V3.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\StockJSONClipper.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Stock JSON Clipper V3.0"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall Stock JSON Clipper"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Stock JSON Clipper V3.0"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Stock JSON Clipper"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\*.json"
Type: files; Name: "{app}\config.ini"
