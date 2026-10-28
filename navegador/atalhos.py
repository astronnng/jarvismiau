# -*- coding: utf-8 -*-
"""
ATALHOS - fluxos prontos e exatos por site
-------------------------------------------
Aqui mora todo o conhecimento de site (seletores, URLs, filtros). A extensao so
oferece operacoes genericas (consultar, clicar_seletor, video, abrir_url...).

Para adicionar um site: escreva uma funcao aqui usando `navegador.enviar(...)`,
registre uma acao em acoes_navegador.py e documente em docs/NAVEGADOR.md.

Cada funcao devolve a frase que o Jarvis fala. Erros viram ErroNavegador.

Resultados de busca ficam em memoria (`_ultimos`): assim "abre o primeiro" e depois
"abre o segundo em outra aba" funcionam mesmo que o primeiro tenha saido da pagina
de resultados.
"""

import re
import time
import urllib.parse
import webbrowser

from . import enviar, conectado
from .ponte import ErroNavegador

VALIDADE_RESULTADOS = 15 * 60       # segundos que uma lista de resultados continua valendo
_ultimos = {}                       # site -> {"quando": ts, "itens": [{"titulo", "url"}]}


# ============================================================================
# Auxiliares
# ============================================================================
def _consulta(**args):
    return (enviar("consultar", **args) or {}).get("itens", [])


def _aguardar_itens(minimo=1, tempo=8, **args):
    """Paginas modernas montam a lista depois de carregar: tenta ate aparecer."""
    fim = time.monotonic() + tempo
    while True:
        itens = _consulta(**args)
        if len(itens) >= minimo or time.monotonic() >= fim:
            return itens
        time.sleep(0.5)


def _aba_ativa():
    for aba in enviar("abas_listar") or []:
        if aba.get("ativa"):
            return aba
    raise ErroNavegador("Nao encontrei uma aba ativa, senhor.")


def _host(url):
    return (urllib.parse.urlparse(url or "").hostname or "").lower()


def _curto(texto, limite=70):
    texto = re.sub(r"\s+", " ", texto or "").strip()
    return texto if len(texto) <= limite else texto[:limite - 1].rstrip() + "..."


def abrir_url(url, nova_aba=True, segundo_plano=False):
    """Abre no navegador da extensao; sem a extensao, cai no navegador padrao do Windows."""
    if conectado():
        enviar("abrir_url", url=url, nova_aba=nova_aba, segundo_plano=segundo_plano)
    else:
        webbrowser.open(url)


def _aba_do_site(sufixo_host):
    """Aba aberta do site (prefere a ativa), ou None."""
    achadas = [a for a in (enviar("abas_listar") or [])
               if _host(a.get("url")).endswith(sufixo_host)]
    return next((a for a in achadas if a.get("ativa")), achadas[0] if achadas else None)


def _abrir_no_site(sufixo_host, url, nova_aba=None):
    """
    nova_aba=None (automatico): reaproveita a aba do site se ja houver uma, senao abre nova.
    True/False: o usuario pediu explicitamente.
    """
    if not conectado():
        webbrowser.open(url)
        return
    if nova_aba is None:
        existente = _aba_do_site(sufixo_host)
        if existente:
            enviar("abrir_url", url=url, nova_aba=False, aba=existente["id"])
            return
        nova_aba = True
    enviar("abrir_url", url=url, nova_aba=nova_aba)


def _guardar(site, itens):
    _ultimos[site] = {"quando": time.monotonic(), "itens": itens}


def _recentes(site):
    registro = _ultimos.get(site)
    if registro and time.monotonic() - registro["quando"] < VALIDADE_RESULTADOS:
        return registro["itens"]
    return None


def _escolher(itens, posicao, o_que):
    if not itens:
        raise ErroNavegador(
            f"Nao encontrei {o_que} nesta pagina, senhor. Se o site mudou, peca o diagnostico do navegador.")
    posicao = int(posicao)
    if posicao == -1:                   # "o ultimo"
        return itens[-1]
    if not 1 <= posicao <= len(itens):
        raise ErroNavegador(f"So encontrei {len(itens)} {o_que}, senhor.")
    return itens[posicao - 1]


# ============================================================================
# YOUTUBE
# ============================================================================
_YT_SELETOR = 'a[href*="/watch?v="]'
# anuncios, Shorts, topo da pagina e o proprio player ficam de fora
_YT_EXCLUIR = ("ytd-ad-slot-renderer, ytd-promoted-sparkles-web-renderer, ytd-display-ad-renderer, "
               "ytd-in-feed-ad-layout-renderer, ytd-reel-shelf-renderer, ytd-masthead, "
               "ytd-miniplayer, #player")
_YT_ID = re.compile(r"[?&]v=([\w-]{6,})")

# botoes do player (classes estaveis do YouTube) -> controle
_YT_BOTOES = {
    "proximo": ".ytp-next-button",
    "legendas": ".ytp-subtitles-button",
    "pular_anuncio": ".ytp-skip-ad-button, .ytp-ad-skip-button, .ytp-ad-skip-button-modern",
}


def youtube_pesquisar(termo, nova_aba=None):
    termo = (termo or "").strip()
    if not termo:
        raise ErroNavegador("O que o senhor quer pesquisar no YouTube?")
    _abrir_no_site("youtube.com",
                   "https://www.youtube.com/results?search_query=" + urllib.parse.quote(termo),
                   nova_aba)
    _ultimos.pop("youtube", None)       # busca nova invalida a lista anterior
    return f"Pesquisando {termo} no YouTube, senhor."


# A miniatura tambem e um link do video, mas o texto dela e a duracao ("11:53 Em reproducao").
_YT_RUIDO = re.compile(
    r"^\s*(\d{1,2}:)?\d{1,2}:\d{2}\b|^\s*(em reprodu|assistir mais tarde|adicionar|now playing|watch later)",
    re.IGNORECASE)


def _videos_da_pagina():
    brutos = _consulta(seletor=_YT_SELETOR, excluir=_YT_EXCLUIR, filtro_href=r"/watch\?v=", limite=80)
    ordem, textos = [], {}
    for item in brutos:
        achado = _YT_ID.search(item.get("href", ""))
        if not achado:
            continue
        video_id = achado.group(1)
        if video_id not in textos:
            ordem.append(video_id)
            textos[video_id] = []
        textos[video_id].append(item.get("texto", ""))

    videos = []
    for video_id in ordem:
        candidatos = [t for t in textos[video_id] if t and not _YT_RUIDO.match(t)]
        if candidatos:      # sem titulo = so a miniatura carregou ate agora
            videos.append({"titulo": max(candidatos, key=len),
                           "url": "https://www.youtube.com/watch?v=" + video_id})
    return videos


def _youtube_videos(tempo=8):
    """Videos da pagina atual (resultados, inicio ou recomendados), sem repeticao."""
    fim = time.monotonic() + tempo
    while True:
        videos = _videos_da_pagina()
        if videos or time.monotonic() >= fim:
            return videos
        time.sleep(0.5)


def youtube_resultados():
    """Lista de videos: da pagina aberta se for do YouTube, senao a ultima busca."""
    aba = _aba_ativa()
    no_youtube = "youtube.com" in _host(aba.get("url"))
    pagina_de_busca = no_youtube and "/results" in (aba.get("url") or "")
    if pagina_de_busca or (no_youtube and _recentes("youtube") is None):
        videos = _youtube_videos()
        if videos:
            _guardar("youtube", videos)
        return videos
    memoria = _recentes("youtube")
    if memoria is not None:
        return memoria
    raise ErroNavegador("Peca primeiro para pesquisar no YouTube, senhor.")


def youtube_abrir_resultado(posicao=1, nova_aba=False, segundo_plano=False):
    video = _escolher(youtube_resultados(), posicao, "videos")
    abrir_url(video["url"], nova_aba=nova_aba, segundo_plano=segundo_plano)
    return f"Abrindo {_curto(video['titulo'])}, senhor."


def youtube_abrir_varios(quantidade=3):
    """Abre os N primeiros em abas separadas; a primeira fica em foco."""
    quantidade = max(1, min(int(quantidade), 5))
    videos = youtube_resultados()[:quantidade]
    if not videos:
        raise ErroNavegador("Nao encontrei videos nesta pagina, senhor.")
    for indice, video in enumerate(videos):
        abrir_url(video["url"], nova_aba=True, segundo_plano=indice > 0)
    return f"Abri {len(videos)} videos em abas separadas, senhor."


def abrir_resultado(posicao=1, nova_aba=None, segundo_plano=False):
    """
    "Abre o segundo": decide sozinho se e video do YouTube ou resultado do Google, olhando a
    aba atual e, se ela nao for de nenhum dos dois, a lista pesquisada mais recentemente.
    nova_aba=None usa o padrao de cada site (YouTube: mesma aba; Google: aba nova).
    """
    listas = [(r["quando"], s) for s, r in _ultimos.items()
              if s in ("historico", "favoritos") and time.monotonic() - r["quando"] < 120]
    if listas:      # acabou de buscar no historico/favoritos: "abre o segundo" e dessa lista
        return abrir_da_lista(max(listas)[1], posicao, True if nova_aba is None else nova_aba,
                              segundo_plano)
    host = _host(_aba_ativa().get("url"))
    if "youtube.com" in host:
        site = "youtube"
    elif "google." in host:
        site = "google"
    else:
        recentes = [(r["quando"], s) for s, r in _ultimos.items() if _recentes(s) is not None]
        if not recentes:
            raise ErroNavegador("Peca primeiro uma pesquisa, senhor.")
        site = max(recentes)[1]
    if site == "youtube":
        return youtube_abrir_resultado(posicao, bool(nova_aba), segundo_plano)
    return google_abrir_resultado(posicao, True if nova_aba is None else nova_aba, segundo_plano)


def _aba_youtube():
    """Aba do YouTube a controlar: a ativa, senao a que toca som, senao a primeira."""
    abas = [a for a in (enviar("abas_listar", todas_janelas=True) or [])
            if _host(a.get("url")).endswith("youtube.com") and "music." not in _host(a.get("url"))]
    if not abas:
        raise ErroNavegador("Nao ha nenhuma aba do YouTube aberta, senhor.")
    abas.sort(key=lambda a: (not a.get("ativa"), not a.get("audivel")))
    return abas[0]


def youtube_player(controle, valor=None):
    """controle: alternar|play|pausa|proximo|legendas|pular_anuncio|velocidade|pular|mudo|desmudo|volume"""
    controle = (controle or "alternar").lower()
    alvo = {"aba": _aba_youtube()["id"]}      # funciona mesmo com o video em segundo plano
    if controle in _YT_BOTOES:
        enviar("clicar_seletor", seletor=_YT_BOTOES[controle], exigir_texto=False, **alvo)
        return {"proximo": "Proximo video, senhor.", "legendas": "Legendas alternadas, senhor.",
                "pular_anuncio": "Anuncio pulado, senhor."}[controle]
    if controle in ("alternar", "play", "pausa", "mudo", "desmudo"):
        enviar("video", acao=controle, **alvo)
        return {"alternar": "Feito, senhor.", "play": "Tocando, senhor.", "pausa": "Pausado, senhor.",
                "mudo": "Video sem som, senhor.", "desmudo": "Som do video ligado, senhor."}[controle]
    if controle in ("velocidade", "pular", "volume"):
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            raise ErroNavegador(f"Faltou o valor para {controle}, senhor.")
        enviar("video", acao=controle, valor=numero, **alvo)
        return {"velocidade": f"Velocidade {numero:g}x, senhor.",
                "pular": "Pulei, senhor.", "volume": f"Volume do video em {numero:g}%, senhor."}[controle]
    raise ErroNavegador(f"Nao conheco o controle {controle} do player, senhor.")


# ============================================================================
# GOOGLE
# ============================================================================
_GOOGLE_SELETOR = "#search a:has(h3)"
_GOOGLE_EXCLUIR = "#tads, #tadsb, #tvcap, [data-text-ad], [data-ad-slot]"
_GOOGLE_FILTRO = r"^https?://(?!(www\.)?google\.)"      # fora os links internos do Google


def google_pesquisar(termo, nova_aba=None):
    termo = (termo or "").strip()
    if not termo:
        raise ErroNavegador("O que o senhor quer pesquisar, senhor?")
    _abrir_no_site("google.com", "https://www.google.com/search?q=" + urllib.parse.quote(termo),
                   nova_aba)
    _ultimos.pop("google", None)
    return f"Pesquisando {termo}, senhor."


def google_resultados():
    aba = _aba_ativa()
    url = aba.get("url") or ""
    na_busca = "google." in _host(url) and "/search" in url
    if na_busca:
        brutos = _aguardar_itens(
            seletor=_GOOGLE_SELETOR, excluir=_GOOGLE_EXCLUIR, filtro_href=_GOOGLE_FILTRO,
            rotulo_seletor="h3", limite=20)
        itens = [{"titulo": i["texto"], "url": i["href"]} for i in brutos]
        if itens:
            _guardar("google", itens)
        return itens
    memoria = _recentes("google")
    if memoria is not None:
        return memoria
    raise ErroNavegador("Peca primeiro uma pesquisa no Google, senhor.")


def google_abrir_resultado(posicao=1, nova_aba=True, segundo_plano=False):
    item = _escolher(google_resultados(), posicao, "resultados")
    abrir_url(item["url"], nova_aba=nova_aba, segundo_plano=segundo_plano)
    return f"Abrindo {_curto(item['titulo'])}, senhor."


# ============================================================================
# GMAIL (somente leitura: nao envia, nao apaga, nao arquiva)
# ============================================================================
_GMAIL_CAIXA = "https://mail.google.com/mail/u/0/#inbox"
_GMAIL_LINHA = "tr.zA"
_GMAIL_CONTAGEM = re.compile(r"\((\d+)\)")


def _aba_gmail(abrir=True):
    for aba in enviar("abas_listar") or []:
        if "mail.google.com" in _host(aba.get("url")):
            return aba
    if not abrir:
        return None
    enviar("abrir_url", url=_GMAIL_CAIXA, nova_aba=True)
    fim = time.monotonic() + 10
    while time.monotonic() < fim:
        for aba in enviar("abas_listar") or []:
            if "mail.google.com" in _host(aba.get("url")) and "Gmail" in (aba.get("titulo") or ""):
                return aba
        time.sleep(0.5)
    raise ErroNavegador("O Gmail nao terminou de carregar, senhor.")


def gmail_nao_lidos():
    # O titulo da aba traz a contagem: "Caixa de entrada (12) - voce@gmail.com - Gmail".
    aba = _aba_gmail()
    achado = _GMAIL_CONTAGEM.search(aba.get("titulo") or "")
    total = int(achado.group(1)) if achado else 0
    if total == 0:
        return "Nenhum e-mail nao lido, senhor."
    return f"O senhor tem {total} e-mail{'s' if total != 1 else ''} nao lido{'s' if total != 1 else ''}."


def _gmail_na_caixa():
    aba = _aba_gmail()
    enviar("aba_trocar", id=aba["id"])
    if "#inbox" not in (aba.get("url") or ""):
        enviar("abrir_url", url=_GMAIL_CAIXA, nova_aba=False)
    return _aguardar_itens(seletor=_GMAIL_LINHA, limite=20, max_texto=160)


def gmail_listar(quantidade=5):
    quantidade = max(1, min(int(quantidade), 10))
    linhas = _gmail_na_caixa()[:quantidade]
    if not linhas:
        return "Nao encontrei e-mails na caixa de entrada, senhor."
    partes = []
    for numero, linha in enumerate(linhas, 1):
        marca = "nao lido: " if " zE " in f" {linha.get('classes', '')} " else ""
        partes.append(f"{numero}, {marca}{_curto(linha['texto'], 90)}")
    return "Seus e-mails: " + ". ".join(partes) + "."


def gmail_abrir(posicao=1):
    linhas = _gmail_na_caixa()
    _escolher(linhas, posicao, "e-mails")
    indice = len(linhas) - 1 if int(posicao) == -1 else int(posicao) - 1
    enviar("clicar_seletor", seletor=_GMAIL_LINHA, indice=indice)
    corpo = _aguardar_itens(seletor=".a3s", limite=1, max_texto=700, tempo=6)
    assunto = _consulta(seletor="h2.hP", limite=1)
    titulo = assunto[0]["texto"] if assunto else "sem assunto"
    texto = corpo[0]["texto"] if corpo else "nao consegui ler o conteudo"
    return f"{_curto(titulo, 100)}. {texto}"


# ============================================================================
# ATALHOS POR URL (funcionam ate sem a extensao, no navegador padrao)
# ============================================================================
def maps_buscar(termo):
    termo = (termo or "").strip()
    if not termo:
        raise ErroNavegador("O que o senhor quer procurar no mapa?")
    abrir_url("https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(termo))
    return f"Procurando {termo} no mapa, senhor."


def maps_rota(destino, origem=""):
    destino = (destino or "").strip()
    if not destino:
        raise ErroNavegador("Para onde o senhor quer ir?")
    url = "https://www.google.com/maps/dir/?api=1&destination=" + urllib.parse.quote(destino)
    if (origem or "").strip():
        url += "&origin=" + urllib.parse.quote(origem.strip())
    abrir_url(url)
    return f"Tracando a rota para {destino}, senhor."


def rastrear_encomenda(codigo):
    codigo = re.sub(r"\s+", "", codigo or "").upper()
    if not codigo:
        raise ErroNavegador("Qual e o codigo de rastreio, senhor?")
    abrir_url("https://www.google.com/search?q=" + urllib.parse.quote("rastrear " + codigo))
    return f"Procurando o rastreio {codigo}, senhor."


_GITHUB = {
    "notificacoes": "https://github.com/notifications",
    "pull requests": "https://github.com/pulls",
    "issues": "https://github.com/issues",
    "inicio": "https://github.com/",
}


def github_abrir(destino="inicio"):
    """destino: notificacoes | pull requests | issues | inicio | dono/repositorio"""
    chave = (destino or "inicio").strip().lower()
    if chave in _GITHUB:
        url = _GITHUB[chave]
    elif re.fullmatch(r"[\w.-]+/[\w.-]+", chave):
        url = "https://github.com/" + destino.strip()
    else:
        raise ErroNavegador("Nao entendi o destino no GitHub, senhor.")
    abrir_url(url)
    return f"Abrindo {destino} no GitHub, senhor."


def gmail_abrir_caixa():
    abrir_url(_GMAIL_CAIXA)
    return "Abrindo o Gmail, senhor."


# ============================================================================
# ABAS EM LOTE E SOM POR ABA
# ============================================================================
LIMITE_SEM_CONFIRMAR = 3        # fechar mais abas do que isso exige um "sim"


def _nomes(abas, limite=3):
    nomes = ", ".join(_curto(a.get("titulo"), 30) for a in abas[:limite])
    extra = len(abas) - limite
    return nomes + (f" e mais {extra}" if extra > 0 else "")


def abas_com_som():
    tocando = enviar("abas_buscar", audivel=True) or []
    if not tocando:
        return "Nenhuma aba esta tocando som, senhor."
    return "Tocando som: " + _nomes(tocando) + "."


def aba_silenciar(alvo="", silenciar=True):
    """
    alvo vazio: silencia tudo que esta tocando (ou, ao religar, tudo que esta mudo);
    com texto: abas cujo titulo ou endereco contem o texto.
    """
    alvo = (alvo or "").strip()
    if alvo:
        abas = enviar("abas_buscar", texto=alvo) or []
    elif silenciar:
        abas = enviar("abas_buscar", audivel=True) or []
    else:
        abas = [a for a in (enviar("abas_buscar") or []) if a.get("mudo")]
    if not abas:
        raise ErroNavegador("Nao encontrei abas para isso, senhor.")
    for aba in abas:
        enviar("aba_mudo", aba=aba["id"], mudo=bool(silenciar))
    return ("Silenciei " if silenciar else "Liguei o som de ") + _nomes(abas) + ", senhor."


def fechar_abas(texto="", duplicadas=False, confirmar=None):
    """Fecha abas por texto ou as repetidas. Passa de LIMITE_SEM_CONFIRMAR: pede "sim"."""
    if not (texto or "").strip() and not duplicadas:
        raise ErroNavegador("Quais abas o senhor quer fechar?")
    abas = enviar("abas_buscar", texto=(texto or "").strip() or None, duplicadas=bool(duplicadas)) or []
    abas = [a for a in abas if not a.get("fixada")]          # abas fixadas ficam
    if not abas:
        return "Nao encontrei abas para fechar, senhor."
    if len(abas) > LIMITE_SEM_CONFIRMAR:
        pergunta = f"Vou fechar {len(abas)} abas: {_nomes(abas)}. Confirma?"
        if confirmar is None or not confirmar(pergunta):
            return "Nao fechei nada, senhor."
    enviar("aba_fechar", ids=[a["id"] for a in abas])
    plural = "s" if len(abas) != 1 else ""
    return f"Fechei {len(abas)} aba{plural}, senhor. Se quiser, eu reabro."


def reabrir_aba():
    enviar("aba_reabrir")
    return "Reabri a ultima aba fechada, senhor."


def fixar_aba(fixar=True):
    enviar("aba_fixar", fixar=bool(fixar))
    return "Aba fixada, senhor." if fixar else "Aba desafixada, senhor."


def agrupar_abas(texto, titulo=""):
    texto = (texto or "").strip()
    if not texto:
        raise ErroNavegador("Quais abas o senhor quer agrupar?")
    abas = enviar("abas_buscar", texto=texto) or []
    if not abas:
        raise ErroNavegador(f"Nao encontrei abas com {texto}, senhor.")
    janela = abas[0].get("janela")                           # um grupo vive numa janela so
    abas = [a for a in abas if a.get("janela") == janela]
    nome = (titulo or texto).strip()
    enviar("abas_agrupar", ids=[a["id"] for a in abas], titulo=nome)
    return f"Agrupei {len(abas)} abas em {nome}, senhor."


# ============================================================================
# MUSICA NO NAVEGADOR (Spotify Web, YouTube Music): age na aba certa, mesmo em segundo plano
# ============================================================================
_PLAYERS = {
    "spotify": {
        "nome": "Spotify", "host": "open.spotify.com",
        "botoes": {"alternar": '[data-testid="control-button-playpause"]',
                   "proximo": '[data-testid="control-button-skip-forward"]',
                   "anterior": '[data-testid="control-button-skip-back"]'},
        "titulo": '[data-testid="context-item-info-title"]',
        "artista": '[data-testid="context-item-info-artist"]',
    },
    "ytmusic": {
        "nome": "YouTube Music", "host": "music.youtube.com",
        "botoes": {"alternar": "#play-pause-button", "proximo": ".next-button",
                   "anterior": ".previous-button"},
        "titulo": "ytmusic-player-bar .title",
        "artista": "ytmusic-player-bar .byline",
    },
}


def _aba_player(servico=""):
    """(chave, aba) do player aberto; prefere o que esta tocando som."""
    achados = []
    for aba in enviar("abas_listar", todas_janelas=True) or []:
        for chave, player in _PLAYERS.items():
            if player["host"] in _host(aba.get("url")) and servico in ("", chave):
                achados.append((chave, aba))
    if not achados:
        raise ErroNavegador("Nao achei o Spotify nem o YouTube Music abertos no navegador, senhor.")
    achados.sort(key=lambda par: not par[1].get("audivel"))
    return achados[0]


def musica_controle(controle="alternar", servico=""):
    """controle: alternar | proximo | anterior"""
    if controle not in ("alternar", "proximo", "anterior"):
        raise ErroNavegador(f"Nao conheco o controle {controle} de musica, senhor.")
    chave, aba = _aba_player((servico or "").lower())
    seletor = _PLAYERS[chave]["botoes"][controle]
    enviar("clicar_seletor", seletor=seletor, exigir_texto=False, aba=aba["id"])
    return {"alternar": "Feito, senhor.", "proximo": "Proxima, senhor.",
            "anterior": "Voltando, senhor."}[controle]


def musica_tocando(servico=""):
    chave, aba = _aba_player((servico or "").lower())
    player = _PLAYERS[chave]
    titulo = _consulta(seletor=player["titulo"], limite=1, aba=aba["id"])
    if not titulo:
        return f"Nao consegui ler o que esta tocando no {player['nome']}, senhor."
    artista = _consulta(seletor=player["artista"], limite=1, aba=aba["id"])
    de = f", de {artista[0]['texto']}" if artista else ""
    return f"Tocando {titulo[0]['texto']}{de}, no {player['nome']}."


# ============================================================================
# HISTORICO E FAVORITOS (leitura local; nada sai do computador)
# ============================================================================
def _listar_e_guardar(site, itens, termo, onde):
    if not itens:
        return f"Nao achei {termo} {onde}, senhor."
    _guardar(site, [{"titulo": i["titulo"], "url": i["url"]} for i in itens])
    lista = ". ".join(f"{n}, {_curto(i['titulo'], 50)}" for n, i in enumerate(itens[:3], 1))
    return f"Achei: {lista}."


def historico_buscar(termo, dias=30):
    termo = (termo or "").strip()
    if not termo:
        raise ErroNavegador("O que o senhor quer procurar no historico?")
    itens = enviar("historico_buscar", texto=termo, dias=int(dias), limite=10) or []
    return _listar_e_guardar("historico", itens, termo, f"no historico dos ultimos {int(dias)} dias")


def favoritos_buscar(termo):
    termo = (termo or "").strip()
    if not termo:
        raise ErroNavegador("O que o senhor quer procurar nos favoritos?")
    itens = enviar("favoritos_buscar", texto=termo, limite=10) or []
    return _listar_e_guardar("favoritos", itens, termo, "nos favoritos")


def abrir_da_lista(site, posicao=1, nova_aba=True, segundo_plano=False):
    """Abre o N-esimo item da ultima busca de historico ou favoritos."""
    itens = _recentes(site)
    if itens is None:
        raise ErroNavegador("Peca primeiro uma busca no historico ou nos favoritos, senhor.")
    item = _escolher(itens, posicao, "itens")
    abrir_url(item["url"], nova_aba=nova_aba, segundo_plano=segundo_plano)
    return f"Abrindo {_curto(item['titulo'])}, senhor."


def favorito_salvar():
    salvo = enviar("favorito_criar") or {}
    return f"Salvei {_curto(salvo.get('titulo'), 50)} nos favoritos, senhor."


# ============================================================================
# DIAGNOSTICO: diz se os seletores de cada site ainda encontram o que precisam
# ============================================================================
def diagnostico():
    versao = (enviar("ping") or {}).get("versao", "?")
    aba = _aba_ativa()
    url = aba.get("url") or ""
    host = _host(url)
    partes = [f"Extensao {versao} conectada.", f"Aba ativa: {host or 'sem endereco'}."]

    if host.endswith("music.youtube.com") or host.endswith("open.spotify.com"):
        player = _PLAYERS["ytmusic" if "music.youtube" in host else "spotify"]
        faltam = [nome for nome, seletor in player["botoes"].items()
                  if not _consulta(seletor=seletor, exigir_texto=False, limite=1)]
        partes.append("Botoes do player ok." if not faltam
                      else "Nao achei os botoes: " + ", ".join(faltam) + ". O site pode ter mudado.")
    elif host.endswith("youtube.com"):
        n = len(_videos_da_pagina())
        partes.append(f"Videos encontrados: {n}." + ("" if n else " O seletor do YouTube pode ter mudado."))
    elif "google." in host and "/search" in url:
        n = len(_consulta(seletor=_GOOGLE_SELETOR, excluir=_GOOGLE_EXCLUIR,
                          filtro_href=_GOOGLE_FILTRO, rotulo_seletor="h3", limite=20))
        partes.append(f"Resultados encontrados: {n}." + ("" if n else " O seletor do Google pode ter mudado."))
    elif host.endswith("mail.google.com"):
        n = len(_consulta(seletor=_GMAIL_LINHA, limite=20, max_texto=40))
        partes.append(f"E-mails encontrados na lista: {n}."
                      + ("" if n else " Abra a caixa de entrada ou o seletor mudou."))
    else:
        partes.append("Sem atalho especifico para este site; o modo generico funciona em qualquer pagina.")
    return " ".join(partes)
