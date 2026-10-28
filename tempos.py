# -*- coding: utf-8 -*-
"""
TEMPOS - mede onde o tempo de cada comando foi
-----------------------------------------------
Cada comando processado vira uma linha em tempos.jsonl (ignorado pelo Git; contem as
frases ditas, entao fica so no seu computador):

  {"ts": 1730000000, "frase": "abre o segundo video", "caminho": "atalho",
   "total_ms": 412, "etapas": {"acao": 380, "fala": 30}}

Caminhos:
  atalho  regra local do navegador (jarvis._atalho_navegador)
  regra   outra regra local do jarvis.py (hora, volume, abrir site...)
  cache   plano do Gemini reaproveitado de uma frase ja vista (cache_planos.py)
  ia      consultou o Gemini

Etapas: ia (Gemini), acao (executar), fala (sintese/emissao de voz).
Veja o resumo no Jarvis com /tempos. Os pontos de medicao ficam em jarvis.py
(processar, processar_com_ia, executar_acao); quando nao ha comando em andamento,
tudo aqui vira no-op.
"""

import json
import statistics
import threading
import time
from contextlib import contextmanager
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent / "tempos.jsonl"
MAX_LINHAS = 1000
_local = threading.local()
_escrita = threading.Lock()


def iniciar(frase):
    _local.trace = {"frase": str(frase)[:200], "inicio": time.perf_counter(),
                    "caminho": None, "etapas": {}, "extra": {}}


def _trace():
    return getattr(_local, "trace", None)


def caminho(nome):
    """Marca o caminho usado ("atalho", "cache"...). Vale o primeiro marcado."""
    trace = _trace()
    if trace is not None and trace["caminho"] is None:
        trace["caminho"] = nome


def extra(**dados):
    trace = _trace()
    if trace is not None:
        trace["extra"].update(dados)


@contextmanager
def medir(etapa):
    inicio = time.perf_counter()
    try:
        yield
    finally:
        trace = _trace()
        if trace is not None:
            ms = (time.perf_counter() - inicio) * 1000
            trace["etapas"][etapa] = trace["etapas"].get(etapa, 0) + ms


def finalizar(arquivo=None):
    """Fecha o comando atual e grava a linha. Devolve o registro (ou None)."""
    trace = _trace()
    _local.trace = None
    if trace is None:
        return None
    etapas = trace["etapas"]
    caminho_final = trace["caminho"] or ("ia" if "ia" in etapas else "regra")
    registro = {
        "ts": int(time.time()),
        "frase": trace["frase"],
        "caminho": caminho_final,
        "total_ms": round((time.perf_counter() - trace["inicio"]) * 1000),
        "etapas": {k: round(v) for k, v in etapas.items()},
    }
    registro.update(trace["extra"])
    _gravar(registro, arquivo or ARQUIVO)
    return registro


def _gravar(registro, arquivo):
    try:
        with _escrita:
            with open(arquivo, "a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            if arquivo.stat().st_size > MAX_LINHAS * 200:
                linhas = arquivo.read_text(encoding="utf-8").splitlines()[-MAX_LINHAS:]
                arquivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    except OSError:
        pass            # medir nunca pode atrapalhar o comando


def ler(n=200, arquivo=None):
    arquivo = arquivo or ARQUIVO
    try:
        linhas = arquivo.read_text(encoding="utf-8").splitlines()[-n:]
    except OSError:
        return []
    registros = []
    for linha in linhas:
        try:
            registros.append(json.loads(linha))
        except ValueError:
            continue
    return registros


def resumo(n=200, arquivo=None):
    """Texto com contagem e mediana por caminho, e a mediana de cada etapa."""
    registros = ler(n, arquivo)
    if not registros:
        return "Ainda nao ha medicoes. Use o Jarvis um pouco e rode /tempos de novo."
    por_caminho = {}
    for r in registros:
        por_caminho.setdefault(r["caminho"], []).append(r)
    linhas = [f"Ultimos {len(registros)} comandos:"]
    for nome in ("atalho", "regra", "cache", "ia"):
        grupo = por_caminho.get(nome)
        if not grupo:
            continue
        mediana = round(statistics.median(r["total_ms"] for r in grupo))
        etapas = {}
        for r in grupo:
            for etapa, ms in r.get("etapas", {}).items():
                etapas.setdefault(etapa, []).append(ms)
        detalhe = ", ".join(f"{e} {round(statistics.median(v))} ms" for e, v in sorted(etapas.items()))
        linhas.append(f"- {nome}: {len(grupo)}x, mediana {mediana} ms" + (f" ({detalhe})" if detalhe else ""))
    return "\n".join(linhas)
