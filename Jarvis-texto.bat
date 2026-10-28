@echo off
chcp 65001 >nul
title Jarvis - modo texto
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
    echo Rode primeiro o arquivo instalar.bat
    pause
    exit /b
)
call ".venv\Scripts\activate.bat"
set "JARVIS_INTERACTIVE=1"
python jarvis.py --texto
pause
