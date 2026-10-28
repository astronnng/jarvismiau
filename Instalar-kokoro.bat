@echo off
chcp 65001 >nul
title Jarvis - instalar a voz Kokoro (opcional)
cd /d "%~dp0"

echo ==================================================
echo    VOZ KOKORO (opcional, roda no seu computador)
echo ==================================================
echo.
echo Isto instala a biblioteca (poucas centenas de MB) e, se voce
echo confirmar, baixa os modelos (cerca de 350 MB). Nada muda na voz
echo atual do Jarvis ate voce usar /voz usar kokoro.
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERRO] Rode primeiro o arquivo instalar.bat
    echo.
    pause
    exit /b
)
call ".venv\Scripts\activate.bat"

echo Instalando a biblioteca...
python -m pip install -r requirements-kokoro.txt
if errorlevel 1 (
    echo.
    echo [ERRO] A instalacao da biblioteca falhou. A voz atual continua funcionando.
    pause
    exit /b
)

echo.
python -m voz.instalar

echo.
echo ==================================================
echo    Pronto. No Jarvis (Jarvis-texto.bat), use:
echo      /voz kokoro testar   ouve a voz sem ativar
echo      /voz usar kokoro     ativa
echo      /voz                 ajusta mistura, idioma, velocidade
echo ==================================================
pause
