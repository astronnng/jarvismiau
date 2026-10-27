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
import datetime
import tempfile
import subprocess
import unicodedata
import urllib.request
import urllib.parse
import webbrowser

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
        "hora": "Sao {h} horas e {m} minutos, senhor.",
        "data": "Hoje e {dia}, {d} de {mes} de {ano}, senhor.",
        "clima": "Em {cidade} esta {temp} graus e {condicao}.",
        "clima_erro": "Nao consegui consultar o clima agora, senhor.",
        "pesquisando": "Pesquisando {termo}, senhor.",
        "abrindo_site": "Abrindo {alvo}, senhor.",
        "abrindo_app": "Abrindo {alvo}, senhor.",
        "nao_conheco": "Nao conheco {alvo}, senhor. Vou pesquisar.",
        "yt": "Procurando {termo} no YouTube, senhor.",
        "bloqueando": "Blocando o computador, senhor.",
        "nao_sei": "Ainda nao fui programado para isso, senhor. Pesquisar no Google?",
        "sem_microfone": "Nao encontrei o microfone, senhor.",
        "sem_internet": "Estou sem conexao com o servico de voz, senhor.",
        "o_que_pesquisar": "O que o senhor deseja pesquisar?",
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
        "nao_sei": "I am not programmed for that yet, sir. Shall I search the web?",
        "sem_microfone": "I cannot find the microphone, sir.",
        "sem_internet": "I have lost the connection to the speech service, sir.",
        "o_que_pesquisar": "What shall I search for, sir?",
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


def _falar_windows(texto):
    if _sapi is None:
        return False
    try:
        _sapi.say(texto)
        _sapi.runAndWait()
        return True
    except Exception:
        return False


def _tocar_mp3(caminho):
    """Toca um arquivo mp3 (usa pygame; cai no player padrao do Windows se falhar)."""
    global _pygame_ok
    if _pygame_ok is None:
        try:
            import pygame

            pygame.mixer.init()
            _pygame_ok = True
        except Exception:
            _pygame_ok = False
    if _pygame_ok:
        try:
            import pygame

            pygame.mixer.music.load(caminho)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.unload()
            return True
        except Exception:
            pass
    # ultimo recurso no Windows: abre no player padrao
    try:
        os.startfile(caminho)  # noqa: S606  (so existe no Windows)
        time.sleep(2.5)
        return True
    except Exception:
        return False


def _falar_neural(texto):
    """Gera a fala com a voz neural (edge-tts) e toca."""
    try:
        import edge_tts
    except ImportError:
        return False
    try:
        tmp = os.path.join(tempfile.gettempdir(), "jarvis_fala.mp3")

        async def gerar():
            com = edge_tts.Communicate(
                texto, PERFIL["voz"],
                rate=PERFIL.get("rate", "+0%"),
                pitch=PERFIL.get("pitch", "+0Hz"),
            )
            await com.save(tmp)

        asyncio.run(gerar())
        return _tocar_mp3(tmp)
    except Exception:
        return False


def falar(texto):
    """Fala o texto com o motor escolhido. Sempre imprime na tela."""
    print(f"{NOME}: {texto}")
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
def ouvir():
    try:
        import speech_recognition as sr
    except ImportError:
        falar(f("sem_microfone"))
        return ""
    r = sr.Recognizer()
    try:
        with sr.Microphone() as fonte:
            r.adjust_for_ambient_noise(fonte, duration=0.4)
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
        falar(f("hora", h=a.hour, m=a.minute))


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


def tarefa_bloquear():
    falar(f("bloqueando"))
    time.sleep(0.6)
    abrir_programa("rundll32.exe user32.dll,LockWorkStation")


# ============================================================================
# 9. O CEREBRO  (padroes em portugues + ingles)
# ============================================================================
R_SAIR = r"\b(sair|tchau|encerrar|desligar|exit|quit|goodbye|shut down|stop)\b"
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


def processar(comando):
    c = normalizar(comando)

    if not c:
        falar(f("nao_ouvi"))
        return True

    if re.search(R_SAIR, c):
        falar(f("sair"))
        return False
    if re.search(R_BEM, c):
        falar(f("bem"))
    elif re.search(R_OLA, c):
        falar(f("ola"))
    elif re.search(R_HORA, c) and not re.search(R_CLIMA, c):
        tarefa_hora()
    elif re.search(R_DATA, c):
        tarefa_data()
    elif re.search(R_CLIMA, c):
        tarefa_clima(c)
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
    else:
        falar(f("nao_sei"))
        if MODO_TEXTO:
            if re.match(R_SIM, input("(s/n) ").strip().lower()):
                tarefa_pesquisar(comando)

    return True


# ============================================================================
# 10. INICIO
# ============================================================================
DEMO = {
    "en": "Good evening, sir. All systems are online. Shall I open the workshop?",
    "pt": "Boa noite, senhor. Todos os sistemas estao online. Devo abrir a oficina?",
}


def main():
    if MODO_DEMO:
        falar(DEMO[IDIOMA_FALA])
        return
    falar(f("inicio"))
    while True:
        try:
            comando = pegar_comando()
        except KeyboardInterrupt:
            falar(f("sair"))
            break
        if not processar(comando):
            break


if __name__ == "__main__":
    main()
