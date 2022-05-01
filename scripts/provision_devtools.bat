choco install -y --no-progress --require-checksums git
choco install -y --no-progress --require-checksums -m python3 --version 3.9.12
choco install -y --no-progress --require-checksums -m python3 --version 3.10.4
choco install -y --no-progress --require-checksums visualcpp-build-tools
choco install -y --no-progress --require-checksums innosetup
refreshenv
py -3 -m pip install --upgrade setuptools pip tox diffoscope
git config --global core.autocrlf false
reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f
