Invoke-WebRequest -Uri https://www.digicert.com/StaticFiles/SafeNetAuthenticationClient-x64.msi -OutFile C:\tmp\SafeNetAuthenticationClient-x64.msi -UseBasicParsing
msiexec.exe /i "C:\tmp\SafeNetAuthenticationClient-x64.msi"
