# -*- coding: utf-8 -*-
"""
CEREBRO IA - a camada que faz o Jarvis "entender" em vez de decorar comandos
---------------------------------------------------------------------------
Como funciona:
  1. Voce fala: "dar play no spotify" (ou qualquer frase, do jeito que quiser)
  2. Este modulo manda a frase + o CATALOGO DE ACOES para uma IA (Gemini)
  3. A IA devolve um plano em JSON: o que falar e quais acoes executar
  4. O plano e validado: so acoes do catalogo rodam; as perigosas pedem confirmacao

Sem chave de API, nada quebra: o Jarvis usa apenas as regras locais.

Configuracao em dados/ia_config.json (criado por `Jarvis.bat ia`):
{
  "api_key": "SUA_CHAVE",
  "modelo": "gemini-3.5-flash-lite",
  "modelos_alternativos": ["gemini-3.8-flash", "gemini-3.1-flash-lite"],
  "ativo": true
}
"""

import os
import re
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import caminhos

AQUI = Path(__file__).resolve().parent
CONFIG_PATH = caminhos.dados("ia_config.json")
API_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "{modelo}:generateContent")

# ordem de tentativa, caso o modelo principal nao exista na sua chave
MODELOS_PADRAO = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
]

_cache_config = {"mtime": None, "cfg": None}


def carregar_config():
    """Le ia_config.json (com cache para nao reler a cada comando)."""
    global _cache_config
    if not CONFIG_PATH.exists():
        return {}
    try:
        mtime = CONFIG_PATH.stat().st_mtime
        if _cache_config["mtime"] == mtime and _cache_config["cfg"] is not None:
            return _cache_config["cfg"]
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        _cache_config = {"mtime": mtime, "cfg": cfg}
        return cfg
    except Exception:
        return {}


def salvar_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    global _cache_config
    _cache_config = {"mtime": None, "cfg": None}


def chave():
    cfg = carregar_config()
    return (cfg.get("api_key") or os.environ.get("GEMINI_API_KEY", "")).strip()


def disponivel():
    cfg = carregar_config()
    if cfg.get("ativo") is False:
        return False
    return bool(chave())


def modelos():
    cfg = carregar_config()
    principal = cfg.get("modelo")
    alternativos = cfg.get("modelos_alternativos") or []
    lista = []
    if principal:
        lista.append(principal)
    for m in alternativos:
        if m not in lista:
            lista.append(m)
    for m in MODELOS_PADRAO:
        if m not in lista:
            lista.append(m)
    return lista


# ============================================================================
# O PROMPT
# ============================================================================
# Regra extra, so enviada quando a frase fala de navegador (junto com as acoes dele).
REGRA_NAVEGADOR = """10. NAVEGADOR. Para "abre o primeiro/segundo video", use youtube_pesquisar e depois
    youtube_abrir_resultado (posicao 1, 2...; nova_aba true se pedirem outra aba). O mesmo vale
    para o Google com google_pesquisar e google_abrir_resultado. Se o usuario ja estiver numa
    pesquisa, use so a acao de abrir. Controles do video ("pausa", "proximo", "velocidade 1.5")
    usam youtube_player. E-mails usam gmail_*. Spotify Web e YouTube Music usam musica_controle e
    musica_tocando. Abas: aba_silenciar (som so da aba), abas_fechar, aba_reabrir, abas_agrupar.
    "Aquele site que vi sobre X" usa historico_buscar (ou favoritos_buscar) e depois resultado_abrir.
    Em um site sem acao propria, use navegador_tarefa com a instrucao completa. Se a acao
    responder que a extensao nao esta conectada, repasse isso. Se um atalho nao achar nada,
    sugira navegador_diagnostico.
"""


def _parte_fixa(catalogo, navegador=True):
    """
    Tudo que NAO muda entre chamadas. Vai primeiro no prompt: o Gemini reaproveita
    automaticamente prefixos repetidos (cache implicito), entao quanto mais estavel e
    longo o comeco, mais rapida e barata a chamada. Nao ponha hora, contexto ou o
    comando do usuario aqui.
    """
    regra_navegador = REGRA_NAVEGADOR if navegador else ""
    ultima = 11 if navegador else 10
    return f"""Voce e o JARVIS, o assistente do senhor. Fala portugues do Brasil,
trata o usuario por "senhor", e responde em frases curtas e naturais (sera falado em voz alta).

Voce controla o computador Windows dele. Estas sao as UNICAS acoes que existem:

{catalogo}

Sua tarefa: receber o comando do usuario e devolver um JSON valido, sem texto fora do JSON.

Formato:
{{"fala": "o que voce vai dizer ao senhor (curto)",
  "passos": [{{"acao": "nome_da_acao", "params": {{"parametro": "valor"}}}}]}}

REGRAS IMPORTANTES:
1. Use no maximo 3 passos. Para pergunta/conversa sem acao, use "passos": [].
2. Nunca invente acoes ou parametros que nao estejam na lista acima.
3. "dar play", "pausar", "tocar musica" -> midia_play_pausa. Pular -> midia_proxima.
4. "colocar a musica X", "tocar X" -> youtube_tocar (funciona sempre). Se o usuario disser
   explicitamente Spotify com uma musica, use spotify_buscar com o termo.
5. "aumentar/diminuir volume" -> volume. "silenciar" -> volume com sentido "mudo".
   Para um nivel exato (ex: 35 por cento), use volume com parametro percentual: 35.
   Ao pedirem a lista, use listar_lembretes. Para parar um alarme que esta tocando, ou cancelar
   um lembrete ("encerre", "encerrar o lembrete", "ok, verificado"), use confirmar_lembrete:
   assunto vazio vale para o que esta tocando (ou o unico lembrete pendente). Nunca trate
   "encerrar o lembrete" como pedido para fechar o Jarvis.
6. Se o usuario pedir algo que o computador faz mas nao esta na lista, use pesquisar_google
   com um termo bom, e diga isso na "fala".
7. Se a frase for uma pergunta de conhecimento (ex: "quanto e 15% de 340", "quem foi Santos Dumont"),
   responda voce mesmo no campo "fala" e deixe "passos": [].
8. Se faltar um dado essencial (ex: "toca uma musica" sem dizer qual), use "passos": [] e
   pergunte na "fala".
9. NUNCA escreva a acao "desligar" sem o usuario pedir claramente para desligar o computador.
{regra_navegador}{ultima}. Responda SOMENTE o JSON."""


def _parte_variavel(contexto=""):
    """O que muda a cada chamada: hora e conversa recente. Sempre depois da parte fixa."""
    hoje = time.strftime("%A, %d de %B de %Y, %H:%M")
    return (f"\n\nData e hora agora: {hoje}"
            + (f"\nContexto da conversa: {contexto}" if contexto else ""))


def montar_prompt(catalogo, contexto="", navegador=True):
    return _parte_fixa(catalogo, navegador) + _parte_variavel(contexto)


# ============================================================================
# CHAMADA DA API
# ============================================================================
def _chamar(modelo, api_key, prompt, timeout=20):
    corpo = {
        "contents": [{"parts": [{"text": prompt}], "role": "user"}],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 400,
            "responseMimeType": "application/json",
        },
    }
    dados = json.dumps(corpo).encode("utf-8")
    req = urllib.request.Request(
        API_URL.format(modelo=modelo),
        data=dados,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resposta = json.loads(r.read().decode("utf-8"))
    partes = resposta["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in partes)


def _limpar_json(texto):
    """A IA as vezes coloca ```json ... ``` mesmo pedindo so o JSON."""
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?\s*", "", texto)
    texto = re.sub(r"\s*```$", "", texto)
    ini = texto.find("{")
    fim = texto.rfind("}")
    if ini == -1 or fim == -1:
        return None
    try:
        return json.loads(texto[ini:fim + 1])
    except Exception:
        return None


def interpretar(texto, catalogo, contexto="", erro_anterior=None, navegador=True):
    """
    Manda a frase para a IA e devolve {"fala": str, "passos": [...]} ou None.
    Faz fallback entre modelos se um nao existir/estourar limite.
    `navegador=False` omite a regra do navegador (use com o catalogo sem essas acoes).
    """
    api_key = chave()
    if not api_key:
        return None

    prompt = montar_prompt(catalogo, contexto, navegador)
    if erro_anterior:
        prompt += (f"\n\nATENCAO: a tentativa anterior falhou ({erro_anterior})."
                   "\nCorrija o JSON e use apenas acoes e parametros validos.")
    prompt += f"\n\nCOMANDO DO USUARIO: {texto}"

    ultimo_erro = None
    for modelo in modelos():
        try:
            bruto = _chamar(modelo, api_key, prompt)
        except urllib.error.HTTPError as e:
            codigo = e.code
            ultimo_erro = f"HTTP {codigo}"
            if codigo in (400, 404, 429, 503):
                continue          # modelo indisponivel/limite -> tenta o proximo
            if codigo in (401, 403):
                return {"erro": "chave invalida ou sem permissao"}
            continue
        except Exception as e:
            ultimo_erro = str(e)
            continue

        plano = _limpar_json(bruto)
        if not plano:
            ultimo_erro = "JSON invalido"
            continue

        plano.setdefault("fala", "")
        plano.setdefault("passos", [])
        if not isinstance(plano["passos"], list):
            plano["passos"] = []
        plano["_modelo"] = modelo
        return plano

    return {"erro": ultimo_erro or "sem resposta"}


def responder_json(prompt, timeout=25):
    """
    Pergunta avulsa que exige um JSON de volta (usada pelo modo generico do navegador).
    Usa o mesmo fallback entre modelos. Devolve um dict, ou None se nada respondeu.
    """
    api_key = chave()
    if not api_key:
        return None
    for modelo in modelos():
        try:
            dados = _limpar_json(_chamar(modelo, api_key, prompt, timeout=timeout))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return None
            continue
        except Exception:
            continue
        if isinstance(dados, dict):
            return dados
    return None


def conversar(texto, contexto=""):
    """Pergunta livre, sem acoes: usado para 'conversar' quando nao ha catalogo."""
    plano = interpretar(texto, "(nenhuma acao disponivel)", contexto)
    if not plano or plano.get("erro"):
        return None
    return plano.get("fala") or None


def testar_chave(api_key=None, modelo=None):
    """Faz uma chamada minima para validar chave/modelo. Devolve (ok, mensagem)."""
    api_key = (api_key or chave()).strip()
    if not api_key:
        return False, "Nenhuma chave configurada."
    modelos_teste = [modelo] if modelo else modelos()
    erros = []
    for m in modelos_teste:
        try:
            resposta = _chamar(m, api_key, 'Responda apenas o JSON: {"ok": true}', timeout=20)
            if "ok" in resposta.lower():
                return True, f"Funcionando com o modelo {m}."
            return True, f"Respondeu com o modelo {m}."
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return False, "Chave invalida ou sem permissao. Confira no Google AI Studio."
            erros.append(f"{m}: HTTP {e.code}")
        except Exception as e:
            erros.append(f"{m}: {e}")
    return False, "Nenhum modelo respondeu. " + " | ".join(erros[:3])
