#define MyAppName "Gridsync"
#define MyAppVersion "0.5.0rc1"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename={#MyAppName}-setup
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
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
WizardStyle=modern

[Files]
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: desktopicon
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: programsicon
Name: "{autostartup}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: startupicon

[Tasks]
Name: desktopicon; Description: {cm:CreateDesktopIcon}; GroupDescription: {cm:AdditionalIcons}
Name: programsicon; Description: {cm:CreateQuickLaunchIcon}; GroupDescription: {cm:AdditionalIcons}
Name: startupicon; Description: {cm:AutoStartProgram,{#MyAppName}}; GroupDescription: {cm:AutoStartProgramGroupDescription}

[Run]
Filename: "{app}\{#MyAppName}.exe"; Description: {cm:LaunchProgram,{#MyAppName}}; Flags: postinstall
