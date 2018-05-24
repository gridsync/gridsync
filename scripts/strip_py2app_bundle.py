# A quick-and-dirty script to remove unused Qt components from py2app bundles,
# drastically reducing the filesize of the resultant application
import os
import shutil
import sys

unused = [
    'QtBluetooth',
    'QtCLucene',
    'QtConcurrent',
    'QtDBus',
    'QtDesigner',
    'QtHelp',
    'QtLocation',
    'QtMultimedia',
    'QtMultimediaWidgets',
    'QtNetwork',
    'QtNfc',
    'QtOpenGL',
    'QtPositioning',
    'QtQml',
    'QtQuick',
    'QtQuickControls2',
    'QtQuickParticles',
    'QtQuickTemplates2',
    'QtQuickTest',
    'QtQuickWidgets',
    'QtSensors',
    'QtSerialPort',
    'QtSql',
    'QtTest',
    'QtWebChannel',
    'QtWebEngine',
    'QtWebEngineCore',
    'QtWebEngineWidgets',
    'QtWebSockets',
    'QtXml',
    'QtXmlPatterns',
]

pyqtdir = 'dist/gridsync.app/Contents/Resources/lib/python{}.{}/PyQt5/'.format(
    sys.version_info[0], sys.version_info[1])

for name in unused:
    path = '{}{}.so'.format(pyqtdir, name)
    try:
        os.remove(path)
        print('Removed: {}'.format(path))
    except OSError:
        pass

paths = []
for name in unused:
    paths.append('{}Qt/lib/{}.framework'.format(pyqtdir, name))
paths.append('{}Qt/qml'.format(pyqtdir))
paths.append('{}Qt/translations'.format(pyqtdir))

for path in paths:
    try:
        shutil.rmtree(path)
        print('Removed: {}'.format(path))
    except OSError:
        pass
