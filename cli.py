# -*- coding: utf-8 -*-
"""Interface de terminal do Jarvis: apresentacao, entrada e sugestoes."""

import asyncio
import io
import os
import sys

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
    def __init__(self, obter_alvos=None, obter_lembretes=None):
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
        self.ia_ativa = False
        self.session = None
        if self.interativo:
            self.session = PromptSession(
                completer=self.completer,
                complete_while_typing=True,
                complete_in_thread=True,
                reserve_space_for_menu=6,
                style=Style.from_dict({
                    "prompt": "bold #00d7ff",
                    "bottom-toolbar": "bg:#071626 #6b8ba4",
                    "completion-menu.completion": "bg:#102a43 #d8f3ff",
                    "completion-menu.completion.current": "bg:#00a6c7 #00131d bold",
                    "completion-menu.meta.completion": "bg:#102a43 #81a9c5",
                    "completion-menu.meta.completion.current": "bg:#00a6c7 #003244",
                }),
            )

    @staticmethod
    def _rich_text(renderable, *, color=True):
        buffer = io.StringIO()
        console = Console(
            file=buffer,
            force_terminal=color,
            color_system="truecolor" if color else None,
            no_color=not color,
            highlight=False,
        )
        console.print(renderable)
        return buffer.getvalue().rstrip("\n")

    def imprimir(self, renderable):
        texto = self._rich_text(renderable, color=self.com_cores)
        encoding = getattr(sys.stdout, "encoding", None)
        if encoding:
            try:
                texto.encode(encoding)
            except UnicodeEncodeError:
                texto = texto.encode(encoding, errors="replace").decode(encoding)
        # A entrega de saidas durante a entrada passa por run_in_terminal.
        print(texto, flush=True)

    def cabecalho(self, ia_ativa):
        self.ia_ativa = bool(ia_ativa)
        titulo = Text.assemble(
            ("◈  ", "bold bright_cyan"),
            ("J.A.R.V.I.S.", "bold white"),
            ("  /  PERSONAL ASSISTANT", "bright_blue"),
        )
        estado = Text("● ONLINE", style="bold green")
        estado.append("   ┊   IA: ", style="dim")
        estado.append("ATIVA" if ia_ativa else "LOCAL", style="bold cyan")
        estado.append("   ┊   / AJUDA", style="dim")
        self.imprimir(Panel(
            Text.assemble(titulo, "\n", estado),
            border_style="#00c9ff",
            box=box.ROUNDED if self.com_cores else box.ASCII,
            padding=(0, 1),
            expand=False,
        ))

    def usuario(self, texto):
        self.mensagem("VOCÊ", "bold bright_blue", texto)

    def jarvis(self, texto):
        self.mensagem("JARVIS", "bold cyan", texto)

    def mensagem(self, autor, estilo, texto):
        prefixo = Text(f"{autor:<8}", style=estilo)
        prefixo.append("│ ", style="dim")
        self.imprimir(Text.assemble(prefixo, Text(str(texto), style="#d9e8f2")))

    def alarme(self, texto):
        self.imprimir(Panel(
            Text.assemble(
                ("◉  ALARME", "bold bright_red"),
                ("  /  LEMBRETE  ", "dim"),
                (texto, "bold white"),
            ),
            title="[bold bright_red]ATENÇÃO[/]",
            border_style="#ff4568",
            box=box.ROUNDED if self.com_cores else box.ASCII,
            padding=(0, 1),
            expand=False,
        ))

    def erro(self, texto):
        self.imprimir(Panel(
            Text(str(texto), style="yellow"),
            title="[bold yellow]AVISO[/]",
            border_style="yellow",
            box=box.ROUNDED if self.com_cores else box.ASCII,
            padding=(0, 1),
            expand=False,
        ))

    async def imprimir_durante_entrada(self, renderizar):
        """Suspende e redesenha o prompt preservando o buffer digitado."""
        await run_in_terminal(renderizar)

    def ajuda(self):
        corpo = Table.grid(padding=(0, 2))
        corpo.add_column(style="bold cyan", min_width=25)
        corpo.add_column(style="white")
        for comando, descricao in COMANDOS:
            corpo.add_row("/" + comando, descricao)
        self.imprimir(Panel(
            corpo,
            title="[bold cyan]PROTOCOLO DE COMANDOS[/]",
            border_style="blue",
            box=box.ROUNDED if self.com_cores else box.ASCII,
            expand=False,
        ))

    def limpar(self):
        if self.interativo:
            os.system("cls" if os.name == "nt" else "clear")
            self.cabecalho(self.ia_ativa)
        else:
            print("\n" * 2)

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
                HTML("<prompt>VOCÊ   │  </prompt>"),
                bottom_toolbar=HTML(" <b>/ajuda</b> comandos  ·  <b>setas</b> navegar  ·  <b>Tab</b> completar  ·  <b>Ctrl+C</b> sair "),
                pre_run=iniciar_monitor,
            )
        finally:
            if monitor is not None:
                monitor.cancel()
                try:
                    await monitor
                except asyncio.CancelledError:
                    pass
