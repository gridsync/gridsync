#define MyAppName "Gridsync"

[Setup]
AppName={#MyAppName}
AppVersion=0.4
DefaultDirName={pf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename={#MyAppName}-setup
SetupIconFile=images\gridsync.ico
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppName}.exe

[Files]
Source: "dist\Gridsync\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: desktopicon
Name: "{commonprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: programsicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: startupicon

[Tasks]
Name: desktopicon; Description: {cm:CreateDesktopIcon}; GroupDescription: {cm:AdditionalIcons}
Name: programsicon; Description: {cm:CreateQuickLaunchIcon}; GroupDescription: {cm:AdditionalIcons}
Name: startupicon; Description: {cm:AutoStartProgram,Gridsync}; GroupDescription: {cm:AutoStartProgramGroupDescription}

[Run]
Filename: "{app}\{#MyAppName}.exe"; Description: {cm:LaunchProgram,{#MyAppName}}; Flags: postinstall