# -*- coding: utf-8 -*-
"""
MODO GENERICO - qualquer site, sem atalho pronto
-------------------------------------------------
Ciclo (ate MAX_PASSOS vezes):
  1. snapshot da aba ativa: lista numerada de links, botoes e campos visiveis
  2. o Gemini recebe a tarefa + a lista e devolve UM passo em JSON
  3. o Jarvis executa o passo (clicar, digitar, rolar, abrir_url, voltar)
  4. repete ate o Gemini dizer "concluir" ou "falhar"

Escolher um numero numa lista e uma tarefa facil ate para modelos pequenos, e a IA
nunca executa nada fora dos 5 passos abaixo.

Seguranca: clicar em algo com cara de enviar/comprar/pagar/apagar/confirmar exige um
"sim" do usuario (ver SENSIVEL). Campos de senha nunca sao preenchidos (a extensao
recusa) e a IA so ve rotulos, nunca valores digitados.
"""

import re
import time

from . import enviar
from .ponte import ErroNavegador

MAX_PASSOS = 6
PAUSA_ENTRE_PASSOS = 1.2

SENSIVEL = re.compile(
    r"\b(enviar|send|submit|comprar|buy|purchase|pagar|pay|finalizar|checkout|excluir|apagar|"
    r"delete|remover|remove|confirmar|confirm|publicar|publish|postar|post|transferir|transfer|"
    r"assinar|subscribe|aceitar|accept|sair|logout|sign out|encerrar|cancelar|cancel)\b",
    re.IGNORECASE,
)

ACOES_VALIDAS = ("clicar", "digitar", "rolar", "abrir_url", "voltar", "concluir", "falhar")

_PROMPT = """Voce controla uma aba do navegador para cumprir a tarefa do usuario. Fala portugues do Brasil.

TAREFA: {tarefa}

PASSOS JA FEITOS:
{historico}

PAGINA ATUAL: {titulo} ({url})
ELEMENTOS VISIVEIS (n | tipo | rotulo | regiao | destino):
{elementos}

Escolha o PROXIMO passo. Responda SOMENTE um JSON:
{{"acao": "clicar|digitar|rolar|abrir_url|voltar|concluir|falhar",
  "n": numero do elemento (clicar/digitar),
  "texto": "texto a digitar (digitar)", "enviar": true/false (apertar Enter depois de digitar),
  "nova_aba": true/false (clicar: abrir link em outra aba),
  "direcao": "baixo|cima|topo|fim" (rolar), "url": "https://..." (abrir_url),
  "fala": "frase curta para o senhor (obrigatoria em concluir e falhar)"}}

REGRAS:
1. Use apenas numeros que aparecem na lista. Nunca invente.
2. Um passo por resposta. Se a tarefa ja foi cumprida, use "concluir".
3. Se o que precisa nao esta visivel, use "rolar". Se nao for possivel, use "falhar".
4. Nunca digite senhas, dados de cartao ou documentos."""


def _linhas_elementos(itens):
    linhas = []
    for item in itens:
        destino = re.sub(r"^https?://(www\.)?", "", item.get("href", ""))[:60]
        linhas.append(" | ".join([str(item["n"]), item.get("tipo", ""), item.get("rotulo", ""),
                                  item.get("regiao", ""), destino]))
    return "\n".join(linhas) or "(nenhum elemento visivel)"


def montar_prompt(tarefa, snapshot, historico):
    return _PROMPT.format(
        tarefa=tarefa,
        historico="\n".join(f"- {h}" for h in historico) or "(nenhum)",
        titulo=snapshot.get("titulo", ""),
        url=snapshot.get("url", ""),
        elementos=_linhas_elementos(snapshot.get("itens", [])),
    )


def passo_sensivel(decisao, itens_por_n):
    """Devolve o rotulo que torna o passo sensivel, ou None."""
    if decisao.get("acao") != "clicar":
        return None
    rotulo = itens_por_n.get(decisao.get("n"), {}).get("rotulo", "")
    return rotulo if SENSIVEL.search(rotulo) else None


def _decidir_padrao(prompt):
    try:
        import cerebro
    except ImportError:
        return None
    return cerebro.responder_json(prompt) if cerebro.disponivel() else None


def executar(tarefa, confirmar=None, decidir=None, max_passos=MAX_PASSOS, pausa=PAUSA_ENTRE_PASSOS):
    """
    Cumpre `tarefa` na aba ativa. `confirmar(pergunta) -> bool` e chamado antes de passos
    sensiveis (sem ele, esses passos sao recusados). `decidir(prompt) -> dict` e o Gemini.
    """
    tarefa = (tarefa or "").strip()
    if not tarefa:
        raise ErroNavegador("O que o senhor quer que eu faca no navegador?")
    decidir = decidir or _decidir_padrao
    historico = []

    for _ in range(max_passos):
        snapshot = enviar("snapshot", limite=70) or {}
        itens_por_n = {i["n"]: i for i in snapshot.get("itens", [])}

        decisao = decidir(montar_prompt(tarefa, snapshot, historico))
        if not isinstance(decisao, dict):
            raise ErroNavegador("A IA nao conseguiu decidir o proximo passo, senhor.")

        acao = str(decisao.get("acao", "")).lower()
        decisao["acao"] = acao
        if acao not in ACOES_VALIDAS:
            raise ErroNavegador("A IA sugeriu um passo que eu nao conheco, senhor.")
        if acao == "concluir":
            return decisao.get("fala") or "Pronto, senhor."
        if acao == "falhar":
            return decisao.get("fala") or "Nao consegui concluir isso, senhor."

        try:
            decisao["n"] = int(decisao.get("n"))
        except (TypeError, ValueError):
            pass
        if acao in ("clicar", "digitar") and decisao.get("n") not in itens_por_n:
            historico.append(f"tentei o elemento {decisao.get('n')}, que nao existe")
            continue

        sensivel = passo_sensivel(decisao, itens_por_n)
        if sensivel:
            if confirmar is None or not confirmar(f"Senhor, vou clicar em \"{sensivel}\". Confirma?"):
                return "Parei antes desse passo, senhor."

        historico.append(_executar_passo(decisao, itens_por_n))
        time.sleep(pausa)

    return "Fiz o que pude em alguns passos, senhor, mas nao tenho certeza de que terminei."


def _executar_passo(decisao, itens_por_n):
    acao = decisao["acao"]
    n = decisao.get("n")
    rotulo = itens_por_n.get(n, {}).get("rotulo", "")
    if acao == "clicar":
        enviar("clicar", n=n, nova_aba=bool(decisao.get("nova_aba")))
        return f"cliquei em {n} ({rotulo})"
    if acao == "digitar":
        enviar("digitar", n=n, texto=str(decisao.get("texto", "")), enviar=bool(decisao.get("enviar")))
        return f"digitei no campo {n} ({rotulo})"
    if acao == "rolar":
        enviar("rolar", direcao=decisao.get("direcao") or "baixo")
        return f"rolei para {decisao.get('direcao') or 'baixo'}"
    if acao == "abrir_url":
        enviar("abrir_url", url=str(decisao.get("url", "")), nova_aba=False)
        return f"abri {decisao.get('url')}"
    enviar("navegar", acao="voltar")
    return "voltei uma pagina"


def resumir_pagina(decidir=None):
    """Le o texto principal da aba ativa e pede um resumo curto ao Gemini."""
    pagina = enviar("ler_texto", limite=6000) or {}
    texto = pagina.get("texto", "")
    if not texto:
        raise ErroNavegador("Nao encontrei texto nesta pagina, senhor.")
    decidir = decidir or _decidir_padrao
    resposta = decidir(
        "Resuma o texto abaixo em ate 3 frases curtas, em portugues do Brasil, para serem faladas "
        'em voz alta. Responda SOMENTE o JSON {"resumo": "..."}.\n\n'
        f"TITULO: {pagina.get('titulo', '')}\nTEXTO: {texto}")
    if not isinstance(resposta, dict) or not resposta.get("resumo"):
        raise ErroNavegador("A IA nao conseguiu resumir esta pagina, senhor.")
    return resposta["resumo"]
