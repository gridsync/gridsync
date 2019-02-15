#define MyAppName "Gridsync"
#define MyAppVersion "0.4.0"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={userpf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename={#MyAppName}-setup
PrivilegesRequired=lowest
SetupIconFile=images\{#MyAppName}.ico
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppName}.exe
UsePreviousAppDir=no
UsePreviousGroup=no
UsePreviousLanguage=no
UsePreviousPrivileges=no
UsePreviousSetupType=no
UsePreviousTasks=no
UsePreviousUserInfo=no
VersionInfoVersion={#MyAppVersion}
WizardStyle=modern

[Files]
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: desktopicon
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: programsicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: startupicon

[Tasks]
Name: desktopicon; Description: {cm:CreateDesktopIcon}; GroupDescription: {cm:AdditionalIcons}
Name: programsicon; Description: {cm:CreateQuickLaunchIcon}; GroupDescription: {cm:AdditionalIcons}
Name: startupicon; Description: {cm:AutoStartProgram,{#MyAppName}}; GroupDescription: {cm:AutoStartProgramGroupDescription}

[Run]
Filename: "{app}\{#MyAppName}.exe"; Description: {cm:LaunchProgram,{#MyAppName}}; Flags: postinstall
