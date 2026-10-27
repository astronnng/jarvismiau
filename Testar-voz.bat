@echo off
chcp 65001 >nul
title Jarvis - teste de voz
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
    echo Rode primeiro o arquivo instalar.bat
    pause
    exit /b
)
call ".venv\Scripts\activate.bat"
echo Ouvindo a voz configurada no momento...
python jarvis.py --demo
pause
