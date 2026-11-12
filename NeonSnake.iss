; NEON SNAKE installer script (Inno Setup 6)
; Build with:
;   "C:\Users\<you>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\NeonSnake.iss
;
; The setup wraps dist\NeonSnake.exe, installs per-user (no UAC), creates
; Start Menu/optional desktop shortcuts, and preserves the score file.

#define MyAppName "NEON SNAKE"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "NEON SNAKE"
#define MyAppExeName "NeonSnake.exe"

[Setup]
; Stable AppId so future builds upgrade this installation in place.
AppId={{8F4C2B7E-3A5D-4C1E-9B6F-2D7A1E9C4B53}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Per-user install keeps high_scores.json writable without admin rights.
DefaultDirName={localappdata}\Programs\NeonSnake
DefaultGroupName={#MyAppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..
OutputBaseFilename=NeonSnakeSetup
SetupIconFile=..\neon_snake.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=1.1.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoDescription=NEON SNAKE installer

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\neon_snake.ico"; DestDir: "{app}"; Flags: ignoreversion
; Seed the current scores on a fresh install; upgrades keep the newer file.
Source: "..\high_scores.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\neon_snake.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\neon_snake.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
