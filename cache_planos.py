# -*- coding: utf-8 -*-
"""
CACHE DE PLANOS - o Jarvis "aprende" com o que o Gemini ja resolveu
-------------------------------------------------------------------
Quando o Gemini transforma uma frase em acoes e elas funcionam, o plano e guardado em
cache_planos.json (ignorado pelo Git). Da proxima vez que a mesma frase aparecer
(ignorando acentos, maiusculas e enchimento como "por favor"), o plano sai do cache:
instantaneo, sem rede e sem gastar cota.

O que NAO entra no cache (de proposito):
  - respostas so de conversa (sem acoes): podem depender do momento;
  - planos com acoes de risco (desligar, reiniciar...);
  - frases que dependem do contexto ("abre esse", "de novo", "o outro", "agora");
  - planos que falharam: se um plano do cache falha, ele e esquecido na hora.

Se o catalogo de acoes mudar (nomes ou parametros), o cache inteiro e descartado, porque
um plano antigo poderia chamar uma acao que nao existe mais.
Gerencie com /cache (resumo) e /cache limpar.
"""

import json
import os
import re
import threading
import time
from pathlib import Path

import linguagem

ARQUIVO = Path(__file__).resolve().parent / "cache_planos.json"
MAX_ENTRADAS = 500
MAX_PASSOS = 3

# Frases que so fazem sentido no momento em que foram ditas.
_CONTEXTUAL = re.compile(
    r"\b(esse|essa|isso|isto|aquele|aquela|ele|ela|de novo|outro|outra|outros|outras|anterior|"
    r"mesmo|mesma|tambem|agora|ainda|antes|depois|entao)\b")


def chave(frase):
    """Forma canonica da frase: sem enchimento, sem acentos, minuscula."""
    return linguagem.normalizar(linguagem.tirar_enchimento(frase))


def cacheavel(frase, plano, catalogo):
    """True se esse plano pode ser reaproveitado com seguranca. `catalogo` = acoes.CATALOGO."""
    k = chave(frase)
    if not k or len(k) > 120 or _CONTEXTUAL.search(k):
        return False
    passos = plano.get("passos") or []
    if not passos or len(passos) > MAX_PASSOS:
        return False
    for passo in passos:
        if not isinstance(passo, dict):
            return False
        info = catalogo.get(str(passo.get("acao") or ""))
        if info is None or info.get("risco"):
            return False
    return True


class CachePlanos:
    def __init__(self, caminho=ARQUIVO, assinatura=""):
        self.caminho = Path(caminho)
        self.assinatura = assinatura
        self._lock = threading.Lock()
        self._entradas = self._carregar()

    # ----------------------------------------------------------------- consulta
    def obter(self, frase):
        """Plano guardado para a frase (cópia) ou None."""
        with self._lock:
            entrada = self._entradas.get(chave(frase))
            if entrada is None:
                return None
            entrada["usos"] = entrada.get("usos", 0) + 1
            entrada["ultimo"] = time.time()
            self._salvar()
            return json.loads(json.dumps(entrada["plano"]))

    def total(self):
        with self._lock:
            return len(self._entradas)

    # ---------------------------------------------------------------- alteracao
    def guardar(self, frase, plano):
        k = chave(frase)
        limpo = {"fala": str(plano.get("fala") or ""),
                 "passos": [{"acao": p["acao"], "params": p.get("params") or {}}
                            for p in plano["passos"]]}
        with self._lock:
            self._entradas[k] = {"plano": limpo, "usos": 0, "ultimo": time.time(), "criado": time.time()}
            while len(self._entradas) > MAX_ENTRADAS:      # descarta o menos usado recentemente
                velho = min(self._entradas, key=lambda x: self._entradas[x].get("ultimo", 0))
                del self._entradas[velho]
            self._salvar()

    def esquecer(self, frase):
        with self._lock:
            if self._entradas.pop(chave(frase), None) is not None:
                self._salvar()
                return True
            return False

    def limpar(self):
        with self._lock:
            n = len(self._entradas)
            self._entradas = {}
            self._salvar()
            return n

    # ------------------------------------------------------------------ arquivo
    def _carregar(self):
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(dados, dict) or dados.get("catalogo") != self.assinatura:
            return {}               # catalogo mudou: planos antigos nao valem
        entradas = dados.get("entradas")
        return entradas if isinstance(entradas, dict) else {}

    def _salvar(self):
        try:
            tmp = self.caminho.with_suffix(".tmp")
            tmp.write_text(json.dumps({"catalogo": self.assinatura, "entradas": self._entradas},
                                      ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.caminho)
        except OSError:
            pass            # sem cache nao quebra nada
