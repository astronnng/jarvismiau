import _ambiente  # noqa: F401  (isola os dados do usuario; deve ser o primeiro import)

"""
TABELA DE DESPACHO DO processar() - rede de seguranca da reorganizacao (fase 3)

Para cada frase, registra QUAL handler do jarvis.py e acionado e com que argumentos. Todos os
handlers sao trocados por gravadores, entao nada e executado de verdade (sem audio, sem navegador,
sem rede). O que esta aqui e o comportamento ATUAL: a ordem das regras em `_processar` decide qual
comando "ganha" quando mais de uma regra casaria, e e exatamente isso que um refactor costuma quebrar.

Linhas marcadas com "CONHECIDO" registram um comportamento que parece errado hoje, mas que a
reorganizacao nao deve mudar sem querer. Corrigi-lo e uma decisao a parte: ao corrigir, altere a linha.
"""

import unittest
from unittest.mock import MagicMock, patch

import jarvis

DICT = "{!r}".format


def assinatura(log):
    """Sequencia de handlers acionados, em texto curto e estavel."""
    saida = []
    for nome, args in log:
        if nome == "acao":
            saida.append("acao:" + args[0] + (":" + DICT(args[1]) if len(args) > 1 else ""))
        elif nome in ("tentar_abrir", "tarefa_clima", "tarefa_pesquisar", "tarefa_youtube", "tarefa_lembrete",
                      "cadastrar", "webbrowser", "ia"):
            saida.append(f"{nome}:{args[0]}")
        else:
            saida.append(nome)
    return saida


def despachar(frase, alarme_tocando=False, abrir_ok=True):
    """Roda jarvis.processar com todos os handlers gravados. Devolve (continua, assinatura)."""
    log = []

    def gravador(nome, retorno=None):
        def f(*args, **kwargs):
            log.append((nome, args))
            return retorno
        return f

    banco = MagicMock()
    banco.return_value.tem_alarmas_tocando.return_value = alarme_tocando
    patches = [
        patch.object(jarvis, "falar", gravador("falar")),
        patch.object(jarvis, "executar_acao", gravador("acao", (True, "ok"))),
        patch.object(jarvis, "tarefa_hora", gravador("tarefa_hora")),
        patch.object(jarvis, "tarefa_data", gravador("tarefa_data")),
        patch.object(jarvis, "tarefa_clima", gravador("tarefa_clima")),
        patch.object(jarvis, "tarefa_pesquisar", gravador("tarefa_pesquisar")),
        patch.object(jarvis, "tarefa_youtube", gravador("tarefa_youtube")),
        patch.object(jarvis, "tarefa_bloquear", gravador("tarefa_bloquear")),
        patch.object(jarvis, "tarefa_lembrete", gravador("tarefa_lembrete")),
        patch.object(jarvis, "tentar_abrir", gravador("tentar_abrir", abrir_ok)),
        patch.object(jarvis, "processar_com_ia", gravador("ia", True)),
        patch.object(jarvis, "cadastrar_entrada_catalogo", gravador("cadastrar")),
        patch.object(jarvis, "perguntar_sim_nao", gravador("sim_nao", False)),
        patch.object(jarvis.webbrowser, "open", gravador("webbrowser")),
        patch.object(jarvis.lembretes, "Lembretes", banco),
        patch.object(jarvis, "_ultimo_uso_navegador", 0.0),
    ]
    for p in patches:
        p.start()
    try:
        continua = jarvis.processar(frase)
    finally:
        for p in patches:
            p.stop()
    return continua, assinatura(log)


# (frase, alarme tocando?, continua?, handlers acionados em ordem)
TABELA = [
    # ---- sair ----
    ("sair", False, False, ["falar"]),
    ("tchau", False, False, ["falar"]),
    ("goodbye", False, False, ["falar"]),
    ("encerrar", False, False, ["falar"]),
    ("desligar o jarvis", False, False, ["falar"]),
    # ---- cadastro de sites e programas ----
    ("adicionar site meu banco", False, True, ["cadastrar:site"]),
    ("cadastrar programa meu editor", False, True, ["cadastrar:programa"]),
    # ---- navegador: regras locais rapidas (antes da IA) ----
    ("abre o segundo video", False, True, ["acao:resultado_abrir:{'posicao': 2}"]),
    ("pesquisa lofi no youtube e abre o primeiro", False, True,
     ["acao:youtube_pesquisar:{'termo': 'lofi'}", "acao:resultado_abrir:{'posicao': 1, 'nova_aba': False}"]),
    ("pesquisa lofi no google", False, True, ["acao:google_pesquisar:{'termo': 'lofi'}"]),
    ("abre os 3 primeiros videos", False, True, ["acao:youtube_abrir_varios:{'quantidade': 3}"]),
    ("velocidade 1.5", False, True, ["acao:youtube_player:{'controle': 'velocidade', 'valor': '1.5'}"]),
    ("pular anuncio", False, True, ["acao:youtube_player:{'controle': 'pular_anuncio'}"]),
    ("legendas", False, True, ["acao:youtube_player:{'controle': 'legendas'}"]),
    ("quantos e-mails nao lidos", False, True, ["acao:gmail_nao_lidos"]),
    ("silencia a aba do youtube", False, True, ["acao:aba_silenciar:{'silenciar': True, 'alvo': 'youtube'}"]),
    ("fecha as abas duplicadas", False, True, ["acao:abas_fechar:{'duplicadas': True}"]),
    ("o que esta tocando", False, True, ["acao:musica_tocando"]),
    ("procura no historico receita de pao", False, True, ["acao:historico_buscar:{'termo': 'receita de pao'}"]),
    ("salva essa pagina nos favoritos", False, True, ["acao:favorito_salvar"]),
    ("diagnostico do navegador", False, True, ["acao:navegador_diagnostico"]),
    # ---- varias acoes na mesma frase: quem planeja e a IA ----
    ("abre o netflix e aumenta o volume", False, True, ["ia:abre o netflix e aumenta o volume"]),
    # ---- conversa, hora, data, clima ----
    ("oi", False, True, ["falar"]),
    ("bom dia", False, True, ["falar"]),
    ("tudo bem", False, True, ["falar"]),
    ("que horas sao", False, True, ["tarefa_hora"]),
    ("que dia e hoje", False, True, ["tarefa_data"]),
    ("clima em Bariri", False, True, ["tarefa_clima:clima em bariri"]),
    # CONHECIDO: so a primeira parte e atendida ("abre o youtube" some); nao e tratado como multi-comando
    ("que horas sao e abre o youtube", False, True, ["tarefa_hora"]),
    # ---- sistema ----
    ("cancelar desligamento", False, True, ["acao:cancelar_desligamento"]),
    ("desligar o computador", False, True, ["acao:desligar:{'segundos': 60}"]),
    ("reiniciar o pc", False, True, ["acao:reiniciar:{'segundos': 60}"]),
    ("hibernar o computador", False, True, ["acao:hibernar:{'segundos': 60}"]),
    ("como esta a memoria do pc", False, True, ["acao:status_pc"]),
    ("status", False, True, ["acao:status_pc"]),
    ("bloquear o computador", False, True, ["tarefa_bloquear"]),
    # ---- lembretes ----
    ("listar lembretes", False, True, ["acao:listar_lembretes"]),
    ("me lembre em 10 minutos de ver o arroz", False, True,
     ["tarefa_lembrete:me lembre em 10 minutos de ver o arroz"]),
    ("confirmar arroz no fogo", False, True, ["acao:confirmar_lembrete:{'assunto': 'arroz no fogo'}"]),
    ("encerrar o lembrete", False, True, ["acao:confirmar_lembrete:{'assunto': ''}"]),
    # ---- volume e midia ----
    ("volume em 35%", False, True, ["acao:volume:{'percentual': 35}"]),
    ("diminuir volume em 20%", False, True, ["acao:volume:{'percentual': 20}"]),
    ("silenciar", False, True, ["acao:volume:{'sentido': 'mudo'}"]),
    ("abaixa o volume", False, True, ["acao:volume:{'sentido': 'diminuir', 'quanto': 3}"]),
    ("aumentar o volume", False, True, ["acao:volume:{'sentido': 'aumentar', 'quanto': 3}"]),
    ("mais volume", False, True, ["acao:volume:{'sentido': 'aumentar', 'quanto': 3}"]),
    ("volume", False, True, ["acao:volume:{'sentido': 'aumentar', 'quanto': 3}"]),
    ("anterior", False, True, ["acao:midia_anterior"]),
    ("proxima musica", False, True, ["acao:midia_proxima"]),
    ("dar play", False, True, ["acao:midia_play_pausa"]),
    ("pausar", False, True, ["acao:midia_play_pausa"]),
    ("pausa a musica", False, True, ["acao:midia_play_pausa"]),
    ("play no spotify", False, True, ["acao:spotify_abrir"]),
    # CONHECIDO: "parar" sozinho nao tem regra local; quem decide e a IA (midia_parar so existe pelo catalogo)
    ("parar", False, True, ["ia:parar"]),
    ("pare a musica", False, True, ["ia:pare a musica"]),
    # ---- pesquisar, tocar, abrir ----
    ("pesquisar receita de bolo", False, True, ["tarefa_pesquisar:receita de bolo"]),
    # CONHECIDO: R_PLAY casa com "tocar/toca" antes de R_TOCAR, entao "tocar X" vira play/pausa em vez de
    # buscar X no YouTube (o README diz o contrario). Hoje so "colocar X" chega em tarefa_youtube.
    ("tocar legiao urbana", False, True, ["acao:midia_play_pausa"]),
    ("toca uma musica qualquer coisa", False, True, ["acao:midia_play_pausa"]),
    ("colocar queen", False, True, ["tarefa_youtube:queen"]),
    ("colocar uma musica do queen", False, True, ["tarefa_youtube:queen"]),
    ("abrir youtube", False, True, ["tentar_abrir:youtube"]),
    ("abrir calculadora", False, True, ["tentar_abrir:calculadora"]),
    ("abre o bloco de notas", False, True, ["tentar_abrir:bloco de notas"]),
    ("abrir", False, True, ["tentar_abrir:"]),
    # ---- frases livres vao para a IA ----
    ("quem descobriu o brasil", False, True, ["ia:quem descobriu o brasil"]),
    ("obrigado", False, True, ["ia:obrigado"]),
    ("ajuda", False, True, ["ia:ajuda"]),
    # ---- alarmes: sem nada tocando, estas frases NAO sao de alarme ----
    ("ok", False, True, ["ia:ok"]),
    ("ok, verificado", False, True, ["ia:ok, verificado"]),
    ("encerre", False, True, ["ia:encerre"]),
    ("para", False, True, ["ia:para"]),
    # ---- alarmes: com um alarme tocando elas encerram o alarme (e vencem a regra de sair) ----
    ("ok", True, True, ["acao:confirmar_lembrete:{'assunto': ''}"]),
    ("ok, verificado", True, True, ["acao:confirmar_lembrete:{'assunto': ''}"]),
    ("encerre", True, True, ["acao:confirmar_lembrete:{'assunto': ''}"]),
    ("encerrar", True, True, ["acao:confirmar_lembrete:{'assunto': ''}"]),
    ("para", True, True, ["acao:confirmar_lembrete:{'assunto': ''}"]),
    # CONHECIDO: com alarme tocando, "pare a musica" e lido como "encerrar o alarme de musica"
    ("pare a musica", True, True, ["acao:confirmar_lembrete:{'assunto': 'musica'}"]),
    # sair continua saindo mesmo com alarme tocando
    ("tchau", True, False, ["falar"]),
]


class DespachoTests(unittest.TestCase):
    def test_tabela_de_despacho(self):
        for frase, alarme, continua_esperado, passos_esperados in TABELA:
            with self.subTest(frase=frase, alarme_tocando=alarme):
                continua, passos = despachar(frase, alarme_tocando=alarme)
                self.assertEqual(passos, passos_esperados)
                self.assertEqual(continua, continua_esperado)

    def test_frase_desconhecida_tenta_abrir_e_cai_na_pesquisa_do_google(self):
        continua, passos = despachar("abrir coisa inexistente", abrir_ok=False)
        self.assertTrue(continua)
        self.assertEqual(passos, ["tentar_abrir:coisa inexistente", "falar",
                                  "webbrowser:https://www.google.com/search?q=coisa%20inexistente"])

    def test_frase_vazia_pede_para_repetir(self):
        continua, passos = despachar("   ")
        self.assertEqual((continua, passos), (True, ["falar"]))

    def test_a_tabela_nao_tem_linhas_repetidas(self):
        chaves = [(f, a) for f, a, _, _ in TABELA]
        self.assertEqual(len(chaves), len(set(chaves)))

    def test_toda_acao_citada_na_tabela_existe_no_catalogo(self):
        import acoes
        citadas = {p.split(":")[1] for _, _, _, passos in TABELA for p in passos if p.startswith("acao:")}
        self.assertEqual([a for a in sorted(citadas) if not acoes.existe(a)], [])


if __name__ == "__main__":
    unittest.main()
