# -*- coding: utf-8 -*-
"""
JARVIS simples - v2 (com vozes naturais)
----------------------------------------
Novidades desta versao:
  * Motor de voz neural (edge-tts), muito mais natural que a voz do Windows
  * Perfis de voz prontos: JARVIS britanico, JARVIS alternativo, brasileira, Windows
  * Entende comandos em Portugues E em Ingles
  * Se o perfil for ingles, ele responde em ingles (como o JARVIS de verdade)
    mas continua entendendo o que voce fala em portugues.

Como usar:
    python jarvis.py            -> modo voz (aperte ENTER para falar)
    python jarvis.py --texto    -> modo texto (digite os comandos)
    python jarvis.py --demo     -> so fala uma frase de teste (para ouvir a voz)
"""

import os
import re
import sys
import time
import random
import asyncio
import hashlib
import datetime
import tempfile
import threading
import subprocess
import unicodedata
import urllib.request
import urllib.parse
import webbrowser

try:
    import acoes
    import cerebro
except Exception:      # se algum arquivo faltar, o Jarvis continua so com regras locais
    acoes = None
    cerebro = None

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# ============================================================================
# 1. ESCOLHA A VOZ AQUI  <-- e a unica linha que voce precisa mexer
# ============================================================================
VOZ = "BR_REMY"
# --- Vozes brasileiras (respondem em portugues) --------------------------
#   "BR_ANTONIO"        -> brasileira nativa, masculina, grave e neutra  [recomendada]
#   "BR_ANTONIO_GRAVE"  -> a mesma, mais grave e mais lenta (estilo mordomo)
#   "BR_ANDREW"         -> timbre encorpado, sotaque levemente estrangeiro
#   "BR_BRIAN"          -> mais jovem e conversacional
#   "BR_GIUSEPPE"       -> timbre caloroso, sotaque perceptivel
#   "BR_REMY"           -> timbre suave, sotaque perceptivel
#   "BR_FRANCISCA"      -> brasileira nativa, feminina
#   "BR_THALITA"        -> brasileira, feminina e mais jovem
# --- Outras vozes -------------------------------------------------------
#   "JARVIS"      -> britanica masculina (a mais parecida com o JARVIS dos filmes)
#   "JARVIS_ALT"  -> outra britanica masculina, um pouco mais grave
#   "BRASILEIRA"  -> apelido antigo de BR_ANTONIO
#   "WINDOWS"     -> voz offline do Windows (robotica, mas funciona sem internet)

# Idioma que o microfone escuta. Deixe "pt-BR" para falar em portugues.
# Troque para "en-US" se preferir dar os comandos falando em ingles.
IDIOMA_MICROFONE = "pt-BR"

# ============================================================================
# 2. PERFIS DE VOZ
# ============================================================================
def _br(voz, rate="-6%", pitch="-4Hz", forcar_pt=False):
    """Atalho para criar um perfil que responde em portugues."""
    return {"motor": "edge", "voz": voz, "idioma": "pt",
            "rate": rate, "pitch": pitch, "forcar_pt": forcar_pt}


PERFIS = {
    # ---------------- vozes brasileiras ----------------
    "BR_ANTONIO":       _br("pt-BR-AntonioNeural", "-8%", "-6Hz"),
    "BR_ANTONIO_GRAVE": _br("pt-BR-AntonioNeural", "-14%", "-18Hz"),
    "BR_ANDREW":        _br("en-US-AndrewMultilingualNeural", "-6%", "-4Hz"),
    "BR_BRIAN":         _br("en-US-BrianMultilingualNeural", "-6%", "-4Hz"),
    "BR_GIUSEPPE":      _br("it-IT-GiuseppeMultilingualNeural", "-6%", "-4Hz"),
    "BR_REMY":          _br("fr-FR-RemyMultilingualNeural", "-6%", "-4Hz"),
    "BR_FRANCISCA":     _br("pt-BR-FranciscaNeural", "-6%", "-2Hz"),
    "BR_THALITA":       _br("pt-BR-ThalitaMultilingualNeural", "-6%", "-2Hz"),
    # ---------------- outras ----------------
    "JARVIS": {
        "motor": "edge", "voz": "en-GB-RyanNeural", "idioma": "en",
        "rate": "-8%", "pitch": "-8Hz",
    },
    "JARVIS_ALT": {
        "motor": "edge", "voz": "en-GB-ThomasNeural", "idioma": "en",
        "rate": "-10%", "pitch": "-5Hz",
    },
    "WINDOWS": {
        "motor": "sapi", "voz": None, "idioma": "pt", "rate": 170,
    },
}
PERFIS["BRASILEIRA"] = PERFIS["BR_ANTONIO"]  # apelido antigo

VOZ = os.environ.get("JARVIS_VOZ", VOZ)          # permite testar: set JARVIS_VOZ=BR_BRIAN
PERFIL = PERFIS.get(VOZ, PERFIS["BR_ANTONIO"])
IDIOMA_FALA = PERFIL["idioma"]          # idioma das respostas

NOME = "Jarvis"
MODO_TEXTO = "--texto" in sys.argv
MODO_DEMO = "--demo" in sys.argv
MOSTRAR_LATENCIA = "--latencia" in sys.argv   # mostra quanto tempo a fala levou
SEM_PREAQUECER = "--sem-cache" in sys.argv    # desliga o cache/pre-aquecimento

# ---- modo de escuta -------------------------------------------------------
#   "palavra"   -> fica ouvindo sempre, mas so atende quando ouve "Jarvis" (padrao)
#   "continuo"  -> atende qualquer fala, sem palavra de ativacao
#   "pressione" -> espera voce apertar ENTER (modo antigo)
MODO_ESCUTA = "palavra"          # padrao: so atende quando ouve a palavra de ativacao
if "--pressione" in sys.argv:
    MODO_ESCUTA = "pressione"
elif "--continuo" in sys.argv:
    MODO_ESCUTA = "continuo"

PALAVRA_ATIVACAO = "jarvis"      # palavra de ativacao
# variantes que o reconhecedor costuma devolver no lugar de "jarvis"
VARIANTES_ATIVACAO = ["jarvis", "javis", "jarves", "jarbis", "jarvi", "jarve", "charvis"]
SEGUNDOS_SILENCIO = 0.55         # silencio que marca o fim da sua fala
LIMITE_FRASE = 8                 # segundos maximos de uma fala
PAUSA_APOS_ERRO = 2              # segundos de descanso se a rede falhar
JANELA_SEGUIMENTO = 6            # apos responder, aceita comandos sem dizer "Jarvis"

# Cerebro de IA: entende frases livres e decide as acoes sozinho.
# Precisa de uma chave gratuita do Google AI Studio (rode Configurar-IA.bat).
# Use --sem-ia para desligar e ficar so nas regras locais.
USAR_IA = "--sem-ia" not in sys.argv

# Bloqueios usados pelo bot do Telegram (evitam acoes perigosas a distancia
# e impedem que o bot tente abrir o microfone do PC para pedir confirmacao)
PERMITIR_ACOES_ARRISCADAS = True
ENTRADA_BLOQUEADA = False

# ============================================================================
# 3. FRASES  (portugues e ingles, no estilo do JARVIS)
# ============================================================================
FRASES = {
    "pt": {
        "inicio": "Sistemas iniciados. Ola, eu sou o {nome}. Diga 'sair' para encerrar.",
        "ola": ["Pois nao, senhor.", "As suas ordens, senhor.", "Estou ouvindo, senhor."],
        "bem": "Tudo em ordem, senhor. Pronto para ajudar.",
        "sair": "Ate logo, senhor.",
        "nao_ouvi": ["Nao ouvi nada, senhor.", "Pode repetir, senhor?"],
        "hora": "Sao {h} horas e {m}, senhor.",
        "data": "Hoje e {dia}, {d} de {mes} de {ano}, senhor.",
        "clima": "Em {cidade} esta {temp} graus e {condicao}.",
        "clima_erro": "Nao consegui consultar o clima agora, senhor.",
        "pesquisando": "Pesquisando {termo}, senhor.",
        "abrindo_site": "Abrindo {alvo}, senhor.",
        "abrindo_app": "Abrindo {alvo}, senhor.",
        "nao_conheco": "Nao conheco {alvo}, senhor. Vou pesquisar.",
        "yt": "Procurando {termo} no YouTube, senhor.",
        "bloqueando": "Blocando o computador, senhor.",
        "nao_sei": "Ainda nao fui programado para isso, senhor. Pesquisar no Google? Diga sim ou nao.",
        "sem_microfone": "Nao encontrei o microfone, senhor.",
        "sem_internet": "Estou sem conexao com o servico de voz, senhor.",
        "o_que_pesquisar": "O que o senhor deseja pesquisar?",
        "ativo": "Estou ouvindo o tempo todo, senhor. Pode falar quando quiser.",
        "pode_falar": "Pode falar, senhor.",
    },
    "en": {
        "inicio": "All systems online. Good to see you, sir. Say exit to shut down.",
        "ola": ["At your service, sir.", "Always a pleasure, sir.", "I am listening, sir."],
        "bem": "Everything is in order, sir. Ready when you are.",
        "sair": "Goodbye, sir. Do call again.",
        "nao_ouvi": ["I did not catch that, sir.", "Would you repeat that, sir?"],
        "hora": "It is {h}:{m} {ampm}, sir.",
        "data": "Today is {dia}, the {d} of {mes}, {ano}, sir.",
        "clima": "In {cidade} it is {temp} degrees and {condicao}.",
        "clima_erro": "I am unable to reach the weather service, sir.",
        "pesquisando": "Searching for {termo}, sir.",
        "abrindo_site": "Opening {alvo}, sir.",
        "abrindo_app": "Launching {alvo}, sir.",
        "nao_conheco": "I am not familiar with {alvo}, sir. Searching instead.",
        "yt": "Searching YouTube for {termo}, sir.",
        "bloqueando": "Locking the workstation, sir.",
        "nao_sei": "I am not programmed for that yet, sir. Shall I search the web? Say yes or no.",
        "sem_microfone": "I cannot find the microphone, sir.",
        "sem_internet": "I have lost the connection to the speech service, sir.",
        "o_que_pesquisar": "What shall I search for, sir?",
        "ativo": "I am listening at all times, sir. Speak whenever you wish.",
        "pode_falar": "Go ahead, sir.",
    },
}

MESES = {
    "pt": ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho",
           "agosto", "setembro", "outubro", "novembro", "dezembro"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}
DIAS = {
    "pt": ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
           "sexta-feira", "sabado", "domingo"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}


def f(chave, **kw):
    """Monta uma frase no idioma da voz atual."""
    txt = FRASES[IDIOMA_FALA][chave]
    if isinstance(txt, list):
        txt = random.choice(txt)
    return txt.format(nome=NOME, **kw) if kw or "{" in txt else txt


# ============================================================================
# 4. MOTORES DE VOZ
# ============================================================================
_sapi = None
_pygame_ok = None
_sons = {}          # cache em memoria: texto -> objeto de som ja carregado


def _init_sapi():
    global _sapi
    try:
        import pyttsx3

        _sapi = pyttsx3.init()
        _sapi.setProperty("rate", PERFIL.get("rate", 170))
        for _v in _sapi.getProperty("voices"):
            if "portug" in str(_v.name).lower() or "brazil" in str(_v.id).lower():
                _sapi.setProperty("voice", _v.id)
                break
    except Exception:
        _sapi = None
    return _sapi


def _falar_windows(texto):
    if not _sapi and not _init_sapi():
        return False
    if _sapi is None:
        return False
    try:
        _sapi.say(texto)
        _sapi.runAndWait()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- cache em disco
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_voz")


def _assinatura(texto):
    """Identifica a frase + a voz usada, para o cache nao misturar perfis."""
    bruto = f"{PERFIL.get('voz')}|{PERFIL.get('rate')}|{PERFIL.get('pitch')}|{texto}"
    return hashlib.md5(bruto.encode("utf-8")).hexdigest()


def caminho_cache(texto):
    return os.path.join(CACHE_DIR, _assinatura(texto) + ".mp3")


def _init_player():
    """Liga o mixer uma unica vez (ligar/desligar a cada frase custa ~200ms)."""
    global _pygame_ok
    if _pygame_ok is None:
        try:
            import pygame

            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            _pygame_ok = True
        except Exception:
            _pygame_ok = False
    return _pygame_ok


def _tocar_arquivo(caminho):
    """Toca o mp3 com o mixer ja ligado. Carrega em memoria e guarda para reuso."""
    if _init_player():
        try:
            import pygame

            som = _sons.get(caminho)
            if som is None:
                som = pygame.mixer.Sound(caminho)
                _sons[caminho] = som
            canal = som.play()
            if canal is not None:
                while canal.get_busy():
                    time.sleep(0.02)
            return True
        except Exception:
            pass
    # ultimo recurso (Windows): player padrao do sistema
    try:
        os.startfile(caminho)  # noqa: S606
        time.sleep(2.5)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- player em fluxo
_ffplay = None


def _tem_ffplay():
    """O ffplay (do pacote ffmpeg) toca audio enquanto ele ainda esta chegando."""
    global _ffplay
    if _ffplay is None:
        import shutil as _sh

        _ffplay = _sh.which("ffplay") is not None
    return _ffplay


def _falar_stream(texto):
    """
    Toca a frase enquanto ela e gerada: o som comeca em ~250ms em vez de ~1200ms.
    Tambem salva o audio no cache, para as proximas vezes serem instantaneas.
    """
    import subprocess as _sp

    try:
        import edge_tts
    except ImportError:
        return False

    cache = caminho_cache(texto)
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except Exception:
        return False

    criacao = getattr(_sp, "CREATE_NO_WINDOW", 0)
    try:
        player = _sp.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-i", "pipe:0"],
            stdin=_sp.PIPE, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
            creationflags=criacao)
    except Exception:
        return False

    pedacos = bytearray()
    erro = {"quebrou": False}

    async def transmitir():
        com = edge_tts.Communicate(
            texto, PERFIL["voz"],
            rate=PERFIL.get("rate", "+0%"),
            pitch=PERFIL.get("pitch", "+0Hz"))
        async for bloco in com.stream():
            if bloco.get("type") != "audio":
                continue
            dados = bloco["data"]
            pedacos.extend(dados)
            if not erro["quebrou"]:
                try:
                    player.stdin.write(dados)
                    player.stdin.flush()
                except Exception:
                    erro["quebrou"] = True   # o player saiu antes; seguimos gravando

    try:
        asyncio.run(transmitir())
    except Exception:
        try:
            player.kill()
        except Exception:
            pass
        return False
    finally:
        try:
            player.stdin.close()
        except Exception:
            pass

    try:
        player.wait(timeout=30)
    except Exception:
        pass

    if len(pedacos) > 500:
        try:
            with open(cache, "wb") as fh:
                fh.write(bytes(pedacos))
        except Exception:
            pass
        return True
    return False


# ---------------------------------------------------------------- geracao da voz
def gerar_mp3(texto, destino):
    """Gera (ou reaproveita do cache) o mp3 da frase. Devolve o caminho ou None."""
    em_cache = caminho_cache(texto)
    if os.path.exists(em_cache) and os.path.getsize(em_cache) > 500:
        if destino != em_cache:
            try:
                import shutil

                shutil.copyfile(em_cache, destino)
            except Exception:
                return em_cache
        return destino

    try:
        import edge_tts
    except ImportError:
        return None

    try:
        os.makedirs(CACHE_DIR, exist_ok=True)

        async def gerar():
            com = edge_tts.Communicate(
                texto, PERFIL["voz"],
                rate=PERFIL.get("rate", "+0%"),
                pitch=PERFIL.get("pitch", "+0Hz"),
            )
            await com.save(em_cache)

        asyncio.run(gerar())
        if os.path.getsize(em_cache) < 500:
            return None
        if destino != em_cache:
            try:
                import shutil

                shutil.copyfile(em_cache, destino)
            except Exception:
                return em_cache
        return destino
    except Exception:
        return None


def _falar_neural(texto):
    """
    Estrategias, da mais rapida para a mais lenta:
      1) frase ja esta no cache -> toca na hora (0 ms de espera)
      2) frase nova + ffplay     -> toca em fluxo (~250-400 ms)
      3) frase nova sem ffplay   -> gera o arquivo (~1,2 s) e guarda no cache
    """
    t0 = time.time()
    em_cache = caminho_cache(texto)

    # 1) cache
    if os.path.exists(em_cache) and os.path.getsize(em_cache) > 500:
        ok = _tocar_arquivo(em_cache)
        if MOSTRAR_LATENCIA:
            print(f"   [latencia] CACHE: {int((time.time() - t0) * 1000)} ms")
        return ok

    # 2) fluxo
    if _tem_ffplay():
        ok = _falar_stream(texto)
        if ok:
            if MOSTRAR_LATENCIA:
                print(f"   [latencia] FLUXO: {int((time.time() - t0) * 1000)} ms")
            return True

    # 3) arquivo
    caminho = gerar_mp3(texto, os.path.join(tempfile.gettempdir(), "jarvis_fala.mp3"))
    if not caminho:
        return False
    ok = _tocar_arquivo(caminho)
    if MOSTRAR_LATENCIA:
        print(f"   [latencia] ARQUIVO: {int((time.time() - t0) * 1000)} ms")
    return ok


# ---------------------------------------------------------------- pre-aquecimento
def frases_conhecidas():
    """Lista das frases fixas que o Jarvis costuma falar (para gerar antecipado)."""
    lista = set()
    for valor in FRASES[IDIOMA_FALA].values():
        for v in (valor if isinstance(valor, list) else [valor]):
            if "{" not in v:
                lista.add(v)
    lista.add(DEMO[IDIOMA_FALA])
    # "Abrindo X, senhor." para cada site e programa cadastrado
    for alvo in list(SITES.keys()) + list(PROGRAMAS.keys()):
        lista.add(f("abrindo_site", alvo=alvo))
    # horas e datas do momento (as mais provaveis agora)
    a = datetime.datetime.now()
    lista.add(f("hora", h=a.hour, m=f"{a.minute} minutos"))
    lista.add(f("data", dia=DIAS[IDIOMA_FALA][a.weekday()], d=a.day,
                mes=MESES[IDIOMA_FALA][a.month - 1], ano=a.year))
    lista.add(f("clima", cidade="Bariri", temp="22", condicao="ensolarado"))
    return [x for x in lista if x.strip()]


def preaquecer_cache():
    """Gera as frases mais usadas em segundo plano, enquanto voce ainda nem falou."""
    if SEM_PREAQUECER or PERFIL["motor"] != "edge":
        return
    faltando = [t for t in frases_conhecidas() if not os.path.exists(caminho_cache(t))]
    if not faltando:
        return

    def trabalho():
        try:
            import edge_tts  # noqa: F401
            from concurrent.futures import ThreadPoolExecutor
        except ImportError:
            return

        def gerar_um(texto):
            try:
                gerar_mp3(texto, caminho_cache(texto))
            except Exception:
                pass

        # 4 em paralelo: ~4x mais rapido que gerar uma por uma
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(gerar_um, faltando))

    print(f"(preparando {len(faltando)} frases em segundo plano, pode falar normalmente)")
    threading.Thread(target=trabalho, daemon=True).start()


# Quando CAPTURAR = True, falar() nao usa o alto-falante: apenas guarda o texto.
# E assim que o bot do Telegram reaproveita toda a logica deste arquivo.
CAPTURAR = False
CAPTURADO = []


def falar(texto):
    """Fala o texto com o motor escolhido. Sempre imprime na tela."""
    print(f"{NOME}: {texto}")
    if CAPTURAR:
        CAPTURADO.append(texto)
        return
    if PERFIL["motor"] == "edge":
        if _falar_neural(texto):
            return
        # se a voz neural falhar (sem internet, por exemplo), usa a do Windows
        _falar_windows(texto)
    else:
        if not _falar_windows(texto):
            pass


# ============================================================================
# 5. MICROFONE
# ============================================================================
_reconhecedor = None
_microfone = None
_calibrado = False


def _preparar_microfone():
    """Abre o microfone e calibra o ruido UMA vez (reabrir a cada comando custa ~300ms)."""
    global _reconhecedor, _microfone, _calibrado
    import speech_recognition as sr

    if _reconhecedor is None:
        _reconhecedor = sr.Recognizer()
        # Padroes que cortam a espera: ele para de gravar mais rapido
        _reconhecedor.pause_threshold = 0.55      # silencio que encerra a fala
        _reconhecedor.non_speaking_duration = 0.4
        _reconhecedor.phrase_threshold = 0.25     # ignora ruidos muito curtos
        _reconhecedor.dynamic_energy_threshold = True
        _reconhecedor.energy_threshold = 300

    if _microfone is None:
        _microfone = sr.Microphone()
        _microfone.__enter__()                    # mantem o dispositivo aberto

    if not _calibrado:
        _reconhecedor.adjust_for_ambient_noise(_microfone, duration=0.3)
        _calibrado = True

    return _reconhecedor, _microfone


def ouvir():
    try:
        import speech_recognition as sr
    except ImportError:
        falar(f("sem_microfone"))
        return ""
    try:
        r, fonte = _preparar_microfone()
    except Exception:
        falar(f("sem_microfone"))
        return ""

    print("(fale agora...)")
    try:
        audio = r.listen(fonte, timeout=6, phrase_time_limit=8)
    except sr.WaitTimeoutError:
        return ""
    except Exception:
        falar(f("sem_microfone"))
        return ""

    try:
        return r.recognize_google(audio, language=IDIOMA_MICROFONE)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        falar(f("sem_internet"))
        return ""


def descartar_buffer():
    """Joga fora o audio captado enquanto o Jarvis falava (evita ouvir a si mesmo)."""
    global _microfone
    if _microfone is None:
        return
    try:
        fluxo = _microfone.stream
        disponivel = fluxo.get_read_available()
        if disponivel:
            fluxo.read(disponivel)
        else:
            fluxo.read(_microfone.CHUNK)
    except Exception:
        pass


def ouvir_continuo(avisar_erro=True):
    """
    Uma rodada de escuta em modo continuo.
    Devolve o texto reconhecido, "" se nao entendeu, ou None se houve falha.
    """
    try:
        import speech_recognition as sr
    except ImportError:
        if avisar_erro:
            falar(f("sem_microfone"))
        return None
    try:
        r, fonte = _preparar_microfone()
    except Exception:
        if avisar_erro:
            falar(f("sem_microfone"))
        return None

    descartar_buffer()
    try:
        audio = r.listen(fonte, timeout=None, phrase_time_limit=LIMITE_FRASE)
    except sr.WaitTimeoutError:
        return ""
    except KeyboardInterrupt:
        raise
    except Exception:
        return None

    try:
        return r.recognize_google(audio, language=IDIOMA_MICROFONE)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        if avisar_erro:
            falar(f("sem_internet"))
        return None


def tirar_palavra_ativacao(texto):
    """
    No modo 'palavra', devolve o comando sem a palavra de ativacao.
    Devolve None se a palavra nao foi dita (ou seja: ignorar o que ouviu).

    Funciona por posicao de palavra, para nao perder os acentos do comando
    (ex.: "Jávis, tocar Legião Urbana" -> "tocar Legião Urbana").
    """
    limpo = normalizar(texto)
    alternacao = "|".join(re.escape(v) for v in VARIANTES_ATIVACAO)
    achado = re.search(r"\b(" + alternacao + r")\b", limpo)
    if not achado:
        return None

    # quantas palavras existem ate o fim da palavra de ativacao
    palavras_limpas = limpo[:achado.end()].split()
    palavras_originais = texto.split()
    if len(palavras_limpas) > len(palavras_originais):
        return ""
    resto = palavras_originais[len(palavras_limpas):]

    # descarta um "ei"/"ok"/"oi" que tenha sobrado no comeco
    while resto and normalizar(resto[0]).strip(",.!?;:") in (
            "ei", "oi", "ok", "hey", "ola", "por", "favor", "pf"):
        resto.pop(0)

    return " ".join(resto).strip(" ,.!?;:")


def loop_voz():
    """Fica ouvindo o microfone sem parar, ate voce dizer 'sair' ou apertar Ctrl+C."""
    if MODO_ESCUTA == "palavra":
        falar(f("ativo") if IDIOMA_FALA == "pt" else f("ativo"))
        print(f'(modo palavra de ativacao: comece a fala dizendo "{PALAVRA_ATIVACAO}")')
    else:
        print("(modo continuo: fale normalmente. 'sair' ou Ctrl+C encerram.)")
    print()

    erros_seguidos = 0
    janela_ate = 0.0          # ate quando aceitar comandos sem a palavra de ativacao
    while True:
        try:
            texto = ouvir_continuo(avisar_erro=(erros_seguidos == 0))
        except KeyboardInterrupt:
            print()
            falar(f("sair"))
            break
        except Exception:
            texto = None

        if texto is None:
            erros_seguidos += 1
            if erros_seguidos == 1:
                print("(tive um problema com o microfone; tentando de novo...)")
            if erros_seguidos >= 4:
                # microfone inutilizavel: nao deixa o terminal travado em silencio
                print()
                print("Nao consegui usar o microfone. Passando para o modo digitado.")
                print("(verifique o microfone em Configuracoes > Privacidade > Microfone)")
                print("Digite seus comandos. 'sair' ou Ctrl+C encerram.\n")
                while True:
                    try:
                        comando = input("Voce: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        falar(f("sair"))
                        return
                    if not processar(comando):
                        return
                return
            time.sleep(PAUSA_APOS_ERRO)
            continue
        erros_seguidos = 0

        if not texto:
            continue

        print(f"Voce: {texto}")

        if MODO_ESCUTA == "palavra":
            # "sair" sozinho sempre encerra, mesmo sem a palavra de ativacao
            if re.fullmatch(r"(sair|tchau|encerrar|desligar|exit|quit|goodbye|stop)",
                            normalizar(texto)):
                comando = texto
            else:
                comando = tirar_palavra_ativacao(texto)

                # janela de acompanhamento: logo depois de uma conversa com ele,
                # voce pode continuar falando sem repetir "Jarvis"
                if comando is None and time.time() < janela_ate:
                    comando = texto
                    print("   (dentro da janela de acompanhamento: aceito)")

            if comando is None:
                print("   (sem a palavra de ativacao, ignorado)")
                continue
            if not comando:
                falar(f("pode_falar"))
                janela_ate = time.time() + JANELA_SEGUIMENTO + 4
                continue
        else:
            comando = texto

        try:
            if not processar(comando):
                break
            if MODO_ESCUTA == "palavra":
                janela_ate = time.time() + JANELA_SEGUIMENTO
        except KeyboardInterrupt:
            print()
            falar(f("sair"))
            break
        except Exception as e:
            print(f"(erro ao executar: {e})")
            continue


def encerrar_microfone():
    global _microfone
    if _microfone is not None:
        try:
            _microfone.__exit__(None, None, None)
        except Exception:
            pass
        _microfone = None


def pegar_comando():
    if MODO_TEXTO:
        try:
            return input("Voce: ").strip()
        except (EOFError, KeyboardInterrupt):
            return "sair"
    input("Aperte ENTER para falar...")
    return ouvir()


# ============================================================================
# 6. UTILITARIOS
# ============================================================================
def normalizar(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip()


def termo_original(comando, c_resto):
    """Recupera o trecho do comando original (com acentos) a partir do normalizado."""
    n = len(c_resto.split())
    return " ".join(comando.split()[-n:]) if n else ""


def abrir_programa(cmd):
    subprocess.Popen(cmd, shell=True)


# ============================================================================
# 7. CATALOGOS
# ============================================================================
SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "whatsapp": "https://web.whatsapp.com",
    "gmail": "https://mail.google.com",
    "email": "https://mail.google.com",
    "e-mail": "https://mail.google.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "netflix": "https://www.netflix.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "gemini": "https://gemini.google.com",
    "noticias": "https://news.google.com",
    "news": "https://news.google.com",
    "mapa": "https://maps.google.com",
    "mapas": "https://maps.google.com",
    "mercado livre": "https://www.mercadolivre.com.br",
    "correios": "https://www.correios.com.br",
    "clima": "https://wttr.in",
}

PROGRAMAS = {
    "calculadora": "calc.exe", "calculator": "calc.exe",
    "bloco de notas": "notepad.exe", "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe", "arquivos": "explorer.exe", "files": "explorer.exe",
    "gerenciador de tarefas": "taskmgr.exe", "task manager": "taskmgr.exe",
    "configuracoes": "start ms-settings:", "settings": "start ms-settings:",
    "spotify": "start spotify:",
    "whatsapp app": "start whatsapp:",
    "camera": "start microsoft.windows.camera:",
    "word": "start winword",
    "excel": "start excel",
    "steam": "start steam:",
}


# ============================================================================
# 8. TAREFAS
# ============================================================================
def tarefa_hora():
    a = datetime.datetime.now()
    if IDIOMA_FALA == "en":
        h12 = a.hour % 12 or 12
        ampm = "AM" if a.hour < 12 else "PM"
        falar(f("hora", h=h12, m=f"{a.minute:02d}", ampm=ampm))
    else:
        plural = "minuto" if a.minute == 1 else "minutos"
        falar(f("hora", h=a.hour, m=f"{a.minute} {plural}"))


def tarefa_data():
    a = datetime.datetime.now()
    falar(f("data", dia=DIAS[IDIOMA_FALA][a.weekday()], d=a.day,
            mes=MESES[IDIOMA_FALA][a.month - 1], ano=a.year))


def tarefa_clima(comando):
    cidade = re.sub(
        r".*(clima|temperatura|previsao do tempo|tempo|weather|forecast)\s*"
        r"(em|de|no|na|in|for|at|hoje|today)?\s*", "", comando).strip()
    cidade = cidade or "Bariri"
    lang = "pt" if IDIOMA_FALA == "pt" else "en"
    try:
        url = (f"https://wttr.in/{urllib.parse.quote(cidade)}"
               f"?format=%l|%t|%C&m&lang={lang}")
        with urllib.request.urlopen(url, timeout=8) as r:
            nome_cidade, temp, condicao = r.read().decode("utf-8").strip().split("|")
        temp = temp.replace("+", "").replace("°C", "").strip()
        falar(f("clima", cidade=nome_cidade, temp=temp, condicao=condicao.lower()))
    except Exception:
        falar(f("clima_erro"))


def tarefa_pesquisar(termo):
    if not termo:
        falar(f("o_que_pesquisar"))
        return
    falar(f("pesquisando", termo=termo))
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(termo))


def tentar_abrir(alvo):
    if alvo in PROGRAMAS:
        falar(f("abrindo_app", alvo=alvo))
        abrir_programa(PROGRAMAS[alvo])
        return True
    if alvo in SITES:
        falar(f("abrindo_site", alvo=alvo))
        webbrowser.open(SITES[alvo])
        return True
    return False


def tarefa_youtube(termo):
    falar(f("yt", termo=termo))
    webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote(termo))


def tarefa_lembrete(comando, c=None):
    """Entende 'me lembre em 10 minutos de beber agua'."""
    c = c or normalizar(comando)
    minutos = None

    m = re.search(r"\bem\s+(\d+(?:[.,]\d+)?)\s*(segundos?|minutos?|min|horas?|h)\b", c)
    if m:
        valor = float(m.group(1).replace(",", "."))
        unidade = m.group(2)
        if unidade.startswith("seg"):
            minutos = valor / 60
        elif unidade.startswith("h"):
            minutos = valor * 60
        else:
            minutos = valor
    elif re.search(r"\bem\s+meia\s+hora\b", c):
        minutos = 30
    elif re.search(r"\b(uma|1)\s+hora\b", c):
        minutos = 60

    if minutos is None:
        falar("Em quanto tempo, senhor? Diga por exemplo: em 10 minutos.")
        if perguntar_sim_nao(tentativas=1):
            minutos = 10
        else:
            return
    if minutos <= 0:
        minutos = 1

    # o motivo e o que vier depois de "de/para/que" (no texto ORIGINAL, com acentos)
    motivo = "o lembrete"
    m2 = re.search(r"\b(?:de|para|pra|que)\s+(.+)$", comando, re.IGNORECASE)
    if m2:
        motivo = m2.group(1).strip(" .")
    else:
        motivo = re.sub(r".*\b(lembre|lembrar|avise|avisar|alarme|timer|cronometro)\b", "", c).strip(" .")
        motivo = re.sub(r"\bem\s+\d+([.,]\d+)?\s*(segundos?|minutos?|min|horas?|h)\b", "", motivo).strip(" .")
        motivo = motivo or "o lembrete"

    executar_acao("lembrete", {"minutos": minutos, "motivo": motivo})


def tarefa_bloquear():
    falar(f("bloqueando"))
    time.sleep(0.6)
    abrir_programa("rundll32.exe user32.dll,LockWorkStation")


# ============================================================================
# 9. O CEREBRO  (padroes em portugues + ingles)
# ============================================================================
R_SAIR = r"\b(sair|tchau|encerrar|exit|quit|goodbye|stop)\b"
R_SAIR_ASSISTENTE = r"\bdesligar\b.*\b(assistente|jarvis|voce|você|microfone)\b"
R_OLA = r"\b(oi|ola|bom dia|boa tarde|boa noite|hello|hi|good morning|good evening)\b"
R_BEM = r"\b(tudo bem|como voce esta|como vai|how are you|are you there)\b"
R_HORA = r"\b(horas?|que hora|hora agora|time|what time)\b"
R_DATA = r"\b(data|dia de hoje|que dia|date|what day)\b"
R_CLIMA = r"\b(clima|temperatura|previsao do tempo|tempo em|tempo hoje|weather|forecast)\b"
R_PESQ = r"^(pesquisar|pesquise|procure|buscar|busque|search|google)\b"
R_ABRIR = r"^(abrir|abra|abre|entrar no|entrar na|va para|ir para|open|launch|go to)\b"
R_TOCAR = r"^(tocar|colocar|play)\b"
R_BLOQUEAR = r"\b(bloquear|trancar|lock)\b"
R_SIM = r"^(s|sim|yes|y|claro|pode)\b"

# --- midia e sistema (funcionam sem internet e sem IA) ---
R_PLAY = r"(\b(play|tocar|toca|dá play|dar play|despausar|continuar|retomar|pausar|pausa|pause)\b)"
R_PROXIMA = r"(\b(proxim[ao]|pular|pula|avancar|avanca|next|passar (a|de) (musica|faixa))\b)"
R_ANTERIOR = r"(\b(anterior|voltar (a |de )?(musica|faixa)|volta (a |de )?(musica|faixa)|previous)\b)"
R_VOLUME = r"\b(volume|som|mudo|silenciar|silencia|mutar)\b"
R_LEMBRETE = r"\b(lembre|lembra|lembrar|avise|avisa|avisar|alarme|timer|cronometro)\b"
R_STATUS = r"\b(como (esta|estao) (o pc|o computador|a memoria)|memoria|status|desempenho)\b"
R_DESLIGAR_PC = r"\b(desligar|desliga|reiniciar|reinicia|hibernar)\b.*\b(pc|computador|maquina|windows)\b"
R_CANCELAR_DESLIGAMENTO = r"\bcancelar\b.*\bdesligamento\b"


R_NAO = r"^(n|nao|não|no|nope|deixa|deixa pra la|nao precisa|cancelar)\b"


def perguntar_sim_nao(tentativas=3):
    """
    Espera a resposta do usuario: sim ou nao.
    Funciona nos tres modos (texto, continuo e palavra de ativacao).
    No modo por voz, o 'sim' NAO precisa vir depois de 'Jarvis'.
    """
    if ENTRADA_BLOQUEADA and not MODO_TEXTO:
        return False
    for _ in range(tentativas):
        if MODO_TEXTO:
            try:
                resposta = input("(sim/nao) ").strip()
            except (EOFError, KeyboardInterrupt):
                return False
        else:
            print("(aguardando sua resposta...)")
            try:
                resposta = ouvir_continuo(avisar_erro=True)
            except KeyboardInterrupt:
                return False
            # ouviu a propria pergunta ou ruido: tenta de novo sem falar nada
            if not resposta:
                continue

        limpa = normalizar(resposta)
        print(f"Voce: {resposta}")

        if re.match(R_NAO, limpa):
            falar("Tudo bem, senhor.")
            return False
        if re.match(R_SIM, limpa) or re.search(r"\b(sim|claro|pode|isso|quero|manda|yes)\b", limpa):
            return True
        # resposta que nao e sim nem nao: pergunta de novo uma vez
        falar("Sim ou nao, senhor?")
    return False


# ============================================================================
# EXECUCAO DE ACOES (catalogo) E CEREBRO DE IA
# ============================================================================
MENSAGENS_CONFIRMACAO = {
    "desligar": "Isso vai DESLIGAR o computador. Confirma?",
    "reiniciar": "Isso vai REINICIAR o computador. Confirma?",
    "hibernar": "Isso vai colocar o computador em hibernacao. Confirma?",
}


def confirmar_acao_arriscada(nome):
    """Pergunta antes de qualquer acao marcada como risco no catalogo."""
    if not PERMITIR_ACOES_ARRISCADAS:
        falar("Por seguranca, isso so pode ser feito direto no computador, senhor.")
        return False
    aviso = MENSAGENS_CONFIRMACAO.get(nome, f"Confirmar a acao {nome}?")
    falar(aviso)
    return perguntar_sim_nao(tentativas=2)


def executar_acao(nome, params=None):
    """Roda uma acao do catalogo. Devolve (ok, fala)."""
    if acoes is None:
        return False, None
    ok, fala = acoes.executar(nome, params or {}, sys.modules[__name__],
                              pedir_confirmacao=confirmar_acao_arriscada)
    if fala:
        falar(fala)
    return ok, fala


HISTORICO = []          # ultimas trocas, para a IA entender o contexto


def parece_multi_comando(c):
    """Detecta 'abre o netflix E aumenta o volume': duas coisas na mesma frase."""
    if not re.search(r"\b(e|depois|entao|tambem|em seguida)\b", c):
        return False
    verbos = re.findall(r"\b(abr\w*|toc\w*|coloc\w*|aument\w*|diminu\w*|baix\w*|pesquis\w*|"
                        r"mand\w*|paus\w*|fech\w*|deslig\w*|ligar|bota\w*)\b", c)
    return len(set(verbos)) >= 2


def _lembrar(usuario, resposta):
    HISTORICO.append((usuario, resposta))
    del HISTORICO[:-4]


def _contexto_texto():
    if not HISTORICO:
        return ""
    linhas = [f"usuario: {u} | jarvis: {r}" for u, r in HISTORICO[-3:]]
    return " || ".join(linhas)


def processar_com_ia(comando):
    """
    Passa a frase para a IA, que devolve um plano de acoes do catalogo.
    Devolve True se conseguiu tratar (mesmo que so conversando).
    """
    if not USAR_IA or cerebro is None or acoes is None:
        return False
    if not cerebro.disponivel():
        return False

    plano = cerebro.interpretar(comando, acoes.listar_para_ia(), _contexto_texto())

    if not plano:
        return False
    if plano.get("erro"):
        print(f"   (IA indisponivel: {plano['erro']})")
        return False

    fala_ia = (plano.get("fala") or "").strip()
    passos = [p for p in (plano.get("passos") or []) if isinstance(p, dict)][:3]

    if not passos:
        if fala_ia:
            falar(fala_ia)
            _lembrar(comando, fala_ia)
            return True
        return False

    falado = False
    executou = False
    for passo in passos:
        nome = str(passo.get("acao") or "").strip()
        params = passo.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        if not acoes.existe(nome):
            print(f"   (IA sugeriu acao desconhecida: {nome} - ignorada)")
            continue
        ok, fala_acao = executar_acao(nome, params)
        executou = executou or ok
        falado = falado or bool(fala_acao)

    if not executou and not falado and fala_ia:
        falar(fala_ia)
        _lembrar(comando, fala_ia)
        return True
    if falado:
        _lembrar(comando, "(acao executada)")
    return executou or falado


def processar(comando):
    c = normalizar(comando)

    if not c:
        falar(f("nao_ouvi"))
        return True

    if re.search(R_SAIR_ASSISTENTE, c):
        falar(f("sair"))
        return False
    if re.search(R_SAIR, c) and not re.search(r"\b(pc|computador|maquina|windows|desligamento)\b", c):
        falar(f("sair"))
        return False

    # Frase com mais de uma acao: melhor deixar a IA planejar tudo de uma vez
    if parece_multi_comando(c) and processar_com_ia(comando):
        return True
    if re.search(R_BEM, c):
        falar(f("bem"))
    elif re.search(R_OLA, c):
        falar(f("ola"))
    elif re.search(R_HORA, c) and not re.search(R_CLIMA, c) and not re.search(R_LEMBRETE, c):
        tarefa_hora()
    elif re.search(R_DATA, c):
        tarefa_data()
    elif re.search(R_CLIMA, c):
        tarefa_clima(c)
    elif re.search(R_CANCELAR_DESLIGAMENTO, c):
        executar_acao("cancelar_desligamento")
    elif re.search(R_DESLIGAR_PC, c):
        verbo = "reiniciar" if re.search(r"reinici", c) else (
            "hibernar" if re.search(r"hibern", c) else "desligar")
        executar_acao(verbo, {"segundos": 60})
    elif re.search(R_STATUS, c):
        executar_acao("status_pc")
    elif re.search(R_LEMBRETE, c):
        tarefa_lembrete(comando, c)
    elif re.search(R_VOLUME, c) and not re.search(R_PESQ, c):
        if re.search(r"\b(mudo|silenciar|silencia|mutar)\b", c):
            executar_acao("volume", {"sentido": "mudo"})
        elif re.search(r"\b(abaix|baix|diminu|menos|reduz)\w*", c):
            executar_acao("volume", {"sentido": "diminuir", "quanto": 3})
        else:
            executar_acao("volume", {"sentido": "aumentar", "quanto": 3})
    elif re.search(R_ANTERIOR, c):
        executar_acao("midia_anterior")
    elif re.search(R_PROXIMA, c):
        executar_acao("midia_proxima")
    elif re.search(R_PLAY, c):
        # "dar play no spotify", "pausar a musica", "toca de novo"...
        if re.search(r"\bspotify\b", c) and not re.search(r"\b(abr|open)\w*", c):
            executar_acao("spotify_abrir")
        else:
            executar_acao("midia_play_pausa")
    elif re.search(R_PESQ, c):
        tarefa_pesquisar(termo_original(comando, re.sub(R_PESQ + r"\s*", "", c)))
    elif re.search(R_BLOQUEAR, c):
        tarefa_bloquear()
    elif re.search(R_TOCAR, c):
        termo = re.sub(R_TOCAR + r"\s*", "", c)
        termo = re.sub(r"^(uma\s+)?(musica|video|song|music)\s*(de|do|da|by|of)?\s*", "", termo).strip()
        tarefa_youtube(termo_original(comando, termo))
    elif re.search(R_ABRIR, c):
        alvo = re.sub(R_ABRIR + r"\s*", "", c)
        alvo = re.sub(r"^(o|a|os|as|the)\s+", "", alvo).strip()
        if not tentar_abrir(alvo):
            falar(f("nao_conheco", alvo=alvo))
            webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(alvo))
    elif processar_com_ia(comando):
        pass
    elif ENTRADA_BLOQUEADA:
        falar("Ainda nao fui programado para isso, senhor. "
              "Se quiser, diga: pesquisar e o assunto.")
    else:
        falar(f("nao_sei"))
        if perguntar_sim_nao():
            tarefa_pesquisar(comando)

    return True


def responder(comando):
    """Usada pelo bot: processa o comando e devolve a lista de frases de resposta."""
    global CAPTURAR
    CAPTURAR = True
    CAPTURADO.clear()
    try:
        continuar = processar(comando)
    finally:
        CAPTURAR = False
    return continuar, list(CAPTURADO)


# ============================================================================
# 10. INICIO
# ============================================================================
DEMO = {
    "en": "Good evening, sir. All systems are online. Shall I open the workshop?",
    "pt": "Boa noite, senhor. Todos os sistemas estao online. Devo abrir a oficina?",
}


def mostrar_status_ia():
    """Diagnostico rapido: --ia-status"""
    print("=" * 60)
    print("   STATUS DO CEREBRO DE IA")
    print("=" * 60)
    if cerebro is None or acoes is None:
        print("Arquivos acoes.py / cerebro.py nao encontrados.")
        return
    print(f"Modo IA habilitado: {USAR_IA}")
    cfg = cerebro.carregar_config()
    if not cfg.get("api_key"):
        print("Chave: nenhuma (rode Configurar-IA.bat)")
        print(f"Acoes disponiveis no catalogo: {len(acoes.CATALOGO)}")
        return
    chave = cfg["api_key"]
    print(f"Chave: {chave[:6]}...{chave[-4:]}")
    print(f"Modelo principal: {cfg.get('modelo')}")
    print(f"Alternativos: {', '.join(cfg.get('modelos_alternativos') or []) or '(nenhum)'}")
    print(f"Acoes disponiveis no catalogo: {len(acoes.CATALOGO)}")
    print("Testando a conexao...")
    ok, msg = cerebro.testar_chave()
    print(("OK: " if ok else "FALHOU: ") + msg)
    print("=" * 60)


def main():
    if "--ia-status" in sys.argv:
        mostrar_status_ia()
        return
    if MODO_DEMO:
        falar(DEMO[IDIOMA_FALA])
        return

    preaquecer_cache()

    if MODO_DEMO:
        pass
    elif cerebro is not None and cerebro.disponivel() and USAR_IA:
        print("(cerebro de IA ativo: entendo frases livres e decido as acoes)")
    elif USAR_IA:
        print("(IA desligada: sem chave. Rode Configurar-IA.bat para ele entender frases livres.)")

    falar(f("inicio"))

    try:
        if MODO_TEXTO or MODO_ESCUTA == "pressione":
            # modos antigos: digitar ou apertar ENTER
            while True:
                try:
                    comando = pegar_comando()
                except KeyboardInterrupt:
                    falar(f("sair"))
                    break
                if not processar(comando):
                    break
        else:
            # modo maos-livres: microfone sempre aberto
            loop_voz()
    finally:
        encerrar_microfone()


if __name__ == "__main__":
    main()
