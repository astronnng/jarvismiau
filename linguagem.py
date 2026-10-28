# -*- coding: utf-8 -*-
"""
LINGUAGEM - tolerancia a fala natural nas regras locais
--------------------------------------------------------
As regras locais (regex) sao rapidas mas literais. Antes de aplicar as do navegador e de
procurar no cache de planos, o texto passa por `tirar_enchimento`, que remove o que as
pessoas dizem sem mudar o pedido:

  "Jarvis, por favor, pode abrir o segundo video pra mim?"  ->  "abrir o segundo video"
  "da pra pesquisar lofi no youtube ai"                       ->  "pesquisar lofi no youtube"

Nao troca palavras do pedido (verbos, numeros, termos de busca) e preserva acentos e
maiusculas do que sobrar, para o termo pesquisado sair intacto.

Sinonimos de verbos e ordinais ("ultimo", "numero 3", "o de cima") ficam nas regras do
jarvis.py, ao lado de cada comando.
"""

import re
import unicodedata

_I = re.IGNORECASE

# "Jarvis, por favor, entao ..." no comeco
_ABERTURA = re.compile(
    r"^\s*(?:(?:jarvis|por favor|pf|pfv|ei|oi|ol[aá]|bom|ent[aã]o|ok|olha|vamos|agora)\b[\s,.!:-]*)+", _I)

# "voce pode", "da pra", "quero que voce", "faz favor de" antes do verbo
_PEDIDO = re.compile(
    r"^\s*(?:(?:voc[eê]|vc|tu|o senhor)\s+)?"
    r"(?:(?:pode|poderia|consegue|conseguiria|d[aá]|daria)\s+(?:(?:pra|para)\s+)?"
    r"|(?:eu\s+)?(?:quero|queria|gostaria|preciso|precisava)\s+que\s+(?:voc[eê]|vc|o senhor)\s+"
    r"|(?:faz|fa[cç]a)\s+(?:o\s+)?favor\s+de\s+)", _I)

# "me abre", "pra mim abre" no comeco
_PARA_MIM_INICIO = re.compile(r"^\s*(?:(?:me|pra mim|para mim)\s+)+", _I)

# "... por favor", "... pra mim", "... ai", "... agora" no fim
_FECHAMENTO = re.compile(
    r"(?:[\s,]+(?:por favor|pf|pfv|pra mim|para mim|a[ií]|ali|agora|ok|valeu|obrigad[oa]|jarvis))+[\s.!?]*$", _I)

_PONTUACAO_FINAL = re.compile(r"[\s.!?,;:]+$")


def tirar_enchimento(texto):
    """Remove aberturas, pedidos de cortesia e fechamentos. Devolve o resto, sem acentos tocados."""
    t = str(texto or "").strip()
    for _ in range(3):          # as camadas se combinam: "jarvis, por favor, pode me abrir..."
        antes = t
        t = _ABERTURA.sub("", t)
        t = _PEDIDO.sub("", t)
        t = _PARA_MIM_INICIO.sub("", t)
        if t == antes:
            break
    t = _FECHAMENTO.sub("", t)
    t = _PONTUACAO_FINAL.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def normalizar(texto):
    """minusculas, sem acentos, espacos unicos (mesma forma usada pelas regras do Jarvis)."""
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip()
