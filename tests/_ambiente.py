"""
Isola a suite dos dados REAIS do usuario e do mundo externo.

Cada arquivo de teste importa este modulo antes de qualquer modulo do projeto.

1) JARVIS_DADOS aponta para uma pasta temporaria: nada de dados/ (config, lembretes, voz.json, cache...)
   e lido, criado ou migrado durante os testes. A pasta some quando o processo termina.

2) Alarme de I/O real: abrir o navegador, abrir arquivo/URL pelo Windows ou iniciar um programa de
   verdade dentro de um teste e sempre um erro. Os testes que precisam disso trocam a funcao por um
   gravador (patch), que tem prioridade sobre este alarme. Se uma reorganizacao do codigo fizer um
   patch mirar o lugar errado, o teste deixa de passar em silencio e falha apontando o culpado.
   Subprocessos do proprio Python (sys.executable) continuam permitidos.
"""

import atexit
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser

_pasta = tempfile.mkdtemp(prefix="jarvis-testes-")
os.environ["JARVIS_DADOS"] = _pasta
atexit.register(shutil.rmtree, _pasta, ignore_errors=True)


def _proibido(o_que):
    def alarme(*args, **kwargs):
        raise AssertionError(
            f"I/O REAL durante um teste: {o_que}{args[:1]!r}. Troque por um patch (gravador) no lugar onde o "
            "codigo o procura; se acabou de mover codigo, o patch provavelmente mira o modulo antigo.")
    return alarme


for _nome in ("open", "open_new", "open_new_tab"):
    setattr(webbrowser, _nome, _proibido(f"webbrowser.{_nome}"))
if hasattr(os, "startfile"):
    os.startfile = _proibido("os.startfile")

_popen_original = subprocess.Popen


class _PopenVigiado(_popen_original):
    def __init__(self, args, *a, **k):
        primeiro = args[0] if isinstance(args, (list, tuple)) and args else args
        if str(primeiro) != sys.executable:
            raise AssertionError(
                f"I/O REAL durante um teste: subprocess.Popen({str(args)[:80]!r}). Troque por um patch (gravador); "
                "so subprocessos do proprio Python (sys.executable) sao permitidos.")
        super().__init__(args, *a, **k)


subprocess.Popen = _PopenVigiado
