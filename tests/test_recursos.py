import json
import io
import re
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import acoes
import catalogo
import jarvis
from lembretes import Lembretes, ServicoAlarmes
import tempos


def setUpModule():
    """jarvis.processar mede tempos: nos testes, o log vai para uma pasta descartavel."""
    global _pasta_tempos, _tempos_original
    _pasta_tempos = tempfile.TemporaryDirectory()
    _tempos_original = tempos.ARQUIVO
    tempos.ARQUIVO = Path(_pasta_tempos.name) / "tempos.jsonl"


def tearDownModule():
    tempos.ARQUIVO = _tempos_original
    _pasta_tempos.cleanup()


class CatalogoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.old_config = catalogo.CONFIG_PATH
        self.old_example = catalogo.EXEMPLO_PATH
        catalogo.CONFIG_PATH = Path(self.temp.name) / "config.json"
        catalogo.EXEMPLO_PATH = Path(self.temp.name) / "config.example.json"
        catalogo.EXEMPLO_PATH.write_text(json.dumps({
            "sites": {"exemplo": "https://example.com"},
            "programas": {"calculadora": "calc.exe"},
        }), encoding="utf-8")
        catalogo.resetar_cache()
        self.addCleanup(self.restaurar_catalogo)

    def restaurar_catalogo(self):
        catalogo.CONFIG_PATH = self.old_config
        catalogo.EXEMPLO_PATH = self.old_example
        catalogo.resetar_cache()

    def test_cria_config_local_e_recarrega_edicoes_externas(self):
        inicial = catalogo.carregar()
        self.assertEqual(inicial["sites"]["exemplo"], "https://example.com")
        local = json.loads(catalogo.CONFIG_PATH.read_text(encoding="utf-8"))
        local["sites"]["novo"] = "https://novo.example"
        catalogo.CONFIG_PATH.write_text(json.dumps(local), encoding="utf-8")
        self.assertEqual(catalogo.carregar()["sites"]["novo"], "https://novo.example")

    def test_rejeita_site_sem_http_ou_https(self):
        ok, _ = catalogo.validar_entrada("site", "teste", "javascript:alert(1)")
        self.assertFalse(ok)

    def test_salva_programa_com_uri_de_aplicativo(self):
        ok, _ = catalogo.salvar_entrada("programa", "Meu App", "minhaapp:")
        self.assertTrue(ok)
        self.assertEqual(catalogo.carregar()["programas"]["meu app"], "minhaapp:")


class LembreteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Lembretes(Path(self.temp.name) / "lembretes.sqlite3")

    def test_persiste_entre_instancias_e_lista_assunto(self):
        self.store.criar("ver o arroz", 10, agora=1000)
        recarregado = Lembretes(self.store.caminho)
        self.assertEqual(recarregado.listar()[0]["motivo"], "ver o arroz")

    def test_dispara_na_abertura_e_repete_depois_de_30_segundos(self):
        self.store.criar("ver o arroz", 1, agora=1000)
        self.assertEqual(self.store.marcar_alarmas(agora=1060)[0]["motivo"], "ver o arroz")
        self.assertEqual(self.store.marcar_alarmas(agora=1089), [])
        self.assertEqual(self.store.marcar_alarmas(agora=1090)[0]["motivo"], "ver o arroz")

    def test_confirma_por_assunto_sem_acentos(self):
        self.store.criar("ver o arroz no fogao", 0.01, agora=1000)
        self.store.marcar_alarmas(agora=1001)
        resposta = self.store.confirmar("arroz no fogao", agora=1001)
        self.assertIn("confirmado", resposta)
        self.assertEqual(self.store.listar(), [])

    def test_dispensar_sem_assunto_encerra_unico_alarme_tocando(self):
        self.store.criar("verificar o arroz", 0.01, agora=1000)
        self.store.marcar_alarmas(agora=1001)
        resposta = self.store.confirmar("", agora=1001)
        self.assertIn("confirmado", resposta)
        self.assertEqual(self.store.listar(), [])

    def test_dispensar_sem_assunto_nao_escolhe_entre_varios_alarmas(self):
        self.store.criar("ver arroz", 0.01, agora=1000)
        self.store.criar("ver forno", 0.01, agora=1000)
        self.store.marcar_alarmas(agora=1001)
        resposta = self.store.confirmar("", agora=1001)
        self.assertIn("mais de um alarme", resposta)
        self.assertEqual(len(self.store.listar()), 2)

    def test_worker_enfileira_sem_chamar_voz_em_thread_de_fundo(self):
        falas = []
        ctx = types.SimpleNamespace(falar=lambda texto: falas.append(texto))
        self.store.criar("teste de alarme", 0.0001)
        servico = ServicoAlarmes(ctx, self.store.caminho, intervalo=0.1).iniciar()
        self.addCleanup(servico.parar)
        import time
        limite = time.monotonic() + 2
        eventos = []
        while not eventos and time.monotonic() < limite:
            eventos = servico.drenar()
            time.sleep(0.01)
        self.assertEqual([item["motivo"] for item in eventos], ["teste de alarme"])
        self.assertEqual(falas, [])


class AcoesTests(unittest.TestCase):
    def test_volume_percentual_define_escalar(self):
        endpoint = types.SimpleNamespace(SetMasterVolumeLevelScalar=lambda value, ctx: setattr(endpoint, "value", value))
        speakers = types.SimpleNamespace(EndpointVolume=endpoint)
        audio = types.SimpleNamespace(GetSpeakers=lambda: speakers)
        pycaw = types.ModuleType("pycaw")
        pycaw.pycaw = types.SimpleNamespace(AudioUtilities=audio)
        with patch.object(acoes, "NO_WINDOWS", True), patch.dict("sys.modules", {
                "pycaw": pycaw, "pycaw.pycaw": pycaw.pycaw}):
            resposta = acoes.volume(None, percentual=35)
        self.assertEqual(endpoint.value, 0.35)
        self.assertIn("35 por cento", resposta)

    def test_volume_rejeita_percentual_fora_da_faixa(self):
        self.assertIn("entre 0 e 100", acoes.volume(None, percentual=101))


class JarvisDispatchTests(unittest.TestCase):
    def test_comando_percentual_chega_a_acao(self):
        with patch.object(jarvis, "falar"), patch.object(jarvis, "executar_acao") as executar:
            jarvis.processar("volume em 35%")
        executar.assert_called_once_with("volume", {"percentual": 35})

    def test_comando_listar_lembretes_nao_cria_timer(self):
        with patch.object(jarvis, "falar"), patch.object(jarvis, "executar_acao") as executar:
            jarvis.processar("listar lembretes")
        executar.assert_called_once_with("listar_lembretes")

    def test_confirmacao_por_assunto_chega_a_acao(self):
        with patch.object(jarvis, "falar"), patch.object(jarvis, "executar_acao") as executar:
            jarvis.processar("confirmar arroz no fogo")
        executar.assert_called_once_with(
            "confirmar_lembrete", {"assunto": "arroz no fogo"})

    def test_frases_naturais_de_encerrar_alarme_confirmam_em_vez_de_criar(self):
        for comando, assunto in (
                ("encerra o alarme do arroz", "arroz"),
                ("cancela o lembrete de verificar o forno", "verificar o forno"),
                ("para o alarme da panela", "panela")):
            with self.subTest(comando=comando), \
                    patch.object(jarvis, "falar"), \
                    patch.object(jarvis, "executar_acao") as executar:
                jarvis.processar(comando)
            executar.assert_called_once_with(
                "confirmar_lembrete", {"assunto": assunto})

    def test_para_musica_nao_e_confundido_com_confirmacao_de_alarme(self):
        self.assertIsNone(re.match(
            jarvis.R_CONFIRMAR_LEMBRETE, jarvis.normalizar("para a musica")))

    def test_nao_quero_dispensa_unico_alarme_tocando(self):
        with patch.object(jarvis, "falar"), \
                patch.object(jarvis.lembretes, "Lembretes") as store, \
                patch.object(jarvis, "executar_acao") as executar:
            store.return_value.tem_alarmas_tocando.return_value = True
            jarvis.processar("Não quero")
        executar.assert_called_once_with(
            "confirmar_lembrete", {"assunto": ""})

    def test_relato_natural_confirma_alarme_sem_exigir_barra(self):
        for comando, assunto in (
                ("ok, verifiquei", ""),
                ("pok, arroz verificado", "arroz"),
                ("verifiquei o arroz", "arroz")):
            with self.subTest(comando=comando), \
                    patch.object(jarvis, "falar"), \
                    patch.object(jarvis.lembretes, "Lembretes") as store, \
                    patch.object(jarvis, "executar_acao") as executar:
                store.return_value.tem_alarmas_tocando.return_value = True
                jarvis.processar(comando)
            executar.assert_called_once_with(
                "confirmar_lembrete", {"assunto": assunto})

    def test_nao_quero_sem_alarme_nao_chama_confirmacao(self):
        with patch.object(jarvis, "falar"), \
                patch.object(jarvis.lembretes, "Lembretes") as store, \
                patch.object(jarvis, "processar_com_ia", return_value=True), \
                patch.object(jarvis, "executar_acao") as executar:
            store.return_value.tem_alarmas_tocando.return_value = False
            jarvis.processar("Não quero")
        executar.assert_not_called()

    def test_segunda_instancia_do_jarvis_nao_adquire_o_lock(self):
        if jarvis._instancia_lock is not None:
            self.skipTest("O teste deve rodar antes de a aplicacao adquirir o lock")
        if not jarvis._adquirir_lock_instancia():
            self.skipTest("Ja existe outra instancia do Jarvis nesta pasta")
        self.addCleanup(jarvis._liberar_lock_instancia)
        script = "import jarvis; print('acquired' if jarvis._adquirir_lock_instancia() else 'busy')"
        resultado = subprocess.run(
            [sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertEqual(resultado.stdout.strip(), "busy")

    def test_comando_cadastro_e_direcionado_sem_ia(self):
        with patch.object(jarvis, "falar"), patch.object(jarvis, "cadastrar_entrada_catalogo") as cadastrar:
            jarvis.processar("adicionar site meu banco")
        cadastrar.assert_called_once_with("site", "meu banco")

    def test_lembrete_entende_daqui_e_preserva_assunto(self):
        with patch.object(jarvis, "falar"), patch.object(jarvis, "executar_acao") as executar:
            jarvis.tarefa_lembrete("Me lembre daqui 10 minutos de ver o arroz no fogo")
        executar.assert_called_once_with("lembrete", {
            "minutos": 10.0, "motivo": "ver o arroz no fogo"})

    def test_alarme_preserva_linha_digitada_e_fala_na_thread_principal(self):
        principal = threading.get_ident()
        caracteres = iter(["h", "i", "\r"])
        falas = []

        class MockMsvcrt(types.ModuleType):
            def __init__(self):
                super().__init__("msvcrt")

            def kbhit(self):
                return True

            def getwch(self):
                return next(caracteres)

        class ServicoFake:
            chamadas = 0

            def drenar_erros(self):
                return []

            def drenar(self):
                self.chamadas += 1
                if self.chamadas == 3:
                    return [{"motivo": "arroz"}]
                return []

        servico_anterior = jarvis._servico_alarmes
        jarvis._servico_alarmes = ServicoFake()
        self.addCleanup(setattr, jarvis, "_servico_alarmes", servico_anterior)
        with patch.dict(sys.modules, {"msvcrt": MockMsvcrt()}), \
                patch("sys.stdin.isatty", return_value=True), \
                patch("sys.stdout", new_callable=io.StringIO) as saida, \
                patch.object(jarvis, "falar", side_effect=lambda texto: falas.append(
                    (texto, threading.get_ident(), saida.getvalue()))):
            resposta = jarvis._ler_texto_com_alarmas()

        self.assertEqual(resposta, "hi")
        self.assertIn("Voce: hi", saida.getvalue())
        self.assertEqual(falas[0][1], principal)
        self.assertIn("\x1b[2K", falas[0][2])

    def test_cadastro_pede_confirmacao_antes_de_gravar(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        old_config = catalogo.CONFIG_PATH
        old_example = catalogo.EXEMPLO_PATH
        catalogo.CONFIG_PATH = Path(temp.name) / "config.json"
        catalogo.EXEMPLO_PATH = Path(temp.name) / "config.example.json"
        catalogo.EXEMPLO_PATH.write_text(json.dumps({"sites": {}, "programas": {}}), encoding="utf-8")
        catalogo.resetar_cache()
        self.addCleanup(self._restore_paths, old_config, old_example)
        with patch.object(jarvis, "MODO_TEXTO", True), patch.object(jarvis, "falar"), \
                patch("sys.stdin", io.StringIO()), \
                patch("builtins.input", side_effect=["https://example.com", "sim"]):
            jarvis.cadastrar_entrada_catalogo("site", "meu site")
        self.assertEqual(catalogo.carregar()["sites"]["meu site"], "https://example.com")

    def test_cadastro_cancelado_nao_grava(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        old_config = catalogo.CONFIG_PATH
        old_example = catalogo.EXEMPLO_PATH
        catalogo.CONFIG_PATH = Path(temp.name) / "config.json"
        catalogo.EXEMPLO_PATH = Path(temp.name) / "config.example.json"
        catalogo.EXEMPLO_PATH.write_text(json.dumps({"sites": {}, "programas": {}}), encoding="utf-8")
        catalogo.resetar_cache()
        self.addCleanup(self._restore_paths, old_config, old_example)
        with patch.object(jarvis, "MODO_TEXTO", True), patch.object(jarvis, "falar"), \
                patch("sys.stdin", io.StringIO()), \
                patch("builtins.input", side_effect=["https://example.com", "nao"]):
            jarvis.cadastrar_entrada_catalogo("site", "meu site")
        self.assertNotIn("meu site", catalogo.carregar()["sites"])

    @staticmethod
    def _restore_paths(config_path, example_path):
        catalogo.CONFIG_PATH = config_path
        catalogo.EXEMPLO_PATH = example_path
        catalogo.resetar_cache()
        jarvis.atualizar_catalogos()


if __name__ == "__main__":
    unittest.main()
