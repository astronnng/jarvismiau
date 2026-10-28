# -*- coding: utf-8 -*-
"""Catalogo de sites e programas editavel sem reiniciar o Jarvis."""

import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit


PASTA = Path(__file__).resolve().parent
EXEMPLO_PATH = PASTA / "config.example.json"
CONFIG_PATH = PASTA / "config.json"
_cache = {"mtime_ns": None, "config": None}
_ultimo_erro = None


def normalizar(texto):
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto).strip()


def _ler_exemplo():
    try:
        dados = json.loads(EXEMPLO_PATH.read_text(encoding="utf-8"))
        return _validar_estrutura(dados)
    except (OSError, ValueError, TypeError):
        return {"sites": {}, "programas": {}}


def _validar_estrutura(dados):
    if not isinstance(dados, dict):
        raise ValueError("A raiz precisa ser um objeto JSON.")
    saida = {"sites": {}, "programas": {}}
    for secao in saida:
        valores = dados.get(secao, {})
        if not isinstance(valores, dict):
            raise ValueError(f'A secao "{secao}" precisa ser um objeto JSON.')
        for nome, destino in valores.items():
            chave = normalizar(nome)
            destino = str(destino or "").strip()
            if chave and destino:
                saida[secao][chave] = destino
    return saida


def _salvar_atomico(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(prefix="config-", suffix=".tmp", dir=caminho.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, indent=2, ensure_ascii=False)
            arquivo.write("\n")
        os.replace(temporario, caminho)
    finally:
        if os.path.exists(temporario):
            os.unlink(temporario)


def carregar(forcar=False):
    """Lê config.json; cria a cópia local e atualiza o cache quando o arquivo muda."""
    global _cache, _ultimo_erro
    padrao = _ler_exemplo()
    if not CONFIG_PATH.exists():
        try:
            _salvar_atomico(CONFIG_PATH, padrao)
        except OSError:
            pass

    try:
        mtime_ns = CONFIG_PATH.stat().st_mtime_ns
        if not forcar and _cache["mtime_ns"] == mtime_ns and _cache["config"] is not None:
            return _cache["config"]
        dados = _validar_estrutura(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        # Arquivos parciais podem substituir algumas entradas sem apagar os padrões.
        config = {secao: dict(padrao[secao]) for secao in padrao}
        for secao in config:
            config[secao].update(dados[secao])
        _cache = {"mtime_ns": mtime_ns, "config": config}
        _ultimo_erro = None
        return config
    except (OSError, ValueError, TypeError) as erro:
        if _ultimo_erro != str(erro):
            print(f"(config.json invalido ou inacessivel; mantendo o ultimo catalogo valido: {erro})")
            _ultimo_erro = str(erro)
        if _cache["config"] is not None:
            return _cache["config"]
        return padrao


def validar_entrada(tipo, nome, destino):
    tipo = normalizar(tipo)
    nome = normalizar(nome)
    destino = str(destino or "").strip().strip('"')
    if tipo not in ("site", "programa"):
        return False, "Tipo invalido. Use site ou programa."
    if not nome or len(nome) > 80:
        return False, "O nome precisa ter entre 1 e 80 caracteres."
    if not destino or len(destino) > 1000:
        return False, "O destino informado esta vazio ou e longo demais."

    if tipo == "site":
        partes = urlsplit(destino)
        if partes.scheme not in ("http", "https") or not partes.netloc:
            return False, "Informe uma URL completa com http:// ou https://."
        return True, ""

    # Apps novos recebem somente caminho absoluto ou URI de aplicativo; sem shell.
    if os.path.isabs(destino):
        if not os.path.isfile(destino):
            return False, "O caminho do programa precisa apontar para um arquivo existente."
        return True, ""
    partes = urlsplit(destino)
    esquema = partes.scheme.lower()
    if esquema and esquema not in {"http", "https", "file", "javascript", "data"}:
        return True, ""
    return False, "Informe o caminho absoluto do executavel ou uma URI de aplicativo (por exemplo, spotify:)."


def salvar_entrada(tipo, nome, destino):
    """Salva uma entrada depois de validada; quem chama deve coletar confirmacao."""
    tipo = normalizar(tipo)
    nome = normalizar(nome)
    destino = str(destino or "").strip().strip('"')
    ok, mensagem = validar_entrada(tipo, nome, destino)
    if not ok:
        return False, mensagem
    config = carregar(forcar=True)
    secao = "sites" if tipo == "site" else "programas"
    config[secao][nome] = destino
    try:
        _salvar_atomico(CONFIG_PATH, config)
        global _cache, _ultimo_erro
        _cache = {"mtime_ns": None, "config": config}
        _ultimo_erro = None
    except OSError as erro:
        return False, f"Nao consegui salvar config.json: {erro}"
    return True, f'{"Site" if tipo == "site" else "Programa"} "{nome}" cadastrado.'


def resetar_cache():
    """Uso interno de testes e para forcar nova leitura."""
    global _cache, _ultimo_erro
    _cache = {"mtime_ns": None, "config": None}
    _ultimo_erro = None
