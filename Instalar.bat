@echo off
chcp 65001 >nul
title Instalando o Jarvis
cd /d "%~dp0"

rem Instalar.bat          instala o Jarvis (ambiente isolado + bibliotecas)
rem Instalar.bat kokoro   instala a voz Kokoro, opcional e local (requer o Jarvis ja instalado)
if /i "%~1"=="kokoro" goto kokoro

echo ==================================================
echo    INSTALANDO O JARVIS  (leva 1 a 3 minutos)
echo ==================================================
echo.

set "PYTHON=python"
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON=py -3.12"
)

%PYTHON% --version >nul 2>nul
if errorlevel 1 (
    echo [ERRO] O Python nao foi encontrado neste computador.
    echo.
    echo Baixe em: https://www.python.org/downloads/
    echo IMPORTANTE: na primeira tela do instalador, marque a caixa
    echo "Add python.exe to PATH" antes de clicar em Install Now.
    echo Depois de instalar, feche esta janela e rode este arquivo de novo.
    echo.
    pause
    exit /b
)

echo Python encontrado:
%PYTHON% --version
echo.

if not exist ".venv" (
    echo Criando ambiente isolado do Jarvis...
    %PYTHON% -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo Atualizando o instalador de pacotes...
python -m pip install --upgrade pip >nul

echo Baixando as bibliotecas de voz (pode demorar)...
python -m pip install -r requirements.txt

echo.
echo Testando a instalacao...
python -c "import pyttsx3, speech_recognition; from pycaw.pycaw import AudioUtilities; print('Bibliotecas OK')"
if errorlevel 1 (
    echo.
    echo [AVISO] Alguma biblioteca falhou. Se o erro falar de "PyAudio",
    echo instale o Python 3.12 e rode este arquivo novamente.
    echo Mesmo assim, voce ja pode usar o Jarvis digitando:
    echo     Jarvis.bat texto
    echo.
    pause
    exit /b
)

echo.
echo ==================================================
echo    PRONTO! Agora abra o arquivo Jarvis.bat
echo ==================================================
pause
exit /b

:kokoro
echo ==================================================
echo    VOZ KOKORO (opcional, roda no seu computador)
echo ==================================================
echo.
echo Isto instala a biblioteca (poucas centenas de MB) e, se voce
echo confirmar, baixa os modelos (cerca de 350 MB) para dados\modelos.
echo Nada muda na voz atual do Jarvis ate voce usar /voz usar kokoro.
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERRO] Rode primeiro o arquivo Instalar.bat
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
echo    Pronto. No Jarvis (Jarvis.bat texto), use:
echo      /voz kokoro testar   ouve a voz sem ativar
echo      /voz usar kokoro     ativa
echo      /voz                 ajusta mistura, idioma, velocidade
echo ==================================================
pause
