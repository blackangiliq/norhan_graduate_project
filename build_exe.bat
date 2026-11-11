@echo off
chcp 65001 >nul
rem Builds a standalone Windows program: dist\SecureVoice\SecureVoice.exe
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m pip install -q pyinstaller
pyinstaller --noconfirm SecureVoice.spec
if errorlevel 1 (
  echo [ERROR] Build failed
  pause
  exit /b 1
)
echo.
echo [OK] Done: dist\SecureVoice\SecureVoice.exe
echo Copy the whole dist\SecureVoice folder to the second computer.
pause
