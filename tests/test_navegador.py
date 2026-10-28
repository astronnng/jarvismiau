import _ambiente  # noqa: F401  (isola os dados do usuario; deve ser o primeiro import)
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import navegador
from navegador import atalhos, config, generico
from navegador.ponte import ErroNavegador, Ponte


class PonteFalsa:
    """Substitui a ponte real: registra os comandos e responde via `respostas`."""

    def __init__(self, respostas=None, conectada=True):
        self.chamadas = []
        self.respostas = respostas or {}
        self.conectada = conectada

    def ativa(self):
        return True

    def conectado(self):
        return self.conectada

    def enviar(self, cmd, timeout=15, **args):
        if not self.conectada:
            raise ErroNavegador("A extensao do navegador nao esta conectada, senhor.")
        self.chamadas.append((cmd, args))
        resposta = self.respostas.get(cmd)
        return resposta(args) if callable(resposta) else resposta

    def comandos(self, nome):
        return [args for cmd, args in self.chamadas if cmd == nome]


class UsaPonteFalsa(unittest.TestCase):
    def instalar(self, **kw):
        anterior = navegador._ponte
        self.addCleanup(navegador.definir_ponte, anterior)
        self.addCleanup(atalhos._ultimos.clear)
        atalhos._ultimos.clear()
        falsa = PonteFalsa(**kw)
        navegador.definir_ponte(falsa)
        return falsa


class PonteHttpTests(unittest.TestCase):
    def setUp(self):
        self.ponte = Ponte(0, "segredo", espera_poll=1)
        self.assertTrue(self.ponte.iniciar())
        self.addCleanup(self.ponte.parar)
        self.base = f"http://127.0.0.1:{self.ponte.porta}"

    def chamar(self, caminho, token="segredo", dados=None, origem=None):
        req = urllib.request.Request(
            self.base + caminho,
            data=json.dumps(dados).encode() if dados is not None else None,
            headers={"X-Jarvis-Token": token, "Content-Type": "application/json"},
        )
        if origem:
            req.add_header("Origin", origem)
        return urllib.request.urlopen(req, timeout=5)

    def extensao_simulada(self, responder):
        """Faz o papel da extensao: busca um comando e devolve o resultado."""
        def laco():
            resp = self.chamar("/proximo")
            if resp.status == 200:
                comando = json.loads(resp.read())
                self.chamar("/resultado", dados=dict(id=comando["id"], **responder(comando)))
        thread = threading.Thread(target=laco, daemon=True)
        thread.start()
        return thread

    def test_comando_vai_e_volta_pela_ponte(self):
        self.extensao_simulada(lambda c: {"ok": True, "dados": {"eco": c["args"]["x"]}})
        # a extensao precisa estar "no ar" (long polling ativo) para o envio valer
        for _ in range(50):
            if self.ponte.conectado():
                break
            threading.Event().wait(0.05)
        self.assertEqual(self.ponte.enviar("teste", timeout=5, x=7), {"eco": 7})

    def test_erro_da_extensao_vira_frase(self):
        self.extensao_simulada(lambda c: {"ok": False, "erro": "boom"})
        for _ in range(50):
            if self.ponte.conectado():
                break
            threading.Event().wait(0.05)
        with self.assertRaises(ErroNavegador) as ctx:
            self.ponte.enviar("teste", timeout=5)
        self.assertIn("boom", str(ctx.exception))

    def test_extensao_ocupada_com_comando_lento_continua_conectada(self):
        """Regressao: Gmail carregando por >8s fazia a ponte achar que a extensao caiu."""
        import time as _t
        recebido = threading.Event()
        liberar = threading.Event()

        def laco():
            comando = json.loads(self.chamar("/proximo").read())
            recebido.set()
            liberar.wait(5)                      # comando lento: nao consulta a ponte
            self.chamar("/resultado", dados={"id": comando["id"], "ok": True, "dados": 1})
        threading.Thread(target=laco, daemon=True).start()
        for _ in range(50):
            if self.ponte.conectado():
                break
            _t.sleep(0.05)
        resultado = []
        envio = threading.Thread(target=lambda: resultado.append(self.ponte.enviar("lento", timeout=8)))
        envio.start()
        self.assertTrue(recebido.wait(3))
        self.ponte._ultimo_contato -= 60         # finge que o ultimo contato foi ha 1 minuto
        self.assertTrue(self.ponte.conectado())  # mas ha um comando em andamento
        liberar.set()
        envio.join(5)
        self.assertEqual(resultado, [1])

    def test_sem_extensao_falha_na_hora(self):
        with self.assertRaises(ErroNavegador) as ctx:
            self.ponte.enviar("teste", timeout=1)
        self.assertIn("nao esta conectada", str(ctx.exception))

    def test_token_errado_e_recusado(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.chamar("/proximo", token="outro")
        self.assertEqual(ctx.exception.code, 401)

    def test_origem_de_pagina_comum_e_recusada(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.chamar("/proximo", origem="https://site-qualquer.com")
        self.assertEqual(ctx.exception.code, 401)

    def test_origem_de_extensao_e_aceita(self):
        resp = self.chamar("/proximo", origem="chrome-extension://abcdef")
        self.assertEqual(resp.status, 204)


class ConfigTests(unittest.TestCase):
    def test_cria_token_e_grava_arquivo_da_extensao(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "navegador.json"
            cfg = config.carregar(caminho)
            self.assertEqual(cfg["porta"], config.PORTA_PADRAO)
            self.assertGreaterEqual(len(cfg["token"]), 20)
            self.assertEqual(config.carregar(caminho)["token"], cfg["token"])

            destino = Path(pasta) / "extensao" / "config.local.js"
            self.assertTrue(config.gravar_para_extensao(cfg, destino))
            self.assertIn(cfg["token"], destino.read_text(encoding="utf-8"))
            self.assertFalse(config.gravar_para_extensao(cfg, destino))   # sem mudanca


def _itens_youtube():
    return [
        {"texto": "Video A", "href": "https://www.youtube.com/watch?v=aaaaaaaaaaa", "classes": ""},
        {"texto": "Video A (de novo)", "href": "https://www.youtube.com/watch?v=aaaaaaaaaaa&t=5", "classes": ""},
        {"texto": "Video B", "href": "https://www.youtube.com/watch?v=bbbbbbbbbbb", "classes": ""},
        {"texto": "Video C", "href": "https://www.youtube.com/watch?v=ccccccccccc", "classes": ""},
    ]


class YouTubeTests(UsaPonteFalsa):
    def montar(self, url="https://www.youtube.com/results?search_query=pao"):
        return self.instalar(respostas={
            "abas_listar": [{"id": 1, "indice": 0, "titulo": "YouTube", "url": url, "ativa": True}],
            "consultar": {"itens": _itens_youtube()},
        })

    def test_pesquisar_reaproveita_a_aba_do_youtube(self):
        falsa = self.montar(url="https://www.youtube.com/")
        atalhos.youtube_pesquisar("receita de pao")
        abertura = falsa.comandos("abrir_url")[0]
        self.assertIn("results?search_query=receita%20de%20pao", abertura["url"])
        self.assertFalse(abertura["nova_aba"])
        self.assertEqual(abertura["aba"], 1)

    def test_pesquisar_abre_aba_nova_se_nao_ha_youtube(self):
        falsa = self.montar(url="https://exemplo.com/")
        atalhos.youtube_pesquisar("lofi")
        self.assertTrue(falsa.comandos("abrir_url")[0]["nova_aba"])

    def test_pesquisar_respeita_pedido_explicito_de_aba_nova(self):
        falsa = self.montar(url="https://www.youtube.com/")
        atalhos.youtube_pesquisar("lofi", nova_aba=True)
        self.assertTrue(falsa.comandos("abrir_url")[0]["nova_aba"])

    def test_titulo_ignora_duracao_da_miniatura(self):
        falsa = self.montar()
        falsa.respostas["consultar"] = {"itens": [
            {"texto": "11:53:45 Em reproducao", "href": "https://www.youtube.com/watch?v=aaaaaaaaaaa", "classes": ""},
            {"texto": "Lofi hip hop radio", "href": "https://www.youtube.com/watch?v=aaaaaaaaaaa", "classes": ""},
            {"texto": "3:21", "href": "https://www.youtube.com/watch?v=bbbbbbbbbbb", "classes": ""},
            {"texto": "Segundo video de verdade", "href": "https://www.youtube.com/watch?v=bbbbbbbbbbb", "classes": ""},
        ]}
        fala = atalhos.youtube_abrir_resultado(1)
        self.assertIn("Lofi hip hop radio", fala)
        self.assertNotIn("11:53", fala)

    def test_abrir_resultado_generico_escolhe_o_site_pela_aba(self):
        falsa = self.montar()
        atalhos.abrir_resultado(2, nova_aba=True)
        self.assertEqual(falsa.comandos("abrir_url")[0]["url"],
                         "https://www.youtube.com/watch?v=bbbbbbbbbbb")

    def test_abre_o_primeiro_na_mesma_aba_e_sem_repeticao(self):
        falsa = self.montar()
        fala = atalhos.youtube_abrir_resultado(1)
        abertura = falsa.comandos("abrir_url")[0]
        self.assertEqual(abertura["url"], "https://www.youtube.com/watch?v=aaaaaaaaaaa")
        self.assertFalse(abertura["nova_aba"])
        self.assertIn("Video A", fala)

    def test_segundo_em_outra_aba_usa_a_lista_memorizada(self):
        falsa = self.montar()
        atalhos.youtube_abrir_resultado(1)
        # o usuario agora esta na pagina do primeiro video, nao mais nos resultados
        falsa.respostas["abas_listar"] = [{
            "id": 1, "indice": 0, "titulo": "Video A", "ativa": True,
            "url": "https://www.youtube.com/watch?v=aaaaaaaaaaa"}]
        falsa.respostas["consultar"] = {"itens": []}
        atalhos.youtube_abrir_resultado(2, nova_aba=True)
        abertura = falsa.comandos("abrir_url")[-1]
        self.assertEqual(abertura["url"], "https://www.youtube.com/watch?v=bbbbbbbbbbb")
        self.assertTrue(abertura["nova_aba"])

    def test_posicao_inexistente_avisa(self):
        self.montar()
        with self.assertRaises(ErroNavegador):
            atalhos.youtube_abrir_resultado(9)

    def test_fora_do_youtube_sem_busca_pede_para_pesquisar(self):
        self.instalar(respostas={
            "abas_listar": [{"id": 1, "indice": 0, "titulo": "x", "url": "https://exemplo.com", "ativa": True}]})
        with self.assertRaises(ErroNavegador):
            atalhos.youtube_abrir_resultado(1)

    def test_abrir_varios_deixa_a_primeira_em_foco(self):
        falsa = self.montar()
        atalhos.youtube_abrir_varios(3)
        fundos = [a["segundo_plano"] for a in falsa.comandos("abrir_url")]
        self.assertEqual(fundos, [False, True, True])

    def test_player_usa_video_ou_botao(self):
        falsa = self.montar()
        atalhos.youtube_player("pausa")
        atalhos.youtube_player("velocidade", "1.5")
        atalhos.youtube_player("proximo")
        self.assertEqual(falsa.comandos("video")[0]["acao"], "pausa")
        self.assertEqual(falsa.comandos("video")[1]["valor"], 1.5)
        self.assertIn(".ytp-next-button", falsa.comandos("clicar_seletor")[0]["seletor"])


class GoogleGmailTests(UsaPonteFalsa):
    def test_google_ignora_links_internos_no_filtro_e_abre_em_nova_aba(self):
        falsa = self.instalar(respostas={
            "abas_listar": [{"id": 1, "indice": 0, "titulo": "g", "ativa": True,
                             "url": "https://www.google.com/search?q=pao"}],
            "consultar": {"itens": [{"texto": "Receita", "href": "https://receitas.com/pao", "classes": ""}]},
        })
        atalhos.google_abrir_resultado(1)
        consulta = falsa.comandos("consultar")[0]
        self.assertIn("google", consulta["filtro_href"])
        self.assertIn("#tads", consulta["excluir"])
        self.assertTrue(falsa.comandos("abrir_url")[0]["nova_aba"])

    def test_gmail_conta_nao_lidos_pelo_titulo(self):
        self.instalar(respostas={"abas_listar": [{
            "id": 3, "indice": 2, "ativa": False, "url": "https://mail.google.com/mail/u/0/#inbox",
            "titulo": "Caixa de entrada (12) - eu@gmail.com - Gmail"}]})
        self.assertIn("12 e-mails nao lidos", atalhos.gmail_nao_lidos())

    def test_gmail_sem_numero_no_titulo_e_zero(self):
        self.instalar(respostas={"abas_listar": [{
            "id": 3, "indice": 2, "ativa": False, "url": "https://mail.google.com/mail/u/0/#inbox",
            "titulo": "Caixa de entrada - eu@gmail.com - Gmail"}]})
        self.assertIn("Nenhum", atalhos.gmail_nao_lidos())

    def test_gmail_listar_marca_nao_lidos(self):
        self.instalar(respostas={
            "abas_listar": [{"id": 3, "indice": 0, "ativa": True, "titulo": "Gmail",
                             "url": "https://mail.google.com/mail/u/0/#inbox"}],
            "consultar": {"itens": [
                {"texto": "Ana Reuniao amanha", "href": "", "classes": "zA zE"},
                {"texto": "Loja Promocao", "href": "", "classes": "zA yO"}]},
        })
        fala = atalhos.gmail_listar(2)
        self.assertIn("1, nao lido: Ana Reuniao amanha", fala)
        self.assertIn("2, Loja Promocao", fala)


class UrlsETests(UsaPonteFalsa):
    def test_url_sem_extensao_usa_navegador_padrao(self):
        from unittest.mock import patch
        self.instalar(conectada=False)
        with patch.object(atalhos.webbrowser, "open") as abrir:
            atalhos.maps_rota("Bariri SP")
        self.assertIn("destination=Bariri%20SP", abrir.call_args[0][0])

    def test_github_aceita_repositorio_e_recusa_lixo(self):
        falsa = self.instalar()
        atalhos.github_abrir("anthropics/claude-code")
        self.assertEqual(falsa.comandos("abrir_url")[0]["url"], "https://github.com/anthropics/claude-code")
        with self.assertRaises(ErroNavegador):
            atalhos.github_abrir("javascript:alert(1)")


class GenericoTests(UsaPonteFalsa):
    SNAPSHOT = {"titulo": "Loja", "url": "https://loja.com", "itens": [
        {"n": 1, "tipo": "link", "rotulo": "Planos", "regiao": "nav", "href": "https://loja.com/planos"},
        {"n": 2, "tipo": "botao", "rotulo": "Comprar agora", "regiao": "main"},
    ]}

    def decisoes(self, *passos):
        fila = list(passos)
        return lambda prompt: fila.pop(0)

    def test_clica_e_conclui(self):
        falsa = self.instalar(respostas={"snapshot": self.SNAPSHOT, "clicar": {"clicado": True}})
        fala = generico.executar(
            "abrir planos", pausa=0,
            decidir=self.decisoes({"acao": "clicar", "n": "1"}, {"acao": "concluir", "fala": "Pronto."}))
        self.assertEqual(fala, "Pronto.")
        self.assertEqual(falsa.comandos("clicar"), [{"n": 1, "nova_aba": False}])

    def test_passo_sensivel_sem_confirmacao_nao_clica(self):
        falsa = self.instalar(respostas={"snapshot": self.SNAPSHOT})
        perguntas = []
        fala = generico.executar(
            "comprar", pausa=0, confirmar=lambda p: perguntas.append(p) or False,
            decidir=self.decisoes({"acao": "clicar", "n": 2}))
        self.assertIn("Comprar agora", perguntas[0])
        self.assertEqual(falsa.comandos("clicar"), [])
        self.assertIn("Parei", fala)

    def test_passo_sensivel_com_confirmacao_clica(self):
        falsa = self.instalar(respostas={"snapshot": self.SNAPSHOT, "clicar": {}})
        generico.executar(
            "comprar", pausa=0, confirmar=lambda p: True,
            decidir=self.decisoes({"acao": "clicar", "n": 2}, {"acao": "concluir"}))
        self.assertEqual(len(falsa.comandos("clicar")), 1)

    def test_sem_confirmador_passo_sensivel_e_recusado(self):
        falsa = self.instalar(respostas={"snapshot": self.SNAPSHOT})
        generico.executar("comprar", pausa=0, decidir=self.decisoes({"acao": "clicar", "n": 2}))
        self.assertEqual(falsa.comandos("clicar"), [])

    def test_elemento_inventado_e_ignorado_e_acao_estranha_falha(self):
        falsa = self.instalar(respostas={"snapshot": self.SNAPSHOT})
        generico.executar("x", pausa=0, max_passos=2,
                          decidir=self.decisoes({"acao": "clicar", "n": 99}, {"acao": "concluir"}))
        self.assertEqual(falsa.comandos("clicar"), [])
        with self.assertRaises(ErroNavegador):
            generico.executar("x", pausa=0, decidir=self.decisoes({"acao": "formatar_disco"}))

    def test_prompt_traz_tarefa_e_elementos_sem_valores(self):
        prompt = generico.montar_prompt("abrir planos", self.SNAPSHOT, ["cliquei em 3"])
        self.assertIn("abrir planos", prompt)
        self.assertIn("1 | link | Planos | nav | loja.com/planos", prompt)
        self.assertIn("cliquei em 3", prompt)

    def test_resumir_pagina(self):
        self.instalar(respostas={"ler_texto": {"titulo": "T", "texto": "conteudo longo"}})
        resumo = generico.resumir_pagina(decidir=lambda p: {"resumo": "Em resumo."})
        self.assertEqual(resumo, "Em resumo.")


def _aba(id, titulo="x", url="https://exemplo.com/", **kw):
    return dict({"id": id, "indice": id, "titulo": titulo, "url": url, "ativa": False,
                 "audivel": False, "mudo": False, "fixada": False, "janela": 1}, **kw)


class AbasEmLoteTests(UsaPonteFalsa):
    def test_silenciar_sem_alvo_silencia_so_o_que_toca(self):
        falsa = self.instalar(respostas={
            "abas_buscar": lambda a: [_aba(1, "YouTube", audivel=True)] if a.get("audivel") else [],
            "aba_mudo": {}})
        fala = atalhos.aba_silenciar()
        self.assertEqual(falsa.comandos("aba_mudo"), [{"aba": 1, "mudo": True}])
        self.assertIn("YouTube", fala)

    def test_religar_afeta_so_abas_mudas(self):
        falsa = self.instalar(respostas={
            "abas_buscar": [_aba(1, mudo=True), _aba(2)], "aba_mudo": {}})
        atalhos.aba_silenciar(silenciar=False)
        self.assertEqual(falsa.comandos("aba_mudo"), [{"aba": 1, "mudo": False}])

    def test_fechar_poucas_abas_nao_pergunta(self):
        falsa = self.instalar(respostas={"abas_buscar": [_aba(1), _aba(2)], "aba_fechar": {}})
        perguntas = []
        atalhos.fechar_abas("youtube", confirmar=lambda p: perguntas.append(p) or True)
        self.assertEqual(perguntas, [])
        self.assertEqual(falsa.comandos("aba_fechar"), [{"ids": [1, 2]}])

    def test_fechar_muitas_abas_exige_confirmacao(self):
        falsa = self.instalar(respostas={"abas_buscar": [_aba(i) for i in range(1, 6)], "aba_fechar": {}})
        fala = atalhos.fechar_abas("youtube", confirmar=lambda p: False)
        self.assertEqual(falsa.comandos("aba_fechar"), [])
        self.assertIn("Nao fechei", fala)
        atalhos.fechar_abas("youtube", confirmar=lambda p: True)
        self.assertEqual(len(falsa.comandos("aba_fechar")[0]["ids"]), 5)

    def test_fechar_muitas_sem_confirmador_nao_fecha(self):
        falsa = self.instalar(respostas={"abas_buscar": [_aba(i) for i in range(1, 6)], "aba_fechar": {}})
        atalhos.fechar_abas("x")
        self.assertEqual(falsa.comandos("aba_fechar"), [])

    def test_abas_fixadas_nunca_sao_fechadas(self):
        falsa = self.instalar(respostas={"abas_buscar": [_aba(1, fixada=True), _aba(2)], "aba_fechar": {}})
        atalhos.fechar_abas("x")
        self.assertEqual(falsa.comandos("aba_fechar"), [{"ids": [2]}])

    def test_fechar_duplicadas_usa_o_filtro_da_extensao(self):
        falsa = self.instalar(respostas={"abas_buscar": [_aba(7)], "aba_fechar": {}})
        atalhos.fechar_abas(duplicadas=True)
        self.assertTrue(falsa.comandos("abas_buscar")[0]["duplicadas"])

    def test_fechar_sem_criterio_pergunta_quais(self):
        self.instalar()
        with self.assertRaises(ErroNavegador):
            atalhos.fechar_abas()

    def test_agrupar_so_abas_da_mesma_janela(self):
        falsa = self.instalar(respostas={
            "abas_buscar": [_aba(1, janela=1), _aba(2, janela=2), _aba(3, janela=1)], "abas_agrupar": {}})
        atalhos.agrupar_abas("doc", "Trabalho")
        self.assertEqual(falsa.comandos("abas_agrupar"), [{"ids": [1, 3], "titulo": "Trabalho"}])


class MusicaTests(UsaPonteFalsa):
    def abas(self):
        return [_aba(1, "Spotify", "https://open.spotify.com/", audivel=False),
                _aba(2, "YT Music", "https://music.youtube.com/watch?v=x", audivel=True),
                _aba(3, "Outro", "https://exemplo.com")]

    def test_controla_o_player_que_esta_tocando_mesmo_em_outra_aba(self):
        falsa = self.instalar(respostas={"abas_listar": self.abas(), "clicar_seletor": {}})
        atalhos.musica_controle("proximo")
        chamada = falsa.comandos("clicar_seletor")[0]
        self.assertEqual(chamada["aba"], 2)
        self.assertEqual(chamada["seletor"], ".next-button")

    def test_servico_explicito(self):
        falsa = self.instalar(respostas={"abas_listar": self.abas(), "clicar_seletor": {}})
        atalhos.musica_controle("alternar", "spotify")
        self.assertEqual(falsa.comandos("clicar_seletor")[0]["aba"], 1)

    def test_sem_player_aberto(self):
        self.instalar(respostas={"abas_listar": [_aba(3)]})
        with self.assertRaises(ErroNavegador):
            atalhos.musica_tocando()

    def test_musica_tocando_le_titulo_e_artista(self):
        def consultar(args):
            texto = "Boa Musica" if "title" in args["seletor"] or "title" in args["seletor"] else "Banda"
            return {"itens": [{"texto": "Boa Musica" if "ytmusic-player-bar .title" == args["seletor"] else "Banda",
                               "href": "", "classes": ""}]}
        self.instalar(respostas={"abas_listar": self.abas(), "consultar": consultar})
        fala = atalhos.musica_tocando()
        self.assertEqual(fala, "Tocando Boa Musica, de Banda, no YouTube Music.")


class HistoricoFavoritosTests(UsaPonteFalsa):
    def test_busca_guarda_lista_e_abre_o_segundo_em_nova_aba(self):
        falsa = self.instalar(respostas={
            "historico_buscar": [{"titulo": "Pao A", "url": "https://a.com"},
                                 {"titulo": "Pao B", "url": "https://b.com"}],
            "abas_listar": [_aba(1, url="https://www.youtube.com/", ativa=True)],
            "abrir_url": {}})
        fala = atalhos.historico_buscar("pao", dias=7)
        self.assertEqual(falsa.comandos("historico_buscar")[0]["dias"], 7)
        self.assertIn("1, Pao A", fala)
        atalhos.abrir_resultado(2)          # mesmo com o YouTube na frente, a lista recente vale
        abertura = falsa.comandos("abrir_url")[-1]
        self.assertEqual(abertura["url"], "https://b.com")
        self.assertTrue(abertura["nova_aba"])

    def test_sem_resultado(self):
        self.instalar(respostas={"historico_buscar": []})
        self.assertIn("Nao achei", atalhos.historico_buscar("xyz"))

    def test_favoritos_e_salvar(self):
        falsa = self.instalar(respostas={
            "favoritos_buscar": [{"titulo": "Receitas", "url": "https://r.com"}],
            "favorito_criar": {"titulo": "Pagina X", "url": "https://x.com"}})
        self.assertIn("Receitas", atalhos.favoritos_buscar("receita"))
        self.assertIn("Pagina X", atalhos.favorito_salvar())


class YouTubeEmSegundoPlanoTests(UsaPonteFalsa):
    def test_player_age_na_aba_do_youtube_que_toca_som(self):
        falsa = self.instalar(respostas={
            "abas_listar": [_aba(1, url="https://exemplo.com", ativa=True),
                            _aba(2, url="https://www.youtube.com/watch?v=a", audivel=True),
                            _aba(3, url="https://music.youtube.com/")],
            "video": {}})
        atalhos.youtube_player("pausa")
        self.assertEqual(falsa.comandos("video"), [{"acao": "pausa", "aba": 2}])

    def test_sem_aba_do_youtube(self):
        self.instalar(respostas={"abas_listar": [_aba(1, url="https://exemplo.com", ativa=True)]})
        with self.assertRaises(ErroNavegador):
            atalhos.youtube_player("pausa")


class DiagnosticoTests(UsaPonteFalsa):
    def test_youtube_sem_videos_aponta_seletor(self):
        self.instalar(respostas={
            "ping": {"versao": "1.1.0"},
            "abas_listar": [_aba(1, url="https://www.youtube.com/results?q=x", ativa=True)],
            "consultar": {"itens": []}})
        fala = atalhos.diagnostico()
        self.assertIn("1.1.0", fala)
        self.assertIn("Videos encontrados: 0", fala)
        self.assertIn("seletor do YouTube pode ter mudado", fala)

    def test_spotify_lista_botoes_ausentes(self):
        def consultar(args):
            achou = "playpause" in args["seletor"]
            return {"itens": [{"texto": "", "href": "", "classes": ""}] if achou else []}
        self.instalar(respostas={
            "ping": {"versao": "1.1.0"},
            "abas_listar": [_aba(1, url="https://open.spotify.com/", ativa=True)],
            "consultar": consultar})
        fala = atalhos.diagnostico()
        self.assertIn("proximo", fala)
        self.assertIn("anterior", fala)
        self.assertNotIn("alternar", fala.split("botoes:")[1])

    def test_site_sem_atalho(self):
        self.instalar(respostas={
            "ping": {"versao": "1"}, "abas_listar": [_aba(1, ativa=True)]})
        self.assertIn("modo generico", atalhos.diagnostico())


class AtalhosLocaisTests(unittest.TestCase):
    """Frases resolvidas em jarvis._atalho_navegador, sem chamar a IA."""

    def rodar(self, frase):
        import jarvis
        from unittest.mock import patch
        chamadas = []
        with patch.object(jarvis, "executar_acao",
                          lambda nome, params=None: chamadas.append((nome, params))):
            tratou = jarvis._atalho_navegador(frase, jarvis.normalizar(frase))
        return tratou, chamadas

    def test_abre_o_segundo_video(self):
        tratou, chamadas = self.rodar("abre o segundo video")
        self.assertTrue(tratou)
        self.assertEqual(chamadas, [("resultado_abrir", {"posicao": 2})])

    def test_abre_o_terceiro_em_outra_aba(self):
        _, chamadas = self.rodar("abre o terceiro em outra aba")
        self.assertEqual(chamadas, [("resultado_abrir", {"posicao": 3, "nova_aba": True})])

    def test_segundo_plano_e_numero(self):
        _, chamadas = self.rodar("abre o 4 resultado em segundo plano")
        self.assertEqual(chamadas[0][1], {"posicao": 4, "segundo_plano": True})

    def test_pesquisa_e_abre_o_primeiro_numa_frase(self):
        _, chamadas = self.rodar("pesquisa lofi no youtube e abre o primeiro")
        self.assertEqual(chamadas, [
            ("youtube_pesquisar", {"termo": "lofi"}),
            ("resultado_abrir", {"posicao": 1, "nova_aba": False})])

    def test_pesquisa_preserva_acentos_do_termo(self):
        _, chamadas = self.rodar("pesquisa receita de pão no google")
        self.assertEqual(chamadas, [("google_pesquisar", {"termo": "receita de pão"})])

    def test_abrir_varios(self):
        _, chamadas = self.rodar("abre os 3 primeiros videos")
        self.assertEqual(chamadas, [("youtube_abrir_varios", {"quantidade": 3})])

    def test_player(self):
        self.assertEqual(self.rodar("velocidade 1,5")[1],
                         [("youtube_player", {"controle": "velocidade", "valor": "1.5"})])
        self.assertEqual(self.rodar("pula o anúncio")[1],
                         [("youtube_player", {"controle": "pular_anuncio"})])
        self.assertEqual(self.rodar("ativa as legendas")[1],
                         [("youtube_player", {"controle": "legendas"})])

    def test_emails(self):
        self.assertEqual(self.rodar("quantos e-mails não lidos eu tenho")[1],
                         [("gmail_nao_lidos", None)])
        self.assertEqual(self.rodar("lê os 3 primeiros e-mails")[1],
                         [("gmail_listar", {"quantidade": 3})])
        self.assertEqual(self.rodar("abre o primeiro e-mail")[1],
                         [("gmail_abrir", {"posicao": 1})])

    def test_abas(self):
        self.assertEqual(self.rodar("silencia a aba do youtube")[1],
                         [("aba_silenciar", {"silenciar": True, "alvo": "youtube"})])
        self.assertEqual(self.rodar("silencia a aba")[1], [("aba_silenciar", {"silenciar": True})])
        self.assertEqual(self.rodar("religa o som da aba do spotify")[1],
                         [("aba_silenciar", {"silenciar": False, "alvo": "spotify"})])
        self.assertEqual(self.rodar("qual aba está tocando")[1], [("abas_som", None)])
        self.assertEqual(self.rodar("fecha as abas duplicadas")[1],
                         [("abas_fechar", {"duplicadas": True})])
        self.assertEqual(self.rodar("fecha todas as abas do youtube")[1],
                         [("abas_fechar", {"texto": "youtube"})])
        self.assertEqual(self.rodar("reabre a última aba")[1], [("aba_reabrir", None)])
        self.assertEqual(self.rodar("fixa essa aba")[1], [("aba_fixar", {"fixar": True})])
        self.assertEqual(self.rodar("desfixa essa aba")[1], [("aba_fixar", {"fixar": False})])

    def test_musica_favoritos_historico_diagnostico(self):
        self.assertEqual(self.rodar("o que está tocando")[1], [("musica_tocando", None)])
        self.assertEqual(self.rodar("salva essa página nos favoritos")[1], [("favorito_salvar", None)])
        self.assertEqual(self.rodar("procura no histórico receita de pão")[1],
                         [("historico_buscar", {"termo": "receita de pão"})])
        self.assertEqual(self.rodar("busca nos favoritos github")[1],
                         [("favoritos_buscar", {"termo": "github"})])
        self.assertEqual(self.rodar("faz o diagnóstico do navegador")[1], [("navegador_diagnostico", None)])

    def test_nao_rouba_frases_comuns(self):
        for frase in ("abre o youtube", "abrir calculadora", "pesquisar legendas de filme",
                      "que horas são", "qual a velocidade do vento", "silenciar o computador",
                      "fecha o programa", "salva o arquivo", "o que é um favorito"):
            self.assertFalse(self.rodar(frase)[0], frase)


class CatalogoTests(unittest.TestCase):
    def test_acoes_do_navegador_estao_no_catalogo(self):
        import acoes
        for nome in ("youtube_abrir_resultado", "youtube_player", "gmail_listar",
                     "navegador_tarefa", "navegador_status"):
            self.assertTrue(acoes.existe(nome), nome)
        # nenhuma acao do navegador pode ser enviada ao Gemini sem descricao
        self.assertIn("youtube_abrir_resultado", acoes.listar_para_ia())

    def test_erro_do_navegador_vira_fala_e_nao_excecao(self):
        import acoes
        anterior = navegador._ponte
        self.addCleanup(navegador.definir_ponte, anterior)
        navegador.definir_ponte(PonteFalsa(conectada=False))
        ok, fala = acoes.executar("aba_listar", {}, ctx=None)
        self.assertTrue(ok)
        self.assertIn("nao esta conectada", fala)


if __name__ == "__main__":
    unittest.main()
