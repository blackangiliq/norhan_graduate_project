@echo off
chcp 65001 >nul
rem Opens the SecureVoice ports in Windows Firewall. Must run as Administrator.
net session >nul 2>&1
if errorlevel 1 (
  echo Requesting Administrator rights...
  powershell -Command "Start-Process '%~f0' -Verb RunAs"
  exit /b
)
netsh advfirewall firewall delete rule name="SecureVoice TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="SecureVoice UDP" >nul 2>&1
netsh advfirewall firewall add rule name="SecureVoice TCP" dir=in action=allow protocol=TCP localport=5000 profile=any
netsh advfirewall firewall add rule name="SecureVoice UDP" dir=in action=allow protocol=UDP localport=5001-5002 profile=any
echo.
echo [OK] Firewall rules added: TCP 5000 , UDP 5001-5002
pause
