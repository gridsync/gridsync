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


version_file = open("gridsync/_version.py").read()
version = re.findall("__version__\s*=\s*'([^']+)'", version_file)[0]


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


a = Analysis(
    ['../gridsync/cli.py'],
    pathex=paths,
    binaries=None,
    datas=[
        ('../gridsync/resources/*', 'resources'),
        ('../gridsync/resources/providers/*', 'resources/providers')
    ],
    hiddenimports=['cffi', 'PyQt5.sip'],
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
    icon=settings['build']['win_icon']
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
    icon=settings['build']['mac_icon'],
    bundle_identifier=settings['build']['mac_bundle_identifier'],
    info_plist={
        'CFBundleShortVersionString': version,
        'LSBackgroundOnly': True,
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
    }
)


if sys.platform.startswith('linux'):
    src = os.path.join('dist', app_name, app_name)
    dest = os.path.join('dist', app_name, app_name.lower())
    shutil.move(src, dest)
    bad_libs = [
        'libX11.so.6',  # https://github.com/gridsync/gridsync/issues/43
        'libdrm.so.2',  # https://github.com/gridsync/gridsync/issues/47
        'libstdc++.so.6',  # https://github.com/gridsync/gridsync/issues/189
    ]
    for lib in bad_libs:
        try:
            os.remove(os.path.join('dist', app_name, lib))
        except Exception as exc:
            print("WARNING: Could not delete {}: {}".format(lib, str(exc)))
        print("Deleted {} from bundle".format(lib))


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
