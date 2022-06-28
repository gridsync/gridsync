:: This script assumes that the dependencies listed in
:: scripts/provision_devtools.bat have already been installed.

@echo off

set PY_PYTHON=3.10

if "%1"=="clean" call :clean
if "%1"=="test" call :test
if "%1"=="test-integration" call :test-integration
if "%1"=="pyinstaller" call :pyinstaller
if "%1"=="zip" call :zip
if "%1"=="test-determinism" call :test-determinism
if "%1"=="installer" call :installer
if "%1"=="vagrant-build-linux" call :vagrant-build-linux
if "%1"=="vagrant-build-macos" call :vagrant-build-macos
if "%1"=="vagrant-build-windows" call :vagrant-build-windows
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
call rmdir /s /q .\.pytest_cache
call rmdir /s /q .\.mypy_cache
for /d /r %%i in (*__pycache__*) do rmdir /s /q "%%i"
call del .\.coverage
goto :eof

:test
py -m tox || goto :error
goto :eof

:test-integration
py -m tox -e integration || goto :error
goto :eof

:pyinstaller-separate
py -m tox -e pyinstaller-tahoe || goto :error
py -m tox -e pyinstaller-magic-folder || goto :error
py -m tox -e pyinstaller-gridsync || goto :error
goto :eof

:pyinstaller-merged
py -m tox -e pyinstaller || goto :error
goto :eof

:pyinstaller
call :pyinstaller-merged
goto :eof

:zip
py .\scripts\update_permissions.py .\dist || goto :error
py .\scripts\update_timestamps.py .\dist || goto :error
py .\scripts\make_zip.py || goto :error
goto :eof

:test-determinism
py .\scripts\test_determinism.py || goto :error
goto :eof

:installer
call py .\scripts\make_installer.py || goto :error
goto :eof


:vagrant-build-linux
call vagrant up centos-7
call vagrant provision --provision-with devtools,test,build centos-7
goto :eof

:vagrant-build-macos
call vagrant up --provision-with devtools,test,build macos-10.14
goto :eof

:vagrant-build-windows
call vagrant up --provision-with devtools,test,build windows-10
goto :eof


:all
call :pyinstaller
call :zip
call :installer
call py .\scripts\sha256sum.py .\dist\*.*
goto :eof

:error
echo Error in batch file; exiting with error level %errorlevel%
exit %errorlevel%
