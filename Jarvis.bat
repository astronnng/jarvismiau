@echo off
chcp 65001 >nul
title Jarvis
cd /d "%~dp0"

rem Jarvis.bat                 menu (sem tecla em 60 s, inicia o modo voz)
rem Jarvis.bat texto           modo texto        Jarvis.bat continuo    voz sem palavra de ativacao
rem Jarvis.bat enter           voz com ENTER     Jarvis.bat bot         bot do Telegram
rem Jarvis.bat ia              configurar a IA   Jarvis.bat testar-voz  testar a voz
rem Jarvis.bat ajuda           lista todos os modos (opcoes extras: Jarvis.bat texto --sem-ia)

if not exist ".venv\Scripts\activate.bat" (
    echo Rode primeiro o arquivo Instalar.bat
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
python lancador.py %*
if errorlevel 1 pause
