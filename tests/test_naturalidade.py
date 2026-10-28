import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import acoes
import cache_planos
import cerebro
import jarvis
import linguagem
import tempos


class EnchimentoTests(unittest.TestCase):
    def test_remove_cortesia_e_pedidos(self):
        casos = {
            "Jarvis, por favor, pode abrir o segundo video pra mim?": "abrir o segundo video",
            "dá pra pesquisar lofi no youtube aí": "pesquisar lofi no youtube",
            "Quero que você abra o terceiro em outra aba": "abra o terceiro em outra aba",
            "me abre o primeiro agora": "abre o primeiro",
            "Poderia me mostrar o último resultado, por favor?": "mostrar o último resultado",
            "vamos abrir o segundo": "abrir o segundo",
            "faz o favor de pausar": "pausar",
        }
        for entrada, esperado in casos.items():
            self.assertEqual(linguagem.tirar_enchimento(entrada), esperado, entrada)

    def test_nao_mexe_em_pedido_sem_enchimento_e_preserva_acentos(self):
        self.assertEqual(linguagem.tirar_enchimento("abre o youtube"), "abre o youtube")
        self.assertEqual(linguagem.tirar_enchimento("pesquisa receita de pão no google"),
                         "pesquisa receita de pão no google")


class FalaNaturalNavegadorTests(unittest.TestCase):
    def rodar(self, frase):
        chamadas = []
        with patch.object(jarvis, "executar_acao",
                          lambda nome, params=None: chamadas.append((nome, params))):
            tratou = jarvis._atalho_navegador(frase, jarvis.normalizar(frase))
        return tratou, chamadas

    def test_cortesia_nao_atrapalha(self):
        for frase in ("por favor, abre o segundo video",
                      "Jarvis, pode abrir o segundo vídeo pra mim?",
                      "dá pra abrir o segundo video ai",
                      "quero que você abra o segundo vídeo"):
            self.assertEqual(self.rodar(frase)[1], [("resultado_abrir", {"posicao": 2})], frase)

    def test_sinonimos_de_abrir(self):
        for frase in ("bota o segundo video", "mostra o segundo resultado", "toca o segundo video",
                      "quero ver o segundo video", "vai pro segundo video", "coloca o segundo"):
            self.assertEqual(self.rodar(frase)[1], [("resultado_abrir", {"posicao": 2})], frase)

    def test_posicoes_alternativas(self):
        self.assertEqual(self.rodar("abre o último vídeo")[1], [("resultado_abrir", {"posicao": -1})])
        self.assertEqual(self.rodar("abre o numero tres")[1], [("resultado_abrir", {"posicao": 3})])
        self.assertEqual(self.rodar("mostra o de cima")[1], [("resultado_abrir", {"posicao": 1})])
        self.assertEqual(self.rodar("abre o 2 resultado")[1], [("resultado_abrir", {"posicao": 2})])

    def test_aba_nova_e_segundo_plano_em_outras_palavras(self):
        self.assertEqual(self.rodar("abre o segundo video ao lado")[1],
                         [("resultado_abrir", {"posicao": 2, "nova_aba": True})])
        self.assertEqual(self.rodar("abre o segundo nessa aba")[1],
                         [("resultado_abrir", {"posicao": 2, "nova_aba": False})])
        self.assertEqual(self.rodar("abre o terceiro sem sair daqui")[1],
                         [("resultado_abrir", {"posicao": 3, "segundo_plano": True})])

    def test_pesquisa_com_sinonimos_de_site_e_cortesia(self):
        esperado = [("youtube_pesquisar", {"termo": "lofi"})]
        for frase in ("pesquisa lofi no yt", "Jarvis, me mostra lofi no you tube",
                      "pode procurar lofi pelo youtube pra mim", "acha lofi no youtube"):
            self.assertEqual(self.rodar(frase)[1], esperado, frase)
        self.assertEqual(self.rodar("busca receita de pão no google")[1],
                         [("google_pesquisar", {"termo": "receita de pão"})])

    def test_abrir_varios_com_palavras(self):
        self.assertEqual(self.rodar("abre os dois primeiros videos")[1],
                         [("youtube_abrir_varios", {"quantidade": 2})])
        self.assertEqual(self.rodar("abre os 4 primeiros")[1],
                         [("youtube_abrir_varios", {"quantidade": 4})])

    def test_emails_novos(self):
        self.assertEqual(self.rodar("tenho e-mail novo?")[1], [("gmail_nao_lidos", None)])

    def test_nao_rouba_pedidos_comuns(self):
        for frase in ("abre um site novo", "abre o youtube", "toca uma musica", "mostra as horas",
                      "abre o bloco de notas", "coloca uma musica do queen"):
            self.assertFalse(self.rodar(frase)[0], frase)


class CachePlanosTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.caminho = Path(self.pasta.name) / "cache.json"
        self.catalogo = {"a": {"risco": False}, "perigo": {"risco": True}}
        self.plano = {"fala": "Feito.", "passos": [{"acao": "a", "params": {"x": 1}}]}

    def cache(self, assinatura="v1"):
        return cache_planos.CachePlanos(self.caminho, assinatura)

    def test_chave_ignora_acentos_caixa_e_enchimento(self):
        self.assertEqual(cache_planos.chave("Jarvis, por favor, aumenta o VOLUME pra mim!"),
                         cache_planos.chave("aumenta o volume"))
        self.assertEqual(cache_planos.chave("Abrí o Pão"), cache_planos.chave("abri o pao"))

    def test_guarda_obtem_e_persiste_em_disco(self):
        c = self.cache()
        c.guardar("liga a luz da sala", self.plano)
        self.assertEqual(c.obter("Liga a luz da sala, por favor"), self.plano)
        self.assertEqual(self.cache().obter("liga a luz da sala"), self.plano)    # outro processo

    def test_catalogo_alterado_descarta_o_cache(self):
        self.cache("v1").guardar("liga a luz", self.plano)
        self.assertIsNone(self.cache("v2").obter("liga a luz"))

    def test_esquecer_e_limpar(self):
        c = self.cache()
        c.guardar("a b", self.plano)
        c.guardar("c d", self.plano)
        self.assertTrue(c.esquecer("a b"))
        self.assertFalse(c.esquecer("a b"))
        self.assertEqual(c.limpar(), 1)
        self.assertEqual(c.total(), 0)

    def test_obter_devolve_copia(self):
        c = self.cache()
        c.guardar("liga a luz", self.plano)
        c.obter("liga a luz")["passos"].clear()
        self.assertEqual(len(c.obter("liga a luz")["passos"]), 1)

    def test_regras_do_que_pode_ser_guardado(self):
        ok = cache_planos.cacheavel
        self.assertTrue(ok("liga a luz da sala", self.plano, self.catalogo))
        self.assertFalse(ok("conversa", {"fala": "oi", "passos": []}, self.catalogo))            # so papo
        self.assertFalse(ok("desliga", {"passos": [{"acao": "perigo"}]}, self.catalogo))          # risco
        self.assertFalse(ok("faz", {"passos": [{"acao": "nao_existe"}]}, self.catalogo))          # desconhecida
        self.assertFalse(ok("abre esse", self.plano, self.catalogo))                              # contexto
        self.assertFalse(ok("toca de novo", self.plano, self.catalogo))
        self.assertFalse(ok("x " * 80, self.plano, self.catalogo))                                # longa

    def test_limite_de_entradas_descarta_a_menos_usada(self):
        with patch.object(cache_planos, "MAX_ENTRADAS", 2):
            c = self.cache()
            c.guardar("um", self.plano)
            time.sleep(0.01)
            c.guardar("dois", self.plano)
            time.sleep(0.01)
            c.obter("um")                                  # "um" fica recente
            c.guardar("tres", self.plano)
        self.assertIsNotNone(c.obter("um"))
        self.assertIsNone(c.obter("dois"))


class ProcessarComIaTests(unittest.TestCase):
    """O caminho Gemini -> cache -> execucao, sem rede e sem falar."""

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.cache = cache_planos.CachePlanos(Path(self.pasta.name) / "c.json", acoes.assinatura())
        anterior = jarvis._cache_planos
        self.addCleanup(setattr, jarvis, "_cache_planos", anterior)
        jarvis._cache_planos = self.cache
        self.plano = {"fala": "Pronto.", "passos": [{"acao": "volume", "params": {"percentual": 30}}],
                      "_modelo": "m"}
        self.chamadas = []

    def rodar(self, frase, resultado_acao=(True, "ok")):
        with ExitStack() as pilha:
            for p in (
                patch.object(jarvis, "USAR_IA", True),
                patch.object(jarvis.cerebro, "disponivel", return_value=True),
                patch.object(jarvis.cerebro, "interpretar",
                             side_effect=lambda *a, **k: self.chamadas.append((a, k)) or dict(self.plano)),
                patch.object(jarvis, "executar_acao", return_value=resultado_acao),
                patch.object(jarvis, "falar"),
                patch.object(jarvis, "_lembrar"),
            ):
                pilha.enter_context(p)
            return jarvis.processar_com_ia(frase)

    def test_segunda_vez_sai_do_cache_sem_chamar_o_gemini(self):
        self.assertTrue(self.rodar("deixa o som em trinta por cento"))
        self.assertEqual(len(self.chamadas), 1)
        self.assertTrue(self.rodar("Jarvis, deixa o som em trinta por cento, por favor"))
        self.assertEqual(len(self.chamadas), 1)            # nao chamou de novo

    def test_plano_que_falhou_nao_e_guardado(self):
        self.rodar("faz uma coisa", resultado_acao=(False, None))
        self.assertEqual(self.cache.total(), 0)

    def test_plano_do_cache_que_falha_e_esquecido(self):
        self.cache.guardar("deixa o som baixo", self.plano)
        self.rodar("deixa o som baixo", resultado_acao=(False, None))
        self.assertEqual(self.chamadas, [])                # usou o cache...
        self.assertEqual(self.cache.total(), 0)            # ...e o esqueceu por ter falhado

    def test_frase_dependente_de_contexto_nao_e_guardada(self):
        self.rodar("faz isso de novo")
        self.assertEqual(self.cache.total(), 0)

    def test_catalogo_reduzido_quando_a_frase_nao_e_de_navegador(self):
        with patch.object(jarvis, "_ultimo_uso_navegador", 0.0):
            self.rodar("aumenta o volume do computador")
        catalogo, kwargs = self.chamadas[0][0][1], self.chamadas[0][1]
        self.assertNotIn("youtube_abrir_resultado", catalogo)
        self.assertIn("volume", catalogo)
        self.assertFalse(kwargs["navegador"])

    def test_catalogo_completo_quando_fala_de_navegador(self):
        with patch.object(jarvis, "_ultimo_uso_navegador", 0.0):
            self.rodar("fecha as abas do youtube")
        catalogo, kwargs = self.chamadas[0][0][1], self.chamadas[0][1]
        self.assertIn("youtube_abrir_resultado", catalogo)
        self.assertTrue(kwargs["navegador"])

    def test_catalogo_completo_logo_apos_usar_o_navegador(self):
        with patch.object(jarvis, "_ultimo_uso_navegador", time.monotonic()):
            self.rodar("e o outro?")
        self.assertIn("youtube_abrir_resultado", self.chamadas[0][0][1])


class PromptTests(unittest.TestCase):
    def test_parte_fixa_e_identica_entre_chamadas(self):
        catalogo = acoes.listar_para_ia()
        fixa = cerebro._parte_fixa(catalogo, True)
        for contexto in ("", "usuario: oi | jarvis: ola"):
            self.assertTrue(cerebro.montar_prompt(catalogo, contexto).startswith(fixa))
        self.assertNotIn("Data e hora", fixa)       # hora so no fim: nao quebra o cache de prefixo

    def test_regra_do_navegador_so_quando_pedida(self):
        self.assertIn("NAVEGADOR", cerebro.montar_prompt("x", "", True))
        self.assertNotIn("NAVEGADOR", cerebro.montar_prompt("x", "", False))
        self.assertIn("10. Responda SOMENTE", cerebro.montar_prompt("x", "", False))

    def test_catalogo_reduzido_e_bem_menor(self):
        self.assertLess(len(acoes.listar_para_ia({"geral"})), len(acoes.listar_para_ia()) * 0.4)


class TemposTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.arquivo = Path(self.pasta.name) / "t.jsonl"

    def test_registra_caminho_e_etapas(self):
        tempos.iniciar("abre o segundo video")
        tempos.caminho("atalho")
        with tempos.medir("acao"):
            time.sleep(0.01)
        registro = tempos.finalizar(self.arquivo)
        self.assertEqual(registro["caminho"], "atalho")
        self.assertGreaterEqual(registro["etapas"]["acao"], 10)
        self.assertEqual(tempos.ler(arquivo=self.arquivo)[0]["frase"], "abre o segundo video")

    def test_caminho_ia_e_deduzido_da_etapa(self):
        tempos.iniciar("x")
        with tempos.medir("ia"):
            pass
        self.assertEqual(tempos.finalizar(self.arquivo)["caminho"], "ia")

    def test_sem_comando_em_andamento_tudo_e_no_op(self):
        with tempos.medir("acao"):
            pass
        tempos.caminho("cache")
        self.assertIsNone(tempos.finalizar(self.arquivo))

    def test_resumo(self):
        for caminho, ms in (("atalho", 100), ("atalho", 300), ("ia", 2000)):
            tempos._gravar({"ts": 1, "frase": "x", "caminho": caminho, "total_ms": ms,
                            "etapas": {"ia": ms} if caminho == "ia" else {}}, self.arquivo)
        texto = tempos.resumo(arquivo=self.arquivo)
        self.assertIn("atalho: 2x, mediana 200 ms", texto)
        self.assertIn("ia: 1x, mediana 2000 ms (ia 2000 ms)", texto)
        self.assertIn("Ainda nao ha medicoes", tempos.resumo(arquivo=Path(self.pasta.name) / "nada"))

    def test_processar_grava_uma_linha_por_comando(self):
        with patch.object(tempos, "ARQUIVO", self.arquivo), \
                patch.object(jarvis, "_processar", return_value=True):
            self.assertTrue(jarvis.processar("que horas sao"))
        linhas = tempos.ler(arquivo=self.arquivo)
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["caminho"], "regra")


if __name__ == "__main__":
    unittest.main()
