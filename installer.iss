; ============================================================
; OnyxPad Pro — Inno Setup Script
; Generates OnyxPad_Setup_v1.0.2.exe for Windows 10/11
; ============================================================

[Setup]
AppId={{D37F8A22-963C-4E7B-B12A-6A9280F08B9C}
AppName=OnyxPad Pro
AppVersion=1.0.2
AppPublisher=jpXProject
AppPublisherURL=https://github.com/jpXproject/OnyxPad
AppSupportURL=https://github.com/jpXproject/OnyxPad/issues
AppUpdatesURL=https://github.com/jpXproject/OnyxPad/releases
DefaultDirName={autopf}\OnyxPad
DefaultGroupName=OnyxPad Pro
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=OnyxPad_Setup_v1.0.2
SetupIconFile=favicon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Tasks: desktopicon

[Files]
Source: "dist\OnyxPad.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\OnyxPad Pro"; Filename: "{app}\OnyxPad.exe"; IconFilename: "{app}\OnyxPad.exe"
Name: "{group}\{cm:UninstallProgram,OnyxPad Pro}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\OnyxPad Pro"; Filename: "{app}\OnyxPad.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OnyxPad.exe"; Description: "{cm:LaunchProgram,OnyxPad Pro}"; Flags: nowait postinstall skipifsilent
