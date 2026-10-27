@echo off
chcp 65001 >nul
title Jarvis - configurar IA
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
    echo Rode primeiro o arquivo instalar.bat
    pause
    exit /b
)
call ".venv\Scripts\activate.bat"
python configurar_ia.py
pause
