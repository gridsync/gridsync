::
:: This script assumes that the following dependencies have been installed:
::
::  1) Git <https://git-scm.com/download/win>
::
::  2) Python 2.7 <https://www.python.org>
::
::  3) Python 3.6 <https://www.python.org>
::      -Select "Add Python 3.6 to PATH" option during install
::
::  4) Microsoft Visual C++ Compiler for Python 2.7 <https://aka.ms/vcpython27>
::
::  5) Microsoft .NET Framework <https://www.microsoft.com/net/download/framework>
::
::  6) Microsoft Visual C++ Build Tools 2015 <http://landinghub.visualstudio.com/visual-cpp-build-tools>
::      -Select "Windows 8.1 SDK" and "Windows 10 SDK" options during install
::

@echo off

if defined APPVEYOR (
    if "%PYTHON_ARCH%" == "64" (
        set PYTHON2=C:\Python27-x64\python.exe
    ) else (
        set PYTHON2=C:\Python27\python.exe
    )
    set PYTHON3=%PYTHON%\python.exe
) else (
    set PYTHON2=py -2.7
    set PYTHON3=py -3.6
)

if "%1"=="clean" call :clean
if "%1"=="test" call :test
if "%1"=="pytest" call :pytest
if "%1"=="frozen-tahoe" call :frozen-tahoe
if "%1"=="all" call :all
if "%1"=="" call :all
goto :eof

:clean
call rmdir /s /q .\build
call rmdir /s /q .\dist
call rmdir /s /q .\.eggs
call rmdir /s /q .\.cache
call rmdir /s /q .\.tox
call rmdir /s /q .\htmlcov
call del .\.coverage
goto :eof

:test
call %PYTHON3% -m tox || exit /b 1
goto :eof

:pytest
call python -m pytest || exit /b 1
goto :eof

:frozen-tahoe
call %PYTHON2% -m pip install --upgrade setuptools pip virtualenv
call %PYTHON2% -m virtualenv --clear .\build\venv-tahoe
call .\build\venv-tahoe\Scripts\activate
::call powershell -Command "(New-Object Net.WebClient).DownloadFile('https://tahoe-lafs.org/downloads/tahoe-lafs-1.11.0.zip', '.\build\tahoe-lafs.zip')"
::call C:\Python27\python.exe -m zipfile -e .\build\tahoe-lafs.zip .\build
::call move .\build\tahoe-lafs-1.11.0 .\build\tahoe-lafs
call pip install --upgrade setuptools pip
call git clone https://github.com/tahoe-lafs/tahoe-lafs.git .\build\tahoe-lafs
call git --git-dir=build\tahoe-lafs\.git --work-tree=build\tahoe-lafs checkout 05edde9a64986375d4c8d97ae8caa16cba3f2cb8
::call copy .\misc\tahoe.spec .\build\tahoe-lafs
call pushd .\build\tahoe-lafs
call python setup.py update_version
call pip install .
call pip install packaging
call pip install pyinstaller==3.3.1
call pip list
call set PYTHONHASHSEED=1
call pyinstaller pyinstaller.spec
call python -m zipfile -c dist\Tahoe-LAFS.zip dist\Tahoe-LAFS
call set PYTHONHASHSEED=
call move dist ..\..
call popd
call deactivate
goto :eof

:all
if exist .\dist\Tahoe-LAFS.zip (
    call %PYTHON2% -m zipfile -e .\dist\Tahoe-LAFS.zip dist
    call .\dist\Tahoe-LAFS\tahoe.exe --version-and-path
) else (
    call :frozen-tahoe
)
call %PYTHON3% -m venv --clear .\build\venv-gridsync
call .\build\venv-gridsync\Scripts\activate
call pip install --upgrade setuptools pip
call pip install -r .\requirements\requirements-hashes.txt
call pip install . 
call pip install pyinstaller==3.3.1
call pip list
call set PYTHONHASHSEED=1
call pyinstaller -y --clean misc\gridsync.spec
call set PYTHONHASHSEED=
call deactivate
goto :eof
