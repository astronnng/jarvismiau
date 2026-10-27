# -*- coding: utf-8 -*-
"""
Escolher-voz: ouve as vozes brasileiras e grava a sua favorita no jarvis.py
---------------------------------------------------------------------------
Rode com dois cliques em "Escolher-voz.bat" (ou: python escolher_voz.py).
Nada e instalado aqui: ele usa as mesmas bibliotecas do Jarvis.
"""

import os
import re
import sys
import time
import asyncio
import tempfile
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import jarvis  # noqa: E402  (para reaproveitar os perfis de voz)

FRASE = ("Boa noite, senhor. Todos os sistemas estao online. "
         "Sao quatorze horas e vinte e dois minutos, e esta vinte e dois graus em Bariri.")

# (perfil, rotulo, descricao)
OPCOES = [
    ("BR_ANTONIO",       "Antonio",            "brasileira nativa, masculina, grave e neutra"),
    ("BR_ANTONIO_GRAVE", "Antonio mais grave", "a mesma voz, mais lenta e solene"),
    ("BR_ANDREW",        "Andrew",             "timbre encorpado, sotaque leve"),
    ("BR_BRIAN",         "Brian",              "jovem e conversacional"),
    ("BR_GIUSEPPE",      "Giuseppe",           "caloroso, sotaque perceptivel"),
    ("BR_REMY",          "Remy",               "suave, sotaque perceptivel"),
    ("BR_FRANCISCA",     "Francisca",          "brasileira nativa, feminina"),
    ("BR_THALITA",       "Thalita",            "brasileira, feminina e mais jovem"),
    ("JARVIS",           "JARVIS britanico",   "a voz dos filmes (responde em ingles)"),
    ("WINDOWS",          "Windows",            "offline, robotica, sem internet"),
]


def tocar(caminho):
    try:
        import pygame

        pygame.mixer.init()
        pygame.mixer.music.load(caminho)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
        return True
    except Exception:
        pass
    try:
        os.startfile(caminho)  # noqa: S606 (Windows)
        time.sleep(4)
        return True
    except Exception:
        print(f"  (nao consegui tocar o audio aqui; abra manualmente: {caminho})")
        return False


def falar_perfil(perfil_nome):
    """Gera e toca a frase de teste com o perfil escolhido."""
    perfil = jarvis.PERFIS[perfil_nome]

    if perfil["motor"] == "sapi":
        jarvis.PERFIL = perfil
        jarvis.falar(FRASE)
        return

    try:
        import edge_tts
    except ImportError:
        print("  Falta a biblioteca edge-tts. Rode o instalar.bat primeiro.")
        return

    arq = os.path.join(tempfile.gettempdir(), "jarvis_teste_voz.mp3")

    async def gerar():
        com = edge_tts.Communicate(
            FRASE, perfil["voz"],
            rate=perfil.get("rate", "+0%"),
            pitch=perfil.get("pitch", "+0Hz"),
        )
        await com.save(arq)

    try:
        asyncio.run(gerar())
    except Exception:
        print("  Nao consegui gerar o audio (sem internet?). Tente de novo.")
        return
    tocar(arq)


def gravar_escolha(perfil_nome):
    alvo = AQUI / "jarvis.py"
    texto = alvo.read_text(encoding="utf-8")
    novo, n = re.subn(r'^VOZ = "[^"]*"', f'VOZ = "{perfil_nome}"', texto,
                      count=1, flags=re.M)
    if n == 0:
        print("Nao achei a linha VOZ = ... no jarvis.py. Edite manualmente.")
        return False
    alvo.write_text(novo, encoding="utf-8")
    return True


def menu():
    print("=" * 62)
    print("   ESCOLHEDOR DE VOZ DO JARVIS")
    print("=" * 62)
    for i, (_, rotulo, desc) in enumerate(OPCOES, start=1):
        print(f"  {i:2d}. {rotulo:<20} {desc}")
    print("   q. sair sem alterar")
    print("=" * 62)
    print("Dica: ouça cada uma com o numero; depois aperte 's' na pergunta")
    print("      para gravar a que voce gostou no Jarvis.\n")


def main():
    atual = re.search(r'^VOZ = "([^"]*)"', (AQUI / "jarvis.py").read_text(encoding="utf-8"),
                      re.M)
    if atual:
        print(f"Voz configurada no momento: {atual.group(1)}\n")

    ultima = None
    while True:
        menu()
        escolha = input("Numero da voz (ou ENTER para repetir a ultima): ").strip().lower()

        if escolha in ("q", "sair"):
            print("Nada foi alterado.")
            return

        if escolha == "":
            if not ultima:
                continue
            perfil_nome = ultima
        elif escolha.isdigit() and 1 <= int(escolha) <= len(OPCOES):
            perfil_nome = OPCOES[int(escolha) - 1][0]
            ultima = perfil_nome
        else:
            print("Opcao invalida.\n")
            continue

        rotulo = next(r for p, r, _ in OPCOES if p == perfil_nome)
        print(f"\n>>> Tocando: {rotulo} ({perfil_nome})...")
        falar_perfil(perfil_nome)
        print()

        resp = input("Usar esta voz no Jarvis? (s/n) ").strip().lower()
        if resp.startswith("s"):
            if gravar_escolha(perfil_nome):
                print(f"\nPronto! O jarvis.py agora usa VOZ = \"{perfil_nome}\".")
                print("Abra o Jarvis.bat e ele ja falara com essa voz.\n")
            return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado. Nada foi alterado.")
