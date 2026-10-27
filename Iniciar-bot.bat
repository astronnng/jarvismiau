@echo off
chcp 65001 >nul
title Jarvis - bot do Telegram
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
    echo Rode primeiro o arquivo instalar.bat
    pause
    exit /b
)
call ".venv\Scripts\activate.bat"
python telegram_bot.py
echo.
echo O bot foi encerrado.
pause
