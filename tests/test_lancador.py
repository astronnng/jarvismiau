import _ambiente  # noqa: F401  (isola os dados do usuario; deve ser o primeiro import)

import os
import sys
import unittest
from pathlib import Path

import lancador

RAIZ_PROJETO = Path(__file__).resolve().parents[1]


class InterpretarTests(unittest.TestCase):
    def test_sem_argumentos_pede_o_menu(self):
        self.assertEqual(lancador.interpretar([]), (None, []))

    def test_cada_modo_conhecido(self):
        for modo in lancador.MODOS:
            self.assertEqual(lancador.interpretar([modo]), (modo, []), modo)

    def test_maiusculas_e_opcoes_extras(self):
        self.assertEqual(lancador.interpretar(["TEXTO", "--sem-ia"]), ("texto", ["--sem-ia"]))
        self.assertEqual(lancador.interpretar(["voz", "--latencia", "--sem-cache"]),
                         ("voz", ["--latencia", "--sem-cache"]))

    def test_nomes_antigos_continuam_valendo(self):
        self.assertEqual(lancador.interpretar(["pressione"])[0], "enter")
        self.assertEqual(lancador.interpretar(["palavra"])[0], "voz")
        self.assertEqual(lancador.interpretar(["telegram"])[0], "bot")
        self.assertEqual(lancador.interpretar(["configurar-ia"])[0], "ia")

    def test_opcoes_antigas_sem_modo_vao_para_voz(self):
        # "Jarvis.bat --sem-ia" e "Jarvis.bat --latencia" funcionavam antes
        self.assertEqual(lancador.interpretar(["--sem-ia"]), ("voz", ["--sem-ia"]))
        self.assertEqual(lancador.interpretar(["--ia-status"]), ("voz", ["--ia-status"]))

    def test_modo_desconhecido_explica_e_lista_os_modos(self):
        with self.assertRaises(lancador.ErroDeUso) as erro:
            lancador.interpretar(["banana"])
        self.assertIn('Não conheço o modo "banana"', str(erro.exception))
        self.assertIn("testar-voz", str(erro.exception))

    def test_ajuda(self):
        for pedido in ("ajuda", "--ajuda", "-h", "--help"):
            with self.assertRaises(lancador.ErroDeUso) as erro:
                lancador.interpretar([pedido])
            self.assertEqual(str(erro.exception), lancador.ajuda())


class MontarTests(unittest.TestCase):
    def test_modo_texto_liga_o_terminal_interativo(self):
        comando, ambiente = lancador.montar("texto", executavel="py")
        self.assertEqual(comando, ["py", str(RAIZ_PROJETO / "jarvis.py"), "--texto"])
        self.assertEqual(ambiente["JARVIS_INTERACTIVE"], "1")

    def test_equivalencia_com_os_bats_antigos(self):
        esperado = {
            "voz": ("jarvis.py", []),
            "continuo": ("jarvis.py", ["--continuo"]),
            "enter": ("jarvis.py", ["--pressione"]),
            "texto": ("jarvis.py", ["--texto"]),
            "testar-voz": ("jarvis.py", ["--demo"]),
            "bot": ("telegram_bot.py", []),
            "ia": ("configurar_ia.py", []),
            "escolher-voz": ("escolher_voz.py", []),
        }
        for modo, (script, flags) in esperado.items():
            comando, _ = lancador.montar(modo, executavel="py")
            self.assertEqual(comando[1:], [str(RAIZ_PROJETO / script), *flags], modo)

    def test_extras_vao_no_fim_e_o_ambiente_e_herdado(self):
        comando, ambiente = lancador.montar("voz", ["--sem-ia"], executavel="py")
        self.assertEqual(comando[-1], "--sem-ia")
        self.assertEqual(ambiente["JARVIS_DADOS"], os.environ["JARVIS_DADOS"])
        self.assertNotIn("JARVIS_INTERACTIVE", lancador.montar("voz")[1].keys() - os.environ.keys())

    def test_todo_script_existe_e_todo_item_do_menu_tem_modo(self):
        for modo, (script, *_resto) in lancador.MODOS.items():
            self.assertTrue((RAIZ_PROJETO / script).is_file(), f"{modo}: {script}")
        modos_do_menu = {modo for _, modo, _ in lancador.MENU if modo}
        self.assertEqual(modos_do_menu, set(lancador.MODOS))


class MenuTests(unittest.TestCase):
    def escolher(self, *teclas):
        fila = list(teclas)
        saida = []
        modo = lancador.escolher_modo(lambda espera: fila.pop(0) if fila else None, saida.append)
        return modo, "\n".join(saida)

    def test_sem_tecla_inicia_no_modo_voz_e_avisa_a_contagem(self):
        modo, tela = self.escolher(None)
        self.assertEqual(modo, "voz")
        self.assertIn("Iniciando o modo voz em 60 s", tela)

    def test_mostra_todas_as_opcoes(self):
        _, tela = self.escolher(None)
        for rotulo in ("Voz:", "Texto:", "Voz contínua", "Voz com ENTER", "Bot do Telegram",
                       "Configurar a IA", "Testar a voz", "Escolher a voz", "Sair"):
            self.assertIn(rotulo, tela)

    def test_numeros_escolhem_o_modo(self):
        for tecla, modo in (("1", "voz"), ("2", "texto"), ("3", "continuo"), ("4", "enter"),
                            ("5", "bot"), ("6", "ia"), ("7", "testar-voz"), ("8", "escolher-voz")):
            self.assertEqual(self.escolher(tecla)[0], modo, tecla)

    def test_enter_e_zero(self):
        self.assertEqual(self.escolher("\r")[0], "voz")
        self.assertIsNone(self.escolher("0")[0])

    def test_tecla_invalida_pergunta_de_novo(self):
        modo, tela = self.escolher("x", "9", "2")
        self.assertEqual(modo, "texto")
        self.assertEqual(tela.count("Opção inválida"), 2)

    def test_sem_teclado_interativo_vai_direto_para_o_padrao(self):
        self.assertIsNone(lancador._tecla_padrao(0.01) if not sys.stdin.isatty() else None)


class MainTests(unittest.TestCase):
    def rodar(self, argv, *teclas):
        chamadas, saida = [], []
        fila = list(teclas)

        def fake(comando, env=None, cwd=None):
            chamadas.append((comando, env, cwd))
            return 0

        codigo = lancador.main(argv, tecla=lambda e: fila.pop(0) if fila else None,
                               rodar=fake, imprimir=saida.append)
        return codigo, chamadas, "\n".join(saida)

    def test_sem_argumento_e_sem_tecla_inicia_a_voz(self):
        codigo, chamadas, _ = self.rodar([])
        self.assertEqual(codigo, 0)
        self.assertEqual(len(chamadas), 1)
        self.assertEqual(chamadas[0][0][1:], [str(RAIZ_PROJETO / "jarvis.py")])
        self.assertEqual(chamadas[0][2], str(RAIZ_PROJETO))

    def test_sair_pelo_menu_nao_roda_nada(self):
        codigo, chamadas, _ = self.rodar([], "0")
        self.assertEqual((codigo, chamadas), (0, []))

    def test_modo_direto_nao_mostra_menu(self):
        codigo, chamadas, tela = self.rodar(["texto"])
        self.assertNotIn("J.A.R.V.I.S", tela)
        self.assertEqual(chamadas[0][0][-1], "--texto")
        self.assertEqual(chamadas[0][1]["JARVIS_INTERACTIVE"], "1")

    def test_codigo_de_saida_do_programa_e_repassado(self):
        codigo = lancador.main(["voz"], rodar=lambda *a, **k: 3, imprimir=lambda t: None)
        self.assertEqual(codigo, 3)

    def test_modo_desconhecido_sai_com_erro_e_nao_roda_nada(self):
        codigo, chamadas, tela = self.rodar(["banana"])
        self.assertEqual((codigo, chamadas), (2, []))
        self.assertIn("Não conheço", tela)

    def test_ajuda_sai_sem_erro(self):
        codigo, chamadas, tela = self.rodar(["ajuda"])
        self.assertEqual((codigo, chamadas), (0, []))
        self.assertIn("Uso: Jarvis.bat", tela)

    def test_mensagens_de_bot_e_teste_de_voz(self):
        self.assertIn("O bot foi encerrado", self.rodar(["bot"])[2])
        self.assertIn("Ouvindo a voz configurada", self.rodar(["testar-voz"])[2])

    def test_ctrl_c_nao_vira_erro(self):
        def interrompe(*a, **k):
            raise KeyboardInterrupt
        self.assertEqual(lancador.main(["texto"], rodar=interrompe, imprimir=lambda t: None), 0)


class ArquivosBatTests(unittest.TestCase):
    def test_so_restam_dois_bat_na_raiz(self):
        self.assertEqual(sorted(p.name for p in RAIZ_PROJETO.glob("*.bat")), ["Instalar.bat", "Jarvis.bat"])

    def test_jarvis_bat_repassa_os_argumentos_ao_lancador(self):
        texto = (RAIZ_PROJETO / "Jarvis.bat").read_text(encoding="utf-8")
        self.assertIn("python lancador.py %*", texto)
        self.assertIn(r'.venv\Scripts\activate.bat', texto)

    def test_instalar_bat_tem_o_ramo_do_kokoro(self):
        texto = (RAIZ_PROJETO / "Instalar.bat").read_text(encoding="utf-8")
        self.assertIn('if /i "%~1"=="kokoro" goto kokoro', texto)
        self.assertIn(":kokoro", texto)
        self.assertIn("requirements-kokoro.txt", texto)
        self.assertIn("python -m voz.instalar", texto)

    def test_nenhum_bat_nem_mensagem_cita_os_nomes_removidos(self):
        removidos = ("Jarvis-texto.bat", "Jarvis-continuo.bat", "Jarvis-pressione.bat", "Iniciar-bot.bat",
                     "Configurar-IA.bat", "Testar-voz.bat", "Escolher-voz.bat", "Instalar-kokoro.bat",
                     "instalar.bat")
        problemas = []
        for arquivo in list(RAIZ_PROJETO.glob("*.py")) + list((RAIZ_PROJETO / "voz").glob("*.py")) \
                + list((RAIZ_PROJETO / "navegador").glob("*.py")) + list(RAIZ_PROJETO.glob("*.bat")) \
                + list(RAIZ_PROJETO.glob("*.txt")):
            conteudo = arquivo.read_text(encoding="utf-8")
            problemas += [f"{arquivo.name}: {nome}" for nome in removidos if nome in conteudo]
        self.assertEqual(problemas, [])


if __name__ == "__main__":
    unittest.main()
