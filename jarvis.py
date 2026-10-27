# -*- coding: utf-8 -*-
"""
JARVIS simples - v1
--------------------
Um assistente por voz para Windows que conversa e executa tarefas basicas.

Como usar:
    python jarvis.py            -> modo voz (aperte ENTER para falar)
    python jarvis.py --texto    -> modo texto (digite os comandos)

Dica: para testar sem microfone, use o modo texto.
"""

import os
import re
import sys
import time
import random
import datetime
import subprocess
import unicodedata
import webbrowser
import urllib.request
import urllib.parse

# ----------------------------------------------------------------------------
# 1. CONFIGURACOES
# ----------------------------------------------------------------------------
NOME = "Jarvis"
IDIOMA_VOZ = "pt-BR"

MODO_TEXTO = "--texto" in sys.argv

FRASES_DE_ESPERA = [
    "Pois nao, senhor.",
    "As suas ordens.",
    "Estou ouvindo.",
    "Sim, senhor.",
]


# ----------------------------------------------------------------------------
# 2. FALA E ESCUTA
# ----------------------------------------------------------------------------
try:
    import pyttsx3

    _motor = pyttsx3.init()
    _motor.setProperty("rate", 180)
    for _v in _motor.getProperty("voices"):
        if "portug" in str(_v.name).lower() or "brazil" in str(_v.id).lower():
            _motor.setProperty("voice", _v.id)
            break
except Exception:
    _motor = None


def falar(texto):
    """Fala o texto (ou imprime, se a voz nao estiver disponivel)."""
    print(f"{NOME}: {texto}")
    if _motor is None:
        return
    try:
        _motor.say(texto)
        _motor.runAndWait()
    except Exception:
        pass


def ouvir():
    """Escuta o microfone e devolve o texto reconhecido (string vazia se falhar)."""
    import speech_recognition as sr

    r = sr.Recognizer()
    with sr.Microphone() as fonte:
        r.adjust_for_ambient_noise(fonte, duration=0.4)
        print("(fale agora...)")
        try:
            audio = r.listen(fonte, timeout=6, phrase_time_limit=8)
        except sr.WaitTimeoutError:
            return ""
    try:
        return r.recognize_google(audio, language=IDIOMA_VOZ)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        falar("Estou sem conexao com o servico de voz.")
        return ""


def pegar_comando():
    if MODO_TEXTO:
        try:
            return input("Voce: ").strip()
        except (EOFError, KeyboardInterrupt):
            return "sair"
    input("Aperte ENTER para falar...")
    return ouvir()


# ----------------------------------------------------------------------------
# 3. UTILITARIOS
# ----------------------------------------------------------------------------
def normalizar(t):
    """minusculas, sem acentos e sem pontuacao extra."""
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip()


def abrir_programa(caminho):
    subprocess.Popen(caminho, shell=True)


# ----------------------------------------------------------------------------
# 4. CATALOGOS (voce pode adicionar o que quiser aqui)
# ----------------------------------------------------------------------------
SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "whatsapp": "https://web.whatsapp.com",
    "gmail": "https://mail.google.com",
    "email": "https://mail.google.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "netflix": "https://www.netflix.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "gemini": "https://gemini.google.com",
    "noticias": "https://news.google.com",
    "mapa": "https://maps.google.com",
    "mapas": "https://maps.google.com",
    "mercado livre": "https://www.mercadolivre.com.br",
    "correios": "https://www.correios.com.br",
}

PROGRAMAS = {
    "calculadora": "calc.exe",
    "bloco de notas": "notepad.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "arquivos": "explorer.exe",
    "gerenciador de tarefas": "taskmgr.exe",
    "configuracoes": "start ms-settings:",
    "spotify": "start spotify:",
    "whatsapp": "start whatsapp:",
    "camera": "start microsoft.windows.camera:",
    "word": "start winword",
    "excel": "start excel",
}


# ----------------------------------------------------------------------------
# 5. TAREFAS
# ----------------------------------------------------------------------------
def horas():
    agora = datetime.datetime.now()
    falar(f"Sao {agora.hour} horas e {agora.minute} minutos.")


def data():
    agora = datetime.datetime.now()
    meses = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho",
             "agosto", "setembro", "outubro", "novembro", "dezembro"]
    dias = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
            "sexta-feira", "sabado", "domingo"]
    falar(f"Hoje e {dias[agora.weekday()]}, {agora.day} de {meses[agora.month - 1]} de {agora.year}.")


def clima(comando):
    cidade = re.sub(r".*(clima|previsao do tempo|temperatura|tempo)\s*(em|de|no|na|hoje)?\s*", "", comando).strip()
    cidade = cidade or "Bariri"
    try:
        url = f"https://wttr.in/{urllib.parse.quote(cidade)}?format=%l|%t|%C&m&lang=pt"
        with urllib.request.urlopen(url, timeout=8) as r:
            nome_cidade, temp, condicao = r.read().decode("utf-8").strip().split("|")
        temp = temp.replace("+", "").replace("°C", " graus")
        falar(f"Em {nome_cidade} esta {temp} e {condicao.lower()}.")
    except Exception:
        falar("Nao consegui consultar o clima agora.")


def pesquisar(termo):
    if not termo:
        falar("O que voce quer pesquisar?")
        return
    falar(f"Pesquisando {termo}.")
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(termo))


def abrir_site(nome):
    if nome in SITES:
        falar(f"Abrindo {nome}.")
        webbrowser.open(SITES[nome])
        return True
    return False


def abrir_app(nome):
    if nome in PROGRAMAS:
        falar(f"Abrindo {nome}.")
        abrir_programa(PROGRAMAS[nome])
        return True
    return False


def bloquear():
    falar("Blocando o computador.")
    time.sleep(0.8)
    abrir_programa("rundll32.exe user32.dll,LockWorkStation")


# ----------------------------------------------------------------------------
# 6. O CEREBRO: escolhe a tarefa a partir do que foi dito
# ----------------------------------------------------------------------------
def processar(comando):
    """Recebe o comando em texto. Executa a acao e devolve False para sair."""
    c = normalizar(comando)

    if not c:
        falar(random.choice(["Nao ouvi nada.", "Pode repetir?"]))
        return True

    # --- conversa / saudacoes ---
    if re.search(r"\b(oi|ola|bom dia|boa tarde|boa noite)\b", c):
        falar(f"Ola! {random.choice(FRASES_DE_ESPERA)}")
    elif re.search(r"\b(tudo bem|como voce esta|como vai)\b", c):
        falar("Tudo em ordem. Pronto para ajudar.")

    # --- sair ---
    elif re.search(r"\b(sair|tchau|desligar assistente|encerrar)\b", c):
        falar("Ate logo, senhor.")
        return False

    # --- hora e data ---
    elif re.search(r"\b(horas?|que hora)\b", c) and "clima" not in c:
        horas()
    elif re.search(r"\b(data|dia de hoje|que dia)\b", c):
        data()

    # --- clima ---
    elif re.search(r"\b(clima|temperatura|previsao do tempo|tempo em|tempo hoje)\b", c):
        clima(c)

    # --- pesquisar ---
    elif re.search(r"^(pesquisar|pesquise|procure|buscar|busque)\b", c):
        pesquisar(re.sub(r"^(pesquisar|pesquise|procure|buscar|busque)\s*", "", c))

    # --- abrir sites ---
    elif re.match(r"^(abrir|abra|abre|entrar no|entrar na|va para|ir para)\b", c):
        alvo = re.sub(r"^(abrir|abra|abre|entrar no|entrar na|va para|ir para)\s*", "", c)
        alvo = re.sub(r"^(o|a|os|as)\s+", "", alvo).strip()
        if abrir_app(alvo) or abrir_site(alvo):
            pass
        else:
            falar(f"Nao conheco {alvo}. Vou pesquisar no Google.")
            pesquisar(alvo)

    # --- YouTube direto ---
    elif re.search(r"^(tocar|colocar)\b", c):
        termo = re.sub(r"^(tocar|colocar)\s*", "", c)
        termo = re.sub(r"^(uma\s+)?(musica|video)\s*(de|do|da)?\s*", "", termo).strip()
        falar(f"Procurando {termo} no YouTube.")
        webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote(termo))

    # --- sistema ---
    elif re.search(r"\b(bloquear|trancar)\b", c):
        bloquear()

    # --- fallback: nao entendeu ---
    else:
        falar(f"Ainda nao sei fazer isso. Quer que eu pesquise '{comando}' no Google?")
        if MODO_TEXTO:
            resp = input("(s/n) ").strip().lower()
            if resp.startswith("s"):
                pesquisar(comando)

    return True


# ----------------------------------------------------------------------------
# 7. INICIO
# ----------------------------------------------------------------------------
def main():
    falar(f"Sistemas iniciados. Ola, eu sou o {NOME}. Diga 'sair' para encerrar.")
    while True:
        try:
            comando = pegar_comando()
        except KeyboardInterrupt:
            falar("Ate logo.")
            break
        if not comando:
            falar("Nao entendi. Tente de novo.")
            continue
        if not processar(comando):
            break


if __name__ == "__main__":
    main()
