# -*- coding: utf-8 -*-
"""
LANCADOR - um unico ponto de entrada para tudo que o Jarvis faz
----------------------------------------------------------------
Usado pelo Jarvis.bat (que so ativa o ambiente e chama este arquivo):

  Jarvis.bat                  menu; sem tecla em 60 s inicia no modo "voz"
  Jarvis.bat voz              diga "Jarvis" e o comando (o padrao de sempre)
  Jarvis.bat texto            digite os comandos (painel e menu de /)
  Jarvis.bat continuo         atende qualquer fala, sem palavra de ativacao
  Jarvis.bat enter            aperte ENTER antes de falar
  Jarvis.bat bot              bot do Telegram
  Jarvis.bat ia               configurar o cerebro de IA (Gemini)
  Jarvis.bat testar-voz       fala uma frase com a voz configurada
  Jarvis.bat escolher-voz     toca os perfis de voz e grava o escolhido

Opcoes extras vao direto para o programa: `Jarvis.bat texto --sem-ia`, `Jarvis.bat voz --latencia`.
Tambem aceita as opcoes antigas sem modo: `Jarvis.bat --sem-ia` equivale a `Jarvis.bat voz --sem-ia`.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ESPERA_MENU_S = 60

# modo -> (script, opcoes fixas, variaveis de ambiente, titulo da janela)
MODOS = {
    "voz": ("jarvis.py", [], {}, "Jarvis - diga Jarvis para ativar"),
    "texto": ("jarvis.py", ["--texto"], {"JARVIS_INTERACTIVE": "1"}, "Jarvis - modo texto"),
    "continuo": ("jarvis.py", ["--continuo"], {}, "Jarvis - escuta continua (sem palavra)"),
    "enter": ("jarvis.py", ["--pressione"], {}, "Jarvis - aperte ENTER para falar"),
    "bot": ("telegram_bot.py", [], {}, "Jarvis - bot do Telegram"),
    "ia": ("configurar_ia.py", [], {}, "Jarvis - configurar IA"),
    "testar-voz": ("jarvis.py", ["--demo"], {}, "Jarvis - teste de voz"),
    "escolher-voz": ("escolher_voz.py", [], {}, "Jarvis - escolher voz"),
}
# nomes antigos dos modos (e dos .bat que existiam) continuam valendo
APELIDOS = {"palavra": "voz", "pressione": "enter", "telegram": "bot", "testarvoz": "testar-voz",
            "escolhervoz": "escolher-voz", "configurar-ia": "ia"}

MENU = [
    ("1", "voz", 'Voz: diga "Jarvis" e o comando (padrão)'),
    ("2", "texto", "Texto: digite os comandos"),
    ("3", "continuo", "Voz contínua: sem palavra de ativação"),
    ("4", "enter", "Voz com ENTER: aperte antes de falar"),
    ("5", "bot", "Bot do Telegram"),
    ("6", "ia", "Configurar a IA (Gemini)"),
    ("7", "testar-voz", "Testar a voz"),
    ("8", "escolher-voz", "Escolher a voz (comparar perfis)"),
    ("0", None, "Sair"),
]


class ErroDeUso(Exception):
    """Argumentos que o lancador nao entende; a mensagem ja e para o usuario."""


def interpretar(args):
    """
    args (sem o nome do programa) -> (modo, extras). Sem argumentos: (None, []) = mostrar o menu.
    Opcoes antigas sem modo (ex.: --sem-ia) vao para o modo "voz".
    """
    args = list(args)
    if not args:
        return None, []
    primeiro = args[0].lower()
    if primeiro in ("ajuda", "-h", "--ajuda", "--help", "?"):
        raise ErroDeUso(ajuda())
    if primeiro.startswith("-"):
        return "voz", args
    modo = APELIDOS.get(primeiro, primeiro)
    if modo not in MODOS:
        raise ErroDeUso(f'Não conheço o modo "{args[0]}".\n\n' + ajuda())
    return modo, args[1:]


def montar(modo, extras=(), raiz=RAIZ, executavel=None):
    """(comando, ambiente) para rodar o modo. O ambiente herda o atual."""
    script, fixas, ambiente, _ = MODOS[modo]
    comando = [executavel or sys.executable, str(Path(raiz) / script), *fixas, *extras]
    return comando, dict(os.environ, **ambiente)


def ajuda():
    linhas = ["Uso: Jarvis.bat [modo] [opções]", ""]
    nomes = {modo: descricao for _, modo, descricao in MENU if modo}
    for modo in MODOS:
        linhas.append(f"  {modo:<13} {nomes.get(modo, '')}")
    linhas += ["", "Sem modo, mostra um menu e, em %d s sem tecla, inicia o modo voz." % ESPERA_MENU_S]
    return "\n".join(linhas)


# ------------------------------------------------------------------------- menu
def _tecla_windows(timeout):
    """Espera uma tecla por `timeout` segundos. Devolve o caractere ou None."""
    import msvcrt

    fim = time.monotonic() + timeout
    while time.monotonic() < fim:
        if msvcrt.kbhit():
            return msvcrt.getwch()
        time.sleep(0.05)
    return None


def _tecla_padrao(timeout):
    if os.name == "nt" and sys.stdin is not None and sys.stdin.isatty():
        try:
            return _tecla_windows(timeout)
        except Exception:
            return None
    return None                          # sem teclado interativo: segue no padrao


def desenhar_menu(imprimir=print, contagem=None):
    imprimir("")
    imprimir("  ◈  J.A.R.V.I.S")
    imprimir("  ─────────────────────────────────────────────")
    for numero, modo, descricao in MENU:
        imprimir(f"   {numero}  {descricao}")
    imprimir("  ─────────────────────────────────────────────")
    if contagem:
        imprimir(f"  Iniciando o modo voz em {contagem} s. Aperte uma tecla para escolher.")


def escolher_modo(tecla=_tecla_padrao, imprimir=print, espera=ESPERA_MENU_S):
    """Mostra o menu e devolve o modo escolhido (None = sair). Sem tecla: o modo voz."""
    desenhar_menu(imprimir, contagem=espera)
    primeira = tecla(espera)
    if primeira is None or primeira in ("\r", "\n"):
        return "voz"
    validas = {numero: modo for numero, modo, _ in MENU}
    atual = primeira
    while True:
        if atual in validas:
            return validas[atual]
        imprimir("  Opção inválida. Escolha um número do menu (ENTER = voz).")
        atual = tecla(3600)
        if atual is None or atual in ("\r", "\n"):
            return "voz"


# ----------------------------------------------------------------------- execucao
def definir_titulo(texto):
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(texto)
    except Exception:
        pass


def executar(modo, extras=(), rodar=subprocess.call, imprimir=print):
    comando, ambiente = montar(modo, extras)
    definir_titulo(MODOS[modo][3])
    if modo == "testar-voz":
        imprimir("Ouvindo a voz configurada no momento...")
    try:
        codigo = rodar(comando, env=ambiente, cwd=str(RAIZ))
    except KeyboardInterrupt:
        codigo = 0
    if modo == "bot":
        imprimir("O bot foi encerrado.")
    return codigo


def main(argv=None, tecla=_tecla_padrao, rodar=subprocess.call, imprimir=print):
    try:
        modo, extras = interpretar(sys.argv[1:] if argv is None else argv)
    except ErroDeUso as erro:
        imprimir(str(erro))
        return 0 if str(erro) == ajuda() else 2
    if modo is None:
        modo = escolher_modo(tecla, imprimir)
        if modo is None:
            return 0
    return executar(modo, extras, rodar, imprimir)


if __name__ == "__main__":
    sys.exit(main())
