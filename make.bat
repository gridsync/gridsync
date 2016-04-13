::
:: This script assumes that the following dependencies have already been 
:: downloaded and properly installed:
::
::      Python 2.7: https://www.python.org/
::      Microsoft Visual C++ Compiler for Python 2.7: https://www.microsoft.com/en-us/download/details.aspx?id=44266
::      Git: https://git-scm.com/download/win
::          (select "Use Git from the Windows Command Prompt" and "Checkout
::          as-is" in setup wizard)
::      PyQt5 (currently 5.5.1): https://www.riverbankcomputing.com/software/pyqt/download5
::      Python 3.4 (PyQt5-5.5.1 requires Python 3.4, not 3.5): https://www.python.org/
::

@echo off

if "%1"=="test" call :test
if "%1"=="pytest" call :pytest
if "%1"=="frozen-tahoe" call :frozen-tahoe
if "%1"=="all" call :all
if "%1"=="" call :all
goto :eof

:test
call py setup.py test || exit /b
goto :eof

:pytest
call python -m pytest || exit /b
goto :eof

:frozen-tahoe
call mkdir .\build
call powershell -Command "(New-Object Net.WebClient).DownloadFile('https://tahoe-lafs.org/downloads/tahoe-lafs-1.11.0.zip', '.\build\tahoe-lafs.zip')"
call C:\Python27\python.exe -m zipfile -e .\build\tahoe-lafs.zip .\build
call move .\build\tahoe-lafs-1.11.0 .\build\tahoe-lafs
call C:\Python27\python.exe -m pip install --upgrade virtualenv
call C:\Python27\python.exe -m virtualenv --clear .\build\venv
call .\build\venv\Scripts\activate
call pip install --find-links=https://tahoe-lafs.org/deps/ .\build\tahoe-lafs
call pip install pyinstaller
call copy .\misc\tahoe.spec .\build\tahoe-lafs
call pushd .\build\tahoe-lafs
call set PYTHONHASHSEED=1
call pyinstaller tahoe.spec
call python -m zipfile -c dist\Tahoe-LAFS.zip dist\Tahoe-LAFS
call set PYTHONHASHSEED=
call move dist ..\..
call popd
call .\build\venv\Scripts\deactivate
goto :eof

:all
if exist .\dist\Tahoe-LAFS.zip (
    call C:\Python27\python.exe -m zipfile -e .\dist\Tahoe-LAFS.zip dist
) else (
    call :frozen-tahoe
)
call .\dist\Tahoe-LAFS\tahoe.exe --version-and-path
call C:\Python34\python.exe -m pip install --upgrade --editable .
call C:\Python34\python.exe -m pip install --upgrade pyinstaller
call set PYTHONHASHSEED=1
call C:\Python34\Scripts\pyinstaller.exe --windowed --icon=images\gridsync.ico --name=Gridsync gridsync\cli.py
call set PYTHONHASHSEED=
call move dist\Tahoe-LAFS dist\Gridsync\Tahoe-LAFS
call C:\Python27\python.exe -m zipfile -c dist\Gridsync.zip dist\Gridsync
goto :eof

