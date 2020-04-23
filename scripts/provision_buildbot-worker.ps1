py -2 -m pip install --upgrade buildbot-worker pywin32
C:\\Python27\\Scripts\\buildbot-worker.exe create-worker C:\\Users\\Vagrant\\buildbot $Env:BUILDBOT_HOST $Env:BUILDBOT_NAME $Env:BUILDBOT_PASS
"C:\\Python27\\Scripts\\buildbot-worker.exe restart C:\\Users\\vagrant\\buildbot" | Out-File -FilePath "C:\\Users\\vagrant\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\run-buildbot-worker.bat" -Encoding Ascii
