# -*- coding: utf-8 -*-
"""
Download dos modelos do Kokoro (opcional).

Origem: release oficial "model-files-v1.0" do projeto kokoro-onnx no GitHub. Os dois arquivos
sao verificados por tamanho exato e SHA-256 (conferidos contra a release no dia da implementacao).
Se o projeto republicar um arquivo, a verificacao falha de proposito: confira a origem e
atualize ARQUIVOS abaixo.

Uso:  python -m voz.instalar        (pergunta antes de baixar)
      /voz kokoro instalar          (mesmo fluxo, dentro do Jarvis)
"""

import hashlib
import os
import sys
import urllib.request
from pathlib import Path

from . import config

ORIGEM = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
ARQUIVOS = [
    {"nome": "kokoro-v1.0.onnx", "tamanho": 325532387,
     "sha256": "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5"},
    {"nome": "voices-v1.0.bin", "tamanho": 28214398,
     "sha256": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"},
]
BLOCO = 1024 * 1024


class ErroInstalacao(Exception):
    pass


def faltando(pasta=None):
    """Arquivos ausentes ou com tamanho errado."""
    pasta = Path(pasta or config.PASTA_MODELOS)
    return [a for a in ARQUIVOS
            if not (pasta / a["nome"]).exists() or (pasta / a["nome"]).stat().st_size != a["tamanho"]]


def descricao(itens):
    partes = [f"{a['nome']} ({a['tamanho'] / 1e6:.0f} MB)" for a in itens]
    return " e ".join(partes) + " de github.com/thewh1teagle/kokoro-onnx (release model-files-v1.0)"


def _baixar(item, pasta, progresso):
    destino = pasta / item["nome"]
    parcial = destino.with_suffix(destino.suffix + ".part")
    sha = hashlib.sha256()
    baixado, ultimo = 0, -1
    try:
        with urllib.request.urlopen(ORIGEM + item["nome"], timeout=60) as resposta, \
                open(parcial, "wb") as saida:
            while True:
                bloco = resposta.read(BLOCO)
                if not bloco:
                    break
                saida.write(bloco)
                sha.update(bloco)
                baixado += len(bloco)
                pct = baixado * 100 // item["tamanho"]
                if progresso and pct // 10 != ultimo:
                    ultimo = pct // 10
                    progresso(f"  {item['nome']}: {min(pct, 100)}%")
        if baixado != item["tamanho"]:
            raise ErroInstalacao(f"{item['nome']}: tamanho inesperado ({baixado} bytes).")
        if sha.hexdigest() != item["sha256"]:
            raise ErroInstalacao(f"{item['nome']}: o SHA-256 nao confere; o arquivo foi descartado.")
        os.replace(parcial, destino)
    except (OSError, ErroInstalacao):
        parcial.unlink(missing_ok=True)
        raise


def instalar(confirmar=None, pasta=None, progresso=print):
    """
    Baixa o que falta. `confirmar(descricao) -> bool` e chamado antes de baixar (sem ele,
    nada e baixado). Devolve a lista de nomes baixados; levanta ErroInstalacao em falha.
    """
    pasta = Path(pasta or config.PASTA_MODELOS)
    itens = faltando(pasta)
    if not itens:
        return []
    if confirmar is None or not confirmar(descricao(itens)):
        return []
    pasta.mkdir(parents=True, exist_ok=True)
    baixados = []
    for item in itens:
        progresso(f"Baixando {item['nome']}...")
        try:
            _baixar(item, pasta, progresso)
        except OSError as erro:
            raise ErroInstalacao(f"falha de rede ou de disco em {item['nome']}: {erro}")
        baixados.append(item["nome"])
    return baixados


def _principal():
    itens = faltando()
    if not itens:
        print("Os modelos do Kokoro ja estao instalados em dados/modelos/kokoro.")
        return 0
    print("Vou baixar:", descricao(itens))
    print(f"Destino: {config.PASTA_MODELOS}")

    def perguntar(_):
        return input("Confirma o download? (s/n) ").strip().lower() in ("s", "sim", "y", "yes")

    try:
        baixados = instalar(perguntar)
    except ErroInstalacao as erro:
        print(f"Falhou: {erro}")
        return 1
    print("Pronto. No Jarvis, use /voz usar kokoro." if baixados else "Nada foi baixado.")
    return 0


if __name__ == "__main__":
    sys.exit(_principal())
