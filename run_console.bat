@echo off
chcp 65001 >nul
rem Run with a console window to see any error messages
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python main.py
pause
