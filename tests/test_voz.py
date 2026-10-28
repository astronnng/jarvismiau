import _ambiente  # noqa: F401  (isola os dados do usuario; deve ser o primeiro import)
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    import numpy as np
except ImportError:                      # o Kokoro e opcional: sem numpy, so os testes de config rodam
    np = None

import cli
import jarvis
import voz
from voz import comandos, config, instalar
from voz.comandos import ContextoVoz
from voz.kokoro_motor import MotorKokoro, aplicar_pronuncias, dividir_frases


class ConfigIsolada(unittest.TestCase):
    """voz.json de teste em pasta temporaria: nunca toca no do usuario."""

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.arquivo = Path(self.pasta.name) / "voz.json"
        patcher = patch.object(config, "ARQUIVO", self.arquivo)
        patcher.start()
        self.addCleanup(patcher.stop)


class ConfigTests(ConfigIsolada):
    def test_padroes_pedidos(self):
        cfg = config.carregar()
        self.assertEqual(cfg["motor"], "padrao")            # Kokoro e opcional: comeca desligado
        self.assertEqual(cfg["kokoro"]["mistura"],
                         [{"voz": "bm_daniel", "peso": 0.5}, {"voz": "am_michael", "peso": 0.4},
                          {"voz": "pm_alex", "peso": 0.3}])
        self.assertEqual(cfg["kokoro"]["idioma"], "pt-br")
        self.assertEqual(cfg["kokoro"]["velocidade"], 1.0)

    def test_pesos_sao_normalizados(self):
        normal = config.mistura_normalizada(config.carregar()["kokoro"]["mistura"])
        self.assertAlmostEqual(normal[0][1], 0.5 / 1.2)
        self.assertAlmostEqual(sum(f for _, f in normal), 1.0)
        self.assertEqual(config.resumo_mistura(config.carregar()["kokoro"]["mistura"]),
                         "bm_daniel 42% + am_michael 33% + pm_alex 25%")

    def test_idioma_nunca_fica_automatico(self):
        for ruim in ("", None, "auto", "automatico", "  "):
            self.arquivo.write_text(json.dumps({"kokoro": {"idioma": ruim}}), encoding="utf-8")
            config._cache.update(mtime=None, cfg=None, arquivo=None)
            self.assertEqual(config.carregar()["kokoro"]["idioma"], "pt-br", repr(ruim))
        for ruim in ("auto", "", "portugues do brasil"):
            with self.assertRaises(ValueError):
                config.validar_idioma(ruim)
        self.assertEqual(config.validar_idioma("PT-BR"), "pt-br")

    def test_interpretar_mistura(self):
        esperado = [{"voz": "bm_daniel", "peso": 0.5}, {"voz": "am_michael", "peso": 0.4}]
        for texto in ("bm_daniel=0.5 am_michael=0.4", "bm_daniel:0,5 am_michael:0,4",
                      "bm_daniel 0.5 am_michael 0.4"):
            self.assertEqual(config.interpretar_mistura(texto), esperado, texto)
        self.assertEqual(config.interpretar_mistura("pm_alex"), [{"voz": "pm_alex", "peso": 1.0}])

    def test_mistura_invalida(self):
        for texto in ("", "voz qualquer", "bm_daniel=0 am_michael=1", "bm_daniel=1 bm_daniel=2",
                      "af_bella=1 af_heart=1 bm_george=1 pf_dora=1"):
            with self.assertRaises(ValueError, msg=texto):
                config.interpretar_mistura(texto)

    def test_velocidade(self):
        self.assertEqual(config.validar_velocidade("1,25"), 1.25)
        for ruim in ("0.1", "3", "rapido"):
            with self.assertRaises(ValueError):
                config.validar_velocidade(ruim)

    def test_salvar_e_mesclar_com_padroes(self):
        config.atualizar(lambda c: c.update(motor="kokoro"))
        self.arquivo.write_text(json.dumps({"motor": "kokoro", "kokoro": {"velocidade": 1.2}}), encoding="utf-8")
        config._cache.update(mtime=None, cfg=None, arquivo=None)
        cfg = config.carregar()
        self.assertEqual(cfg["kokoro"]["velocidade"], 1.2)
        self.assertEqual(cfg["kokoro"]["idioma"], "pt-br")      # o que falta vem do padrao

    def test_arquivo_corrompido_volta_ao_padrao(self):
        self.arquivo.write_text("{ isso nao e json", encoding="utf-8")
        self.assertEqual(config.carregar()["motor"], "padrao")


class FraseTests(unittest.TestCase):
    def test_dividir_frases_junta_fragmentos_curtos(self):
        self.assertEqual(dividir_frases("Sim. Entendido, senhor. Vou providenciar isso agora mesmo."),
                         ["Sim. Entendido, senhor.", "Vou providenciar isso agora mesmo."])
        self.assertEqual(dividir_frases("Ola."), ["Ola."])
        self.assertEqual(dividir_frases("   "), [])

    def test_pronuncias_preservam_caixa_e_palavras_inteiras(self):
        mapa = {"nao": "não", "sao": "são"}
        self.assertEqual(aplicar_pronuncias("Nao sei. Sao Paulo, nacao.", mapa), "Não sei. São Paulo, nacao.")
        self.assertEqual(aplicar_pronuncias("texto", {}), "texto")


@unittest.skipIf(np is None, "numpy nao instalado (Kokoro e opcional)")
class MotorTests(ConfigIsolada):
    def setUp(self):
        super().setUp()
        base = Path(self.pasta.name)
        self.vozes_arq = base / "vozes.npz"
        np.savez(self.vozes_arq,
                 bm_daniel=np.full((510, 1, 256), 1.0, np.float32),
                 am_michael=np.full((510, 1, 256), 3.0, np.float32),
                 pf_dora=np.full((510, 1, 256), 5.0, np.float32),
                 pm_alex=np.full((510, 1, 256), 7.0, np.float32))
        self.modelo = base / "modelo.onnx"
        self.modelo.write_bytes(b"x")
        self.criacoes = []
        self.chamadas = []

        class Falso:
            tokenizer = SimpleNamespace(phonemize=lambda t, lang: (_ for _ in ()).throw(RuntimeError("x"))
                                        if lang == "xx-yy" else "ok")

            def get_voices(inner):
                return ["am_michael", "bm_daniel", "pf_dora", "pm_alex"]

            def get_voice_style(inner, nome):
                return np.load(self.vozes_arq)[nome]

            def create(inner, text, voice, speed, lang):
                self.chamadas.append({"text": text, "voice": voice, "speed": speed, "lang": lang})
                return np.full(2400, 0.2, np.float32), 24000

        def fabrica(modelo, vozes):
            self.criacoes.append((modelo, vozes))
            return Falso()

        self.motor = MotorKokoro(fabrica=fabrica, pasta_cache=base / "cache", modelo=self.modelo,
                                 vozes=self.vozes_arq)
        self.tocados = []

    def tocar(self, caminho):
        self.tocados.append(caminho)
        return True

    def ativar(self, **kokoro):
        config.atualizar(lambda c: (c.update(motor="kokoro"), c["kokoro"].update(kokoro)))

    def test_motor_padrao_nao_fala_e_nem_carrega_o_modelo(self):
        self.assertFalse(self.motor.falar("Ola, senhor.", self.tocar))
        self.assertEqual(self.criacoes, [])
        self.assertEqual(self.tocados, [])

    def test_fala_com_a_mistura_o_idioma_e_a_velocidade_configurados(self):
        self.ativar()
        self.assertTrue(self.motor.falar("Todos os sistemas estão online.", self.tocar))
        chamada = self.chamadas[0]
        self.assertEqual(chamada["lang"], "pt-br")                      # explicito, nunca en-us
        self.assertEqual(chamada["speed"], 1.0)
        esperado = (0.5 * 1.0 + 0.4 * 3.0 + 0.3 * 7.0) / 1.2             # soma ponderada normalizada
        self.assertTrue(np.allclose(chamada["voice"], esperado))
        self.assertEqual(len(self.tocados), 1)
        self.assertTrue(self.tocados[0].endswith(".wav"))

    def test_idioma_e_velocidade_alterados_chegam_ao_modelo(self):
        self.ativar(idioma="en-gb", velocidade=1.3)
        self.motor.falar("Good evening, sir.", self.tocar)
        self.assertEqual((self.chamadas[0]["lang"], self.chamadas[0]["speed"]), ("en-gb", 1.3))

    def test_voz_unica_vai_pelo_nome(self):
        self.ativar(mistura=[{"voz": "pf_dora", "peso": 1.0}])
        self.motor.falar("Ola, senhor, tudo bem por aqui.", self.tocar)
        self.assertEqual(self.chamadas[0]["voice"], "pf_dora")

    def test_segunda_vez_sai_do_cache_sem_sintetizar(self):
        self.ativar()
        self.motor.falar("Todos os sistemas estão online.", self.tocar)
        self.motor.falar("Todos os sistemas estão online.", self.tocar)
        self.assertEqual(len(self.chamadas), 1)
        self.assertEqual(len(self.tocados), 2)

    def test_mudar_a_voz_invalida_o_cache(self):
        self.ativar()
        self.motor.falar("Todos os sistemas estão online.", self.tocar)
        self.ativar(velocidade=1.1)
        self.motor.falar("Todos os sistemas estão online.", self.tocar)
        self.assertEqual(len(self.chamadas), 2)

    def test_pronuncias_so_em_portugues(self):
        self.ativar()
        self.motor.falar("Nao tenho como saber isso, senhor.", self.tocar)
        self.assertTrue(self.chamadas[0]["text"].startswith("Não tenho"))
        self.ativar(idioma="en-us")
        self.motor.falar("Nao e uma palavra inglesa, sir.", self.tocar)
        self.assertTrue(self.chamadas[1]["text"].startswith("Nao e"))

    def test_voz_inexistente_cai_para_a_cadeia_de_sempre(self):
        self.ativar(mistura=[{"voz": "xx_nada", "peso": 1.0}])
        self.assertFalse(self.motor.falar("Ola, senhor, tudo bem por aqui.", self.tocar))
        self.assertIn("nao existe", self.motor.ultimo_erro)

    def test_varias_frases_tocam_em_ordem(self):
        self.ativar()
        self.assertTrue(self.motor.falar(
            "Primeira frase bem comprida para passar o minimo. Segunda frase tambem comprida e clara.",
            self.tocar))
        self.assertEqual([c["text"][:7] for c in self.chamadas], ["Primeir", "Segunda"])
        self.assertEqual(len(self.tocados), 2)

    def test_falha_na_segunda_frase_nao_repete_a_primeira(self):
        self.ativar()
        original = self.motor.gerar

        def gerar(texto, kcfg):
            if texto.startswith("Segunda"):
                raise RuntimeError("boom")
            return original(texto, kcfg)

        with patch.object(self.motor, "gerar", gerar):
            ok = self.motor.falar(
                "Primeira frase bem comprida para passar o minimo. Segunda frase tambem comprida e clara.",
                self.tocar)
        self.assertTrue(ok)                                    # ja falou algo: nao dispara o fallback
        self.assertEqual(len(self.tocados), 1)

    def test_falha_na_primeira_devolve_false(self):
        self.ativar()
        with patch.object(self.motor, "gerar", side_effect=RuntimeError("boom")):
            self.assertFalse(self.motor.falar("Uma frase qualquer comprida o bastante.", self.tocar))
        self.assertEqual(self.motor.ultimo_erro, "boom")

    def test_player_que_falha_devolve_false(self):
        self.ativar()
        self.assertFalse(self.motor.falar("Uma frase qualquer comprida o bastante.", lambda c: False))

    def test_modelo_ausente_nao_quebra(self):
        motor = MotorKokoro(fabrica=lambda *a: None, modelo=Path(self.pasta.name) / "nao_existe.onnx",
                            vozes=self.vozes_arq, pasta_cache=Path(self.pasta.name) / "c2")
        self.ativar()
        ok, motivo = motor.disponivel()
        self.assertFalse(ok)
        self.assertIn("/voz kokoro instalar", motivo)
        self.assertFalse(motor.falar("Ola, senhor.", self.tocar))

    def test_falha_ao_carregar_o_modelo_e_registrada(self):
        motor = MotorKokoro(fabrica=lambda *a: (_ for _ in ()).throw(RuntimeError("arquivo corrompido")),
                            modelo=self.modelo, vozes=self.vozes_arq, pasta_cache=Path(self.pasta.name) / "c3")
        self.ativar()
        self.assertFalse(motor.falar("Uma frase qualquer comprida o bastante.", self.tocar))
        self.assertIn("corrompido", motor.ultimo_erro)

    def test_lista_vozes_do_arquivo_sem_carregar_o_modelo(self):
        self.assertEqual(self.motor.vozes(), ["am_michael", "bm_daniel", "pf_dora", "pm_alex"])
        self.assertEqual(self.criacoes, [])

    def test_preaquecer_gera_so_o_que_falta_e_respeita_a_troca_de_voz(self):
        self.ativar()
        self.assertEqual(self.motor.preaquecer(["Ola, senhor, tudo bem por aqui?", "Sistemas online, senhor."]), 2)
        n = len(self.chamadas)
        self.assertEqual(self.motor.preaquecer(["Ola, senhor, tudo bem por aqui?"]), 0)   # ja esta no cache
        self.assertEqual(len(self.chamadas), n + 1)                                       # so o aquecimento
        # cancelar interrompe
        self.assertEqual(self.motor.preaquecer(["Frase nova e comprida o bastante."], cancelar=lambda: True), 0)

    def test_preaquecer_desligado_ou_motor_padrao_nao_faz_nada(self):
        self.assertEqual(self.motor.preaquecer(["Ola, senhor."]), 0)
        self.ativar(preaquecer=False)
        self.assertEqual(self.motor.preaquecer(["Ola, senhor."]), 0)
        self.assertEqual(self.chamadas, [])

    def test_idioma_valido_pergunta_ao_espeak(self):
        self.assertTrue(self.motor.idioma_valido("pt-br"))
        self.assertFalse(self.motor.idioma_valido("xx-yy"))


@unittest.skipIf(np is None, "numpy nao instalado (Kokoro e opcional)")
class ComandosTests(MotorTests):
    def setUp(self):
        super().setUp()
        self.falas, self.perfil, self.preaquecimentos = [], ["BR_REMY"], []
        self.ctx = ContextoVoz(
            falar=self.falas.append,
            confirmar=lambda p: self.falas.append(p) or True,
            perfis=lambda: [("BR_ANTONIO", "edge"), ("BR_REMY", "edge"), ("WINDOWS", "sapi")],
            perfil_atual=lambda: self.perfil[0],
            aplicar_perfil=lambda nome: self.perfil.__setitem__(0, nome) or True,
            tocar_wav=lambda caminho: self.tocados.append(caminho) or True,
            preaquecer=lambda: self.preaquecimentos.append(1))

    def voz(self, texto):
        return comandos.executar(texto, self.ctx, self.motor)

    def test_status(self):
        texto = self.voz("")
        self.assertIn("Motor ativo: padrao", texto)
        self.assertIn("bm_daniel 42% + am_michael 33% + pm_alex 25%", texto)
        self.assertIn("pesos 0.5 / 0.4 / 0.3", texto)
        self.assertIn("pt-br (fixo", texto)
        self.assertNotIn("sotaque", texto)                    # o padrao ja tem uma voz nativa (pm_alex)
        self.voz("kokoro mistura bm_daniel=1 am_michael=1")
        self.assertIn("sotaque", self.voz(""))                # so vozes inglesas: avisa

    def test_usar_kokoro_e_voltar(self):
        self.assertIn("Kokoro ativado", self.voz("usar kokoro"))
        self.assertEqual(config.carregar()["motor"], "kokoro")
        self.assertEqual(self.preaquecimentos, [1])
        self.voz("usar padrao")
        self.assertEqual(config.carregar()["motor"], "padrao")

    def test_nao_ativa_se_o_kokoro_nao_esta_pronto(self):
        self.motor.modelo = Path(self.pasta.name) / "sumiu.onnx"
        self.assertIn("Não dá para ativar", self.voz("usar kokoro"))
        self.assertEqual(config.carregar()["motor"], "padrao")

    def test_padrao_lista_e_escolhe_perfil(self):
        self.assertIn("▸ BR_REMY", self.voz("padrao"))
        self.assertIn("BR_ANTONIO", self.voz("padrao br_antonio"))
        self.assertEqual(self.perfil[0], "BR_ANTONIO")
        self.assertEqual(config.carregar()["perfil_padrao"], "BR_ANTONIO")
        self.assertIn("Não existe", self.voz("padrao NAO_EXISTE"))

    def test_mistura(self):
        self.assertIn("bm_daniel 56% + am_michael 44%", self.voz("kokoro mistura bm_daniel=0.5 am_michael=0.4"))
        self.assertIn("pf_dora 60% + bm_daniel 40%", self.voz("kokoro mistura pf_dora=60 bm_daniel=40"))
        self.assertIn("diferentes", self.voz("kokoro mistura pf_dora=60 bm_daniel=40"))     # aviso de idiomas
        self.assertNotIn("diferentes", self.voz("kokoro mistura bm_daniel=1 am_michael=1"))  # ingles + ingles: ok
        self.assertIn("não encontrada", self.voz("kokoro mistura xx_nada=1"))
        self.assertIn("no maximo", self.voz("kokoro mistura af_bella=1 af_heart=1 bm_george=1 pf_dora=1"))
        self.assertTrue(self.preaquecimentos)

    def test_idioma_e_velocidade(self):
        self.assertIn("pt-br", self.voz("kokoro idioma pt-br"))
        self.assertIn("pronúncia estrangeira", self.voz("kokoro idioma en-us"))
        self.assertIn("não conhece", self.voz("kokoro idioma xx-yy"))
        self.assertEqual(config.carregar()["kokoro"]["idioma"], "en-us")
        self.assertIn("invalido", self.voz("kokoro idioma auto"))
        self.assertIn("Velocidade: 1.1", self.voz("kokoro velocidade 1.1"))
        self.assertIn("vai de 0.5 a 2.0", self.voz("kokoro velocidade 5"))

    def test_presets(self):
        self.assertIn("Nenhum preset", self.voz("kokoro preset lista"))
        self.voz("kokoro preset salvar jarvis")
        self.voz("kokoro mistura pf_dora=1")
        self.voz("kokoro velocidade 1.4")
        self.assertIn("bm_daniel 42%", self.voz("kokoro preset usar jarvis"))
        cfg = config.carregar()["kokoro"]
        self.assertEqual((cfg["velocidade"], cfg["idioma"]), (1.0, "pt-br"))
        self.assertIn("jarvis", self.voz("kokoro preset lista"))
        self.voz("kokoro preset apagar jarvis")
        self.assertIn("Não existe", self.voz("kokoro preset usar jarvis"))

    def test_pronuncias(self):
        self.assertIn("'nao' é lida como 'não'", self.voz("kokoro pronuncia nao=não") .replace("Agora ", ""))
        self.voz("kokoro pronuncia bariri=baríri")
        self.assertEqual(config.carregar()["kokoro"]["pronuncias"]["bariri"], "baríri")
        self.assertIn("removida", self.voz("kokoro pronuncia remover bariri"))
        self.assertNotIn("bariri", config.carregar()["kokoro"]["pronuncias"])

    def test_testar_toca_sem_ativar_e_mostra_se_veio_do_cache(self):
        texto = self.voz("kokoro testar Boa noite, senhor, tudo certo por aqui.")
        self.assertIn("gerado em", texto)
        self.assertEqual(len(self.tocados), 1)
        self.assertIn("do cache", self.voz("kokoro testar Boa noite, senhor, tudo certo por aqui."))
        self.assertEqual(config.carregar()["motor"], "padrao")          # testar nao ativa

    def test_vozes_agrupadas_por_idioma(self):
        texto = self.voz("kokoro vozes")
        self.assertIn("en-gb: bm_daniel (M)", texto)
        self.assertIn("pt-br: pf_dora (F)", texto)
        self.assertIn("Nenhuma voz", self.voz("kokoro vozes zzz"))

    def test_comando_desconhecido_e_ajuda(self):
        self.assertIn("Digite /voz ajuda", self.voz("blabla"))
        self.assertIn("/voz kokoro", self.voz("ajuda") + "/voz kokoro")
        self.assertIn("Não conheço /voz kokoro", self.voz("kokoro xyz"))

    def test_testar_com_motor_ativo_fala_pelo_jarvis(self):
        self.assertIsNone(self.voz("testar Ola, senhor."))
        self.assertEqual(self.falas, ["Ola, senhor."])

    def test_sugestoes_do_menu(self):
        def nomes(*anteriores):
            return [t for t, _ in comandos.sugestoes(list(anteriores), self.ctx, self.motor)]
        self.assertEqual(nomes(), ["usar", "padrao", "kokoro", "testar", "ajuda"])
        self.assertEqual(nomes("usar"), ["kokoro", "padrao"])
        self.assertIn("BR_REMY", nomes("padrao"))
        self.assertIn("mistura", nomes("kokoro"))
        self.assertEqual(nomes("kokoro", "mistura"), ["am_michael=", "bm_daniel=", "pf_dora=", "pm_alex="])
        self.assertIn("pt-br", nomes("kokoro", "idioma"))
        self.assertIn("1.0", nomes("kokoro", "velocidade"))
        self.voz("kokoro preset salvar calma")
        self.assertEqual(nomes("kokoro", "preset", "usar"), ["calma"])


class InstaladorTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.conteudo = b"modelo de mentira" * 50
        self.item = {"nome": "m.bin", "tamanho": len(self.conteudo),
                     "sha256": hashlib.sha256(self.conteudo).hexdigest()}

    def baixar(self, conteudo, confirmar=lambda d: True, item=None):
        item = item or self.item
        with patch.object(instalar, "ARQUIVOS", [item]), \
                patch("voz.instalar.urllib.request.urlopen", return_value=io.BytesIO(conteudo)):
            return instalar.instalar(confirmar, pasta=self.pasta.name, progresso=lambda t: None)

    def test_baixa_confere_e_instala(self):
        self.assertEqual(self.baixar(self.conteudo), ["m.bin"])
        self.assertEqual((Path(self.pasta.name) / "m.bin").read_bytes(), self.conteudo)
        with patch.object(instalar, "ARQUIVOS", [self.item]):
            self.assertEqual(instalar.faltando(self.pasta.name), [])

    def test_sem_confirmacao_nao_baixa_nada(self):
        self.assertEqual(self.baixar(self.conteudo, confirmar=lambda d: False), [])
        self.assertEqual(os.listdir(self.pasta.name), [])
        with patch.object(instalar, "ARQUIVOS", [self.item]), \
                patch("voz.instalar.urllib.request.urlopen") as rede:
            self.assertEqual(instalar.instalar(None, pasta=self.pasta.name), [])
            rede.assert_not_called()

    def test_arquivo_adulterado_e_descartado(self):
        errado = b"x" * len(self.conteudo)                    # mesmo tamanho, outro conteudo
        with self.assertRaises(instalar.ErroInstalacao) as erro:
            self.baixar(errado)
        self.assertIn("SHA-256", str(erro.exception))
        self.assertEqual(os.listdir(self.pasta.name), [])      # nem o .part sobra

    def test_tamanho_errado_e_descartado(self):
        with self.assertRaises(instalar.ErroInstalacao):
            self.baixar(self.conteudo[:-1])
        self.assertEqual(os.listdir(self.pasta.name), [])

    def test_descricao_informa_arquivos_tamanho_e_origem(self):
        texto = instalar.descricao(instalar.ARQUIVOS)
        self.assertIn("kokoro-v1.0.onnx (326 MB)", texto)
        self.assertIn("voices-v1.0.bin (28 MB)", texto)
        self.assertIn("github.com/thewh1teagle/kokoro-onnx", texto)


class CompletadorVozTests(unittest.TestCase):
    def test_sugere_a_partir_do_que_foi_digitado(self):
        from prompt_toolkit.document import Document
        completer = cli.JarvisCompleter(obter_voz=lambda anteriores: [("mistura", "x"), ("idioma", "y")]
                                        if anteriores == ["kokoro"] else [("kokoro", "k")])
        sugerir = lambda texto: list(completer.get_completions(Document(texto), None))
        achados = sugerir("/voz kokoro mi")
        self.assertEqual([(a.text, a.start_position) for a in achados], [("mistura", -2)])
        self.assertEqual([a.text for a in sugerir("/voz ")], ["kokoro"])
        self.assertEqual(sugerir("/voz kokoro mistura bm_daniel=0."), [])        # digitando o peso


class IntegracaoJarvisTests(ConfigIsolada):
    def test_kokoro_falando_dispensa_a_cadeia_antiga(self):
        with patch.object(jarvis, "CAPTURAR", False), \
                patch.object(jarvis.voz_pacote, "falar", return_value=True), \
                patch.object(jarvis, "_falar_neural") as edge, patch.object(jarvis, "_falar_windows") as win:
            jarvis._falar_audio("Ola, senhor.")
        edge.assert_not_called()
        win.assert_not_called()

    def test_kokoro_indisponivel_segue_na_cadeia_de_sempre(self):
        with patch.object(jarvis, "CAPTURAR", False), \
                patch.object(jarvis.voz_pacote, "falar", return_value=False), \
                patch.dict(jarvis.PERFIL, {"motor": "edge"}), \
                patch.object(jarvis, "_falar_neural", return_value=True) as edge:
            jarvis._falar_audio("Ola, senhor.")
        edge.assert_called_once_with("Ola, senhor.")

    def test_edge_falha_cai_no_windows_como_antes(self):
        with patch.object(jarvis, "CAPTURAR", False), \
                patch.object(jarvis.voz_pacote, "falar", return_value=False), \
                patch.dict(jarvis.PERFIL, {"motor": "edge"}), \
                patch.object(jarvis, "_falar_neural", return_value=False), \
                patch.object(jarvis, "_falar_windows") as win:
            jarvis._falar_audio("Ola, senhor.")
        win.assert_called_once_with("Ola, senhor.")

    def test_modo_captura_do_telegram_nao_toca_audio(self):
        with patch.object(jarvis, "CAPTURAR", True), patch.object(jarvis, "CAPTURADO", []) as lista, \
                patch.object(jarvis.voz_pacote, "falar") as kokoro:
            jarvis._falar_audio("Ola")
        kokoro.assert_not_called()
        self.assertEqual(lista, ["Ola"])

    def test_sem_voz_json_nada_muda(self):
        self.assertFalse(self.arquivo.exists())
        self.assertFalse(voz.falar("Ola, senhor.", lambda c: True))
        self.assertIsNone(voz.resumo_curto())
        self.assertIsNone(jarvis._perfil_salvo())

    def test_perfil_salvo_valido_e_invalido(self):
        config.atualizar(lambda c: c.update(perfil_padrao="BR_ANTONIO"))
        self.assertEqual(jarvis._perfil_salvo(), "BR_ANTONIO")
        config.atualizar(lambda c: c.update(perfil_padrao="PERFIL_QUE_SUMIU"))
        self.assertIsNone(jarvis._perfil_salvo())

    def test_aplicar_perfil_troca_em_tempo_de_execucao(self):
        anterior = (jarvis.VOZ, jarvis.PERFIL, jarvis.IDIOMA_FALA)
        self.addCleanup(lambda: (setattr(jarvis, "VOZ", anterior[0]), setattr(jarvis, "PERFIL", anterior[1]),
                                 setattr(jarvis, "IDIOMA_FALA", anterior[2])))
        self.assertTrue(jarvis._aplicar_perfil_padrao("JARVIS"))
        self.assertEqual((jarvis.VOZ, jarvis.IDIOMA_FALA), ("JARVIS", "en"))
        self.assertFalse(jarvis._aplicar_perfil_padrao("NAO_EXISTE"))

    def test_painel_mostra_kokoro_quando_ativo(self):
        self.assertNotIn("KOKORO", jarvis._status_painel()["voz"])
        config.atualizar(lambda c: c.update(motor="kokoro"))
        self.assertEqual(jarvis._status_painel()["voz"], "KOKORO · bm_daniel+am_michael+pm_alex")

    def test_slash_voz_responde_no_cli(self):
        with patch.dict(os.environ, {"JARVIS_INTERACTIVE": ""}), patch("sys.stdin", io.StringIO()):
            interface = cli.JarvisCLI()
        anterior = jarvis._cli
        self.addCleanup(setattr, jarvis, "_cli", anterior)
        jarvis._cli = interface
        with patch.object(interface, "jarvis") as mostrar:
            self.assertTrue(jarvis._executar_comando_slash("/voz"))
        self.assertIn("Motor ativo: padrao", mostrar.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
