# 🗣️ Fala natural e desempenho

Como o Jarvis transforma uma frase em ação, e por que algumas frases respondem na hora e outras demoram.

## 🛤️ O caminho de uma frase

```text
frase  ──►  processar()          mede o tempo (tempos.py)
              │
              ├─ 1. alarmes e lembretes, depois sair e cadastro   (jarvis._tratar_alarme)
              ├─ 2. atalhos do navegador        (jarvis._atalho_navegador)   ◄─ tolera fala natural
              ├─ 3. regras antigas (hora, volume, abrir site...)
              └─ 4. processar_com_ia()
                        ├─ cache de planos?      sim ──► executa sem rede     (cache_planos.py)
                        └─ não ──► Gemini        catálogo reduzido ou completo
                                    └─ plano deu certo? ──► guarda no cache
```

Cada camada é uma **via rápida** para a seguinte. Se uma frase não casa com nenhuma regra local, ela cai no Gemini, que conhece todas as ações. Falar de um jeito diferente do previsto só custa tempo, não faz o comando falhar.

## 1. Tolerância na fala local (`linguagem.py`)

Antes das regras do navegador (e das de alarme e da chave do cache), `tirar_enchimento` remove o que as pessoas dizem sem mudar o pedido:

| Você diz | O Jarvis entende |
|---|---|
| "Jarvis, por favor, pode abrir o segundo vídeo pra mim?" | `abrir o segundo vídeo` |
| "dá pra pesquisar lofi no yt aí" | `pesquisar lofi no yt` |
| "quero que você abra o terceiro ao lado" | `abra o terceiro ao lado` |

As regras em si aceitam sinônimos e formas de falar a posição:

- **Verbos:** abre, coloca, bota, mostra, toca, assiste, vai pro, quero ver.
- **Posições:** primeiro...décimo, `2`, "número três", "o último", "o de cima".
- **Aba:** "em outra aba", "ao lado", "em paralelo" (nova); "nessa aba", "aqui mesmo" (mesma); "sem sair daqui", "em segundo plano" (fundo).
- **Sites:** "yt", "you tube", "google".

Para ensinar uma variação nova, ajuste a regra correspondente em `jarvis.py` (constantes `R_*`, `_VERBOS_ABRIR`, `_R_ORD`, `_escolha_de_aba`) e acrescente um caso em `tests/test_naturalidade.py`.

## 2. Cache de planos (`cache_planos.py`)

Quando o Gemini resolve uma frase e as ações funcionam, o plano é guardado em `dados/cache_planos.json`. Na próxima vez que a mesma frase aparecer (sem diferença de acento, caixa ou cortesia), ela é executada na hora, sem rede e sem gastar cota.

**Não entram no cache:** conversa sem ações, ações de risco, frases que dependem do contexto ("esse", "de novo", "o outro", "agora"), e planos que falharam. Se um plano do cache falhar, ele é esquecido na hora. Se o catálogo de ações mudar, o cache inteiro é descartado.

Comandos: `/cache` (quantas frases) e `/cache limpar`.

## 3. Menos prompt, resposta mais rápida

- **Prefixo estável:** em `cerebro.py`, a parte do prompt que não muda (persona, ações, regras) vem primeiro, e hora e contexto vão no fim. O Gemini reaproveita sozinho prefixos repetidos, então as chamadas ficam mais rápidas e baratas. Nunca ponha hora ou contexto na `_parte_fixa`.
- **Catálogo por grupo:** cada ação tem um `grupo` (`geral` ou `navegador`). Se a frase não fala de navegador (veja `R_FALA_DE_NAVEGADOR` em `jarvis.py`) e o navegador não foi usado nos últimos 5 minutos, as ~35 ações dele e a regra 10 do prompt ficam de fora. O prompt cai de ~10 mil para ~4,3 mil caracteres.
- Quando uma frase de navegador não fala nenhuma das palavras de `R_FALA_DE_NAVEGADOR`, acrescente a palavra lá.
- Ações novas do navegador entram no grupo automaticamente (o fim de `acoes_navegador.py` marca tudo que ele registra).

## 4. Medição (`tempos.py`)

Cada comando vira uma linha em `dados/tempos.jsonl` (local, ignorado pelo Git, contém as frases ditas):

```json
{"ts": 1730000000, "frase": "abre o segundo video", "caminho": "atalho",
 "total_ms": 412, "etapas": {"acao": 380, "fala": 30}}
```

- **Caminhos:** `atalho` (regra do navegador), `regra` (outras regras locais), `cache`, `ia` (Gemini; guarda também o modelo e se o catálogo foi `reduzido` ou `completo`).
- **Etapas:** `ia` (rede + Gemini), `acao` (executar), `fala` (voz).
- Rode `/tempos` no Jarvis para ver a mediana por caminho e por etapa. Depois de usar um pouco, ela mostra onde o tempo realmente vai.

## 5. Alarmes e lembretes na fala

As frases de encerrar alarme (`_tratar_alarme`, em `jarvis.py`) rodam **antes** da regra de sair, para que "encerrar o lembrete" não feche o Jarvis. Elas testam a frase como foi dita e sem o enchimento.

- **Com um alarme tocando:** `ok, verificado`, `feito`, `encerre`, `pare`, `para`, `chega`, `ok`, `pode encerrar`... encerram o que está tocando. Com assunto (`ok, discord verificado`, `encerra o do discord`), encerram só aquele.
- **Verbos ambíguos** (encerrar, parar, cancelar, desativar) sozinhos só valem como alarme quando há um alarme tocando ou a frase cita "alarme" ou "lembrete". Fora disso, "cancelar desligamento" e "pare a música" seguem para os seus próprios comandos. `confirmar X` continua valendo sempre.
- **Nada tocando:** "encerrar o lembrete" cancela um lembrete que ainda não venceu: o do assunto citado, ou o único pendente. Havendo vários, o Jarvis lista e pergunta qual. Um alarme tocando tem prioridade sobre cancelar um futuro.
- Frases que citam "lembrete", "alarme", "aviso", "timer" ou "cronômetro" nunca disparam a regra de sair.

## 🧪 Testes

`tests/test_naturalidade.py` cobre o normalizador, as variações de fala, o cache, o roteamento de catálogo, o prefixo estável do prompt e a medição. `tests/test_alarmes_fala.py` cobre o encerramento de alarmes e lembretes. Nada disso usa rede.

## ⚠️ Limites conhecidos

- O cache guarda a frase **inteira**: "aumenta o volume" e "aumenta o volume em 20" são frases diferentes.
- As frases do cache não são editáveis uma a uma, só `/cache limpar`.
- O catálogo reduzido depende de palavras-chave. Se o Gemini errar uma frase de navegador sem nenhuma delas, inclua a palavra em `R_FALA_DE_NAVEGADOR`.
- Ainda não foi medido o ganho real de latência no seu computador. Use `/tempos` depois de alguns dias.
