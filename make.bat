::
:: This script assumes that the following dependencies have already been 
:: downloaded and properly installed:
::
::      Python 2.7: https://www.python.org/
::      Microsoft Visual C++ Compiler for Python 2.7: https://www.microsoft.com/en-us/download/details.aspx?id=44266
::      Python 3.5: https://www.python.org/
::

@echo off

if "%1"=="test" call :test
if "%1"=="pytest" call :pytest
if "%1"=="frozen-tahoe" call :frozen-tahoe
if "%1"=="all" call :all
if "%1"=="" call :all
goto :eof

:test
call py setup.py test || exit /b 1
goto :eof

:pytest
call python -m pytest || exit /b 1
goto :eof

:frozen-tahoe
call mkdir .\build
::call powershell -Command "(New-Object Net.WebClient).DownloadFile('https://tahoe-lafs.org/downloads/tahoe-lafs-1.11.0.zip', '.\build\tahoe-lafs.zip')"
::call C:\Python27\python.exe -m zipfile -e .\build\tahoe-lafs.zip .\build
::call move .\build\tahoe-lafs-1.11.0 .\build\tahoe-lafs
call git clone https://github.com/tahoe-lafs/tahoe-lafs.git .\build\tahoe-lafs
call C:\Python27\python.exe -m pip install --upgrade virtualenv
call C:\Python27\python.exe -m virtualenv --clear .\build\venv-tahoe
call .\build\venv-tahoe\Scripts\activate
call pip install --find-links=https://tahoe-lafs.org/deps/ .\build\tahoe-lafs
call pip install git+https://github.com/pyinstaller/pyinstaller.git
call pip install zope.interface==4.3.2
call copy .\misc\tahoe.spec .\build\tahoe-lafs
call pushd .\build\tahoe-lafs
call set PYTHONHASHSEED=1
call pyinstaller tahoe.spec
call python -m zipfile -c dist\Tahoe-LAFS.zip dist\Tahoe-LAFS
call set PYTHONHASHSEED=
call move dist ..\..
call popd
call .\build\venv-tahoe\Scripts\deactivate
goto :eof

:all
if exist .\dist\Tahoe-LAFS.zip (
    call C:\Python27\python.exe -m zipfile -e .\dist\Tahoe-LAFS.zip dist
) else (
    call :frozen-tahoe
)
call .\dist\Tahoe-LAFS\tahoe.exe --version-and-path
call py -3.5 -m pip install --upgrade pip virtualenv
call py -3.5 -m virtualenv --clear .\build\venv-gridsync
call .\build\venv-gridsync\Scripts\activate
call pip install pyqt5==5.6
call pip install git+https://github.com/crwood/qt5reactor.git
call pip install . 
call pip install git+https://github.com/pyinstaller/pyinstaller.git
call set PYTHONHASHSEED=1
call pyinstaller misc\gridsync.spec
call move dist\Tahoe-LAFS dist\Gridsync\Tahoe-LAFS
call python -m zipfile -c dist\Gridsync.zip dist\Gridsync
call deactivate
goto :eof
