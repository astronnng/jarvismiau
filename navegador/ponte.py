# -*- coding: utf-8 -*-
"""
PONTE - servidor local que conversa com a extensao do navegador
----------------------------------------------------------------
Protocolo (HTTP em 127.0.0.1, long polling; sem dependencias externas):

  GET  /proximo     a extensao pede o proximo comando. Responde 200 com
                    {"id", "cmd", "args"} ou 204 se nada chegou em ESPERA_POLL s.
  POST /resultado   a extensao devolve {"id", "ok", "dados" | "erro"}.

Toda chamada exige o cabecalho X-Jarvis-Token, o Host 127.0.0.1/localhost e, quando
houver, Origin de extensao. Quem usa esta classe so precisa de `enviar()`.
"""

import hmac
import json
import queue
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ESPERA_POLL = 20          # segundos que /proximo segura a conexao
TOLERANCIA_CONEXAO = 15   # segundos sem contato ate considerar a extensao desconectada
LIMITE_CORPO = 5 * 1024 * 1024

MSG_DESCONECTADO = ("A extensao do navegador nao esta conectada, senhor. "
                    "Veja o passo a passo em docs/NAVEGADOR.md.")


class ErroNavegador(Exception):
    """Falha ao falar com o navegador. A mensagem ja e uma frase para o usuario."""


class Ponte:
    def __init__(self, porta, token, espera_poll=ESPERA_POLL):
        self.porta = porta
        self.token = token
        self.espera_poll = espera_poll
        self._fila = queue.Queue()
        self._pendentes = {}
        self._lock = threading.Lock()
        self._polls_ativos = 0
        self._ultimo_contato = 0.0
        self._servidor = None
        self._thread = None

    # ------------------------------------------------------------ ciclo de vida
    def iniciar(self):
        """Sobe o servidor em segundo plano. Devolve False se a porta estiver ocupada."""
        if self._servidor is not None:
            return True
        ponte = self

        class Manipulador(_Manipulador):
            origem_ponte = ponte

        try:
            self._servidor = ThreadingHTTPServer(("127.0.0.1", self.porta), Manipulador)
        except OSError:
            self._servidor = None
            return False
        self._servidor.daemon_threads = True
        self.porta = self._servidor.server_address[1]
        self._thread = threading.Thread(
            target=self._servidor.serve_forever, name="jarvis-ponte", daemon=True)
        self._thread.start()
        return True

    def parar(self):
        if self._servidor is not None:
            self._servidor.shutdown()
            self._servidor.server_close()
            self._servidor = None

    # ------------------------------------------------------------------ estado
    def ativa(self):
        return self._servidor is not None

    def conectado(self):
        """Extensao esperando comando, executando um (pode demorar: pagina carregando) ou vista ha pouco."""
        with self._lock:
            return (self._polls_ativos > 0
                    or bool(self._pendentes)
                    or (time.monotonic() - self._ultimo_contato) < TOLERANCIA_CONEXAO)

    # ------------------------------------------------------------ uso principal
    def enviar(self, cmd, timeout=15, **args):
        """Executa um comando no navegador e devolve os dados, ou levanta ErroNavegador."""
        if not self.ativa():
            raise ErroNavegador("A ponte do navegador nao esta ativa (a porta pode estar em uso).")
        if not self.conectado():
            raise ErroNavegador(MSG_DESCONECTADO)

        id_comando = uuid.uuid4().hex[:8]
        item = {"evento": threading.Event(), "resposta": None}
        with self._lock:
            self._pendentes[id_comando] = item
        self._fila.put({"id": id_comando, "cmd": cmd, "args": args})

        if not item["evento"].wait(timeout):
            with self._lock:
                self._pendentes.pop(id_comando, None)
            raise ErroNavegador("O navegador nao respondeu a tempo, senhor.")

        resposta = item["resposta"] or {}
        if not resposta.get("ok"):
            raise ErroNavegador(_frase_de_erro(resposta.get("erro")))
        return resposta.get("dados")

    # ----------------------------------------------- usados pelo manipulador HTTP
    def _proximo(self):
        """Espera um comando valido (descarta os que ja expiraram). None se nada veio."""
        with self._lock:
            self._polls_ativos += 1
        try:
            fim = time.monotonic() + self.espera_poll
            while True:
                restante = fim - time.monotonic()
                if restante <= 0:
                    return None
                try:
                    comando = self._fila.get(timeout=restante)
                except queue.Empty:
                    return None
                with self._lock:
                    if comando["id"] in self._pendentes:
                        return comando
        finally:
            with self._lock:
                self._polls_ativos -= 1
                self._ultimo_contato = time.monotonic()

    def _registrar_resultado(self, corpo):
        with self._lock:
            self._ultimo_contato = time.monotonic()
            item = self._pendentes.pop(corpo.get("id"), None)
        if item is not None:
            item["resposta"] = corpo
            item["evento"].set()


def _frase_de_erro(erro):
    erro = str(erro or "falha desconhecida")
    return f"Nao consegui no navegador, senhor: {erro}."


class _Manipulador(BaseHTTPRequestHandler):
    origem_ponte = None
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):      # silencioso: o terminal e do Jarvis
        pass

    def _autorizado(self):
        ponte = self.origem_ponte
        host = self.headers.get("Host", "").split(":")[0].lower()
        if host not in ("127.0.0.1", "localhost"):
            return False                # protege contra DNS rebinding
        origem = self.headers.get("Origin", "")
        if origem and not origem.startswith(("chrome-extension://", "moz-extension://")):
            return False                # uma pagina web comum nao pode usar esta ponte
        recebido = self.headers.get("X-Jarvis-Token", "")
        return hmac.compare_digest(recebido.encode(), ponte.token.encode())

    def _responder(self, codigo, corpo=None):
        dados = json.dumps(corpo).encode("utf-8") if corpo is not None else b""
        self.send_response(codigo)
        if corpo is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        if dados:
            self.wfile.write(dados)

    def do_GET(self):
        if not self._autorizado():
            return self._responder(401, {"erro": "nao autorizado"})
        if self.path.split("?")[0] == "/proximo":
            comando = self.origem_ponte._proximo()
            return self._responder(200, comando) if comando else self._responder(204)
        self._responder(404, {"erro": "rota desconhecida"})

    def do_POST(self):
        if not self._autorizado():
            return self._responder(401, {"erro": "nao autorizado"})
        if self.path.split("?")[0] != "/resultado":
            return self._responder(404, {"erro": "rota desconhecida"})
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            if not 0 < tamanho <= LIMITE_CORPO:
                raise ValueError
            corpo = json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self._responder(400, {"erro": "corpo invalido"})
        self.origem_ponte._registrar_resultado(corpo)
        self._responder(200, {"ok": True})

    def do_OPTIONS(self):               # sem CORS: preflight de paginas comuns e recusado
        self._responder(403, {"erro": "CORS nao permitido"})
