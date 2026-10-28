# -*- coding: utf-8 -*-
"""
ACOES DO NAVEGADOR - registra no catalogo o que o pacote `navegador` sabe fazer.

Este arquivo e so a "cola": nomes e descricoes que a IA enxerga, chamando as funcoes de
navegador/atalhos.py e navegador/generico.py. A logica de verdade mora la.
Carregado por acoes.py (no final do arquivo). Guia: docs/NAVEGADOR.md
"""

import functools

import navegador
from navegador import atalhos, generico
from navegador.ponte import ErroNavegador

from acoes import CATALOGO, acao


def _seguro(funcao):
    """Erros esperados do navegador viram a frase falada, em vez de 'algo deu errado'."""
    @functools.wraps(funcao)
    def interna(ctx, **kw):
        try:
            return funcao(ctx, **kw)
        except ErroNavegador as erro:
            return str(erro)
    return interna


def _como_bool(valor):
    if isinstance(valor, str):
        return valor.strip().lower() in ("1", "true", "sim", "yes", "verdadeiro")
    return bool(valor)


def _tri(valor):
    """None = automatico (o Jarvis decide); caso contrario, o que o usuario pediu."""
    return None if valor is None else _como_bool(valor)


def _confirmador(ctx):
    """Usa a mesma pergunta de sim/nao das outras acoes arriscadas."""
    def confirmar(pergunta):
        if not getattr(ctx, "PERMITIR_ACOES_ARRISCADAS", True):
            return False
        ctx.falar(pergunta)
        return bool(ctx.perguntar_sim_nao(tentativas=2))
    return confirmar


# ============================================================================
# STATUS E ABAS
# ============================================================================
@acao("navegador_status", "Verifica se a extensao que controla o navegador esta conectada")
@_seguro
def navegador_status(ctx, **kw):
    if navegador.conectado():
        return "Extensao do navegador conectada, senhor."
    return ("A extensao do navegador nao esta conectada, senhor. "
            "O passo a passo esta em docs/NAVEGADOR.md.")


@acao("aba_listar", "Diz quais abas estao abertas no navegador")
@_seguro
def aba_listar(ctx, **kw):
    abas = navegador.enviar("abas_listar") or []
    if not abas:
        return "Nao ha abas abertas, senhor."
    nomes = [f"{a['indice'] + 1}, {atalhos._curto(a.get('titulo'), 40)}" for a in abas[:8]]
    extra = f" E mais {len(abas) - 8}." if len(abas) > 8 else ""
    return f"O senhor tem {len(abas)} abas: " + ". ".join(nomes) + "." + extra


@acao("aba_trocar", "Muda para outra aba do navegador",
      "alvo: numero da aba (1 = primeira) ou parte do titulo/site, ex: 'youtube'")
@_seguro
def aba_trocar(ctx, alvo="", **kw):
    alvo = str(alvo).strip()
    argumentos = {"indice": int(alvo)} if alvo.isdigit() else {"texto": alvo}
    aba = navegador.enviar("aba_trocar", **argumentos)
    return f"Aba {atalhos._curto(aba.get('titulo'), 50)}, senhor."


@acao("aba_fechar", "Fecha a aba atual do navegador")
@_seguro
def aba_fechar(ctx, **kw):
    navegador.enviar("aba_fechar")
    return "Aba fechada, senhor."


@acao("aba_duplicar", "Duplica a aba atual em outra aba")
@_seguro
def aba_duplicar(ctx, **kw):
    navegador.enviar("aba_duplicar")
    return "Aba duplicada, senhor."


@acao("pagina_navegar", "Volta, avanca ou recarrega a pagina atual do navegador",
      "acao: voltar|avancar|recarregar")
@_seguro
def pagina_navegar(ctx, acao="recarregar", **kw):
    navegador.enviar("navegar", acao=str(acao).lower())
    return "Feito, senhor."


@acao("pagina_rolar", "Rola a pagina atual do navegador", "direcao: baixo|cima|topo|fim")
@_seguro
def pagina_rolar(ctx, direcao="baixo", **kw):
    navegador.enviar("rolar", direcao=str(direcao).lower())
    return None


@acao("pagina_resumir", "Le e resume a pagina que esta aberta no navegador")
@_seguro
def pagina_resumir(ctx, **kw):
    return generico.resumir_pagina()


# ============================================================================
# YOUTUBE
# ============================================================================
@acao("youtube_pesquisar",
      "Pesquisa no YouTube e deixa os resultados prontos para abrir videos por posicao. "
      "Reaproveita a aba do YouTube ja aberta. Use antes de youtube_abrir_resultado/youtube_abrir_varios",
      "termo: o que pesquisar ; nova_aba: true so se o usuario pedir outra aba")
@_seguro
def youtube_pesquisar(ctx, termo="", nova_aba=None, **kw):
    return atalhos.youtube_pesquisar(termo, _tri(nova_aba))


@acao("resultado_abrir",
      "Abre o N-esimo resultado da ultima pesquisa (video do YouTube ou resultado do Google, "
      "o sistema descobre qual). Use para 'abre o segundo', 'abre o terceiro em outra aba'",
      "posicao: 1 = primeiro ; nova_aba: true se pedirem outra aba ; segundo_plano: true para nao trocar de aba")
@_seguro
def resultado_abrir(ctx, posicao=1, nova_aba=None, segundo_plano=False, **kw):
    return atalhos.abrir_resultado(posicao, _tri(nova_aba), _como_bool(segundo_plano))


@acao("youtube_abrir_resultado",
      "Abre o N-esimo video da pagina de resultados do YouTube (ou dos recomendados)",
      "posicao: 1 = primeiro ; nova_aba: true para abrir em outra aba ; "
      "segundo_plano: true para nao trocar de aba")
@_seguro
def youtube_abrir_resultado(ctx, posicao=1, nova_aba=False, segundo_plano=False, **kw):
    return atalhos.youtube_abrir_resultado(
        posicao, _como_bool(nova_aba), _como_bool(segundo_plano))


@acao("youtube_abrir_varios", "Abre os primeiros videos do YouTube, cada um em uma aba",
      "quantidade: 1 a 5")
@_seguro
def youtube_abrir_varios(ctx, quantidade=3, **kw):
    return atalhos.youtube_abrir_varios(quantidade)


@acao("youtube_player", "Controla o video aberto no YouTube",
      "controle: alternar|play|pausa|proximo|legendas|pular_anuncio|velocidade|pular|mudo|desmudo|volume ; "
      "valor: numero (velocidade 1.5, pular em segundos -10 ou 30, volume 0-100)")
@_seguro
def youtube_player(ctx, controle="alternar", valor=None, **kw):
    return atalhos.youtube_player(controle, valor)


# ============================================================================
# GOOGLE E GMAIL
# ============================================================================
@acao("google_pesquisar",
      "Pesquisa no Google no navegador conectado e deixa os resultados prontos para abrir por posicao",
      "termo: o que pesquisar ; nova_aba: true so se o usuario pedir outra aba")
@_seguro
def google_pesquisar(ctx, termo="", nova_aba=None, **kw):
    return atalhos.google_pesquisar(termo, _tri(nova_aba))


@acao("google_abrir_resultado", "Abre o N-esimo resultado de uma pesquisa do Google",
      "posicao: 1 = primeiro ; nova_aba: true/false (padrao true)")
@_seguro
def google_abrir_resultado(ctx, posicao=1, nova_aba=True, **kw):
    return atalhos.google_abrir_resultado(posicao, _como_bool(nova_aba))


@acao("gmail_nao_lidos", "Diz quantos e-mails nao lidos existem no Gmail")
@_seguro
def gmail_nao_lidos(ctx, **kw):
    return atalhos.gmail_nao_lidos()


@acao("gmail_listar", "Le os assuntos dos primeiros e-mails da caixa de entrada (somente leitura)",
      "quantidade: 1 a 10 (padrao 5)")
@_seguro
def gmail_listar(ctx, quantidade=5, **kw):
    return atalhos.gmail_listar(quantidade)


@acao("gmail_abrir", "Abre e le o N-esimo e-mail da caixa de entrada (somente leitura)",
      "posicao: 1 = o mais recente")
@_seguro
def gmail_abrir(ctx, posicao=1, **kw):
    return atalhos.gmail_abrir(posicao)


# ============================================================================
# MAPAS, RASTREIO, GITHUB (funcionam mesmo sem a extensao)
# ============================================================================
@acao("maps_buscar", "Procura um lugar no Google Maps", "termo: lugar ou tipo de lugar")
@_seguro
def maps_buscar(ctx, termo="", **kw):
    return atalhos.maps_buscar(termo)


@acao("maps_rota", "Mostra a rota ate um destino no Google Maps",
      "destino: endereco ou lugar ; origem: opcional")
@_seguro
def maps_rota(ctx, destino="", origem="", **kw):
    return atalhos.maps_rota(destino, origem)


@acao("rastrear_encomenda", "Procura o rastreio de uma encomenda pelo codigo", "codigo: codigo de rastreio")
@_seguro
def rastrear_encomenda(ctx, codigo="", **kw):
    return atalhos.rastrear_encomenda(codigo)


@acao("github_abrir", "Abre uma pagina do GitHub",
      "destino: notificacoes|pull requests|issues|inicio|dono/repositorio")
@_seguro
def github_abrir(ctx, destino="inicio", **kw):
    return atalhos.github_abrir(destino)


# ============================================================================
# ABAS EM LOTE, SOM POR ABA
# ============================================================================
@acao("abas_som", "Diz quais abas do navegador estao tocando som agora")
@_seguro
def abas_som(ctx, **kw):
    return atalhos.abas_com_som()


@acao("aba_silenciar", "Silencia (ou religa o som de) abas do navegador, sem mexer no volume do computador",
      "alvo: parte do titulo/site, ex: 'youtube' (vazio = tudo que esta tocando) ; "
      "silenciar: true para silenciar, false para religar")
@_seguro
def aba_silenciar(ctx, alvo="", silenciar=True, **kw):
    return atalhos.aba_silenciar(alvo, _como_bool(silenciar))


@acao("abas_fechar", "Fecha varias abas do navegador de uma vez, por site/titulo ou as duplicadas. "
      "Mais de 3 abas pedem confirmacao; da para reabrir",
      "texto: parte do titulo/site (ex: 'youtube') ; duplicadas: true para fechar so as repetidas")
@_seguro
def abas_fechar(ctx, texto="", duplicadas=False, **kw):
    return atalhos.fechar_abas(texto, _como_bool(duplicadas), confirmar=_confirmador(ctx))


@acao("aba_reabrir", "Reabre a ultima aba que foi fechada no navegador")
@_seguro
def aba_reabrir(ctx, **kw):
    return atalhos.reabrir_aba()


@acao("aba_fixar", "Fixa (ou desafixa) a aba atual do navegador", "fixar: true para fixar, false para desafixar")
@_seguro
def aba_fixar(ctx, fixar=True, **kw):
    return atalhos.fixar_aba(_como_bool(fixar))


@acao("abas_agrupar", "Agrupa abas do navegador num grupo com nome",
      "texto: parte do titulo/site das abas ; titulo: nome do grupo (opcional)")
@_seguro
def abas_agrupar(ctx, texto="", titulo="", **kw):
    return atalhos.agrupar_abas(texto, titulo)


# ============================================================================
# MUSICA NO NAVEGADOR, HISTORICO, FAVORITOS, DIAGNOSTICO
# ============================================================================
@acao("musica_controle", "Controla o Spotify Web ou YouTube Music abertos no navegador, mesmo em outra aba",
      "controle: alternar|proximo|anterior ; servico: spotify|ytmusic (opcional)")
@_seguro
def musica_controle(ctx, controle="alternar", servico="", **kw):
    return atalhos.musica_controle(controle, servico)


@acao("musica_tocando", "Diz qual musica esta tocando no Spotify Web ou YouTube Music",
      "servico: spotify|ytmusic (opcional)")
@_seguro
def musica_tocando(ctx, servico="", **kw):
    return atalhos.musica_tocando(servico)


@acao("historico_buscar",
      "Procura no historico do navegador (ex: 'aquele site sobre X que vi ontem') e deixa os "
      "resultados prontos para resultado_abrir",
      "termo: palavras do titulo/site ; dias: quantos dias para tras (padrao 30)")
@_seguro
def historico_buscar(ctx, termo="", dias=30, **kw):
    return atalhos.historico_buscar(termo, dias)


@acao("favoritos_buscar", "Procura nos favoritos do navegador e deixa os resultados prontos para resultado_abrir",
      "termo: palavras do titulo/site")
@_seguro
def favoritos_buscar(ctx, termo="", **kw):
    return atalhos.favoritos_buscar(termo)


@acao("favorito_salvar", "Salva a pagina atual do navegador nos favoritos")
@_seguro
def favorito_salvar(ctx, **kw):
    return atalhos.favorito_salvar()


@acao("navegador_diagnostico",
      "Verifica se a extensao esta conectada e se os atalhos do site da aba atual ainda encontram o que precisam")
@_seguro
def navegador_diagnostico(ctx, **kw):
    return atalhos.diagnostico()


# ============================================================================
# MODO GENERICO
# ============================================================================
@acao("navegador_tarefa",
      "Cumpre uma tarefa livre na pagina aberta do navegador (clicar, digitar, rolar) em QUALQUER site. "
      "Use quando nao houver uma acao especifica para o site. Passos sensiveis pedem confirmacao",
      "instrucao: o que fazer, completo, ex: 'abrir a aba de precos e clicar no plano mensal'")
@_seguro
def navegador_tarefa(ctx, instrucao="", **kw):
    return generico.executar(instrucao, confirmar=_confirmador(ctx))


# Tudo que este arquivo registrou entra no grupo "navegador": a IA so recebe essas acoes
# quando a frase fala de navegador (ver jarvis._grupos_ia).
for _info in CATALOGO.values():
    if getattr(_info["funcao"], "__module__", "") == __name__:
        _info["grupo"] = "navegador"
