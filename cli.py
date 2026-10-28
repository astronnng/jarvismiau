# -*- coding: utf-8 -*-
"""Interface de terminal do Jarvis: apresentacao, entrada e sugestoes."""

import asyncio
import io
import os
import shutil
import sys
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# Paleta HUD: ciano como destaque, azul como estrutura, cinza-azulado como apoio.
CIANO = "#00e5ff"
AZUL = "#2f80ff"
AZUL_ESCURO = "#1b4f8f"
APOIO = "#5f87a8"
TEXTO = "#d9e8f2"
HORA = "#3b6a93"
MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

COMANDOS = [
    ("ajuda", "mostrar comandos disponiveis"),
    ("lembrete", "listar lembretes ativos"),
    ("lembretes", "listar lembretes ativos"),
    ("volume <0-100>", "definir volume do computador"),
    ("aumentar-volume", "aumentar o volume"),
    ("diminuir-volume", "diminuir o volume"),
    ("silenciar", "silenciar o computador"),
    ("play", "tocar ou pausar midia"),
    ("pausar", "pausar midia"),
    ("proxima", "proxima faixa"),
    ("anterior", "faixa anterior"),
    ("parar", "parar midia"),
    ("abrir <alvo>", "abrir site ou programa do catalogo"),
    ("confirmar <assunto>", "encerrar um alarme"),
    ("limpar", "limpar a tela"),
    ("sair", "encerrar o Jarvis"),
]


class JarvisCompleter(Completer):
    """Sugestoes de slash commands e alvos lidos do catalogo em tempo real."""

    def __init__(self, obter_alvos=None, obter_lembretes=None):
        self.obter_alvos = obter_alvos or (lambda: [])
        self.obter_lembretes = obter_lembretes or (lambda: [])

    def get_completions(self, document, complete_event):
        antes = document.text_before_cursor
        if not antes.startswith("/") or antes.startswith("//"):
            return

        corpo = antes[1:]
        if " " not in corpo:
            prefixo = corpo.lower()
            for comando, descricao in COMANDOS:
                nome = comando.split()[0]
                if nome.startswith(prefixo):
                    yield Completion(
                        nome[len(prefixo):],
                        display="/" + comando,
                        display_meta=descricao,
                    )
            return

        nome, _, argumento = corpo.partition(" ")
        if nome.lower() == "abrir":
            prefixo = argumento.casefold()
            for alvo in sorted(set(self.obter_alvos()), key=str.casefold):
                if alvo.casefold().startswith(prefixo):
                    yield Completion(alvo, start_position=-len(argumento), display=alvo)
        elif nome.lower() == "confirmar":
            prefixo = argumento.casefold()
            for assunto in self.obter_lembretes():
                if assunto.casefold().startswith(prefixo):
                    yield Completion(assunto, start_position=-len(argumento), display=assunto)
        elif nome.lower() == "volume" and not argumento.strip():
            for percentual in ("0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100"):
                yield Completion(percentual, display=percentual + "%")


class JarvisCLI:
    LARGURA_MAXIMA = 92

    def __init__(self, obter_alvos=None, obter_lembretes=None, obter_status=None):
        terminal_integrado = os.environ.get("JARVIS_INTERACTIVE") == "1"
        self.interativo = bool(
            terminal_integrado or getattr(sys.stdin, "isatty", lambda: False)()
        )
        terminal_com_cores = bool(
            terminal_integrado or getattr(sys.stdout, "isatty", lambda: False)()
        )
        terminal_sem_cores = bool(os.environ.get("NO_COLOR")) or (
            os.environ.get("TERM", "").lower() == "dumb" and not terminal_integrado
        )
        self.com_cores = self.interativo and terminal_com_cores and not terminal_sem_cores
        self.completer = JarvisCompleter(obter_alvos, obter_lembretes)
        self.obter_status = obter_status or (lambda: {})
        self.ia_ativa = False
        self.session = None
        self._status_cache = {"voz": "", "lembretes": []}
        self._status_em = None
        if self.interativo:
            self.session = PromptSession(
                completer=self.completer,
                complete_while_typing=True,
                complete_in_thread=True,
                reserve_space_for_menu=6,
                refresh_interval=1.0,
                style=Style.from_dict({
                    "prompt": f"bold {CIANO}",
                    "hora": HORA,
                    "ok": CIANO,
                    "acc": f"bold {AZUL}",
                    "sep": "#1f4468",
                    "bottom-toolbar": f"bg:#06121f {APOIO}",
                    "completion-menu.completion": "bg:#0b2038 #d8f3ff",
                    "completion-menu.completion.current": f"bg:{AZUL} #ffffff bold",
                    "completion-menu.meta.completion": "bg:#0b2038 #6f9bc0",
                    "completion-menu.meta.completion.current": "bg:#1f5fd0 #cfe6ff",
                    "scrollbar.background": "bg:#0b2038",
                    "scrollbar.button": f"bg:{AZUL_ESCURO}",
                }),
            )

    @classmethod
    def _largura(cls):
        colunas = shutil.get_terminal_size((100, 24)).columns
        return max(40, min(colunas - 1, cls.LARGURA_MAXIMA))

    @staticmethod
    def _rich_text(renderable, *, color=True, width=None):
        buffer = io.StringIO()
        console = Console(
            file=buffer,
            force_terminal=color,
            color_system="truecolor" if color else None,
            no_color=not color,
            highlight=False,
            width=width,
        )
        console.print(renderable)
        return buffer.getvalue().rstrip("\n")

    def _caixa(self):
        return box.ROUNDED if self.com_cores else box.ASCII

    def imprimir(self, renderable):
        texto = self._rich_text(renderable, color=self.com_cores, width=self._largura())
        encoding = getattr(sys.stdout, "encoding", None)
        if encoding:
            try:
                texto.encode(encoding)
            except UnicodeEncodeError:
                texto = texto.encode(encoding, errors="replace").decode(encoding)
        # A entrega de saidas durante a entrada passa por run_in_terminal.
        print(texto, flush=True)

    # ------------------------------------------------------------------ status
    def _status(self, forcar=False):
        """Estado do painel, em cache curto para a barra inferior nao pesar."""
        agora = time.monotonic()
        if forcar or self._status_em is None or agora - self._status_em > 3:
            try:
                dados = self.obter_status() or {}
            except Exception:
                dados = {}
            self._status_cache = {
                "voz": str(dados.get("voz") or ""),
                "lembretes": list(dados.get("lembretes") or []),
            }
            self._status_em = agora
        return self._status_cache

    @staticmethod
    def _proximo_alarme(lembretes):
        if not lembretes:
            return None
        item = min(lembretes, key=lambda x: x.get("vence_em") or 0)
        vence = item.get("vence_em")
        hora = time.strftime("%H:%M", time.localtime(vence)) if vence else "--:--"
        return hora, str(item.get("motivo") or "")

    def cabecalho(self, ia_ativa):
        self.ia_ativa = bool(ia_ativa)
        status = self._status(forcar=True)
        agora = time.localtime()
        data = f"{agora.tm_mday:02d} {MESES[agora.tm_mon - 1]} {agora.tm_year}"
        lembretes = status["lembretes"]

        reator = Text()
        reator.append("╭─◈─╮\n", style=AZUL)
        reator.append("│ ", style=AZUL)
        reator.append("◉", style=f"bold {CIANO}")
        reator.append(" │\n", style=AZUL)
        reator.append("╰─◈─╯", style=AZUL)

        def rotulo(nome):
            return Text(nome, style=APOIO)

        metricas = Table.grid(padding=(0, 2))
        for _ in range(4):
            metricas.add_column(no_wrap=True)
        metricas.add_row(
            rotulo("SISTEMA"), Text("● ONLINE", style=f"bold {CIANO}"),
            rotulo("IA"), Text("● ATIVA" if ia_ativa else "○ LOCAL",
                               style=f"bold {CIANO}" if ia_ativa else AZUL),
        )
        metricas.add_row(
            rotulo("VOZ"), Text(status["voz"] or "—", style=TEXTO),
            rotulo("ALARMES"), Text(str(len(lembretes)),
                                    style=f"bold {CIANO}" if lembretes else APOIO),
        )
        proximo = self._proximo_alarme(lembretes)
        metricas.add_row(
            rotulo("PRÓXIMO"),
            Text(f"{proximo[0]} · {proximo[1]}"[:34] if proximo else "nenhum agendado",
                 style=TEXTO if proximo else APOIO),
            Text(""), Text(""),
        )

        titulo = Text.assemble(
            ("J.A.R.V.I.S", f"bold {TEXTO}"),
            ("  PERSONAL ASSISTANT", AZUL),
        )
        info = Table.grid()
        info.add_column()
        info.add_row(titulo)
        info.add_row(metricas)

        corpo = Table.grid(padding=(0, 3))
        corpo.add_column(no_wrap=True)
        corpo.add_column()
        corpo.add_row(reator, info)

        self.imprimir(Panel(
            corpo,
            title=Text.assemble(("▌", AZUL), (" SYS.LINK ", f"bold {CIANO}"), ("▐", AZUL)),
            title_align="left",
            subtitle=Text(f"{data} · {time.strftime('%H:%M', agora)}", style=APOIO),
            subtitle_align="right",
            border_style=AZUL,
            box=self._caixa(),
            padding=(0, 2),
            width=self._largura(),
            safe_box=False,
        ))
        self.imprimir(Text("  ▸ digite / para comandos", style=APOIO))

    # ---------------------------------------------------------------- mensagens
    def usuario(self, texto):
        self.mensagem("VOCÊ", f"bold {AZUL}", texto)

    def jarvis(self, texto):
        self.mensagem("JARVIS", f"bold {CIANO}", texto)

    def mensagem(self, autor, estilo, texto):
        grade = Table.grid(padding=(0, 1), expand=True)
        grade.add_column(no_wrap=True)
        grade.add_column(no_wrap=True)
        grade.add_column(ratio=1)
        grade.add_row(
            Text(time.strftime("%H:%M"), style=HORA),
            Text.assemble((f"{autor:<6} ", estilo), ("│", AZUL_ESCURO)),
            Text(str(texto), style=TEXTO),
        )
        self.imprimir(grade)

    def alarme(self, texto):
        self.imprimir(Panel(
            Text.assemble(
                ("◉  ALARME", "bold #ff4568"),
                ("  /  ", APOIO),
                (texto, "bold white"),
            ),
            title=Text("▌ ATENÇÃO ▐", style="bold #ff4568"),
            title_align="left",
            border_style="#ff4568",
            box=self._caixa(),
            padding=(0, 2),
            width=self._largura(),
            safe_box=False,
        ))

    def erro(self, texto):
        self.imprimir(Panel(
            Text(str(texto), style="#ffc857"),
            title=Text("▌ AVISO ▐", style="bold #ffc857"),
            title_align="left",
            border_style="#ffc857",
            box=self._caixa(),
            padding=(0, 2),
            width=self._largura(),
            safe_box=False,
        ))

    async def imprimir_durante_entrada(self, renderizar):
        """Suspende e redesenha o prompt preservando o buffer digitado."""
        await run_in_terminal(renderizar)

    def ajuda(self):
        corpo = Table.grid(padding=(0, 3))
        corpo.add_column(style=f"bold {CIANO}", min_width=22)
        corpo.add_column(style=TEXTO)
        for comando, descricao in COMANDOS:
            corpo.add_row("/" + comando, descricao)
        self.imprimir(Panel(
            corpo,
            title=Text.assemble(
                ("▌", AZUL), (" PROTOCOLO DE COMANDOS ", f"bold {CIANO}"), ("▐", AZUL)),
            title_align="left",
            border_style=AZUL,
            box=self._caixa(),
            padding=(0, 2),
            width=self._largura(),
            safe_box=False,
        ))

    def limpar(self):
        if self.interativo:
            os.system("cls" if os.name == "nt" else "clear")
            self.cabecalho(self.ia_ativa)
        else:
            print("\n" * 2)

    # ------------------------------------------------------------------ entrada
    def _mensagem_prompt(self):
        return HTML(
            f"<hora>{time.strftime('%H:%M')}</hora> <prompt>VOCÊ   │ </prompt>"
        )

    def _barra_inferior(self):
        alarmes = len(self._status()["lembretes"])
        ia = "ATIVA" if self.ia_ativa else "LOCAL"
        return HTML(
            f" <ok>●</ok> ONLINE <sep>│</sep> IA <acc>{ia}</acc> "
            f"<sep>│</sep> ALARMES <acc>{alarmes}</acc> "
            f"<sep>│</sep> <acc>{time.strftime('%H:%M:%S')}</acc>  <sep>▏</sep>  "
            "<b>/</b> comandos  <b>Tab</b> completar  <b>Ctrl+C</b> sair "
        )

    async def entrada(self, ao_aguardar=None):
        if not self.interativo:
            return await asyncio.to_thread(input, "VOCÊ  >  ")

        monitor = None

        async def monitorar():
            while True:
                await asyncio.sleep(0.2)
                await ao_aguardar()

        def iniciar_monitor():
            nonlocal monitor
            if ao_aguardar is not None:
                # pre_run roda dentro do contexto da Application; a tarefa
                # herda esse contexto para run_in_terminal suspender o prompt.
                monitor = asyncio.create_task(monitorar())

        try:
            return await self.session.prompt_async(
                self._mensagem_prompt,
                bottom_toolbar=self._barra_inferior,
                pre_run=iniciar_monitor,
            )
        finally:
            if monitor is not None:
                monitor.cancel()
                try:
                    await monitor
                except asyncio.CancelledError:
                    pass
