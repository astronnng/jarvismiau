# -*- coding: utf-8 -*-
"""Armazenamento persistente e disparo serial dos lembretes do Jarvis."""

import sqlite3
import math
import threading
import time
import unicodedata
from contextlib import contextmanager
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "lembretes.sqlite3"
INTERVALO_ALARME_SEGUNDOS = 30


def normalizar(texto):
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())


class Lembretes:
    def __init__(self, caminho=DB_PATH):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.inicializar()

    @contextmanager
    def _conectar(self):
        con = sqlite3.connect(str(self.caminho), timeout=10)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def inicializar(self):
        with self._conectar() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS lembretes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    motivo TEXT NOT NULL,
                    criado_em REAL NOT NULL,
                    vence_em REAL NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'pendente',
                    ultimo_alarme REAL
                )
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_lembretes_ativos
                ON lembretes (estado, vence_em)
            """)

    def criar(self, motivo, minutos, agora=None):
        agora = time.time() if agora is None else float(agora)
        minutos = float(minutos)
        if not math.isfinite(minutos) or minutos <= 0:
            raise ValueError("O intervalo precisa ser um numero positivo e finito.")
        vence = agora + minutos * 60
        with self._conectar() as con:
            cur = con.execute(
                "INSERT INTO lembretes (motivo, criado_em, vence_em) VALUES (?, ?, ?)",
                (str(motivo).strip() or "o lembrete", agora, vence),
            )
            return {"id": cur.lastrowid, "motivo": str(motivo).strip() or "o lembrete",
                    "criado_em": agora, "vence_em": vence, "estado": "pendente"}

    def listar(self):
        with self._conectar() as con:
            rows = con.execute(
                "SELECT id, motivo, criado_em, vence_em, estado, ultimo_alarme "
                "FROM lembretes WHERE estado IN ('pendente', 'tocando') ORDER BY vence_em, id"
            ).fetchall()
        return [dict(row) for row in rows]

    def tem_alarmas_tocando(self):
        with self._conectar() as con:
            row = con.execute(
                "SELECT 1 FROM lembretes WHERE estado='tocando' LIMIT 1"
            ).fetchone()
        return row is not None

    def marcar_alarmas(self, agora=None, intervalo=INTERVALO_ALARME_SEGUNDOS):
        """Marca novos vencidos e alarmes que devem repetir, em ordem de vencimento."""
        agora = time.time() if agora is None else float(agora)
        repeticao_ate = agora - float(intervalo)
        with self._conectar() as con:
            con.execute("BEGIN IMMEDIATE")
            novos = con.execute(
                "SELECT id, motivo, criado_em, vence_em, 'tocando' AS estado, ? AS ultimo_alarme "
                "FROM lembretes WHERE estado='pendente' AND vence_em<=? ORDER BY vence_em, id",
                (agora, agora),
            ).fetchall()
            con.execute(
                "UPDATE lembretes SET estado='tocando', ultimo_alarme=? "
                "WHERE estado='pendente' AND vence_em<=?",
                (agora, agora),
            )
            repetidos = con.execute(
                "SELECT id, motivo, criado_em, vence_em, estado, ultimo_alarme "
                "FROM lembretes WHERE estado='tocando' AND ultimo_alarme<=? "
                "ORDER BY vence_em, id",
                (repeticao_ate,),
            ).fetchall()
            if repetidos:
                con.executemany(
                    "UPDATE lembretes SET ultimo_alarme=? WHERE id=?",
                    [(agora, row["id"]) for row in repetidos],
                )
        return [dict(row) for row in novos] + [dict(row) for row in repetidos]

    def confirmar(self, assunto, agora=None):
        """Encerra alarmes que estao tocando (ou ja venceram). Devolve a frase a falar."""
        return self._confirmar(assunto, agora)[1]

    def _confirmar(self, assunto, agora=None):
        """(status, frase): status 'ok', 'ambiguo' ou 'nada' (nenhum alarme tocando casou)."""
        agora = time.time() if agora is None else float(agora)
        chave = normalizar(assunto)
        with self._conectar() as con:
            rows = con.execute(
                "SELECT id, motivo, estado FROM lembretes WHERE estado IN ('pendente', 'tocando') "
                "AND (estado='tocando' OR vence_em<=?) ORDER BY vence_em, id",
                (agora,),
            ).fetchall()
            exatos = []
            if not chave:
                candidatos = [row for row in rows if row["estado"] == "tocando"]
                if len(candidatos) > 1:
                    assuntos = "; ".join(row["motivo"] for row in candidatos)
                    return "ambiguo", (f"Ha mais de um alarme tocando: {assuntos}. "
                                       "Diga qual deseja encerrar, senhor.")
            else:
                exatos = [row for row in rows if normalizar(row["motivo"]) == chave]
                candidatos = exatos or [row for row in rows if chave in normalizar(row["motivo"])]
            if not candidatos:
                return "nada", "Nao encontrei alarme ativo com esse assunto, senhor."
            if len(candidatos) > 1 and not exatos:
                assuntos = "; ".join(row["motivo"] for row in candidatos)
                return "ambiguo", f"Encontrei mais de um alarme: {assuntos}. Diga o assunto completo, senhor."
            con.executemany("UPDATE lembretes SET estado='concluido' WHERE id=?",
                            [(row["id"],) for row in candidatos])
        if len(candidatos) > 1:
            return "ok", f"Alarmes de {candidatos[0]['motivo']} confirmados, senhor."
        return "ok", f"Alarme de {candidatos[0]['motivo']} confirmado, senhor."

    def encerrar(self, assunto, agora=None):
        """
        "Encerrar o lembrete": primeiro o alarme que esta tocando; se nenhum casar, cancela um
        lembrete FUTURO (pelo assunto, ou o unico que existir). Devolve a frase a falar.
        """
        agora = time.time() if agora is None else float(agora)
        status, frase = self._confirmar(assunto, agora)
        if status != "nada":
            return frase
        chave = normalizar(assunto)
        with self._conectar() as con:
            futuros = con.execute(
                "SELECT id, motivo FROM lembretes WHERE estado='pendente' AND vence_em>? "
                "ORDER BY vence_em, id", (agora,)).fetchall()
            if not futuros:
                return frase if chave else "Nao ha alarme tocando nem lembrete pendente, senhor."
            if chave:
                exatos = [r for r in futuros if normalizar(r["motivo"]) == chave]
                candidatos = exatos or [r for r in futuros if chave in normalizar(r["motivo"])]
                if not candidatos:
                    return frase
                if len(candidatos) > 1 and not exatos:
                    assuntos = "; ".join(r["motivo"] for r in candidatos)
                    return f"Encontrei mais de um lembrete: {assuntos}. Diga o assunto completo, senhor."
            elif len(futuros) == 1:
                candidatos = futuros
            else:
                assuntos = "; ".join(r["motivo"] for r in futuros)
                return f"Tenho {len(futuros)} lembretes pendentes: {assuntos}. Diga qual cancelar, senhor."
            con.executemany("UPDATE lembretes SET estado='cancelado' WHERE id=?",
                            [(r["id"],) for r in candidatos])
        return f"Lembrete de {candidatos[0]['motivo']} cancelado, senhor."


class ServicoAlarmes:
    """Verifica vencimentos em background; a thread principal entrega os alarmes."""

    def __init__(self, ctx=None, caminho=DB_PATH, intervalo=INTERVALO_ALARME_SEGUNDOS):
        self.store = Lembretes(caminho)
        self.intervalo = float(intervalo)
        self._parar = threading.Event()
        self._thread = None
        self._pendentes = {}
        self._erros = []
        self._lock = threading.Lock()

    def iniciar(self):
        if self._thread and self._thread.is_alive():
            return self
        self._parar.clear()
        self._thread = threading.Thread(target=self._rodar, name="jarvis-alarmes", daemon=True)
        self._thread.start()
        return self

    def parar(self):
        self._parar.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def drenar(self):
        """Devolve os alarmes aguardando exibicao/fala, sem repetir itens enfileirados."""
        with self._lock:
            itens = list(self._pendentes.values())
            self._pendentes.clear()
        return itens

    def drenar_erros(self):
        with self._lock:
            erros = self._erros[:]
            self._erros.clear()
        return erros

    def _rodar(self):
        while not self._parar.is_set():
            try:
                vencidos = self.store.marcar_alarmas(intervalo=self.intervalo)
                if vencidos:
                    with self._lock:
                        for lembrete in vencidos:
                            self._pendentes.setdefault(lembrete["id"], lembrete)
            except Exception as erro:
                with self._lock:
                    self._erros.append(str(erro))
            self._parar.wait(1)


def formatar_horario(timestamp):
    from datetime import datetime
    return datetime.fromtimestamp(float(timestamp)).strftime("%d/%m %H:%M")

