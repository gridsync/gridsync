# -*- mode: python -*-

from __future__ import print_function

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
from distutils.sysconfig import get_python_lib
import os
import re
import shutil
import sys
from pathlib import Path

from versioneer import get_versions


config = RawConfigParser(allow_no_value=True)
config.read(os.path.join('gridsync', 'resources', 'config.txt'))
settings = {}
print('----------------------- config.txt settings: -----------------------')
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        print("[{}] {} = {}".format(section, option, value))
        settings[section][option] = value
print('--------------------------------------------------------------------')
app_name = settings['application']['name']


version = settings['build'].get('version', get_versions()["version"])
# When running frozen, Versioneer returns a version string of "0+unknown"
# so write the version string from a file that can be read/loaded later.
with open(os.path.join("gridsync", "resources", "version.txt"), "w") as f:
    f.write(version)


paths = []
if sys.platform == "win32":
    paths.append(os.path.join(get_python_lib(), 'PyQt5', 'Qt', 'bin'))
    paths.append(os.path.join(os.path.abspath(os.sep), 'Program Files (x86)', 'Windows Kits', '10', 'bin', 'x86'))
    paths.append(os.path.join(os.path.abspath(os.sep), 'Program Files (x86)', 'Windows Kits', '10', 'bin', 'x64'))
    paths.append(os.path.join(os.path.abspath(os.sep), 'Program Files (x86)', 'Windows Kits', '10', 'Redist', 'ucrt', 'DLLs', 'x86'))
    paths.append(os.path.join(os.path.abspath(os.sep), 'Program Files (x86)', 'Windows Kits', '10', 'Redist', 'ucrt', 'DLLs', 'x64'))
    paths.append(os.path.join(os.path.abspath(os.sep), 'Program Files', 'Windows Kits', '10', 'bin', 'x86'))
    paths.append(os.path.join(os.path.abspath(os.sep), 'Program Files', 'Windows Kits', '10', 'bin', 'x64'))
    paths.append(os.path.join(os.path.abspath(os.sep), 'Program Files', 'Windows Kits', '10', 'Redist', 'ucrt', 'DLLs', 'x86'))
    paths.append(os.path.join(os.path.abspath(os.sep), 'Program Files', 'Windows Kits', '10', 'Redist', 'ucrt', 'DLLs', 'x64'))


mac_background_only = settings["build"].get("mac_background_only", False)
if mac_background_only and mac_background_only.lower() != "false":
    mac_background_only = True


a = Analysis(
    ['../gridsync/cli.py'],
    pathex=paths,
    binaries=None,
    datas=[
        ('../gridsync/resources/*', 'resources'),
        ('../gridsync/resources/providers/*', 'resources/providers')
    ],
    hiddenimports=['cffi', 'PyQt5.sip', 'pkg_resources.py2_warn'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name=app_name,
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.abspath(settings['build']['win_icon'])
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=app_name
)
app = BUNDLE(
    coll,
    name=(app_name + '.app'),
    icon=os.path.abspath(settings['build']['mac_icon']),
    bundle_identifier=settings['build']['mac_bundle_identifier'],
    info_plist={
        'CFBundleShortVersionString': version,
        'LSBackgroundOnly': mac_background_only,
        'LSUIElement': mac_background_only,
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
    }
)


if sys.platform.startswith('linux'):
    src = os.path.join('dist', app_name, app_name)
    dest = os.path.join('dist', app_name, app_name.lower())
    shutil.move(src, dest)


tahoe_bundle_path = os.path.join('dist', 'Tahoe-LAFS')
if os.path.isdir(tahoe_bundle_path):
    if sys.platform == 'darwin':
        dest = os.path.join(
            'dist', app_name + '.app', 'Contents', 'MacOS', 'Tahoe-LAFS')
    else:
        dest = os.path.join('dist', app_name, 'Tahoe-LAFS')
    print("Copying {} to {}...".format(tahoe_bundle_path, dest))
    shutil.copytree(tahoe_bundle_path, dest)
    print("Done")
else:
    print('##################################################################')
    print('WARNING: No Tahoe-LAFS bundle found!')
    print('##################################################################')


magic_folder_bundle_path = os.path.join('dist', 'magic-folder')
if os.path.isdir(magic_folder_bundle_path):
    if sys.platform == 'darwin':
        dest = os.path.join(
            'dist', app_name + '.app', 'Contents', 'MacOS', 'magic-folder')
    else:
        dest = os.path.join('dist', app_name, 'magic-folder')
    print("Copying {} to {}...".format(magic_folder_bundle_path, dest))
    shutil.copytree(magic_folder_bundle_path, dest)
    print("Done")
else:
    print('#################################################################')
    print('WARNING: No magic-folder bundle found!')
    print('#################################################################')


# The presence of *.dist-info/RECORD files causes issues with reproducible
# builds; see: https://github.com/gridsync/gridsync/issues/363
for p in [p for p in Path("dist", app_name).glob("**/*.dist-info/RECORD")]:
    print(f"Removing {p}...")
    try:
        os.remove(p)
    except Exception as exc:
        print(f"WARNING: Could not remove {p}: {str(exc)}")
