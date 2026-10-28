import _ambiente  # noqa: F401  (isola os dados do usuario; deve ser o primeiro import)

"""
CONTRATO ENTRE OS MODULOS - rede de seguranca da reorganizacao (fase 3)

Cada lista abaixo e o conjunto de nomes que OUTROS arquivos (codigo e testes) esperam encontrar em um
modulo. Foram levantados lendo o codigo: `jarvis.<nome>` em telegram_bot.py / escolher_voz.py / testes,
`ctx.<nome>` nas acoes (ctx e o proprio modulo jarvis), e as chamadas `modulo.funcao` de jarvis.py.

Se a fase 3 mover algo de lugar, estes testes falham de proposito: ou o nome continua disponivel
(reexportado), ou a lista e os usuarios dele sao atualizados juntos, de forma consciente.
Tambem ha um teste de importacao de cada modulo em um interpretador novo, para pegar importacao
circular e efeito colateral que so aparecem dependendo de quem importa primeiro.
"""

import importlib
import os
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# modulo -> nomes que os outros arquivos esperam dele
CONTRATO = {
    "jarvis": (
        # usados por telegram_bot.py e escolher_voz.py
        "ENTRADA_BLOQUEADA", "IDIOMA_MICROFONE", "PERFIL", "PERFIS", "PERMITIR_ACOES_ARRISCADAS", "VOZ",
        "gerar_mp3", "responder", "falar",
        # usados pelas acoes (ctx e o proprio modulo jarvis)
        "normalizar", "SITES", "PROGRAMAS", "IDIOMA_FALA", "perguntar_sim_nao", "abrir_programa",
        # usados pelos testes e pelos outros modulos
        "CACHE_DIR", "CAPTURADO", "CAPTURAR", "MODO_TEXTO", "USAR_IA", "R_CONFIRMAR_LEMBRETE",
        "_adquirir_lock_instancia", "_liberar_lock_instancia", "_instancia_lock", "_aplicar_perfil_padrao",
        "_atalho_navegador", "_tratar_alarme", "_cache_planos", "_cli", "_executar_comando_slash",
        "_falar_audio", "_falar_audio_serializado", "_falar_neural", "_falar_windows", "_grupos_ia",
        "_lembrar", "_ler_texto_com_alarmas", "_notificar_alarmas_durante_entrada", "_perfil_salvo",
        "_processar", "_servico_alarmes", "_status_painel", "_ultimo_uso_navegador", "_tocar_wav",
        "atualizar_catalogos", "cadastrar_entrada_catalogo", "executar_acao", "processar",
        "processar_com_ia", "tarefa_lembrete", "tarefa_hora", "tarefa_data", "tarefa_clima",
        "tarefa_pesquisar", "tarefa_youtube", "tarefa_bloquear", "tentar_abrir", "perguntar_sim_nao",
        # modulos que o jarvis.py expoe como atributo (tests fazem patch.object(jarvis, "lembretes"...))
        "acoes", "cerebro", "catalogo", "lembretes", "voz_pacote", "navegador_ponte", "cache_planos",
        "linguagem", "tempos", "caminhos",
        # pontos de entrada de `python jarvis.py`
        "main", "mostrar_status_ia",
    ),
    "acoes": ("CATALOGO", "acao", "listar_para_ia", "executar", "existe", "eh_arriscada", "grupo_de",
              "assinatura", "confirmar_lembrete", "armazenamento_lembretes"),
    "cerebro": ("CONFIG_PATH", "carregar_config", "salvar_config", "chave", "disponivel", "modelos",
                "montar_prompt", "interpretar", "responder_json", "conversar", "testar_chave"),
    "lembretes": ("DB_PATH", "Lembretes", "ServicoAlarmes", "formatar_horario", "normalizar"),
    "catalogo": ("CONFIG_PATH", "EXEMPLO_PATH", "carregar", "salvar_entrada", "validar_entrada"),
    "cli": ("JarvisCLI", "JarvisCompleter", "COMANDOS"),
    "navegador": ("iniciar", "parar", "ponte", "definir_ponte", "conectado", "enviar", "ErroNavegador", "Ponte"),
    "voz": ("motor", "motor_ativo", "falar", "resumo_curto", "preaquecer_em_segundo_plano", "config",
            "MotorKokoro", "ErroKokoro"),
    "tempos": ("ARQUIVO", "iniciar", "caminho", "extra", "medir", "finalizar", "ler", "resumo"),
    "cache_planos": ("ARQUIVO", "CachePlanos", "chave", "cacheavel"),
    "linguagem": ("tirar_enchimento", "normalizar"),
    "caminhos": ("RAIZ", "DADOS", "RECURSOS", "dados", "migrar", "LEGADOS"),
    "lancador": ("MODOS", "MENU", "interpretar", "montar", "escolher_modo", "executar", "main"),
}

# Modulos que precisam importar sozinhos em um interpretador novo (a ordem de importacao importa)
MODULOS_IMPORTAVEIS = (
    "caminhos", "linguagem", "tempos", "cache_planos", "lembretes", "catalogo", "cerebro", "acoes",
    "acoes_navegador", "cli", "jarvis", "lancador", "navegador", "navegador.atalhos", "navegador.generico",
    "navegador.ponte", "voz", "voz.comandos", "voz.instalar", "voz.kokoro_motor",
    "telegram_bot", "configurar_ia", "escolher_voz",
)


class ContratoTests(unittest.TestCase):
    def test_cada_modulo_oferece_os_nomes_que_os_outros_esperam(self):
        faltando = {}
        for nome_modulo, nomes in CONTRATO.items():
            modulo = importlib.import_module(nome_modulo)
            ausentes = [n for n in nomes if not hasattr(modulo, n)]
            if ausentes:
                faltando[nome_modulo] = ausentes
        self.assertEqual(faltando, {}, "nomes que sumiram (reexporte ou atualize os usuarios juntos)")

    def test_ctx_das_acoes_e_o_modulo_jarvis(self):
        # acoes.executar(nome, params, ctx=<modulo jarvis>): toda acao que usa ctx.X precisa que jarvis.X exista
        import re
        usados = set()
        for arquivo in ("acoes.py", "acoes_navegador.py"):
            usados |= set(re.findall(r"\bctx\.([A-Za-z_]+)", (RAIZ / arquivo).read_text(encoding="utf-8")))
        import jarvis
        self.assertEqual([n for n in sorted(usados) if not hasattr(jarvis, n)], [])

    def test_todo_telegram_bot_e_escolher_voz_enxergam_o_que_usam_de_jarvis(self):
        import re
        import jarvis
        usados = set()
        for arquivo in ("telegram_bot.py", "escolher_voz.py"):
            usados |= set(re.findall(r"\bjarvis\.([A-Za-z_][A-Za-z0-9_]*)",
                                     (RAIZ / arquivo).read_text(encoding="utf-8")))
        usados -= {"py", "mp3"}                               # texto de comentario, nao nomes de codigo
        self.assertEqual([n for n in sorted(usados) if not hasattr(jarvis, n)], [])


class AlarmeDeIoRealTests(unittest.TestCase):
    """O alarme de _ambiente.py precisa funcionar, senao um patch no lugar errado passaria em silencio."""

    def test_abrir_navegador_de_verdade_falha(self):
        import webbrowser
        for funcao in (webbrowser.open, webbrowser.open_new, webbrowser.open_new_tab):
            with self.assertRaises(AssertionError) as erro:
                funcao("https://exemplo.com")
            self.assertIn("I/O REAL", str(erro.exception))

    def test_iniciar_programa_de_verdade_falha_mas_python_pode(self):
        with self.assertRaises(AssertionError):
            subprocess.Popen(["notepad.exe"])
        with self.assertRaises(AssertionError):
            subprocess.run("start spotify:", shell=True)
        resultado = subprocess.run([sys.executable, "-c", "print('ok')"], capture_output=True, text=True)
        self.assertEqual(resultado.stdout.strip(), "ok")

    def test_um_patch_tem_prioridade_sobre_o_alarme(self):
        import webbrowser
        from unittest.mock import patch
        with patch.object(webbrowser, "open") as aberto:
            webbrowser.open("https://exemplo.com")
        aberto.assert_called_once_with("https://exemplo.com")

    @unittest.skipUnless(hasattr(os, "startfile"), "os.startfile so existe no Windows")
    def test_os_startfile_falha(self):
        with self.assertRaises(AssertionError):
            os.startfile("C:\\Windows")


class ImportacaoIsoladaTests(unittest.TestCase):
    """Cada modulo, sozinho, em um Python novo: pega ciclos e efeitos colaterais de importacao."""

    def importar(self, modulo):
        saida = subprocess.run(
            [sys.executable, "-c", f"import {modulo}"], cwd=RAIZ, capture_output=True, text=True, timeout=120,
            env=dict(os.environ))                              # herda JARVIS_DADOS (isolado)
        return modulo, saida.returncode, saida.stderr.strip().splitlines()[-1:] or [""]

    def test_cada_modulo_importa_sozinho_e_nao_cria_arquivos_na_raiz(self):
        antes = {n for n in os.listdir(RAIZ) if n != "__pycache__"}
        with ThreadPoolExecutor(max_workers=4) as pool:
            resultados = list(pool.map(self.importar, MODULOS_IMPORTAVEIS))
        falhas = [(m, erro) for m, codigo, erro in resultados if codigo != 0]
        self.assertEqual(falhas, [])
        depois = {n for n in os.listdir(RAIZ) if n != "__pycache__"}
        self.assertEqual(sorted(depois - antes), [], "importar um modulo criou algo na raiz do projeto")

    def test_ponto_de_entrada_do_lancador(self):
        saida = subprocess.run([sys.executable, "lancador.py", "ajuda"], cwd=RAIZ, capture_output=True,
                               text=True, timeout=60, encoding="utf-8",
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertEqual(saida.returncode, 0)
        self.assertIn("Uso: Jarvis.bat", saida.stdout)


if __name__ == "__main__":
    unittest.main()
