# -*- coding: utf-8 -*-
"""
Configuracao da ponte com o navegador.

- navegador.json (ignorado pelo Git): porta e token, criados na primeira execucao.
- extensao/config.local.js (ignorado pelo Git): copia desses dados que a extensao le.
  Assim voce nao precisa copiar o token na mao. Se ele mudar, recarregue a extensao.
"""

import json
import os
import secrets
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "navegador.json"
EXTENSAO_CONFIG = RAIZ / "extensao" / "config.local.js"
PORTA_PADRAO = 8765


def carregar(caminho=ARQUIVO):
    """Le (ou cria) a configuracao. A variavel JARVIS_NAVEGADOR_PORTA tem prioridade."""
    cfg = {}
    if caminho.exists():
        try:
            cfg = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cfg = {}

    mudou = False
    if not isinstance(cfg.get("porta"), int):
        cfg["porta"] = PORTA_PADRAO
        mudou = True
    if not cfg.get("token"):
        cfg["token"] = secrets.token_urlsafe(24)
        mudou = True
    if mudou:
        caminho.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    porta_env = os.environ.get("JARVIS_NAVEGADOR_PORTA", "").strip()
    if porta_env.isdigit():
        cfg = dict(cfg, porta=int(porta_env))
    return cfg


def gravar_para_extensao(cfg, caminho=EXTENSAO_CONFIG):
    """Escreve config.local.js para a extensao, so se o conteudo mudou."""
    conteudo = "self.JARVIS_CONFIG = {0};\n".format(
        json.dumps({"porta": cfg["porta"], "token": cfg["token"]}))
    try:
        if caminho.exists() and caminho.read_text(encoding="utf-8") == conteudo:
            return False
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
        return True
    except OSError:
        return False
