::
:: This script assumes that the following dependencies have been installed:
::
::  1) Git <https://git-scm.com/download/win>
::
::  2) Python 2.7 <https://www.python.org>
::
::  3) Python 3.7 <https://www.python.org>
::      -Select "Add Python 3.7 to PATH" option during install
::      -On Windows Server 2012, if installation fails, try installing update "KB2919355". See https://bugs.python.org/issue29583
::
::  4) Microsoft Visual C++ Compiler for Python 2.7 <https://aka.ms/vcpython27>
::
::  5) Microsoft .NET Framework Dev Pack <https://aka.ms/dotnet-download>
::
::  6) Microsoft Visual C++ Build Tools 2015 <https://aka.ms/buildtools>
::      -Select "Windows 8.1 SDK" and "Windows 10 SDK" options during install
::
::  7) Inno Setup <http://www.jrsoftware.org/isinfo.php>
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
    set PYTHON3=py -3
)

if "%1"=="clean" call :clean
if "%1"=="test" call :test
if "%1"=="frozen-tahoe" call :frozen-tahoe
if "%1"=="pyinstaller" call :pyinstaller
if "%1"=="installer" call :installer
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

:frozen-tahoe
call %PYTHON2% -m pip install --upgrade setuptools pip virtualenv
call %PYTHON2% -m virtualenv --clear .\build\venv-tahoe
call .\build\venv-tahoe\Scripts\activate
call python -m pip install --upgrade setuptools pip
call git clone https://github.com/tahoe-lafs/tahoe-lafs.git .\build\tahoe-lafs
call copy .\misc\tahoe.spec .\build\tahoe-lafs\pyinstaller.spec
call pushd .\build\tahoe-lafs
call git checkout 7263ceb1d112c6a90d90dcc6303eb425051fff50
call python setup.py update_version
call python -m pip install pyrsistent==0.14.11
call python -m pip install .
call python -m pip install packaging
:: Adding --no-use-pep517 suggested by https://github.com/pypa/pip/issues/6163
call python -m pip install --no-use-pep517 pyinstaller==3.4
call python -m pip list
call set PYTHONHASHSEED=1
call pyinstaller pyinstaller.spec
call set PYTHONHASHSEED=
call move dist ..\..
call popd
call deactivate
goto :eof

:pyinstaller
if not exist ".\dist\Tahoe-LAFS" call :frozen-tahoe
%PYTHON3% -m tox -e pyinstaller
goto :eof

:installer
call copy misc\InnoSetup5.iss .
call copy misc\InnoSetup6.iss .
call "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" .\InnoSetup6.iss || "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" .\InnoSetup5.iss
goto :eof

:all
call :pyinstaller
call :installer
call %PYTHON3% .\scripts\sha256sum.py .\dist\*.*
goto :eof
