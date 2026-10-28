# -*- coding: utf-8 -*-
"""
Controle do navegador do usuario (com a sessao logada) pela extensao em extensao/.

Camadas (cada uma so conhece a de baixo):
  generico.py   tarefas livres: o Gemini escolhe elementos de um snapshot da pagina
  atalhos.py    fluxos prontos e exatos: YouTube, Google, Gmail, URLs
  ponte.py      servidor local HTTP que conversa com a extensao
  config.py     porta e token

As acoes do catalogo que usam isto ficam em acoes_navegador.py.
Documentacao completa: docs/NAVEGADOR.md
"""

from . import config
from .ponte import ErroNavegador, Ponte

_ponte = None


def iniciar():
    """Cria e sobe a ponte (idempotente). Devolve True se o servidor esta no ar."""
    global _ponte
    if _ponte is not None and _ponte.ativa():
        return True
    cfg = config.carregar()
    config.gravar_para_extensao(cfg)
    _ponte = Ponte(cfg["porta"], cfg["token"])
    return _ponte.iniciar()


def parar():
    global _ponte
    if _ponte is not None:
        _ponte.parar()
        _ponte = None


def ponte():
    """A ponte em uso; sobe sob demanda. Testes podem trocar por `definir_ponte`."""
    if _ponte is None:
        iniciar()
    return _ponte


def definir_ponte(nova):
    global _ponte
    _ponte = nova


def conectado():
    return _ponte is not None and _ponte.ativa() and _ponte.conectado()


def enviar(cmd, timeout=15, **args):
    """Atalho: executa um comando na extensao. Levanta ErroNavegador em falha."""
    p = ponte()
    if p is None:
        raise ErroNavegador("A ponte do navegador nao esta ativa.")
    return p.enviar(cmd, timeout=timeout, **args)


__all__ = ["ErroNavegador", "Ponte", "iniciar", "parar", "ponte", "definir_ponte",
           "conectado", "enviar"]
