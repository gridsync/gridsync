buildbot-worker stop C:\\Users\\Vagrant\\buildbot
Remove-Item -Recurse -Force C:\\Users\\Vagrant\\buildbot
py -3 -m pip install --upgrade buildbot-worker pywin32
buildbot-worker create-worker C:\\Users\\Vagrant\\buildbot $Env:BUILDBOT_HOST $Env:BUILDBOT_NAME $Env:BUILDBOT_PASS
"buildbot-worker restart C:\\Users\\vagrant\\buildbot" | Out-File -FilePath "C:\\Users\\vagrant\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\run-buildbot-worker.bat" -Encoding Ascii
