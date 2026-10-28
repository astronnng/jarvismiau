# Jarvis simples (Windows) — guia rápido

Um assistente por voz que **conversa** e **executa tarefas básicas** no seu PC.
Sem conta em nuvem, sem chave de API: tudo roda no seu computador.

---

## Passo 1 — Instalar o Python (só uma vez)

1. Acesse **https://www.python.org/downloads/** e baixe o Python 3.12 (recomendado).
2. Abra o instalador e **marque a caixa "Add python.exe to PATH"** na primeira tela.
3. Clique em **Install Now** e espere terminar.

## Passo 2 — Instalar o Jarvis

1. Baixe a pasta `jarvis` deste workspace para o seu PC (ex.: `C:\jarvis`).
2. Dê **dois cliques em `instalar.bat`**.
3. Ele cria um ambiente isolado e baixa as bibliotecas de voz. Aguarde 1–3 minutos.

## Passo 3 — Usar

- **`Jarvis.bat`** → escuta sempre, mas só atende quando ouve **"Jarvis"**.
- **`Jarvis-continuo.bat`** → escuta e atende qualquer fala, sem palavra de ativação.
- **`Jarvis-pressione.bat`** → modo antigo: aperta ENTER e fala.
- **`Jarvis-texto.bat`** → digite os comandos (útil para testar sem microfone).
- **`Testar-voz.bat`** → fala uma frase de teste, para você conferir a voz escolhida.
- **`Escolher-voz.bat`** → toca todas as vozes e grava a sua favorita automaticamente.
- **`comparador-vozes.html`** → compare as 8 vozes brasileiras no navegador.
- **`Iniciar-bot.bat`** → liga o Jarvis no Telegram (guia: `BOT-TELEGRAM.md`).
- **`Configurar-IA.bat`** → liga o cérebro de IA, que entende frases livres (guia: `IA-AUTONOMO.md`).
- **`Instalar-kokoro.bat`** → instala a voz Kokoro, opcional e local (guia: `docs/VOZ.md`).

Na primeira vez o Windows pode pedir permissão para usar o microfone: clique em **Permitir**.

> Dica: clique com o botão direito em `Jarvis.bat` → *Enviar para* → *Área de trabalho (criar atalho)*.
> Depois clique com o botão direito no atalho → *Propriedades* → *Avançado* → marque **Executar como administrador** (necessário só se você usar o comando de bloquear o PC).

---

## 🎙️ As vozes brasileiras (naturais)

O catálogo gratuito de vozes neurais tem **3 vozes brasileiras nativas** e várias vozes
**multilíngues** que também falam português. Todas foram testadas e estão prontas abaixo.

### Jeito mais fácil de escolher

Dois cliques em **`Escolher-voz.bat`**: ele toca uma frase de teste em cada voz, você digita o
número, e se gostar aperta `s`. O programa **grava a escolha sozinho** no `jarvis.py`. Não precisa
editar nada à mão.

Dentro do Jarvis em modo texto, `/voz padrao` lista os perfis e `/voz padrao NOME` troca na hora, sem
reiniciar. Essa escolha fica em `voz.json` e **vence** a constante `VOZ` do `jarvis.py` (e, portanto,
o `Escolher-voz.bat`); só a variável de ambiente `JARVIS_VOZ`, usada para testes, vence o `voz.json`.

Ou abra **`comparador-vozes.html`** para ouvir as oito vozes brasileiras de uma vez no navegador.

### As opções disponíveis

| Perfil no código | Voz | Como soa |
|---|---|---|
| `BR_ANTONIO` ⭐ | Antônio | Brasileira **nativa**, masculina, grave e neutra. Sotaque 100% brasileiro. |
| `BR_ANTONIO_GRAVE` | Antônio | A mesma, 14% mais lenta e mais grave. Mais solene, estilo mordomo. |
| `BR_ANDREW` | Andrew | Timbre encorpado; sotaque levemente estrangeiro, mas discreto. |
| `BR_BRIAN` | Brian | Mais jovem e conversacional, leve sotaque. |
| `BR_GIUSEPPE` | Giuseppe | Caloroso, sotaque perceptível. |
| `BR_REMY` | Rémy | Suave, sotaque perceptível. |
| `BR_FRANCISCA` | Francisca | Brasileira **nativa**, feminina, clara. |
| `BR_THALITA` | Thalita | Brasileira, feminina e mais jovem. |
| `JARVIS` | Ryan | Britânica masculina — responde em inglês. |
| `WINDOWS` | — | Voz do Windows, offline e robótica (plano B sem internet). |

As amostras em áudio estão em `vozes-br/` (brasileiras) e `vozes/` (britânicas).

### Se quiser trocar no código

```python
VOZ = "BR_ANTONIO"
```

Para mudar tom e velocidade, edite o perfil correspondente em `PERFIS`:

```python
"BR_ANTONIO": _br("pt-BR-AntonioNeural", "-8%", "-6Hz"),
#                                        ↑velocidade  ↑tom (mais negativo = mais grave)
```

### Voz local opcional: Kokoro

Além dessas vozes, existe uma voz neural que roda **no seu computador**, sem internet, e permite
**misturar vozes** com proporções (por exemplo `bm_daniel`, `am_michael` e `pm_alex`), escolher o
idioma dos fonemas e a velocidade. Ela é opcional: com o Kokoro desligado, nada muda. Se ele estiver
ativo e falhar por qualquer motivo, o Jarvis volta sozinho para a voz neural acima e, sem internet,
para a voz do Windows.

Instale com **`Instalar-kokoro.bat`** (ele pede confirmação antes de baixar os modelos, cerca de
350 MB) e configure com `/voz` no `Jarvis-texto.bat`. Guia completo: **`docs/VOZ.md`**.

### Quer ainda mais natural que isso?

O limite do catálogo gratuito é esse. Se quiser vozes de qualidade "locutor de rádio", os caminhos
legítimos são (todos exigem criar conta e colar uma chave de API no código):

| Serviço | Vozes brasileiras | Plano gratuito |
|---|---|---|
| **Azure Speech** (mesmo motor daqui, mas com vozes extras) | `pt-BR-FabioNeural`, `pt-BR-DonatoNeural`, `pt-BR-HumbertoNeural`, `pt-BR-JulioNeural` | 500 mil caracteres/mês |
| **Google Cloud TTS** | `pt-BR-Neural2-B`, `pt-BR-Wavenet-B` (masculinas) | 1 milhão de caracteres/mês (WaveNet) |
| **ElevenLabs** | vozes brasileiras da comunidade + clonagem da **sua** voz | 10 mil caracteres/mês |

O **Azure** é o que dá mais opções de timbre brasileiro masculino com pouco esforço: as vozes
`Donato` e `Humberto` são bem mais encorpadas que o Antônio. Você mantém a gratuidade dentro dos
500 mil caracteres — o Jarvis usa ~60 caracteres por frase, ou seja, milhares de comandos por mês.
Se quiser, peço para eu adaptar o `jarvis.py` para o Azure quando você tiver a chave.

---

## O que ele já sabe fazer

| Você diz | Ele faz |
|---|---|
| "que horas são" | fala a hora |
| "que dia é hoje" | fala a data |
| "clima em Bariri" | consulta a temperatura e a condição do tempo |
| "abrir youtube" (ou google, whatsapp, gmail, netflix, instagram, mapa, mercado livre, correios…) | abre o site no navegador |
| "abrir calculadora" (ou bloco de notas, paint, explorer, spotify, excel, word, configurações…) | abre o programa |
| "pesquisar receita de bolo" | pesquisa no Google |
| "tocar Legião Urbana" | abre o YouTube com a busca |
| "bloquear o computador" | bloqueia o Windows |
| "oi", "tudo bem" | responde |
| "dar play", "pausar", "próxima música" | controla o player (Spotify, YouTube…) |
| "aumentar/abaixar o volume", "silenciar" | volume do Windows |
| "volume em 35%" | define o volume do Windows |
| "me lembre em 10 minutos de X" | cria um lembrete persistente |
| "listar lembretes" | mostra assunto, horário e estado |
| "confirmar X" | encerra o alarme com esse assunto |
| "ok, verificado", "encerre" | encerra o alarme que está tocando |
| "encerrar o lembrete" | cancela um lembrete que ainda não venceu |
| "pesquisa lofi no youtube e abre o primeiro", "abre o segundo em outra aba" | controla o seu navegador (precisa da extensão: `docs/NAVEGADOR.md`) |
| "silencia a aba do youtube", "fecha as abas duplicadas" | gerencia as abas do navegador |
| "quantos e-mails não lidos eu tenho" | lê a contagem do Gmail (somente leitura) |
| "como está a memória do pc" | memória, disco e bateria |
| "desligar o computador" | pede confirmação antes de desligar |
| "sair" | encerra o Jarvis |

Se ele não souber algo, oferece pesquisar no Google para você.

---

## Como ensinar coisas novas

O catálogo padrão está em `config.example.json`; o Jarvis cria `config.json` local na primeira execução e recarrega as mudanças automaticamente. Esse arquivo é ignorado pelo Git.

Você também pode pedir:

```text
adicionar site meu banco
adicionar programa meu editor
```

O Jarvis pede a URL ou o caminho/URI do aplicativo, mostra o que será salvo e espera sua confirmação. Programas novos aceitam caminho absoluto para executável existente ou URI registrada pelo aplicativo, como `spotify:`.

Os lembretes são salvos em `lembretes.sqlite3` e continuam depois que o Jarvis fecha. Se um lembrete vencer enquanto o app estiver fechado, o alarme começa quando ele abrir e repete a cada 30 segundos até você confirmar pelo assunto ou, com ele tocando, dizer algo como "ok, verificado" ou "encerre". Quando nada está tocando, "encerrar o lembrete" cancela o lembrete que ainda não venceu (o do assunto citado, ou o único pendente; havendo vários, ele pergunta qual).

---

## Se algo não funcionar

| Problema | Solução |
|---|---|
| `instalar.bat` diz que o Python não foi encontrado | Reinstale o Python marcando **Add python.exe to PATH**. |
| Erro falando de **PyAudio** | Instale o **Python 3.12** (tem instalador pronto). Nas versões mais novas do Python, às vezes é preciso compilar, o que é mais chato. |
| Ele abre, mas não ouve nada | Confira o microfone padrão em *Configurações → Sistema → Som*, e permita o microfone em *Configurações → Privacidade → Microfone*. |
| Ele ouve errado e responde "não entendi" | Fale mais perto do microfone e sem barulho de fundo. O reconhecimento usa a internet. |
| Não fala em voz alta | No modo texto ele só imprime. No `Jarvis.bat` ele fala; se ficar mudo, verifique o volume e o dispositivo de saída. |
| A voz neural não sai | Ela precisa de internet e de `edge-tts` + `pygame` instalados (o `instalar.bat` já instala). Sem internet, o Jarvis cai automaticamente para a voz do Windows. |
| A voz neural demora ~1s para começar | Normal: o texto é gerado na hora. Frases curtas (como as deste Jarvis) levam menos de 1 segundo. |
| Ativei o Kokoro e o Jarvis voltou para a voz de antes | Ele cai sozinho para a voz padrão quando o Kokoro falha. Digite `/voz`: o "último erro" mostra o motivo. Guia: `docs/VOZ.md`. |
| Comandos do navegador dizem que a extensão não está conectada | Abra o Jarvis, recarregue a extensão em `chrome://extensions` e veja o selo **ON**. Guia: `docs/NAVEGADOR.md`. |

**Dica de segurança:** este Jarvis só executa ações de uma lista fixa. Nada de apagar arquivos, mexer em dinheiro ou enviar mensagens sem você confirmar. Mantenha assim.

---

## 🎧 Palavra de ativação "Jarvis"

O **`Jarvis.bat`** fica com o microfone aberto o tempo todo, mas **só atende quando você diz "Jarvis"**.
A janela do terminal precisa estar aberta.

```
(modo palavra de ativacao: comece a fala dizendo "jarvis")

Voce: você viu o jogo ontem
   (sem a palavra de ativacao, ignorado)

Voce: Jarvis, que horas são
Jarvis: Sao 16 horas e 0 minutos, senhor.
```

### Como falar com ele

| Você diz | O que acontece |
|---|---|
| "Jarvis, que horas são" | responde |
| "Ei Jarvis, abrir youtube" | responde (aceita "ei", "oi", "ok" antes) |
| "Jarvis" (sozinho) | responde "Pode falar, senhor" e **aceita o comando seguinte** sem repetir a palavra |
| "que horas são" (sem "Jarvis") | ignora — a menos que esteja nos **6 segundos seguintes** a uma resposta dele |
| "sair" (sozinho) | encerra, mesmo sem a palavra |

**Janela de acompanhamento:** depois que ele responde, você tem **6 segundos** para continuar
a conversa sem repetir "Jarvis". Exemplo:

```
Voce: Jarvis, clima em Bariri
Jarvis: Em Bariri esta 23 graus e ensolarado.
Voce: abrir youtube
   (dentro da janela de acompanhamento: aceito)
Jarvis: Abrindo youtube, senhor.
```

### Ele entende "Jarvis" mesmo quando o reconhecedor erra

O Google costuma devolver "Jávis", "Jarves" ou "Jarbis". Estas variantes são aceitas
automaticamente: `jarvis, javis, jarves, jarbis, jarvi, jarve, charvis`.
Para adicionar outras, edite `VARIANTES_ATIVACAO` no topo do `jarvis.py`.

### Os três modos de escuta

| Atalho | Como funciona | Quando usar |
|---|---|---|
| **`Jarvis.bat`** | Ouve sempre, atende só com "Jarvis" | Padrão — tem gente/TV por perto |
| **`Jarvis-continuo.bat`** | Atende qualquer fala | Você sozinho no ambiente |
| **`Jarvis-pressione.bat`** | Aperta ENTER, fala, ele responde | Microfone ruim ou ambiente barulhento |

### ✅ Confirmar por voz ("sim" / "não")

Quando ele não sabe algo, pergunta: *"Pesquisar no Google? Diga sim ou nao."* — e agora ele
**realmente escuta a resposta**:

```
Voce: Jarvis, quem descobriu o brasil
Jarvis: Ainda nao fui programado para isso, senhor. Pesquisar no Google? Diga sim ou nao.
Voce: sim
Jarvis: Pesquisando quem descobriu o brasil, senhor.
```

O que ele aceita como **sim**: sim, s, claro, pode, isso, quero, manda, yes.
Como **não**: não, n, no, deixa, deixa pra lá, não precisa, cancelar.

Detalhes testados: se você ficar em silêncio ele tenta de novo (até 3 vezes); se responder algo
confuso, ele repete "Sim ou não, senhor?"; e o "sim" **não precisa** da palavra "Jarvis" antes.

### O que foi feito para isso funcionar bem

| Risco | Solução |
|---|---|
| Ele ouvir a própria voz e responder a si mesmo | O microfone é **purgado** antes de cada escuta; ele não escuta enquanto fala |
| Terminal travado para sempre se der erro de rede | Erro isolado: espera 2 s e volta. Erro repetido: **cai para o modo digitado**, avisando |
| Microfone inexistente ou bloqueado pelo Windows | Cai para o modo digitado em vez de ficar em silêncio |
| Responder a conversa de outra pessoa | Só atende com a palavra de ativação (e a janela de 6 s após uma resposta) |
| Calibrar o ruído a cada comando | Calibra **uma vez** ao iniciar |

### Ajustar a sensibilidade

No topo do `jarvis.py`:

```python
SEGUNDOS_SILENCIO = 0.55    # silêncio que marca o fim da sua fala
LIMITE_FRASE = 8            # tempo máximo de uma fala
JANELA_SEGUIMENTO = 6       # segundos após responder em que aceita comandos sem "Jarvis"
```

- **Corta você no meio da frase:** aumente `SEGUNDOS_SILENCIO` para `0.8`.
- **Demora após você calar:** diminua para `0.4`.
- **Dispara com ventilador/TV:** em `_preparar_microfone()` aumente `energy_threshold` de `300` para `500`.
- **Não escuta voz baixa:** diminua `energy_threshold` para `180`.
- **Janela de acompanhamento longa demais:** reduza `JANELA_SEGUIMENTO` para `3` ou `0`.

### Aviso de privacidade

Microfone ligado enquanto o terminal estiver aberto (o Windows mostra o ícone na barra).
O áudio **não é gravado**: cada fala vira texto pelo Google e é descartada. O consumo de CPU é
baixo, porque ele só transcreve quando detecta fala. Para silêncio absoluto, feche a janela.

## ⚡ Velocidade: sem delay na voz

A versão anterior esperava **~1,3 segundo** antes de falar, porque a voz era gerada na
internet a cada frase. Foram três correções:

| O que era lento | O que mudou | Ganho |
|---|---|---|
| Voz gerada a cada frase (rede) | **Cache em disco**: a frase é gravada uma vez e reusada | 1.274 ms → **0 ms** |
| Player ligava e desligava toda vez | Mixer aberto **uma vez só**, som carregado em memória | ~200 ms |
| Microfone reabria e recalibrava a cada comando | Aberto e calibrado **uma vez**; corte de silêncio mais rápido | ~500 ms |
| Frases novas (hora, clima) | **Player em fluxo**: começa a tocar enquanto o áudio chega | ~1.200 ms → **~130 ms** |

**Medido de verdade:** a primeira palavra saía em ~130 ms no modo fluxo e **0 ms** nas frases em cache.

### Como usar

Nada a fazer: é automático. Dois detalhes úteis:

- A pasta **`cache_voz/`** guarda as frases prontas. Já vem preenchida com as 54 frases
  mais usadas na voz da Rémy (1,1 MB), então no seu PC ele começa rápido **desde a primeira vez**.
  Se você trocar de voz, ele gera o cache novo sozinho.
- Para ver os tempos na tela, rode:
  ```
  python jarvis.py --latencia
  ```
  Ele mostra `[latencia] CACHE: 0 ms` ou `[latencia] FLUXO: 130 ms` a cada frase.

### Deixar ainda mais rápido (opcional): instale o ffmpeg

O modo fluxo (o mais rápido para frases novas) usa o `ffplay`, que vem no pacote ffmpeg:

```
winget install ffmpeg
```

Depois de instalar, feche e abra o Jarvis. Sem o ffmpeg ele continua rápido nas frases
em cache e cai no modo arquivo (~1,2 s) só nas frases imprevisíveis.

> O mesmo ffmpeg já era necessário para o bot entender mensagens de voz no Telegram —
> então instalar resolve as duas coisas de uma vez.

### Se você quiser mexer

- `--sem-cache`: desliga o pré-aquecimento (útil para testar a voz "crua").
- Para limpar o cache: apague a pasta `cache_voz/`. Ela se reconstrói sozinha.
- Para diminuir ainda mais a espera depois que você fala, em `ouvir()` está
  `pause_threshold = 0.55`: é quanto silêncio ele espera para entender que você terminou.
  Baixar para `0.4` deixa mais rápido, mas pode cortar quem fala devagar.

---

## 🧠 Cérebro de IA (frases livres)

Sem IA, ele entende comandos conhecidos. **Com IA, ele entende o que você quiser dizer** e
decide sozinho quais ações executar no PC.

**Ligar (5 min, grátis):**

1. Pegue uma chave em **https://aistudio.google.com/apikey** (sem cartão de crédito)
2. Dois cliques em **`Configurar-IA.bat`** → cole a chave
3. Abra o `Jarvis.bat` e fale normalmente

```
Voce: dar play no spotify
Jarvis: Spotify aberto e tocando, senhor.

Voce: abre o netflix e aumenta o volume
Jarvis: Abrindo netflix, senhor.
Jarvis: Volume aumentado, senhor.

Voce: quanto é 15% de 340
Jarvis: Sao 51, senhor.
```

O catálogo tem ações para mídia (play/pausa/próxima/Spotify/YouTube), volume, abrir
programas e sites, pesquisar, clima, horas, data, lembretes, status do PC, bloquear e
desligar/reiniciar (estes com confirmação), além do controle do navegador (abas, YouTube,
Google, Gmail em leitura, Spotify Web, histórico e favoritos, e qualquer site em modo genérico).

Frases que a IA já resolveu ficam em cache: da segunda vez, a mesma frase é executada na hora,
sem internet. Detalhes em **`docs/FALA-E-DESEMPENHO.md`**.

**Como o controle fica com você:** a IA **não tem acesso ao computador**. Ela só pode
escolher nomes de uma lista fechada (`acoes.py`); o que não está na lista é rejeitado.
No Telegram, desligar/reiniciar ficam **bloqueados** de propósito.

Detalhes, limites honestos e como adicionar ações novas: **`IA-AUTONOMO.md`**.
Para desligar a IA: `Jarvis.bat --sem-ia` ou apague o `ia_config.json`.
Diagnóstico: `python jarvis.py --ia-status`.

---

## 📱 No celular (Telegram) — pronto

O bot já está montado. Guia completo em **`BOT-TELEGRAM.md`**, resumo:

1. No Telegram, fale com **@BotFather** → `/newbot` → copie o token.
2. Dois cliques em **`Iniciar-bot.bat`** → cole o token.
3. Mande `/start` para o seu bot. Ele responde em texto **e em voz**.

O primeiro chat que falar com o bot vira o **dono** — qualquer outro chat é
ignorado. O bot roda no seu PC, então ele precisa estar ligado.
