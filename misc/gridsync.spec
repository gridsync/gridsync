# -*- mode: python -*-

block_cipher = None


a = Analysis(['../gridsync/cli.py'],
             pathex=[],
             binaries=None,
             datas=[('../gridsync/resources/*', 'resources')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Gridsync',
          debug=False,
          strip=False,
          upx=False,
          console=False,
          icon='images/gridsync.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='Gridsync')
app = BUNDLE(coll,
             name='Gridsync.app',
             icon='images/gridsync.icns',
             bundle_identifier=None)

