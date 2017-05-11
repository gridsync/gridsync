# -*- mode: python -*-

from __future__ import print_function

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
from distutils.sysconfig import get_python_lib
import os
import shutil
import sys


config = RawConfigParser(allow_no_value=True)
config.read('config.txt')
settings = {}
print('----------------------- config.txt settings: -----------------------')
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        print("[{}] {} = {}".format(section, option, value))
        settings[section][option] = value
print('--------------------------------------------------------------------')


shutil.copy2('config.txt', os.path.join('gridsync', 'resources'))


pathex_paths = []
if sys.platform == "win32":
    pathex_paths.append(os.path.join(get_python_lib(), 'PyQt5', 'Qt', 'bin'))
    pathex_paths.append(os.path.join(os.path.abspath(os.sep), 'Program Files (x86)', 'Windows Kits', '10', 'bin', 'x86'))
    pathex_paths.append(os.path.join(os.path.abspath(os.sep), 'Program Files (x86)', 'Windows Kits', '10', 'Redist', 'ucrt', 'DLLs', 'x86'))

a = Analysis(['../gridsync/cli.py'],
             pathex=pathex_paths,
             binaries=None,
             datas=[('../gridsync/resources/*', 'resources')],
             hiddenimports=['cffi'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=None)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name=settings['application']['name'],
          debug=True,
          strip=False,
          upx=False,
          console=True,
          icon=settings['build']['win_icon'])
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name=settings['application']['name'])
app = BUNDLE(coll,
             name=(settings['application']['name'] + '.app'),
             icon=settings['build']['mac_icon'],
             bundle_identifier=settings['build']['mac_bundle_identifier'])


tahoe_bundle_path = os.path.join('dist', 'Tahoe-LAFS')
if os.path.isdir(tahoe_bundle_path):
    app_name = settings['application']['name']
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


print('Creating zip archive...')
base_name = os.path.join('dist', settings['application']['name'])
shutil.make_archive(base_name, 'zip', 'dist', settings['application']['name'])
print('Done!')
