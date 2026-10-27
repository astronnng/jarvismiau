# -*- coding: utf-8 -*-
"""
JARVIS no Telegram
------------------
Transforma o seu Jarvis em um bot de Telegram: voce manda mensagem (texto ou
audio) pelo celular e ele responde em texto E em voz, usando a mesma voz que
voce escolheu no jarvis.py.

Nao precisa de biblioteca extra: usa apenas a biblioteca padrao do Python.

COMO USAR
  1. Crie o bot no Telegram (guia: BOT-TELEGRAM.md)
  2. Dois cliques em "Iniciar-bot.bat"
  3. Na primeira vez ele pede o token do bot e guarda em bot_config.json
  4. Mande /start no Telegram. O primeiro chat que falar com o bot vira o dono.

IMPORTANTE: o bot roda no seu PC. Se o PC desligar, ele para.
"""

import os
import re
import sys
import json
import time
import mimetypes
import tempfile
import asyncio
import urllib.error
import urllib.parse
import urllib.request
import subprocess
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import jarvis  # noqa: E402

# O bot fala com o PC a distancia: acoes perigosas (desligar, reiniciar) ficam
# bloqueadas aqui de proposito, e a confirmacao nunca tenta abrir o microfone.
jarvis.PERMITIR_ACOES_ARRISCADAS = False
jarvis.ENTRADA_BLOQUEADA = True

CONFIG_PATH = AQUI / "bot_config.json"
API = "https://api.telegram.org/bot{token}/{metodo}"

# ============================================================================
# CONFIGURACAO
# ============================================================================
def carregar_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def salvar_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def pedir_token():
    print("=" * 62)
    print("   PRIMEIRA CONFIGURACAO DO BOT")
    print("=" * 62)
    print("Abra o Telegram, procure o @BotFather, mande /newbot e siga as")
    print("instrucoes. No fim ele te da um token parecido com:")
    print("   1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print()
    print("O guia completo esta em BOT-TELEGRAM.md")
    print("-" * 62)
    token = input("Cole o token aqui: ").strip()
    return token


# ============================================================================
# CHAMADAS A API DO TELEGRAM (sem bibliotecas externas)
# ============================================================================
def _requisicao(url, dados=None, timeout=40):
    if dados is None:
        req = urllib.request.Request(url)
    elif isinstance(dados, bytes):
        req = urllib.request.Request(url, data=dados)
    else:
        req = urllib.request.Request(
            url, data=urllib.parse.urlencode(dados).encode("utf-8"))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _multipart(campos, arquivo_campo, caminho, nome_arquivo, mime):
    limite = "----JarvisBoundary" + str(int(time.time() * 1000))
    corpo = b""
    for k, v in campos.items():
        corpo += f"--{limite}\r\n".encode()
        corpo += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        corpo += f"{v}\r\n".encode()
    corpo += f"--{limite}\r\n".encode()
    corpo += (f'Content-Disposition: form-data; name="{arquivo_campo}"; '
              f'filename="{nome_arquivo}"\r\n').encode()
    corpo += f"Content-Type: {mime}\r\n\r\n".encode()
    corpo += Path(caminho).read_bytes()
    corpo += b"\r\n"
    corpo += f"--{limite}--\r\n".encode()
    return corpo, f"multipart/form-data; boundary={limite}"


class Bot:
    def __init__(self, token):
        self.token = token
        self.offset = 0

    def url(self, metodo):
        return API.format(token=self.token, metodo=metodo)

    # ---------- API ----------
    def get_me(self):
        return _requisicao(self.url("getMe"), timeout=15)["result"]

    def atualizacoes(self, timeout=30):
        try:
            r = _requisicao(
                self.url("getUpdates") +
                f"?offset={self.offset}&timeout={timeout}",
                timeout=timeout + 15)
            return r.get("result", [])
        except urllib.error.URLError:
            time.sleep(3)
            return []
        except Exception:
            time.sleep(3)
            return []

    def enviar_texto(self, chat_id, texto):
        try:
            _requisicao(self.url("sendMessage"),
                        {"chat_id": chat_id, "text": texto})
        except Exception as e:
            print(f"[erro ao enviar texto] {e}")

    def enviar_audio(self, chat_id, caminho_mp3, titulo="Jarvis"):
        try:
            corpo, tipo = _multipart(
                {"chat_id": chat_id, "title": titulo, "performer": "Jarvis"},
                "audio", caminho_mp3, "jarvis.mp3", "audio/mpeg")
            req = urllib.request.Request(self.url("sendAudio"), data=corpo,
                                         headers={"Content-Type": tipo})
            with urllib.request.urlopen(req, timeout=45) as r:
                r.read()
        except Exception as e:
            print(f"[erro ao enviar audio] {e}")

    def baixar_arquivo(self, file_id, destino):
        info = _requisicao(self.url("getFile") + f"?file_id={file_id}",
                           timeout=20)["result"]
        url = (f"https://api.telegram.org/file/bot{self.token}/"
               f"{info['file_path']}")
        with urllib.request.urlopen(url, timeout=45) as r:
            Path(destino).write_bytes(r.read())
        return destino


# ============================================================================
# VOZ: gera o mp3 da resposta com a mesma voz do jarvis.py
# ============================================================================
def gerar_audio(texto, destino):
    """Gera o mp3 da resposta reaproveitando o cache do jarvis.py."""
    if jarvis.PERFIL["motor"] == "sapi":
        return None  # voz do Windows nao gera arquivo
    caminho = jarvis.gerar_mp3(texto, destino)
    return caminho if caminho and os.path.exists(caminho) else None


# ============================================================================
# AUDIO DO USUARIO: transcreve mensagem de voz (precisa do ffmpeg)
# ============================================================================
def tem_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def transcrever(caminho_audio):
    """Converte para wav com ffmpeg e transcreve em portugues."""
    if not tem_ffmpeg():
        return None
    wav = str(Path(caminho_audio).with_suffix(".wav"))
    try:
        subprocess.run(["ffmpeg", "-y", "-i", caminho_audio, "-ar", "16000",
                        "-ac", "1", wav],
                       capture_output=True, timeout=60)
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(wav) as fonte:
            audio = r.record(fonte)
        return r.recognize_google(audio, language=jarvis.IDIOMA_MICROFONE)
    except Exception as e:
        # UnknownValueError = falou mas nao deu para entender -> devolve ""
        if type(e).__name__ == "UnknownValueError":
            return ""
        print(f"[erro ao transcrever] {e}")
        return None


# ============================================================================
# LOGICA DO BOT
# ============================================================================
AJUDA = (
    "🤖 Jarvis online.\n\n"
    "Fale comigo por texto ou por mensagem de voz. Eu respondo por escrito e em áudio.\n\n"
    "EXEMPLOS:\n"
    "• que horas são\n"
    "• que dia é hoje\n"
    "• clima em Bariri\n"
    "• abrir youtube\n"
    "• abrir calculadora\n"
    "• pesquisar preço do dólar\n"
    "• tocar Legião Urbana\n"
    "• bloquear o computador\n\n"
    "COMANDOS DO BOT:\n"
    "/ajuda — esta mensagem\n"
    "/voz — qual voz está ativa\n"
    "/id — mostra o ID deste chat\n\n"
    "Lembre: eu rodo no seu PC, então ele precisa estar ligado."
)


def responder_comando(bot, chat_id, texto):
    """Processa um comando e devolve texto + audio."""
    texto = (texto or "").strip()
    if not texto:
        bot.enviar_texto(chat_id, "Não ouvi nada, senhor.")
        return

    baixo = texto.lower().strip()

    if baixo in ("/start", "/ajuda", "/help", "ajuda"):
        bot.enviar_texto(chat_id, AJUDA)
        return
    if baixo in ("/id", "id"):
        bot.enviar_texto(chat_id, f"Seu chat ID é {chat_id}.")
        return
    if baixo == "/voz":
        bot.enviar_texto(chat_id, f"Voz ativa: {jarvis.VOZ} "
                                  f"({jarvis.PERFIL.get('voz')})")
        return

    print(f"[{chat_id}] -> {texto}")
    continuar, respostas = jarvis.responder(texto)
    if not respostas:
        respostas = ["Não entendi, senhor."]

    for frase in respostas:
        bot.enviar_texto(chat_id, frase)
        mp3 = os.path.join(tempfile.gettempdir(), "jarvis_resposta.mp3")
        if gerar_audio(frase, mp3):
            bot.enviar_audio(chat_id, mp3)
        print(f"[{chat_id}] <- {frase}")


def tratar_mensagem(bot, msg, cfg):
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    if chat_id is None:
        return

    # --- controle de acesso ---
    donos = cfg.setdefault("donos", [])
    if not donos:
        donos.append(chat_id)
        salvar_config(cfg)
        bot.enviar_texto(chat_id,
                         "🔐 Você é o dono deste Jarvis. Só este chat pode dar comandos.\n"
                         "Outros chats serão ignorados.")
    elif chat_id not in donos:
        bot.enviar_texto(chat_id, "Este Jarvis é privado.")
        print(f"[bloqueado] chat {chat_id} tentou falar")
        return

    # --- mensagem de voz ---
    if "voice" in msg or "audio" in msg:
        arquivo = msg.get("voice") or msg.get("audio")
        if not tem_ffmpeg():
            bot.enviar_texto(chat_id,
                             "Ainda não sei ouvir áudio neste computador "
                             "(falta o ffmpeg). Por enquanto me escreva, senhor.")
            return
        destino = os.path.join(tempfile.gettempdir(), "jarvis_entrada.ogg")
        try:
            bot.baixar_arquivo(arquivo["file_id"], destino)
        except Exception as e:
            bot.enviar_texto(chat_id, "Não consegui baixar o áudio.")
            print(f"[erro download] {e}")
            return
        texto = transcrever(destino)
        if texto is None:
            bot.enviar_texto(chat_id, "Não consegui entender o áudio, senhor.")
            return
        if not texto:
            bot.enviar_texto(chat_id, "Não entendi o que foi dito, senhor.")
            return
        responder_comando(bot, chat_id, texto)
        return

    # --- texto ---
    responder_comando(bot, chat_id, msg.get("text", ""))


def main():
    cfg = carregar_config()

    token = cfg.get("token") or os.environ.get("TELEGRAM_TOKEN", "").strip()
    if not token:
        token = pedir_token()
        if not token:
            print("Token vazio. Encerrando.")
            return
        cfg["token"] = token
        salvar_config(cfg)

    bot = Bot(token)

    try:
        eu = bot.get_me()
    except Exception as e:
        print(f"Não consegui falar com o Telegram. Token correto? ({e})")
        print("Apague o arquivo bot_config.json e rode de novo para digitar outro token.")
        return

    print("=" * 62)
    print(f"   BOT ONLINE: @{eu.get('username')}")
    print("=" * 62)
    print(f"Voz: {jarvis.VOZ} ({jarvis.PERFIL.get('voz')})")
    print("Abra o Telegram, encontre o bot e mande /start.")
    if not cfg.get("donos"):
        print("O primeiro chat que mandar mensagem será registrado como dono.")
    print("Deixe esta janela aberta. Ctrl+C encerra.")
    print()

    # avisa os donos que o bot subiu
    for dono in cfg.get("donos", []):
        bot.enviar_texto(dono, "🟢 Jarvis online, senhor.")

    while True:
        try:
            for atualizacao in bot.atualizacoes():
                bot.offset = atualizacao["update_id"] + 1
                msg = atualizacao.get("message") or atualizacao.get("edited_message")
                if not msg:
                    continue
                try:
                    tratar_mensagem(bot, msg, cfg)
                except Exception as e:
                    print(f"[erro ao tratar mensagem] {e}")
        except KeyboardInterrupt:
            print("\nEncerrando o bot. Até logo, senhor.")
            for dono in cfg.get("donos", []):
                bot.enviar_texto(dono, "🔴 Jarvis offline, senhor.")
            break
        except Exception as e:
            print(f"[erro no laço principal] {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
