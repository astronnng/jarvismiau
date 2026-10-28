# -*- coding: utf-8 -*-
"""
CAMINHOS - onde ficam os arquivos do Jarvis
--------------------------------------------
  dados/      tudo que o Jarvis grava no seu computador (ignorado pelo Git):
              config.json, ia_config.json, bot_config.json, voz.json, navegador.json,
              lembretes.sqlite3, tempos.jsonl, cache_planos.json, cache_voz/, modelos/
  recursos/   arquivos que fazem parte do projeto: config.example.json e as amostras de voz

Antes, cada um desses arquivos ficava solto na raiz. Na primeira abertura depois da mudanca,
`migrar` MOVE os que existirem para dados/ (nunca sobrescreve e nunca apaga). Se um arquivo
nao puder ser movido (por exemplo, o banco de lembretes em uso por outro Jarvis aberto),
ele continua sendo usado no lugar antigo ate a proxima abertura: nada some nem fica "vazio".

Variavel de ambiente JARVIS_DADOS: usa outra pasta no lugar de dados/ (sem migrar nada).
Serve para testes e para manter varias configuracoes separadas.
"""

import os
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
RECURSOS = RAIZ / "recursos"
_PERSONALIZADA = bool(os.environ.get("JARVIS_DADOS", "").strip())
DADOS = Path(os.environ["JARVIS_DADOS"]).expanduser() if _PERSONALIZADA else RAIZ / "dados"

# Arquivos e pastas que antes ficavam na raiz. O banco SQLite vai com seus arquivos auxiliares.
LEGADOS = (
    "config.json", "ia_config.json", "bot_config.json", "voz.json", "navegador.json",
    "tempos.jsonl", "cache_planos.json", "lembretes.sqlite3", "cache_voz", "modelos",
)
AUXILIARES_SQLITE = ("-wal", "-shm", "-journal")


def migrar(raiz=None, dados=None):
    """
    Move os arquivos antigos da raiz para dados/. Devolve {"movidos": [...], "pendentes": [...]}.
    `pendentes` sao os que existem nos dois lugares ou que nao puderam ser movidos agora.
    """
    raiz, dados = Path(raiz or RAIZ), Path(dados or DADOS)
    movidos, pendentes = [], []
    try:
        dados.mkdir(parents=True, exist_ok=True)
    except OSError:
        return {"movidos": movidos, "pendentes": list(LEGADOS)}
    for nome in LEGADOS:
        antigo, novo = raiz / nome, dados / nome
        if not antigo.exists():
            continue
        if novo.exists():                       # nunca sobrescreve: fica para o usuario decidir
            pendentes.append(nome)
            continue
        try:
            shutil.move(str(antigo), str(novo))
        except OSError:
            pendentes.append(nome)              # em uso: continua no lugar antigo por enquanto
            continue
        movidos.append(nome)
        if nome == "lembretes.sqlite3":
            for sufixo in AUXILIARES_SQLITE:
                extra = raiz / (nome + sufixo)
                if extra.exists() and not (dados / (nome + sufixo)).exists():
                    try:
                        shutil.move(str(extra), str(dados / (nome + sufixo)))
                    except OSError:
                        pendentes.append(nome + sufixo)
    return {"movidos": movidos, "pendentes": pendentes}


def dados(nome):
    """
    Caminho de um arquivo/pasta de dados do usuario. Normalmente e dados/<nome>; so devolve o lugar
    antigo (raiz) se a migracao ainda nao conseguiu mover um arquivo que existe la.
    """
    novo = DADOS / nome
    if _PERSONALIZADA or novo.exists():
        return novo
    antigo = RAIZ / nome
    return antigo if antigo.exists() else novo


if not _PERSONALIZADA:
    migrar()
else:
    DADOS.mkdir(parents=True, exist_ok=True)
