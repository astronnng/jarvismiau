# -*- coding: utf-8 -*-
"""
Configurar a IA do Jarvis (gratis)
----------------------------------
Pede a chave do Google AI Studio, testa quais modelos gratuitos funcionam
na sua chave e grava tudo em dados/ia_config.json.

Rode com `Jarvis.bat ia`.
"""

import sys
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import cerebro  # noqa: E402

CANDIDATOS = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


def mascarar(chave):
    if not chave:
        return "(vazia)"
    if len(chave) <= 10:
        return chave[:2] + "***"
    return chave[:6] + "..." + chave[-4:]


def descobrir_modelo(api_key):
    """Testa os modelos gratuitos em ordem e devolve os que funcionam."""
    funcionando = []
    for modelo in CANDIDATOS:
        print(f"   testando {modelo}... ", end="", flush=True)
        ok, msg = cerebro.testar_chave(api_key, modelo)
        if ok:
            print("OK")
            funcionando.append(modelo)
            if len(funcionando) >= 2:
                break
        else:
            print("nao disponivel")
    return funcionando


def main():
    cfg = cerebro.carregar_config()

    print("=" * 64)
    print("   IA DO JARVIS  (entender frases livres) - configuracao")
    print("=" * 64)
    print()
    print("O que isso muda: sem IA, o Jarvis entende apenas comandos conhecidos")
    print('("que horas sao", "abrir youtube"). Com IA, ele entende frases livres')
    print('como "dar play no spotify", "quanto ta o dolar" e decide sozinho.')
    print()

    if cfg.get("api_key"):
        print(f"Chave atual: {mascarar(cfg['api_key'])}")
        print(f"Modelo: {cfg.get('modelo')}")
        print()
        resp = input("Quer trocar a chave? (s/n) ").strip().lower()
        if not resp.startswith("s"):
            alvo = input("Testar a configuracao atual? (s/n) ").strip().lower()
            if alvo.startswith("s"):
                ok, msg = cerebro.testar_chave()
                print(("OK: " if ok else "FALHOU: ") + msg)
            return
        print()

    print("-" * 64)
    print("COMO PEGAR A CHAVE GRATIS (2 minutos):")
    print("  1. Abra https://aistudio.google.com/apikey")
    print("  2. Entre com sua conta Google")
    print('  3. Clique em "Create API key" (criar chave de API)')
    print("  4. Copie a chave e cole aqui embaixo")
    print("-" * 64)
    print()

    api_key = input("Cole a chave (ou ENTER para pular): ").strip()

    if not api_key:
        print("\nSem chave. O Jarvis continua funcionando com as regras locais.")
        return

    if len(api_key) < 20:
        print("\nIsso nao parece uma chave valida (curta demais).")
        print("A chave do Google AI Studio comeca com 'AIza' e tem ~39 caracteres.")
        return

    print("\nTestando a chave nos modelos gratuitos...")
    funcionando = descobrir_modelo(api_key)

    if not funcionando:
        print()
        print("Nenhum modelo respondeu. Possiveis causas:")
        print("  - chave copiada pela metade (confira se comeca com AIza)")
        print("  - a chave foi criada em um projeto sem a API habilitada")
        print("  - sem internet agora")
        print()
        guardar = input("Guardar assim mesmo para tentar depois? (s/n) ").strip().lower()
        if not guardar.startswith("s"):
            return
        cfg.update({"api_key": api_key, "ativo": True})
        cerebro.salvar_config(cfg)
        print("Chave guardada. Rode este configurador de novo para testar.")
        return

    cfg.update({
        "api_key": api_key,
        "modelo": funcionando[0],
        "modelos_alternativos": funcionando[1:] + [m for m in CANDIDATOS if m not in funcionando][:3],
        "ativo": True,
    })
    cerebro.salvar_config(cfg)

    print()
    print("=" * 64)
    print("   PRONTO! IA ATIVA")
    print("=" * 64)
    print(f"Modelo principal: {funcionando[0]}")
    if len(funcionando) > 1:
        print(f"Alternativos:     {', '.join(funcionando[1:])}")
    print()
    print("Agora abra o Jarvis.bat e tente:")
    print('   "dar play no spotify"')
    print('   "abre o netflix e aumenta o volume"')
    print('   "quanto ta o dolar"')
    print('   "me lembra em 10 minutos de tirar o bolo"')
    print()
    print("Arquivo salvo: dados/ia_config.json (nao compartilhe: contem sua chave).")
    print()
    print("Quer desligar a IA depois? Use Jarvis.bat --sem-ia ou apague o dados/ia_config.json.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado.")
