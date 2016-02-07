::
:: Build Gridsync on Windows7 (64 bit)
::
:: This script assumes that the following dependencies have already been
:: downloaded and properly installed:
::
::      Python 3.4 (PyQt5-5.5.1 requires 3.4, not 3.5): https://www.python.org/
::      PyQt5 (currently 5.5.1): https://www.riverbankcomputing.com/software/pyqt/download5
::      pywin32 (currently build 220): http://sourceforge.net/projects/pywin32/
::

call .\scripts\make-frozen-tahoe.bat

call C:\Python34\python.exe -m pip install --upgrade --editable .

call C:\Python34\python.exe -m pip install --upgrade pyinstaller
set PYTHONHASHSEED=1
call C:\Python34\Scripts\pyinstaller.exe --windowed --icon=images\gridsync.ico --name=Gridsync gridsync\cli.py
set PYTHONHASHSEED=

move dist\Tahoe-LAFS dist\Gridsync\Tahoe-LAFS

call C:\Python27\python.exe -m zipfile -c dist\Gridsync.zip dist\Gridsync

echo Done!
