@echo off
chcp 65001 >nul
title Jarvis - escolher voz
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
    echo Rode primeiro o arquivo instalar.bat
    pause
    exit /b
)
call ".venv\Scripts\activate.bat"
python escolher_voz.py
pause
