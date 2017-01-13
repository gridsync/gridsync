# -*- mode: python -*-

from __future__ import print_function

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
import os
import shutil


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


a = Analysis(['../gridsync/cli.py'],
             pathex=[],
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
          debug=False,
          strip=False,
          upx=False,
          console=False,
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


print('Creating zip archive...')
base_name = os.path.join('dist', settings['application']['name'])
shutil.make_archive(base_name, 'zip', 'dist', settings['application']['name'])
print('Done!')
