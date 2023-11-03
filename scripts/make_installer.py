import io
import os
import shutil
import subprocess
from configparser import RawConfigParser
from pathlib import Path

config = RawConfigParser(allow_no_value=True)
config.read(os.path.join("gridsync", "resources", "config.txt"))
settings = {}
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        settings[section][option] = value

name = settings["application"]["name"]
version = settings["build"].get(
    "version",
    Path("dist", name, "resources", "version.txt").read_text().strip(),
)
win_icon = settings["build"]["win_icon"].replace("/", "\\")

iss_contents = """#define MyAppName "%s"
#define MyAppVersion "%s"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename={#MyAppName}-setup
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=%s
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
Filename: "{app}\{#MyAppName}.exe"; Description: {cm:LaunchProgram,{#MyAppName}}; Flags: postinstall nowait
""" % (
    name,
    version,
    win_icon,
)

iss_path = name + ".iss"

with io.open(iss_path, "w", newline="\r\n") as f:
    f.write(iss_contents)


innosetup_exe = shutil.which("ISCC")
if not innosetup_exe:
    innosetup_exe = "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"

subprocess.call([innosetup_exe, iss_path])
