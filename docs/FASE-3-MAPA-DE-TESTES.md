# 🧪 Fase 3: mapa de testes (antes de mexer no código)

A fase 3 da reorganização transforma o código em um pacote (`jarvis/`) e quebra o `jarvis.py`, que hoje tem 2.155 linhas. **Nada disso começa** enquanto o que está abaixo não estiver pronto e verde. Este guia mapeia o que já está protegido, o que ainda não está, e quando a fase pode começar.

## 📏 Linha de base (medida)

Rode com `.venv\Scripts\python.exe -m unittest discover -s tests`. Cobertura medida com `coverage` (`requirements-dev.txt`):

```powershell
.\.venv\Scripts\python.exe -m coverage run --source=. --omit=".venv/*,tests/*" -m unittest discover -s tests
.\.venv\Scripts\python.exe -m coverage report --skip-empty
```

**287 testes, todos passando em 3 execuções seguidas. Cobertura total: 59%.**

| Módulo | Cobertura | Situação para a fase 3 |
|---|---|---|
| `linguagem`, `cache_planos`, `caminhos`, `voz/config`, `voz/kokoro_motor`, `tempos`, `navegador/ponte` | 88–100% | pronto para mover |
| `lembretes`, `lancador`, `voz/comandos`, `catalogo`, `navegador/atalhos`, `voz/instalar` | 77–87% | pronto, com atenção aos caminhos |
| `cli`, `acoes_navegador`, `navegador/generico`, `voz/__init__`, `navegador/__init__` | 61–73% | aceitável |
| `jarvis.py` | **48%** | **o ponto crítico**: 735 de 1.422 instruções sem teste |
| `acoes.py` | **39%** | ações de mídia, volume e sistema quase sem teste |
| `cerebro.py` | **22%** | quase só o que o `jarvis` chama indiretamente |
| `telegram_bot.py`, `configurar_ia.py`, `escolher_voz.py` | **0%** | nenhum teste |

## 🛡️ Redes de segurança que já existem

| Arquivo | O que garante |
|---|---|
| `tests/test_contrato.py` | os **nomes** que um módulo espera do outro continuam existindo (50 nomes de `jarvis`, mais os das ações e dos demais módulos); cada um dos 23 módulos importa sozinho em um Python novo, sem ciclo e sem criar arquivos na raiz; o ponto de entrada `lancador.py` roda |
| `tests/test_despacho_processar.py` | para ~80 frases (com e sem alarme tocando), **qual handler** do `processar()` é acionado e com quais argumentos. Protege a ordem das regras, que é o que um refactor mais costuma quebrar |
| `tests/_ambiente.py` | os testes nunca leem nem gravam os dados reais (`JARVIS_DADOS` temporário) e **falham se tentarem I/O real**: `webbrowser.open`, `os.startfile` ou iniciar um programa. Há testes que provam que esse alarme funciona |
| `tests/test_caminhos.py` | a migração para `dados/`: nunca sobrescreve, é idempotente, arquivo em uso fica no lugar, SQLite leva os auxiliares junto |
| `tests/test_lancador.py` | argumentos, compatibilidade com as opções antigas, menu com e sem tecla, equivalência com os `.bat` removidos |

O alarme de I/O real existe por causa de um risco específico desta fase: se uma função for movida de módulo, um `patch.object(jarvis, "x")` passa a mirar o lugar errado, o teste continua **verde** e passa a executar a coisa de verdade. Agora isso falha.

## 🔎 Comportamentos encontrados ao mapear (congelados na tabela, marcados "CONHECIDO")

Nenhum deles foi alterado: a fase 3 precisa preservá-los, e corrigi-los é uma decisão à parte.

1. **`tocar X` vira play/pausa, não busca no YouTube.** A regra `R_PLAY` casa com "tocar/toca" antes da `R_TOCAR`; só `colocar X` chega em `tarefa_youtube`. O README diz o contrário.
2. **`pare a música` com um alarme tocando** é lido como "encerrar o alarme de música".
3. **`que horas são e abre o youtube`** atende só a hora: a segunda parte some.
4. **`parar`** sozinho e **`ajuda`** (sem a barra) não têm regra local e vão para a IA.
5. Os testes de rodadas anteriores chamavam `jarvis.processar` sem isolar o log de tempos, então o `dados/tempos.jsonl` real foi **poluído com frases de teste**. O `_ambiente.py` corrige daqui para frente; o que já foi gravado continua lá.
6. Um teste dependia de um `sleep` fixo de 0,35 s e falhava com a máquina ocupada (`test_alarme_nao_apaga_o_texto_digitado`). Foi trocado por espera até a condição.

## ⚠️ O que a fase 3 pode quebrar

| Risco | Por quê | Como está coberto |
|---|---|---|
| Nome movido de lugar | `telegram_bot`, `escolher_voz`, as ações (`ctx` é o módulo `jarvis`) e vários testes usam `jarvis.<nome>` | `test_contrato.py` |
| Patch mirando o módulo antigo | `patch.object(jarvis, "...")` deixa de interceptar e a função real roda | alarme de I/O real |
| Ordem das regras alterada | `_processar` decide pela ordem em que as regras aparecem | `test_despacho_processar.py` |
| Importação circular ou efeito colateral | `jarvis.py` lê `sys.argv` na importação (`MODO_TEXTO`, `USAR_IA`...) e `caminhos` migra na importação | importação isolada em `test_contrato.py` |
| `escolher_voz.py` reescreve o código | ele edita o texto de `jarvis.py` com um regex em `VOZ = "..."` | **sem teste (lacuna B6)** |
| Scripts chamados por nome | `lancador.MODOS` aponta para `jarvis.py`, `telegram_bot.py`... e `telegram_bot`/`escolher_voz` fazem `sys.path.insert` | `test_lancador.py` verifica que cada script existe |
| Trava de instância única | a identidade do lock é o hash da pasta do `jarvis.py` | só `test_recursos.py`; mudar a pasta muda a identidade (inofensivo, mas deve ser ciente) |
| Caminho padrão preso na definição | `Lembretes(caminho=DB_PATH)` e `navegador.config.carregar(caminho=ARQUIVO)` capturam o valor na importação | `test_caminhos.py` |

## 🕳️ Lacunas que ainda faltam (ordem de prioridade)

**B = bloqueia a fase 3.** Os de B devem existir e passar antes de mover qualquer arquivo.

| # | Área | Hoje | Teste necessário | |
|---|---|---|---|---|
| B1 | `acoes.py` (39%) e `acoes_navegador.py` (68%) | `_tecla`, mídia, volume, `abrir_site`, `clima`, `bloquear`, `desligar`... sem teste | cada ação do catálogo executada com fakes (`_tecla`, `_iniciar`, `webbrowser`, `pycaw`), verificando a frase devolvida e que nada real roda | B |
| B2 | `cerebro.py` (22%) | `interpretar`, `_chamar`, `_limpar_json`, `modelos`, `carregar_config` | resposta HTTP falsa: fallback entre modelos, HTTP 401/403/429/404, JSON dentro de cercas de código, cache da configuração por data do arquivo | B |
| B3 | `telegram_bot.py` (0%) | `tratar_mensagem`, `responder_comando`, `carregar_config`, `pedir_token`, `gerar_audio`, `transcrever` | funções com um servidor Telegram falso: dono, "Este Jarvis é privado", `/start`, `/voz`, `/id`, mensagem de voz sem ffmpeg | B |
| B4 | `jarvis.main()` e o encerramento | ordem: lock, pré-aquecimento, alarmes, ponte, Kokoro, loop, `finally` | `main()` com tudo trocado por fakes: ordem de início e de limpeza, `--ia-status`, `--demo` | B |
| B5 | motores de voz (`_falar_neural`, `_falar_stream`, `gerar_mp3`, `_init_player`, `_tocar_arquivo`, `_init_sapi`) | 2–10% | fakes de `edge_tts`, `pygame` e `ffplay`: cache em disco, fluxo, queda para o Windows | B |
| B6 | `escolher_voz.py` (0%) | `gravar_escolha` reescreve `jarvis.py` | cópia temporária de `jarvis.py`: o regex troca só a linha `VOZ = ...`; decidir se o script continua ou é aposentado (o `/voz padrao` já faz isso) | B |
| B7 | `configurar_ia.py` (0%) | `descobrir_modelo`, `mascarar`, `main` | `cerebro.testar_chave` falso: grava `ia_config.json`, não mostra a chave inteira | B |
| P1 | `tarefa_hora/data/clima/pesquisar/youtube/bloquear/lembrete`, `abrir_programa`, `tentar_abrir` | 8–33% | `urllib` falso e catálogo temporário | |
| P1 | `perguntar_sim_nao`, `confirmar_acao_arriscada`, `_perguntar_texto` | 14–52% | respostas sim/não/silêncio/confusas; bloqueio no Telegram | |
| P1 | `_loop_texto`, `_executar_comando_slash` (58%), `_alvos_catalogo`, `_assuntos_lembretes` | parcial | loop com `JarvisCLI` falso: ordem de alarmes, `/sair`, Ctrl+C | |
| P2 | `ouvir`, `ouvir_continuo`, `loop_voz`, `_preparar_microfone`, `tirar_palavra_ativacao` | 1–7% | `speech_recognition` falso (a palavra de ativação e a janela de 6 s dá para testar sem microfone) | |

## ✋ Verificação manual (não há como automatizar)

Antes e depois de cada etapa da fase 3, em máquina real:

- [ ] `Jarvis.bat` (menu), `Jarvis.bat texto` (painel, `/`), `Jarvis.bat voz` falando "Jarvis, que horas são".
- [ ] Alarme: criar um lembrete de 1 minuto, deixar tocar, `ok, verificado`.
- [ ] Voz: com Edge e com Kokoro ativo; cair para o Windows desligando a internet.
- [ ] Extensão conectada (`/navegador`, selo ON) e "pesquisa lofi no youtube e abre o primeiro".
- [ ] `Jarvis.bat bot` e um `/start` no Telegram.

## ✅ Critérios para começar a fase 3

1. B1 a B7 escritos e passando.
2. Suíte completa verde **3 vezes seguidas**, também com a máquina ocupada.
3. Cobertura de `jarvis.py` ≥ 65% e de `acoes.py` e `cerebro.py` ≥ 70%.
4. `test_contrato.py` e a tabela de despacho sem nenhuma exceção pendente.
5. O alarme de I/O real sem disparos.
6. Verificação manual feita uma vez **antes** de começar, para saber o que é "normal".

## 🗺️ Roteiro da execução (depois do aval)

Um passo por vez, com a suíte completa e um commit a cada passo, para qualquer falha apontar o passo exato:

1. Esqueleto do pacote e mover os módulos "folha" (`linguagem`, `tempos`, `cache_planos`, `caminhos`), deixando um arquivo de reexportação no lugar antigo.
2. `acoes`, `acoes_navegador`, `lembretes`, `catalogo`.
3. `cerebro` e a camada de IA.
4. Motores de voz, tirados de dentro do `jarvis.py` e juntados ao pacote `voz/`.
5. `cli` e `telegram_bot`.
6. O núcleo (`processar`, regras, loop), quebrado em partes.
7. Remover os arquivos de reexportação, atualizar o `lancador`, os testes e a documentação.

A cada passo: testes verdes, `test_contrato.py` atualizado de propósito (e nunca "só para passar") e a tabela de despacho intacta.
