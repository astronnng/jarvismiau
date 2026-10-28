# -*- coding: utf-8 -*-
"""
ACOES - o "corpo" do Jarvis
---------------------------
Catalogo de tudo que ele consegue fazer no computador, com nome, parametros e
nivel de risco. Tanto as regras locais quanto a IA escolhem acoes DESTE catalogo:
a IA nunca executa nada fora daqui. Isso e o que mantem o controle na sua mao.

Cada acao devolve uma frase (o que ele fala) ou None.
"""

import os
import re
import time
import ctypes
import datetime
import math
import subprocess
import webbrowser
import urllib.parse
import urllib.request

import lembretes as armazenamento_lembretes

CATALOGO = {}


def acao(nome, descricao, parametros="", risco=False):
    """Registra uma acao no catalogo."""
    def registrar(funcao):
        CATALOGO[nome] = {
            "nome": nome,
            "descricao": descricao,
            "parametros": parametros,
            "risco": risco,      # se True, o Jarvis pede confirmacao antes
            "funcao": funcao,
        }
        return funcao
    return registrar


def listar_para_ia():
    """Lista compacta do catalogo, para colocar no prompt da IA."""
    linhas = []
    for nome, info in CATALOGO.items():
        params = f" | parametros: {info['parametros']}" if info["parametros"] else ""
        risco = " | EXIGE CONFIRMACAO" if info["risco"] else ""
        linhas.append(f"- {nome}: {info['descricao']}{params}{risco}")
    return "\n".join(linhas)


# ============================================================================
# INFRAESTRUTURA DO WINDOWS
# ============================================================================
NO_WINDOWS = os.name == "nt"

VK = {
    "play_pause": 0xB3,
    "proxima": 0xB0,
    "anterior": 0xB1,
    "parar": 0xB2,
    "volume_up": 0xAF,
    "volume_down": 0xAE,
    "mudo": 0xAD,
}


def _tecla(vk, vezes=1):
    """Aperta uma tecla de midia/volume. No Windows isso funciona em qualquer app."""
    if not NO_WINDOWS:
        return False
    try:
        user32 = ctypes.windll.user32
        for _ in range(vezes):
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
            time.sleep(0.03)
        return True
    except Exception:
        return False


def _iniciar(comando):
    subprocess.Popen(comando, shell=True)


# ============================================================================
# MIDIA
# ============================================================================
@acao("midia_play_pausa", "Da play ou pausa na musica/video que esta tocando (Spotify, YouTube, player)")
def midia_play_pausa(ctx, **kw):
    if _tecla(VK["play_pause"]):
        return "Feito, senhor."
    return "Nao consegui controlar o player neste computador."


@acao("midia_proxima", "Pula para a proxima musica/faixa")
def midia_proxima(ctx, **kw):
    if _tecla(VK["proxima"]):
        return "Proxima, senhor."
    return "Nao consegui pular a faixa."


@acao("midia_anterior", "Volta para a musica/faixa anterior")
def midia_anterior(ctx, **kw):
    if _tecla(VK["anterior"]):
        return "Voltando, senhor."
    return "Nao consegui voltar a faixa."


@acao("midia_parar", "Para completamente a reproducao")
def midia_parar(ctx, **kw):
    if _tecla(VK["parar"]):
        return "Parado, senhor."
    return "Nao consegui parar."


@acao("spotify_abrir", "Abre o Spotify no computador")
def spotify_abrir(ctx, **kw):
    _iniciar("start spotify:")
    time.sleep(2.5)
    _tecla(VK["play_pause"])
    return "Spotify aberto e tocando, senhor."


@acao("spotify_buscar", "Abre o Spotify na busca da musica/podcast desejado",
      "termo: nome da musica, artista ou podcast")
def spotify_buscar(ctx, termo="", **kw):
    termo = (termo or "").strip()
    if not termo:
        spotify_abrir(ctx)
        return "Spotify aberto, senhor."
    _iniciar(f'start "" "spotify:search:{termo}"')
    return f"Busquei {termo} no Spotify, senhor. E so apertar Enter."


@acao("youtube_tocar", "Toca um video ou musica no YouTube", "termo: o que tocar")
def youtube_tocar(ctx, termo="", **kw):
    termo = (termo or "").strip()
    if not termo:
        return "O que o senhor quer ouvir?"
    webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote(termo))
    return f"Procurando {termo} no YouTube, senhor."


@acao("volume", "Controla o volume do computador",
      "sentido: aumentar|diminuir|mudo ; quanto: 1 a 10 (padrao 2) ; percentual: 0 a 100")
def volume(ctx, sentido="aumentar", quanto=2, percentual=None, **kw):
    if percentual is not None:
        try:
            percentual = int(percentual)
        except (TypeError, ValueError):
            return "Informe um percentual inteiro entre 0 e 100, senhor."
        if not 0 <= percentual <= 100:
            return "O volume precisa ficar entre 0 e 100 por cento, senhor."
        if not NO_WINDOWS:
            return "O ajuste exato do volume so esta disponivel no Windows, senhor."
        try:
            from pycaw.pycaw import AudioUtilities

            AudioUtilities.GetSpeakers().EndpointVolume.SetMasterVolumeLevelScalar(
                percentual / 100.0, None)
            return f"Volume ajustado para {percentual} por cento, senhor."
        except Exception:
            return "Nao consegui ajustar o volume exato neste dispositivo de audio, senhor."

    try:
        quanto = max(1, min(int(quanto), 10))
    except Exception:
        quanto = 2
    sentido = (sentido or "aumentar").lower()
    if sentido in ("mudo", "mute", "silenciar"):
        _tecla(VK["mudo"])
        return "Som silenciado, senhor."
    if sentido in ("diminuir", "abaixar", "baixar", "menos"):
        _tecla(VK["volume_down"], quanto)
        return "Volume reduzido, senhor."
    _tecla(VK["volume_up"], quanto)
    return "Volume aumentado, senhor."


# ============================================================================
# APLICATIVOS E SITES
# ============================================================================
@acao("abrir_programa", "Abre um programa instalado no computador",
      "nome: calculadora, bloco de notas, paint, explorer, configuracoes, word, excel, steam, camera")
def abrir_programa(ctx, nome="", **kw):
    chave = ctx.normalizar(nome or "")
    if chave in ctx.PROGRAMAS:
        ctx.abrir_programa(ctx.PROGRAMAS[chave])
        return f"Abrindo {chave}, senhor."
    return None


@acao("abrir_site", "Abre um site no navegador",
      "nome: google, youtube, whatsapp, gmail, instagram, facebook, netflix, github, chatgpt, mapa, correios...")
def abrir_site(ctx, nome="", **kw):
    original = (nome or "").strip()
    chave = ctx.normalizar(original)
    if chave in ctx.SITES:
        webbrowser.open(ctx.SITES[chave])
        return f"Abrindo {chave}, senhor."
    # nome parece um endereco? (ex: "site da caixa.com.br")
    if re.search(r"\b[a-z0-9-]+\.(com|com\.br|net|org|io|gov|edu)(\.br)?\b", chave):
        alvo = re.search(r"([a-z0-9-]+\.)+[a-z]{2,}", chave).group(0)
        webbrowser.open("https://" + alvo)
        return f"Abrindo {alvo}, senhor."
    # nao conheco pelo nome: resolvo pesquisando, em vez de desistir
    if chave:
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(original))
        return f"Nao conheco {original} pelo nome, senhor. Pesquisei no Google."
    return None


@acao("abrir_url", "Abre um endereco de site qualquer", "url: endereco completo")
def abrir_url(ctx, url="", **kw):
    url = (url or "").strip()
    if not url:
        return None
    if not re.match(r"^https?://", url):
        url = "https://" + url
    webbrowser.open(url)
    return "Abrindo, senhor."


@acao("pesquisar_google", "Pesquisa qualquer coisa no Google", "termo: o que pesquisar")
def pesquisar_google(ctx, termo="", **kw):
    termo = (termo or "").strip()
    if not termo:
        return "O que o senhor deseja pesquisar?"
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(termo))
    return f"Pesquisando {termo}, senhor."


# ============================================================================
# INFORMACAO
# ============================================================================
@acao("clima", "Informa o clima/tempo de uma cidade", "cidade: nome da cidade")
def clima(ctx, cidade="", **kw):
    cidade = (cidade or "Bariri").strip()
    lang = "pt" if ctx.IDIOMA_FALA == "pt" else "en"
    try:
        url = (f"https://wttr.in/{urllib.parse.quote(cidade)}"
               f"?format=%l|%t|%C&m&lang={lang}")
        with urllib.request.urlopen(url, timeout=8) as r:
            nome, temp, cond = r.read().decode("utf-8").strip().split("|")
        temp = temp.replace("+", "").replace("°C", "").strip()
        if ctx.IDIOMA_FALA == "pt":
            return f"Em {nome} esta {temp} graus e {cond.lower()}."
        return f"In {nome} it is {temp} degrees and {cond.lower()}."
    except Exception:
        return "Nao consegui consultar o clima agora, senhor."


@acao("horas", "Informa a hora atual")
def horas(ctx, **kw):
    a = datetime.datetime.now()
    plural = "minuto" if a.minute == 1 else "minutos"
    return f"Sao {a.hour} horas e {a.minute} {plural}, senhor."


@acao("data", "Informa a data de hoje")
def data(ctx, **kw):
    a = datetime.datetime.now()
    meses = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho",
             "agosto", "setembro", "outubro", "novembro", "dezembro"]
    dias = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
            "sexta-feira", "sabado", "domingo"]
    return f"Hoje e {dias[a.weekday()]}, {a.day} de {meses[a.month - 1]} de {a.year}, senhor."


# ============================================================================
# LEMBRETES PERSISTENTES
# ============================================================================
@acao("lembrete", "Cria um lembrete que avisa por voz depois de um tempo",
      "minutos: numero (aceita fracoes, ex 0.5) ; motivo: sobre o que avisar")
def lembrete(ctx, minutos=5, motivo="", **kw):
    try:
        minutos = float(minutos)
    except Exception:
        minutos = 5
    if not math.isfinite(minutos) or minutos <= 0:
        minutos = 5
    motivo = (motivo or "o lembrete").strip()
    armazenamento_lembretes.Lembretes().criar(motivo, minutos)

    if minutos < 1:
        seg = int(minutos * 60)
        extra = f" sobre {motivo}" if motivo != "o lembrete" else ""
        return f"Certo, senhor. Aviso em {seg} segundos{extra}."
    if minutos == 1:
        return f"Certo, senhor. Aviso em 1 minuto sobre {motivo}."
    return f"Certo, senhor. Aviso em {minutos:g} minutos sobre {motivo}."


@acao("listar_lembretes", "Lista os lembretes ativos com assunto, horario e estado")
def listar_lembretes(ctx, **kw):
    ativos = armazenamento_lembretes.Lembretes().listar()
    if not ativos:
        return "Nenhum lembrete ativo, senhor."
    linhas = []
    for item in ativos:
        horario = armazenamento_lembretes.formatar_horario(item["vence_em"])
        estado = "alarme tocando" if item["estado"] == "tocando" else "pendente"
        linhas.append(f"{item['motivo']} (vence as {horario}; {estado})")
    return f"Tenho {len(ativos)} lembrete(s): " + "; ".join(linhas) + ", senhor."


@acao("confirmar_lembrete", "Confirma e encerra um alarme de lembrete pelo assunto",
      "assunto: trecho ou titulo do lembrete que esta tocando")
def confirmar_lembrete(ctx, assunto="", **kw):
    return armazenamento_lembretes.Lembretes().confirmar(assunto)


# ============================================================================
# SISTEMA (alguns pedem confirmacao)
# ============================================================================
@acao("bloquear", "Bloqueia o Windows")
def bloquear(ctx, **kw):
    _iniciar("rundll32.exe user32.dll,LockWorkStation")
    return "Blocando o computador, senhor."


@acao("desligar", "Desliga o computador", "segundos: espera antes de desligar (padrao 60)", risco=True)
def desligar(ctx, segundos=60, **kw):
    try:
        segundos = int(segundos)
    except Exception:
        segundos = 60
    _iniciar(f"shutdown /s /t {segundos}")
    return f"Desligando em {segundos} segundos, senhor. Diga 'cancelar desligamento' para abortar."


@acao("cancelar_desligamento", "Cancela um desligamento agendado")
def cancelar_desligamento(ctx, **kw):
    _iniciar("shutdown /a")
    return "Desligamento cancelado, senhor."


@acao("reiniciar", "Reinicia o computador", "segundos: espera antes (padrao 60)", risco=True)
def reiniciar(ctx, segundos=60, **kw):
    try:
        segundos = int(segundos)
    except Exception:
        segundos = 60
    _iniciar(f"shutdown /r /t {segundos}")
    return f"Reiniciando em {segundos} segundos, senhor."


@acao("hibernar", "Coloca o computador em hibernacao", risco=True)
def hibernar(ctx, **kw):
    _iniciar("shutdown /h")
    return "Hibernando, senhor."


@acao("status_pc", "Informa como esta o computador (memoria, disco, bateria, tempo ligado)")
def status_pc(ctx, **kw):
    if not NO_WINDOWS:
        return "So consigo ver isso no Windows, senhor."
    try:
        script = (
            "$os=Get-CimInstance Win32_OperatingSystem;"
            "$livre=[math]::Round($os.FreePhysicalMemory/1MB,1);"
            "$total=[math]::Round($os.TotalVisibleMemorySize/1MB,1);"
            "$d=Get-PSDrive C;"
            "$disco=[math]::Round($d.Free/1GB,1);"
            "$b=Get-CimInstance Win32_Battery;"
            "$bat=if($b){$b.EstimatedChargeRemaining}else{'sem bateria'};"
            "Write-Output \"$livre|$total|$disco|$bat\""
        )
        saida = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        partes = saida.stdout.strip().split("|")
        if len(partes) >= 4:
            livre, total, disco, bat = partes[:4]
            return (f"Memoria livre: {livre} de {total} GB. "
                    f"Disco C com {disco} GB livres. Bateria: {bat}.")
    except Exception:
        pass
    return "Nao consegui ler o status do computador, senhor."


# ============================================================================
# EXECUCAO
# ============================================================================
def executar(nome, params, ctx, pedir_confirmacao=None):
    """
    Executa uma acao do catalogo.
    Devolve (ok, fala). Nunca executa nada fora do catalogo.
    """
    info = CATALOGO.get(nome)
    if not info:
        return False, None

    if info["risco"] and pedir_confirmacao is not None:
        if not pedir_confirmacao(nome):
            return False, None      # quem perguntou ja explicou o motivo

    try:
        resultado = info["funcao"](ctx, **(params or {}))
    except TypeError as e:
        return False, f"Nao entendi os detalhes dessa acao, senhor. ({e})"
    except Exception as e:
        return False, f"Tentei, mas algo deu errado, senhor. ({e})"

    if resultado is None:
        return False, None
    return True, resultado


def existe(nome):
    return nome in CATALOGO


def eh_arriscada(nome):
    return bool(CATALOGO.get(nome, {}).get("risco"))
