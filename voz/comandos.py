# -*- coding: utf-8 -*-
"""
/voz - configuracao de voz dentro do Jarvis

  /voz                                   estado: motor ativo, mistura, idioma, velocidade
  /voz usar kokoro | padrao              troca o motor ativo (grava em voz.json)
  /voz padrao [PERFIL]                   perfis da cadeia atual (Edge/Windows)
  /voz testar [frase]                    fala com o motor ativo
  /voz kokoro vozes [filtro]             vozes do modelo instalado
  /voz kokoro mistura bm_daniel=0.5 am_michael=0.4
  /voz kokoro idioma pt-br | velocidade 1.0
  /voz kokoro preset lista | salvar N | usar N | apagar N
  /voz kokoro pronuncia lista | nao=não | remover nao
  /voz kokoro preaquecer on | off
  /voz kokoro testar [frase] | instalar | status

`executar` devolve o texto a mostrar (ou None se ja falou/mostrou). Nada aqui toca em audio
diretamente: tudo que depende do jarvis.py chega pelo `ContextoVoz`.
"""

import time

from . import config, instalar
from .kokoro_motor import ErroKokoro

FRASE_TESTE = "Todos os sistemas estão online, senhor."
SUBCOMANDOS = [("usar", "trocar o motor ativo (kokoro ou padrao)"),
               ("padrao", "escolher o perfil Edge/Windows"),
               ("kokoro", "configurar o Kokoro"),
               ("testar", "falar uma frase com a voz ativa"),
               ("ajuda", "mostrar os comandos de voz")]
SUBCOMANDOS_KOKORO = [("status", "estado do Kokoro"),
                      ("vozes", "listar as vozes do modelo"),
                      ("mistura", "vozes e proporções, ex: bm_daniel=0.5 am_michael=0.4"),
                      ("idioma", "idioma dos fonemas (pt-br, en-us...)"),
                      ("velocidade", "0.5 a 2.0"),
                      ("preset", "salvar e usar combinações com nome"),
                      ("pronuncia", "corrigir como palavras são lidas"),
                      ("preaquecer", "gerar frases comuns em segundo plano"),
                      ("testar", "ouvir sem ativar o Kokoro"),
                      ("instalar", "baixar os modelos")]
IDIOMAS = [("pt-br", "português do Brasil"), ("en-us", "inglês americano"), ("en-gb", "inglês britânico"),
           ("es", "espanhol"), ("fr-fr", "francês"), ("it", "italiano"), ("ja", "japonês"),
           ("cmn", "mandarim"), ("hi", "hindi")]


class ContextoVoz:
    """Ponte para o que vive no jarvis.py. Tudo tem um valor padrao inofensivo (bom para testes)."""

    def __init__(self, falar=None, confirmar=None, perfis=None, perfil_atual=None, aplicar_perfil=None,
                 tocar_wav=None, preaquecer=None, ambiente_fixa_perfil=False):
        self.falar = falar or (lambda texto: None)
        self.confirmar = confirmar or (lambda pergunta: False)
        self.perfis = perfis or (lambda: [])                  # [(nome, descricao)]
        self.perfil_atual = perfil_atual or (lambda: "")
        self.aplicar_perfil = aplicar_perfil or (lambda nome: False)
        self.tocar_wav = tocar_wav or (lambda caminho: False)
        self.preaquecer = preaquecer or (lambda: None)
        self.ambiente_fixa_perfil = ambiente_fixa_perfil


# ====================================================================== entrada
def executar(argumento, ctx, motor):
    partes = str(argumento or "").split()
    if not partes:
        return _status(ctx, motor)
    cmd, resto = partes[0].lower(), partes[1:]
    if cmd == "usar":
        return _usar(resto, ctx, motor)
    if cmd == "padrao":
        return _padrao(resto, ctx)
    if cmd == "testar":
        ctx.falar(" ".join(resto) or FRASE_TESTE)
        return None
    if cmd == "kokoro":
        return _kokoro(resto, ctx, motor)
    if cmd in ("ajuda", "help"):
        return _ajuda()
    return f"Não conheço /voz {cmd}. Digite /voz ajuda."


def _ajuda():
    linhas = ["Comandos de voz:"]
    linhas += [f"  /voz {nome:<9} {desc}" for nome, desc in SUBCOMANDOS]
    linhas.append("Dentro de /voz kokoro: " + ", ".join(nome for nome, _ in SUBCOMANDOS_KOKORO) + ".")
    return "\n".join(linhas)


# ======================================================================= estado
def _status(ctx, motor):
    cfg = config.carregar()
    ativo = cfg["motor"]
    linhas = [f"Motor ativo: {ativo}"
              + (f"  (padrão: {ctx.perfil_atual()})" if ativo == "kokoro" else f"  ({ctx.perfil_atual()})")]
    linhas += _linhas_kokoro(cfg["kokoro"], motor)
    linhas.append("Use /voz ajuda para ver o que dá para ajustar.")
    return "\n".join(linhas)


def _linhas_kokoro(kcfg, motor):
    ok, motivo = motor.disponivel()
    linhas = ["Kokoro: " + ("pronto" if ok else f"indisponível, {motivo}")]
    pesos = " / ".join("%g" % m["peso"] for m in kcfg["mistura"])
    linhas.append(f"  mistura: {config.resumo_mistura(kcfg['mistura'])}   (pesos {pesos})")
    linhas.append(f"  idioma: {kcfg['idioma']} (fixo, vale para todas as vozes da mistura)"
                  f" · velocidade: {kcfg['velocidade']:g}"
                  f" · pré-aquecer: {'sim' if kcfg.get('preaquecer', True) else 'não'}")
    nativos = {config.idioma_nativo(m["voz"]) for m in kcfg["mistura"]} - {None}
    if kcfg["idioma"].startswith("pt") and "pt-br" not in nativos:
        linhas.append("  nota: nenhuma voz da mistura é nativa em português, então o timbre carrega "
                      "sotaque. Para reduzir, inclua pm_alex, pm_santa ou pf_dora na mistura.")
    if motor.ultimo_erro:
        linhas.append(f"  último erro: {motor.ultimo_erro}")
    return linhas


# ================================================================= usar / padrao
def _usar(resto, ctx, motor):
    alvo = (resto[0].lower() if resto else "")
    if alvo == "padrao":
        config.atualizar(lambda c: c.update(motor="padrao"))
        return "Voz padrão (Edge, com o Windows de reserva) ativada."
    if alvo != "kokoro":
        return "Use /voz usar kokoro ou /voz usar padrao."
    ok, motivo = motor.disponivel()
    if not ok:
        return f"Não dá para ativar o Kokoro: {motivo}."
    try:
        motor._carregar()
    except ErroKokoro as erro:
        return f"Não dá para ativar o Kokoro: {erro}."
    config.atualizar(lambda c: c.update(motor="kokoro"))
    ctx.preaquecer()
    return ("Kokoro ativado. Se algo falhar, o Jarvis volta sozinho para a voz padrão. "
            "Teste com /voz testar.")


def _padrao(resto, ctx):
    perfis = ctx.perfis()
    nomes = {n.lower(): n for n, _ in perfis}
    if not resto:
        atual = ctx.perfil_atual()
        linhas = ["Perfis da voz padrão (Edge/Windows):"]
        linhas += [f"{'▸' if n == atual else ' '} {n:<17} {d}" for n, d in perfis]
        linhas.append("Escolha com /voz padrao NOME.")
        return "\n".join(linhas)
    escolhido = nomes.get(resto[0].lower())
    if escolhido is None:
        return f"Não existe o perfil {resto[0]}. Veja /voz padrao."
    config.atualizar(lambda c: c.update(perfil_padrao=escolhido))
    ctx.aplicar_perfil(escolhido)
    aviso = " (a variável JARVIS_VOZ está definida e vence na próxima abertura)" if ctx.ambiente_fixa_perfil else ""
    return f"Perfil padrão: {escolhido}.{aviso}"


# ====================================================================== kokoro
def _kokoro(partes, ctx, motor):
    if not partes:
        return "\n".join(_linhas_kokoro(config.carregar()["kokoro"], motor))
    cmd, resto = partes[0].lower(), partes[1:]
    funcoes = {"status": _k_status, "vozes": _k_vozes, "mistura": _k_mistura, "idioma": _k_idioma,
               "velocidade": _k_velocidade, "preset": _k_preset, "pronuncia": _k_pronuncia,
               "preaquecer": _k_preaquecer, "testar": _k_testar, "instalar": _k_instalar}
    funcao = funcoes.get(cmd)
    if funcao is None:
        return f"Não conheço /voz kokoro {cmd}. Digite /voz ajuda."
    try:
        return funcao(resto, ctx, motor)
    except ValueError as erro:                      # validacoes de config.py, ja em portugues
        return str(erro)
    except ErroKokoro as erro:
        return f"Kokoro: {erro}."


def _k_status(resto, ctx, motor):
    return "\n".join(_linhas_kokoro(config.carregar()["kokoro"], motor))


def _k_vozes(resto, ctx, motor):
    vozes = motor.vozes()
    if not vozes:
        ok, motivo = motor.disponivel()
        return f"Não consegui ler as vozes: {motivo or 'arquivo de vozes ilegível'}."
    filtro = (resto[0].lower() if resto else "")
    grupos = {}
    for voz in vozes:
        idioma = config.idioma_nativo(voz) or "?"
        if filtro and filtro not in voz and filtro != idioma and not idioma.startswith(filtro):
            continue
        grupos.setdefault(idioma, []).append(f"{voz} ({config.genero(voz)})")
    if not grupos:
        return f"Nenhuma voz combina com '{filtro}'."
    linhas = [f"{idioma}: " + ", ".join(lista) for idioma, lista in sorted(grupos.items())]
    return "\n".join(linhas + ["Misture com /voz kokoro mistura voz=peso voz=peso (até 3)."])


def _k_mistura(resto, ctx, motor):
    if not resto:
        kcfg = config.carregar()["kokoro"]
        return f"Mistura atual: {config.resumo_mistura(kcfg['mistura'])}."
    mistura = config.interpretar_mistura(" ".join(resto))
    existentes = set(motor.vozes())
    desconhecidas = [m["voz"] for m in mistura if existentes and m["voz"] not in existentes]
    if desconhecidas:
        return f"Voz não encontrada: {', '.join(desconhecidas)}. Veja /voz kokoro vozes."
    config.atualizar(lambda c: c["kokoro"].update(mistura=mistura))
    ctx.preaquecer()
    texto = f"Mistura: {config.resumo_mistura(mistura)}."
    idiomas = {config.idioma_nativo(m["voz"]) for m in mistura}
    if len({i for i in idiomas if i} - {"en-us", "en-gb"}) > 1 or (
            len(idiomas) > 1 and not idiomas <= {"en-us", "en-gb"}):
        texto += " Atenção: vozes de idiomas diferentes podem soar estranhas juntas."
    return texto


def _k_idioma(resto, ctx, motor):
    if not resto:
        return f"Idioma atual: {config.carregar()['kokoro']['idioma']}. Exemplos: " + ", ".join(i for i, _ in IDIOMAS)
    codigo = config.validar_idioma(resto[0])
    ok, _ = motor.disponivel()
    if ok and not motor.idioma_valido(codigo):
        return f"O espeak não conhece o idioma {codigo}. Exemplos: " + ", ".join(i for i, _ in IDIOMAS)
    config.atualizar(lambda c: c["kokoro"].update(idioma=codigo))
    ctx.preaquecer()
    return f"Idioma: {codigo}." + ("" if codigo.startswith("pt") else
                                   " O Jarvis fala português: fora de pt-* o texto sai com pronúncia estrangeira.")


def _k_velocidade(resto, ctx, motor):
    if not resto:
        return f"Velocidade atual: {config.carregar()['kokoro']['velocidade']:g} (de 0.5 a 2.0)."
    valor = config.validar_velocidade(resto[0])
    config.atualizar(lambda c: c["kokoro"].update(velocidade=valor))
    ctx.preaquecer()
    return f"Velocidade: {valor:g}."


def _k_preset(resto, ctx, motor):
    kcfg = config.carregar()["kokoro"]
    presets = kcfg["presets"]
    acao = resto[0].lower() if resto else "lista"
    nome = resto[1].lower() if len(resto) > 1 else ""
    if acao == "lista":
        if not presets:
            return "Nenhum preset salvo. Use /voz kokoro preset salvar NOME."
        return "\n".join(f"{n}: {config.resumo_mistura(p['mistura'])} · {p['idioma']} · {p['velocidade']:g}x"
                         for n, p in sorted(presets.items()))
    if not nome:
        return f"Informe o nome: /voz kokoro preset {acao} NOME."
    if acao == "salvar":
        atual = {"mistura": kcfg["mistura"], "idioma": kcfg["idioma"], "velocidade": kcfg["velocidade"]}
        config.atualizar(lambda c: c["kokoro"]["presets"].__setitem__(nome, atual))
        return f"Preset '{nome}' salvo: {config.resumo_mistura(kcfg['mistura'])}."
    if nome not in presets:
        return f"Não existe o preset '{nome}'."
    if acao == "usar":
        p = presets[nome]
        config.atualizar(lambda c: c["kokoro"].update(mistura=p["mistura"], idioma=p["idioma"],
                                                      velocidade=p["velocidade"]))
        ctx.preaquecer()
        return f"Preset '{nome}' aplicado: {config.resumo_mistura(p['mistura'])}."
    if acao == "apagar":
        config.atualizar(lambda c: c["kokoro"]["presets"].pop(nome, None))
        return f"Preset '{nome}' apagado."
    return "Use /voz kokoro preset lista, salvar NOME, usar NOME ou apagar NOME."


def _k_pronuncia(resto, ctx, motor):
    mapa = config.carregar()["kokoro"]["pronuncias"]
    if not resto or resto[0].lower() == "lista":
        return "Pronúncias (sem acento → como ler):\n" + ", ".join(f"{k}={v}" for k, v in sorted(mapa.items()))
    if resto[0].lower() == "remover" and len(resto) > 1:
        chave = resto[1].lower()
        if chave not in mapa:
            return f"'{chave}' não está na lista."
        config.atualizar(lambda c: c["kokoro"]["pronuncias"].pop(chave, None))
        return f"Pronúncia de '{chave}' removida."
    texto = " ".join(resto)
    if "=" not in texto:
        return "Use /voz kokoro pronuncia palavra=como-ler, remover palavra, ou lista."
    chave, _, valor = texto.partition("=")
    chave, valor = chave.strip().lower(), valor.strip()
    if not chave or not valor or " " in chave:
        raise ValueError("Use uma palavra só antes do =, e algo depois dele.")
    config.atualizar(lambda c: c["kokoro"]["pronuncias"].__setitem__(chave, valor))
    return f"Agora '{chave}' é lida como '{valor}'."


def _k_preaquecer(resto, ctx, motor):
    if not resto or resto[0].lower() not in ("on", "off", "sim", "nao", "não"):
        return "Use /voz kokoro preaquecer on ou off."
    ligado = resto[0].lower() in ("on", "sim")
    config.atualizar(lambda c: c["kokoro"].update(preaquecer=ligado))
    if ligado:
        ctx.preaquecer()
    return "Pré-aquecimento " + ("ligado." if ligado else "desligado.")


def _k_testar(resto, ctx, motor):
    ok, motivo = motor.disponivel()
    if not ok:
        return f"Não dá para testar: {motivo}."
    frase = " ".join(resto) or FRASE_TESTE
    kcfg = config.carregar()["kokoro"]
    existia = motor.arquivo_cache(frase, kcfg).exists() if motor.modelo.exists() else False
    inicio = time.perf_counter()
    try:
        caminho = motor.gerar(frase, kcfg)
    except Exception as erro:
        raise ErroKokoro(str(erro) or erro.__class__.__name__)
    gerou_em = time.perf_counter() - inicio
    if not ctx.tocar_wav(str(caminho)):
        return "Gerei o áudio, mas não consegui tocar (o player do Jarvis não iniciou)."
    return (f"{config.resumo_mistura(kcfg['mistura'])} · {kcfg['idioma']} · {kcfg['velocidade']:g}x — "
            + ("do cache." if existia else f"gerado em {gerou_em:.1f} s."))


def _k_instalar(resto, ctx, motor):
    pendentes = instalar.faltando()
    if not pendentes:
        return "Os modelos já estão instalados em modelos/kokoro."
    try:
        baixados = instalar.instalar(
            lambda descricao: ctx.confirmar(f"Vou baixar {descricao}. Confirma?"), progresso=print)
    except instalar.ErroInstalacao as erro:
        return f"Falhou: {erro}"
    if not baixados:
        return "Nada foi baixado."
    return "Modelos instalados. Ative com /voz usar kokoro."


# =================================================================== sugestoes
def sugestoes(anteriores, ctx, motor):
    """Candidatos [(texto, descricao)] para o proximo token; o CLI filtra pelo que foi digitado."""
    anteriores = [a.lower() for a in anteriores]
    if not anteriores:
        return SUBCOMANDOS
    if anteriores[0] == "usar":
        return [("kokoro", "voz local do Kokoro"), ("padrao", "Edge com o Windows de reserva")]
    if anteriores[0] == "padrao":
        return ctx.perfis()
    if anteriores[0] != "kokoro":
        return []
    if len(anteriores) == 1:
        return SUBCOMANDOS_KOKORO
    sub = anteriores[1]
    if sub == "mistura":
        return [(f"{v}=", f"{config.genero(v)} · {config.idioma_nativo(v) or '?'}") for v in motor.vozes()]
    if sub == "idioma":
        return IDIOMAS
    if sub == "velocidade":
        return [(v, "") for v in ("0.8", "0.9", "1.0", "1.1", "1.2", "1.5")]
    if sub == "vozes":
        return [(i, d) for i, d in IDIOMAS]
    if sub == "preaquecer":
        return [("on", "ligar"), ("off", "desligar")]
    if sub == "pronuncia":
        return [("lista", ""), ("remover", "apagar uma regra")] if len(anteriores) == 2 else [
            (k, "") for k in config.carregar()["kokoro"]["pronuncias"]]
    if sub == "preset":
        if len(anteriores) == 2:
            return [("lista", ""), ("salvar", "guardar a voz atual"), ("usar", "aplicar"), ("apagar", "")]
        return [(n, "") for n in config.carregar()["kokoro"]["presets"]]
    return []
