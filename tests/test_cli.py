import asyncio
import io
import os
import unittest
from unittest.mock import patch

from prompt_toolkit.document import Document

import cli
import jarvis
import tempfile
import tempos
from pathlib import Path


def setUpModule():
    """jarvis.processar mede tempos: nos testes, o log vai para uma pasta descartavel."""
    global _pasta_tempos, _tempos_original
    _pasta_tempos = tempfile.TemporaryDirectory()
    _tempos_original = tempos.ARQUIVO
    tempos.ARQUIVO = Path(_pasta_tempos.name) / "tempos.jsonl"


def tearDownModule():
    tempos.ARQUIVO = _tempos_original
    _pasta_tempos.cleanup()


class CompleterTests(unittest.TestCase):
    def setUp(self):
        self.completer = cli.JarvisCompleter(
            obter_alvos=lambda: ["google", "bloco de notas", "calculadora"],
            obter_lembretes=lambda: ["ver o arroz", "regar as plantas"],
        )

    def completar(self, texto):
        return list(self.completer.get_completions(Document(texto), None))

    def test_sugere_comandos_a_partir_da_barra(self):
        sugestoes = self.completar("/vol")
        self.assertEqual([item.text for item in sugestoes], ["ume"])
        self.assertEqual(sugestoes[0].display_text, "/volume <0-100>")
        # "/vo" e ambiguo de proposito: volume e voz
        self.assertEqual(sorted(item.text for item in self.completar("/vo")), ["lume", "z"])

    def test_completa_alvo_dinamico_com_alias_de_varias_palavras(self):
        sugestoes = self.completar("/abrir bloco d")
        self.assertEqual(len(sugestoes), 1)
        self.assertEqual(sugestoes[0].text, "bloco de notas")
        self.assertEqual(sugestoes[0].start_position, -7)

    def test_completa_assunto_de_lembrete(self):
        sugestoes = self.completar("/confirmar ver o a")
        self.assertEqual([item.text for item in sugestoes], ["ver o arroz"])


class SlashCommandTests(unittest.TestCase):
    def setUp(self):
        self.cli_anterior = jarvis._cli
        with patch.dict(os.environ, {"JARVIS_INTERACTIVE": ""}), \
                patch("sys.stdin", io.StringIO()):
            jarvis._cli = cli.JarvisCLI()
        self.addCleanup(setattr, jarvis, "_cli", self.cli_anterior)

    def test_comando_desconhecido_nao_chama_gemini(self):
        with patch.object(jarvis._cli, "jarvis") as mostrar, \
                patch.object(jarvis, "processar_com_ia") as ia:
            self.assertTrue(jarvis._executar_comando_slash("/voo"))
        ia.assert_not_called()
        mostrar.assert_called_once()

    def test_launcher_forca_prompt_interativo_no_windows_terminal(self):
        with patch.dict(os.environ, {"JARVIS_INTERACTIVE": "1", "NO_COLOR": ""}), \
                patch("cli.PromptSession"):
            interface = cli.JarvisCLI()
        self.assertTrue(interface.interativo)
        self.assertTrue(interface.com_cores)

    def test_volume_e_despachado_com_percentual(self):
        with patch.object(jarvis, "executar_acao") as executar:
            jarvis._executar_comando_slash("/volume 45")
        executar.assert_called_once_with("volume", {"percentual": 45})

    def test_lembrete_no_singular_lista_a_lista(self):
        with patch.object(jarvis, "executar_acao") as executar:
            jarvis._executar_comando_slash("/lembrete")
        executar.assert_called_once_with("listar_lembretes")

    def test_abrir_usa_catalogo_e_nao_pesquisa_alvo_desconhecido(self):
        with patch.object(jarvis, "tentar_abrir", return_value=True) as abrir, \
                patch.object(jarvis, "processar_com_ia") as ia:
            jarvis._executar_comando_slash("/abrir meu site")
        abrir.assert_called_once_with("meu site")
        ia.assert_not_called()


class AlarmDuringPromptTests(unittest.IsolatedAsyncioTestCase):
    async def test_alarme_nao_apaga_o_texto_digitado(self):
        from prompt_toolkit import PromptSession
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput

        with create_pipe_input() as pipe:
            with patch.dict(os.environ, {"JARVIS_INTERACTIVE": ""}), \
                    patch("sys.stdin", io.StringIO()):
                interface = cli.JarvisCLI()
            interface.interativo = True
            interface.session = PromptSession(input=pipe, output=DummyOutput())
            cli_anterior = jarvis._cli
            servico_anterior = jarvis._servico_alarmes
            jarvis._cli = interface

            class ServicoFake:
                def drenar_erros(self):
                    return []

                def drenar(self):
                    return [{"motivo": "ver o arroz"}]

            jarvis._servico_alarmes = ServicoFake()
            self.addCleanup(setattr, jarvis, "_cli", cli_anterior)
            self.addCleanup(setattr, jarvis, "_servico_alarmes", servico_anterior)
            with patch("sys.stdout", io.StringIO()):
                with patch.object(jarvis, "_falar_audio_serializado") as falar_audio:
                    entrada = asyncio.create_task(
                        interface.entrada(jarvis._notificar_alarmas_durante_entrada))
                    pipe.send_text("nao terminei")
                    await asyncio.sleep(0.35)
                    falar_audio.assert_called_once_with("Senhor, alarme: ver o arroz.")
                    pipe.send_text("\r")
                    self.assertEqual(await entrada, "nao terminei")


if __name__ == "__main__":
    unittest.main()
