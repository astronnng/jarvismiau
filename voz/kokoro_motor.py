# -*- coding: utf-8 -*-
"""
MOTOR KOKORO - fala local (ONNX, sem internet) como camada OPCIONAL da voz
---------------------------------------------------------------------------
Regras de ouro:
  * Nada aqui pode piorar o que ja funciona: qualquer problema (biblioteca ausente, modelo
    ausente, erro ao sintetizar ou tocar) faz `falar` devolver False, e o jarvis.py segue
    para a cadeia de sempre (Edge -> voz do Windows).
  * A biblioteca so e importada quando o Kokoro e usado de fato (ele e opcional).

Como a voz e montada (config.py):
  - mistura: soma ponderada dos vetores de estilo das vozes (pesos normalizados);
  - idioma:  codigo de fonemas do espeak, independente da voz (pt-br com voz inglesa = sotaque);
  - velocidade: 0.5 a 2.0.

Desempenho (medido neste computador): o modelo carrega em ~2 s e sintetiza a ~0,3x do tempo
real, entao uma frase nova leva ~1 s. Por isso: cache em WAV por (modelo, mistura, idioma,
velocidade, texto), sintese da proxima frase enquanto a anterior toca, e pre-aquecimento das
frases conhecidas em segundo plano.
"""

import hashlib
import importlib.util
import json
import queue
import re
import threading
import time
import wave
from pathlib import Path

from . import config

PAUSA_FINAL_S = 0.06            # silencio depois da frase, para o player nao cortar o fim
MIN_FRASE = 20                  # fragmentos menores que isso se juntam a vizinha
TENTAR_DE_NOVO_APOS_S = 60      # depois de uma falha de carga, so tenta outra vez depois disso


class ErroKokoro(Exception):
    """Falha esperada do Kokoro; a mensagem ja e legivel para o usuario."""


def dividir_frases(texto):
    """Divide em frases para sintetizar a proxima enquanto a anterior toca."""
    partes = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", str(texto or "").strip()) if p.strip()]
    juntas, acumulo = [], ""
    for parte in partes:
        acumulo = f"{acumulo} {parte}".strip()
        if len(acumulo) >= MIN_FRASE:
            juntas.append(acumulo)
            acumulo = ""
    if acumulo:
        if juntas:
            juntas[-1] = f"{juntas[-1]} {acumulo}"
        else:
            juntas.append(acumulo)
    return juntas


def aplicar_pronuncias(texto, mapa):
    """Troca palavras inteiras (sem acento -> com acento) preservando a caixa inicial."""
    if not mapa:
        return texto

    def troca(m):
        palavra = m.group(0)
        novo = mapa.get(palavra.lower())
        if novo is None:
            return palavra
        return novo.capitalize() if palavra[:1].isupper() else novo

    return re.sub(r"\b\w+\b", troca, texto)


def _salvar_wav(caminho, amostras, taxa):
    import numpy as np

    pcm = (np.clip(amostras, -1.0, 1.0) * 32767).astype("<i2")
    pcm = np.concatenate([pcm, np.zeros(int(taxa * PAUSA_FINAL_S), dtype="<i2")])
    tmp = caminho.with_suffix(".tmp")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(pcm.tobytes())
    tmp.replace(caminho)


class MotorKokoro:
    def __init__(self, carregar_config=config.carregar, fabrica=None, pasta_cache=None,
                 modelo=None, vozes=None):
        self._carregar_config = carregar_config
        self._fabrica = fabrica
        self.modelo = Path(modelo or config.MODELO)
        self.arquivo_vozes = Path(vozes or config.VOZES)
        self.pasta_cache = Path(pasta_cache or (config.RAIZ / "cache_voz" / "kokoro"))
        self._kokoro = None
        self._lock_carga = threading.Lock()
        self._lock_sintese = threading.Lock()      # o espeak nao e seguro com threads em paralelo
        self._vozes = None
        self.ultimo_erro = None
        self._falhou_em = 0.0

    # ----------------------------------------------------------------- estado
    def disponivel(self):
        """(ok, motivo). Barato: nao carrega o modelo."""
        if self._fabrica is None and importlib.util.find_spec("kokoro_onnx") is None:
            return False, "a biblioteca kokoro-onnx nao esta instalada (rode Instalar-kokoro.bat)"
        if not self.modelo.exists() or not self.arquivo_vozes.exists():
            return False, "os modelos nao estao em modelos/kokoro (use /voz kokoro instalar)"
        return True, ""

    def carregado(self):
        return self._kokoro is not None

    def _carregar(self):
        with self._lock_carga:
            if self._kokoro is not None:
                return self._kokoro
            if self.ultimo_erro and time.monotonic() - self._falhou_em < TENTAR_DE_NOVO_APOS_S:
                raise ErroKokoro(self.ultimo_erro)
            try:
                if self._fabrica is not None:
                    self._kokoro = self._fabrica(self.modelo, self.arquivo_vozes)
                else:
                    from kokoro_onnx import Kokoro
                    self._kokoro = Kokoro(str(self.modelo), str(self.arquivo_vozes))
                self.ultimo_erro = None
            except Exception as erro:
                self._registrar_falha(f"nao consegui carregar o modelo: {erro}")
                raise ErroKokoro(self.ultimo_erro)
            return self._kokoro

    def _registrar_falha(self, mensagem):
        self.ultimo_erro = mensagem
        self._falhou_em = time.monotonic()

    def vozes(self):
        """Nomes das vozes do modelo instalado (le o arquivo, sem carregar o modelo)."""
        if self._vozes is None:
            try:
                if self._kokoro is not None:
                    self._vozes = list(self._kokoro.get_voices())
                else:
                    import numpy as np
                    self._vozes = sorted(np.load(str(self.arquivo_vozes)).files)
            except Exception:
                return []
        return self._vozes

    def idioma_valido(self, codigo):
        """Pergunta ao espeak do modelo se o idioma existe (so se o modelo ja puder carregar)."""
        kokoro = self._carregar()
        try:
            kokoro.tokenizer.phonemize("teste", codigo)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ sintese
    def _voz_ou_estilo(self, mistura, kokoro):
        normalizada = config.mistura_normalizada(mistura)
        existentes = set(self.vozes())
        for nome, _ in normalizada:
            if existentes and nome not in existentes:
                raise ErroKokoro(f"a voz {nome} nao existe neste modelo (veja /voz kokoro vozes)")
        if len(normalizada) == 1:
            return normalizada[0][0]
        import numpy as np
        return sum(f * kokoro.get_voice_style(n) for n, f in normalizada).astype(np.float32)

    def sintetizar(self, texto, kcfg):
        """(amostras float32, taxa). Aplica pronuncias quando o idioma e portugues."""
        kokoro = self._carregar()
        if str(kcfg["idioma"]).startswith("pt"):
            texto = aplicar_pronuncias(texto, kcfg.get("pronuncias"))
        with self._lock_sintese:
            voz = self._voz_ou_estilo(kcfg["mistura"], kokoro)
            return kokoro.create(texto, voice=voz, speed=float(kcfg["velocidade"]), lang=kcfg["idioma"])

    def arquivo_cache(self, texto, kcfg):
        chave = json.dumps({
            "v": 1, "modelo": f"{self.modelo.name}:{self.modelo.stat().st_size if self.modelo.exists() else 0}",
            "mistura": [(n, round(f, 4)) for n, f in config.mistura_normalizada(kcfg["mistura"])],
            "idioma": kcfg["idioma"], "velocidade": float(kcfg["velocidade"]),
            "pronuncias": kcfg.get("pronuncias") if str(kcfg["idioma"]).startswith("pt") else None,
            "texto": texto,
        }, sort_keys=True, ensure_ascii=False)
        return self.pasta_cache / (hashlib.sha1(chave.encode("utf-8")).hexdigest() + ".wav")

    def gerar(self, texto, kcfg):
        """WAV da frase: do cache, ou sintetizado agora e guardado. Devolve o caminho."""
        caminho = self.arquivo_cache(texto, kcfg)
        if caminho.exists() and caminho.stat().st_size > 1000:
            return caminho
        amostras, taxa = self.sintetizar(texto, kcfg)
        self.pasta_cache.mkdir(parents=True, exist_ok=True)
        _salvar_wav(caminho, amostras, taxa)
        return caminho

    # ------------------------------------------------------------------- fala
    def falar(self, texto, tocar):
        """
        Fala com o Kokoro se ele for o motor ativo e estiver pronto. `tocar(caminho) -> bool`
        e quem reproduz o WAV (vem do jarvis.py). Devolve False para o jarvis seguir na
        cadeia de sempre; nunca levanta excecao.
        """
        try:
            cfg = self._carregar_config()
            if cfg.get("motor") != "kokoro":
                return False
            if not self.disponivel()[0]:
                return False
            frases = dividir_frases(texto)
            if not frases:
                return False
            kcfg = cfg["kokoro"]
            if len(frases) == 1:
                return bool(tocar(str(self.gerar(frases[0], kcfg))))
            return self._falar_em_pipeline(frases, kcfg, tocar)
        except Exception as erro:
            self._registrar_falha(str(erro) or erro.__class__.__name__)
            return False

    def _falar_em_pipeline(self, frases, kcfg, tocar):
        """Toca a frase N enquanto a N+1 e sintetizada."""
        fila = queue.Queue(maxsize=2)
        parar = threading.Event()

        def produtor():
            for frase in frases:
                if parar.is_set():
                    return
                try:
                    fila.put(self.gerar(frase, kcfg))
                except Exception as erro:
                    fila.put(erro)
                    return
            fila.put(None)

        threading.Thread(target=produtor, name="kokoro-sintese", daemon=True).start()
        tocou_algo = False
        try:
            while True:
                item = fila.get()
                if item is None:
                    return True
                if isinstance(item, Exception):
                    self._registrar_falha(str(item))
                    return tocou_algo        # falhou no meio: nao repete o que ja foi dito
                if not tocar(str(item)):
                    return tocou_algo
                tocou_algo = True
        finally:
            parar.set()

    # ------------------------------------------------------------ pre-aquecimento
    def preaquecer(self, frases, cancelar=None):
        """Carrega o modelo, aquece o ONNX e gera as frases que ainda nao estao no cache."""
        cfg = self._carregar_config()
        if cfg.get("motor") != "kokoro" or not cfg["kokoro"].get("preaquecer", True):
            return 0
        if not self.disponivel()[0]:
            return 0
        kcfg = cfg["kokoro"]
        gerou = 0
        try:
            self.sintetizar("ok", kcfg)                       # a 1a inferencia e a mais lenta
            # Mesma divisao em frases de `falar`, senao o cache nao bate.
            trechos = [t for frase in frases for t in dividir_frases(frase)]
            for trecho in trechos:
                if cancelar is not None and cancelar():
                    break
                cfg_atual = self._carregar_config()
                if cfg_atual.get("motor") != "kokoro" or cfg_atual["kokoro"] != kcfg:
                    break                                      # o usuario mudou a voz no meio
                caminho = self.arquivo_cache(trecho, kcfg)
                if not (caminho.exists() and caminho.stat().st_size > 1000):
                    self.gerar(trecho, kcfg)
                    gerou += 1
        except Exception as erro:
            self._registrar_falha(str(erro))
        return gerou
