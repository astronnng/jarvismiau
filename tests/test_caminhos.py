import _ambiente  # noqa: F401  (isola os dados do usuario; deve ser o primeiro import)

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import caminhos

RAIZ_PROJETO = Path(__file__).resolve().parents[1]


class PastasTemporarias(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name) / "raiz"
        self.dados = Path(self.tmp.name) / "dados"
        self.raiz.mkdir()

    def criar(self, nome, conteudo="x"):
        caminho = self.raiz / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
        return caminho


class MigrarTests(PastasTemporarias):
    def test_move_arquivos_e_pastas_antigos(self):
        self.criar("config.json", "{}")
        self.criar("ia_config.json", '{"api_key": "AIza"}')
        self.criar("voz.json")
        self.criar("cache_voz/frase.mp3", "mp3")
        self.criar("modelos/kokoro/kokoro-v1.0.onnx", "modelo")
        resultado = caminhos.migrar(self.raiz, self.dados)
        self.assertEqual(sorted(resultado["movidos"]), ["cache_voz", "config.json", "ia_config.json",
                                                        "modelos", "voz.json"])
        self.assertEqual(resultado["pendentes"], [])
        self.assertEqual((self.dados / "ia_config.json").read_text(encoding="utf-8"), '{"api_key": "AIza"}')
        self.assertTrue((self.dados / "cache_voz" / "frase.mp3").exists())
        self.assertTrue((self.dados / "modelos" / "kokoro" / "kokoro-v1.0.onnx").exists())
        self.assertFalse((self.raiz / "config.json").exists())          # moveu, nao copiou

    def test_e_idempotente(self):
        self.criar("tempos.jsonl")
        self.assertEqual(caminhos.migrar(self.raiz, self.dados)["movidos"], ["tempos.jsonl"])
        segunda = caminhos.migrar(self.raiz, self.dados)
        self.assertEqual(segunda, {"movidos": [], "pendentes": []})

    def test_nao_faz_nada_sem_arquivos_antigos(self):
        self.assertEqual(caminhos.migrar(self.raiz, self.dados), {"movidos": [], "pendentes": []})
        self.assertTrue(self.dados.is_dir())

    def test_nunca_sobrescreve_o_que_ja_esta_em_dados(self):
        self.criar("voz.json", "ANTIGO")
        self.dados.mkdir()
        (self.dados / "voz.json").write_text("NOVO", encoding="utf-8")
        resultado = caminhos.migrar(self.raiz, self.dados)
        self.assertEqual(resultado["pendentes"], ["voz.json"])
        self.assertEqual((self.dados / "voz.json").read_text(encoding="utf-8"), "NOVO")
        self.assertEqual((self.raiz / "voz.json").read_text(encoding="utf-8"), "ANTIGO")   # fica para o usuario

    def test_banco_de_lembretes_leva_os_arquivos_auxiliares(self):
        self.criar("lembretes.sqlite3", "db")
        self.criar("lembretes.sqlite3-wal", "wal")
        self.criar("lembretes.sqlite3-shm", "shm")
        caminhos.migrar(self.raiz, self.dados)
        for nome in ("lembretes.sqlite3", "lembretes.sqlite3-wal", "lembretes.sqlite3-shm"):
            self.assertTrue((self.dados / nome).exists(), nome)
            self.assertFalse((self.raiz / nome).exists(), nome)

    def test_arquivo_em_uso_fica_no_lugar_e_os_outros_seguem(self):
        self.criar("lembretes.sqlite3", "db")
        self.criar("lembretes.sqlite3-wal", "wal")
        self.criar("voz.json")
        real = caminhos.shutil.move

        def mover(origem, destino):
            if origem.endswith("lembretes.sqlite3"):
                raise PermissionError("em uso por outro processo")
            return real(origem, destino)

        with patch.object(caminhos.shutil, "move", mover):
            resultado = caminhos.migrar(self.raiz, self.dados)
        self.assertEqual(resultado["movidos"], ["voz.json"])
        self.assertEqual(resultado["pendentes"], ["lembretes.sqlite3"])
        self.assertTrue((self.raiz / "lembretes.sqlite3").exists())
        self.assertTrue((self.raiz / "lembretes.sqlite3-wal").exists())       # o auxiliar NAO foi sozinho
        self.assertFalse((self.dados / "lembretes.sqlite3-wal").exists())

    def test_pasta_de_dados_impossivel_de_criar_nao_quebra(self):
        self.criar("voz.json")
        with patch.object(Path, "mkdir", side_effect=OSError("sem permissao")):
            resultado = caminhos.migrar(self.raiz, self.dados)
        self.assertEqual(resultado["movidos"], [])
        self.assertIn("voz.json", resultado["pendentes"])
        self.assertTrue((self.raiz / "voz.json").exists())


class ResolverCaminhoTests(PastasTemporarias):
    def trocar(self, personalizada=False):
        for alvo, valor in ((caminhos, {"RAIZ": self.raiz, "DADOS": self.dados,
                                        "_PERSONALIZADA": personalizada}),):
            for nome, v in valor.items():
                patcher = patch.object(alvo, nome, v)
                patcher.start()
                self.addCleanup(patcher.stop)

    def test_prefere_dados_quando_existe(self):
        self.trocar()
        self.criar("voz.json", "antigo")
        self.dados.mkdir()
        (self.dados / "voz.json").write_text("novo", encoding="utf-8")
        self.assertEqual(caminhos.dados("voz.json"), self.dados / "voz.json")

    def test_cai_no_lugar_antigo_so_se_a_migracao_ainda_nao_moveu(self):
        self.trocar()
        self.criar("lembretes.sqlite3")
        self.assertEqual(caminhos.dados("lembretes.sqlite3"), self.raiz / "lembretes.sqlite3")

    def test_arquivo_novo_nasce_em_dados(self):
        self.trocar()
        self.assertEqual(caminhos.dados("voz.json"), self.dados / "voz.json")

    def test_pasta_personalizada_nunca_olha_a_raiz(self):
        self.trocar(personalizada=True)
        self.criar("voz.json")                               # existe no lugar antigo...
        self.assertEqual(caminhos.dados("voz.json"), self.dados / "voz.json")   # ...e e ignorado


class AmbienteDeTesteTests(unittest.TestCase):
    def test_a_suite_usa_uma_pasta_temporaria_e_nao_a_do_usuario(self):
        self.assertEqual(Path(os.environ["JARVIS_DADOS"]), caminhos.DADOS)
        self.assertNotEqual(caminhos.DADOS, RAIZ_PROJETO / "dados")
        self.assertTrue(caminhos.DADOS.is_dir())

    def test_jarvis_dados_e_respeitado_em_outro_processo(self):
        with tempfile.TemporaryDirectory() as pasta:
            saida = subprocess.run(
                [sys.executable, "-c", "import caminhos; print(caminhos.DADOS)"],
                cwd=RAIZ_PROJETO, env=dict(os.environ, JARVIS_DADOS=pasta),
                capture_output=True, text=True, timeout=30)
            self.assertEqual(Path(saida.stdout.strip()), Path(pasta))


class ModulosUsamOsCaminhosTests(unittest.TestCase):
    def test_cada_modulo_aponta_para_dados_ou_recursos(self):
        import cache_planos
        import catalogo
        import cerebro
        import lembretes
        import tempos
        from navegador import config as navegador_config
        from voz import config as voz_config
        import jarvis

        esperados = {
            catalogo.CONFIG_PATH: "config.json",
            cerebro.CONFIG_PATH: "ia_config.json",
            lembretes.DB_PATH: "lembretes.sqlite3",
            tempos.ARQUIVO: "tempos.jsonl",
            cache_planos.ARQUIVO: "cache_planos.json",
            navegador_config.ARQUIVO: "navegador.json",
            voz_config.ARQUIVO: "voz.json",
        }
        for caminho, nome in esperados.items():
            self.assertEqual(Path(caminho), caminhos.DADOS / nome, nome)
        self.assertEqual(voz_config.PASTA_MODELOS, caminhos.DADOS / "modelos" / "kokoro")
        self.assertEqual(voz_config.PASTA_CACHE, caminhos.DADOS / "cache_voz" / "kokoro")
        self.assertEqual(Path(jarvis.CACHE_DIR), caminhos.DADOS / "cache_voz")
        self.assertEqual(catalogo.EXEMPLO_PATH, caminhos.RECURSOS / "config.example.json")

    def test_o_bot_do_telegram_tambem_usa_dados(self):
        # Importar o bot altera flags globais do jarvis, entao so lemos o codigo-fonte.
        fonte = (RAIZ_PROJETO / "telegram_bot.py").read_text(encoding="utf-8")
        self.assertIn('caminhos.dados("bot_config.json")', fonte)

    def test_nenhum_modulo_monta_caminho_de_dado_ao_lado_do_proprio_arquivo(self):
        proibidos = ("config.json", "ia_config.json", "bot_config.json", "voz.json", "navegador.json",
                     "tempos.jsonl", "cache_planos.json", "lembretes.sqlite3", "cache_voz", "modelos")
        arquivos = list(RAIZ_PROJETO.glob("*.py")) + list((RAIZ_PROJETO / "navegador").glob("*.py")) \
            + list((RAIZ_PROJETO / "voz").glob("*.py"))
        problemas = []
        for arquivo in arquivos:
            if arquivo.name == "caminhos.py":
                continue
            for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"(__file__|RAIZ|AQUI|PASTA)\b.*[\"'](" + "|".join(map(re.escape, proibidos)) + r")[\"']",
                             linha) and "caminhos." not in linha:
                    problemas.append(f"{arquivo.name}:{numero}: {linha.strip()}")
        self.assertEqual(problemas, [])


class RecursosTests(unittest.TestCase):
    def test_recursos_do_projeto_estao_em_recursos(self):
        self.assertTrue((caminhos.RECURSOS / "config.example.json").is_file())
        self.assertTrue((caminhos.RECURSOS / "comparador-vozes.html").is_file())
        self.assertEqual(len(list((caminhos.RECURSOS / "vozes-br").glob("*.mp3"))), 8)
        self.assertTrue(list((caminhos.RECURSOS / "vozes").glob("*.mp3")))
        for antigo in ("vozes", "vozes-br", "comparador-vozes.html", "config.example.json"):
            self.assertFalse((RAIZ_PROJETO / antigo).exists(), f"{antigo} ainda esta na raiz")


if __name__ == "__main__":
    unittest.main()
