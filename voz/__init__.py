# -*- coding: utf-8 -*-
"""
Voz opcional do Jarvis (Kokoro) e o comando /voz.

  config.py        voz.json: motor ativo, mistura de vozes, idioma, velocidade, presets
  kokoro_motor.py  a fala local com Kokoro (ONNX), com cache e fallback seguro
  comandos.py      o /voz (e as sugestoes do menu)
  instalar.py      download verificado dos modelos

O Kokoro NUNCA substitui a cadeia de voz existente: ele e tentado antes e, se nao estiver
ativo ou falhar, o jarvis.py continua com Edge -> voz do Windows exatamente como antes.
Guia: docs/VOZ.md
"""

import threading

from . import config
from .kokoro_motor import ErroKokoro, MotorKokoro

motor = MotorKokoro()
_geracao = 0                    # cada novo pre-aquecimento cancela o anterior


def motor_ativo():
    return config.carregar()["motor"]


def falar(texto, tocar):
    """True se o Kokoro falou. False = o chamador segue na cadeia de sempre."""
    return motor.falar(texto, tocar)


def resumo_curto():
    """Texto curto para o painel do CLI, ou None se o Kokoro nao e o motor ativo."""
    cfg = config.carregar()
    if cfg["motor"] != "kokoro":
        return None
    voz = "+".join(m["voz"] for m in cfg["kokoro"]["mistura"])
    return f"KOKORO · {voz}"


def preaquecer_em_segundo_plano(obter_frases):
    """Carrega o modelo e gera as frases comuns sem atrapalhar. Chamar de novo cancela o anterior."""
    global _geracao
    _geracao += 1
    minha = _geracao

    def trabalho():
        motor.preaquecer(obter_frases(), cancelar=lambda: minha != _geracao)

    threading.Thread(target=trabalho, name="kokoro-preaquecer", daemon=True).start()


__all__ = ["config", "motor", "ErroKokoro", "MotorKokoro", "motor_ativo", "falar", "resumo_curto",
           "preaquecer_em_segundo_plano"]
