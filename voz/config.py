# -*- coding: utf-8 -*-
"""
Configuracao de voz (voz.json, ignorado pelo Git).

  {
    "motor": "padrao" | "kokoro",       # quem fala; "padrao" = a cadeia atual (edge -> Windows)
    "perfil_padrao": "BR_ANTONIO",      # perfil da cadeia atual escolhido pelo /voz (opcional)
    "kokoro": { mistura, idioma, velocidade, pronuncias, preaquecer, presets }
  }

Sem voz.json tudo continua como sempre: motor "padrao" e a constante VOZ do jarvis.py.
Os valores do Kokoro que nao estiverem no arquivo vem de PADRAO_KOKORO.
"""

import copy
import json
import os
import re
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "voz.json"
PASTA_MODELOS = RAIZ / "modelos" / "kokoro"
MODELO = PASTA_MODELOS / "kokoro-v1.0.onnx"
VOZES = PASTA_MODELOS / "voices-v1.0.bin"

VELOCIDADE_MIN, VELOCIDADE_MAX = 0.5, 2.0
MAX_VOZES_NA_MISTURA = 3

# Padrao do Kokoro: timbre britanico/americano que lembra o JARVIS dos filmes, com uma voz nativa
# em portugues (pm_alex) para reduzir o sotaque. Pesos 0.5 / 0.4 / 0.3 = 42% / 33% / 25%.
PADRAO_KOKORO = {
    "mistura": [{"voz": "bm_daniel", "peso": 0.5}, {"voz": "am_michael", "peso": 0.4},
                {"voz": "pm_alex", "peso": 0.3}],
    "idioma": "pt-br",
    "velocidade": 1.0,
    "preaquecer": True,
    # As frases do Jarvis saem sem acento; o espeak le melhor com ele. So vale para idioma pt-*.
    "pronuncias": {
        "nao": "não", "voce": "você", "voces": "vocês", "sao": "são", "ola": "olá", "ja": "já",
        "so": "só", "ate": "até", "tambem": "também", "entao": "então", "alem": "além",
        "ha": "há",
        # Fora de proposito: "nos" (pronome, "ele nos disse"), "pe" (sigla PE), "ve"... mudam de sentido.
    },
    "presets": {},
}

_IDIOMA_OK = re.compile(r"[a-z]{2,3}(-[a-z0-9]{2,4})?")
_lock = threading.Lock()
_cache = {"mtime": None, "cfg": None, "arquivo": None}


def _mesclar(base, extra):
    """Mescla recursivamente `extra` sobre uma copia de `base`."""
    saida = copy.deepcopy(base)
    for chave, valor in (extra or {}).items():
        if isinstance(valor, dict) and isinstance(saida.get(chave), dict) and chave != "presets":
            saida[chave] = _mesclar(saida[chave], valor)
        else:
            saida[chave] = valor
    return saida


def padrao():
    return {"motor": "padrao", "perfil_padrao": None, "kokoro": copy.deepcopy(PADRAO_KOKORO)}


def carregar(arquivo=None):
    """Configuracao atual (com cache por data do arquivo: barato de chamar a cada fala)."""
    arquivo = Path(arquivo or ARQUIVO)
    try:
        mtime = arquivo.stat().st_mtime
    except OSError:
        mtime = None
    with _lock:
        if _cache["arquivo"] == str(arquivo) and _cache["mtime"] == mtime and _cache["cfg"] is not None:
            return copy.deepcopy(_cache["cfg"])
        cfg = padrao()
        if mtime is not None:
            try:
                cfg = _mesclar(cfg, json.loads(arquivo.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass                    # arquivo corrompido: volta ao padrao em vez de quebrar a fala
        if cfg.get("motor") not in ("padrao", "kokoro"):
            cfg["motor"] = "padrao"
        # O idioma e sempre explicito. A biblioteca assume en-us quando nao recebe `lang`, e
        # isso faria o portugues sair lido como ingles: um valor vazio/invalido volta para pt-br.
        idioma = str(cfg["kokoro"].get("idioma") or "").strip().lower()
        cfg["kokoro"]["idioma"] = idioma if _IDIOMA_OK.fullmatch(idioma) else PADRAO_KOKORO["idioma"]
        _cache.update(mtime=mtime, cfg=cfg, arquivo=str(arquivo))
        return copy.deepcopy(cfg)


def salvar(cfg, arquivo=None):
    arquivo = Path(arquivo or ARQUIVO)
    tmp = arquivo.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, arquivo)
    with _lock:
        _cache.update(mtime=None, cfg=None, arquivo=None)


def atualizar(funcao, arquivo=None):
    """Le, aplica `funcao(cfg)` (que altera o dict) e grava. Devolve a nova configuracao."""
    cfg = carregar(arquivo)
    funcao(cfg)
    salvar(cfg, arquivo)
    return carregar(arquivo)


# ---------------------------------------------------------------- validacoes
def mistura_normalizada(mistura):
    """[{"voz", "peso"}] -> [(voz, fracao)] com as fracoes somando 1."""
    itens = [(m["voz"], float(m["peso"])) for m in mistura if float(m["peso"]) > 0]
    total = sum(p for _, p in itens)
    if not itens or total <= 0:
        raise ValueError("A mistura precisa de ao menos uma voz com peso maior que zero.")
    return [(voz, peso / total) for voz, peso in itens]


def interpretar_mistura(texto):
    """
    'bm_daniel=0.5 am_michael=0.4' (tambem 'a:60 b:40' ou 'a 0.5 b 0.4') -> lista de {voz, peso}.
    Uma voz sem peso vale 1. Levanta ValueError com mensagem pronta para o usuario.
    """
    achados = re.findall(r"([a-z]{2}_[a-z0-9]+)(?:\s*[=:\s]\s*(\d+(?:[.,]\d+)?))?", texto.lower())
    if not achados:
        raise ValueError("Informe as vozes, por exemplo: bm_daniel=0.5 am_michael=0.4")
    mistura = []
    for voz, peso in achados:
        valor = float(peso.replace(",", ".")) if peso else 1.0
        if valor <= 0:
            raise ValueError(f"O peso de {voz} precisa ser maior que zero.")
        if any(m["voz"] == voz for m in mistura):
            raise ValueError(f"{voz} apareceu duas vezes.")
        mistura.append({"voz": voz, "peso": valor})
    if len(mistura) > MAX_VOZES_NA_MISTURA:
        raise ValueError(f"Use no maximo {MAX_VOZES_NA_MISTURA} vozes na mistura.")
    return mistura


def validar_velocidade(texto):
    try:
        valor = float(str(texto).replace(",", "."))
    except ValueError:
        raise ValueError("A velocidade precisa ser um numero, por exemplo 1.0")
    if not VELOCIDADE_MIN <= valor <= VELOCIDADE_MAX:
        raise ValueError(f"A velocidade vai de {VELOCIDADE_MIN} a {VELOCIDADE_MAX}.")
    return round(valor, 2)


def validar_idioma(texto):
    codigo = str(texto).strip().lower()
    if not _IDIOMA_OK.fullmatch(codigo):
        raise ValueError("Codigo de idioma invalido. Exemplos: pt-br, en-us, en-gb, es, fr-fr, it.")
    return codigo


# Primeira letra do nome da voz = idioma/sotaque nativo; segunda = genero.
IDIOMA_DA_VOZ = {"a": "en-us", "b": "en-gb", "e": "es", "f": "fr-fr", "h": "hi", "i": "it",
                 "j": "ja", "p": "pt-br", "z": "cmn"}


def idioma_nativo(voz):
    return IDIOMA_DA_VOZ.get(voz[:1])


def genero(voz):
    return {"f": "F", "m": "M"}.get(voz[1:2], "?")


def resumo_mistura(mistura):
    """'bm_daniel 56% + am_michael 44%'"""
    return " + ".join(f"{v} {round(f * 100)}%" for v, f in mistura_normalizada(mistura))
