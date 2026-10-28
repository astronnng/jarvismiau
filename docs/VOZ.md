# 🎙️ Voz: Kokoro opcional e o comando `/voz`

O Jarvis fala por padrão com a cadeia de sempre: **Edge (neural, com cache) → voz do Windows**. Este guia descreve a camada **opcional** que adiciona o **Kokoro**, uma voz neural que roda no seu computador (ONNX, sem internet) e que permite misturar vozes.

> Nada muda até você ativar. O Kokoro é tentado **antes** da cadeia atual; se não estiver ativo ou falhar por qualquer motivo, o Jarvis segue sozinho para Edge e Windows, como sempre.

## 📥 Instalação (uma vez)

1. Rode `Instalar.bat kokoro`. Ele instala a biblioteca (`requirements-kokoro.txt`: `kokoro-onnx`, `onnxruntime`, `numpy`, `espeakng-loader`, `phonemizer`; sem PyTorch) e, **se você confirmar**, baixa os modelos para `dados/modelos/kokoro/`:
   - `kokoro-v1.0.onnx` (326 MB, modelo completo) e `voices-v1.0.bin` (28 MB, 54 vozes);
   - origem: release `model-files-v1.0` de github.com/thewh1teagle/kokoro-onnx;
   - cada arquivo é conferido por **tamanho e SHA-256** (em `voz/instalar.py`) e descartado se não bater.
2. No Jarvis (`Jarvis.bat texto`): `/voz kokoro testar` para ouvir sem ativar e `/voz usar kokoro` para ativar.

O mesmo download também está em `/voz kokoro instalar` (pede confirmação dentro do Jarvis).

## 🎛️ O padrão do Kokoro

| Ajuste | Valor padrão |
|---|---|
| Mistura | `bm_daniel` 0.5 + `am_michael` 0.4 + `pm_alex` 0.3 (os pesos viram 42% / 33% / 25%) |
| Idioma | **`pt-br`** (explícito) |
| Velocidade | 1.0 |

O padrão vale quando não há `dados/voz.json` ou quando ele não define a mistura. Quem já tem `dados/voz.json` mantém o que está nele; para voltar ao padrão, use `/voz kokoro mistura bm_daniel=0.5 am_michael=0.4 pm_alex=0.3`.

### Sobre o idioma e o sotaque

No Kokoro, o idioma **não é uma configuração por voz**: é um código único de fonemas (`lang`) aplicado ao texto inteiro, e vale para todas as vozes da mistura. O Jarvis envia `pt-br` **explicitamente em toda fala**. Um valor vazio ou inválido (`auto`, por exemplo) volta para `pt-br`, nunca para o `en-us` que a biblioteca usaria sozinha.

Conferido com o modelo real, para "Não sei, senhor": com `pt-br` os fonemas saem `nˌɐ̃ʊ̃ sˈeɪ, seɲˈor`; com `en-us` sairiam `nˈaʊ sˈeɪ, sˈɛnhɚ`.

`bm_daniel` e `am_michael` são vozes **nativas em inglês**: o texto é lido com fonemas do português, mas o **timbre** delas carrega sotaque, parecido com o dos perfis `BR_REMY` e `BR_ANDREW`. Por isso o padrão inclui `pm_alex`, voz nativa em português, que suaviza esse efeito. Outras opções nativas: `pm_santa` e `pf_dora`. Para mais sotaque, diminua o peso de `pm_alex`; para menos, aumente.

O `/voz` avisa quando nenhuma voz da mistura é nativa em português. Misturar vozes de idiomas diferentes (como no padrão) funciona; o aviso de "idiomas diferentes" ao definir a mistura é só um lembrete.

## ⌨️ O comando `/voz`

O menu de `/` sugere subcomandos, nomes de voz, idiomas, velocidades e presets enquanto você digita.

O `/voz` existe no modo texto (`Jarvis.bat texto`). O que você configurar fica em `dados/voz.json` e vale também no modo de voz (`Jarvis.bat`) e nos outros, porque todos falam pelo mesmo caminho.

| Comando | O que faz |
|---|---|
| `/voz` | estado: motor ativo, mistura, idioma, velocidade |
| `/voz ajuda` | lista os subcomandos |
| `/voz usar kokoro` / `/voz usar padrao` | troca o motor ativo (vale na hora; grava em `dados/voz.json`) |
| `/voz padrao [PERFIL]` | lista ou escolhe o perfil Edge/Windows (ex.: `BR_ANTONIO`) |
| `/voz testar [frase]` | fala com o motor ativo |
| `/voz kokoro vozes [filtro]` | vozes do modelo instalado, por idioma (`pt-br`, `en-gb`...) |
| `/voz kokoro mistura bm_daniel=0.5 am_michael=0.4` | até 3 vozes com pesos (também `a:60 b:40`) |
| `/voz kokoro idioma pt-br` | código de fonemas (validado pelo espeak do modelo) |
| `/voz kokoro velocidade 1.1` | de 0.5 a 2.0 |
| `/voz kokoro preset lista`, `salvar N`, `usar N`, `apagar N` | combinações com nome |
| `/voz kokoro pronuncia nao=não`, `lista`, `remover nao` | como palavras são lidas |
| `/voz kokoro preaquecer on` / `off` | gerar frases comuns em segundo plano |
| `/voz kokoro testar [frase]` | ouve o Kokoro sem ativá-lo (mostra se veio do cache ou quanto levou) |
| `/voz kokoro instalar` | baixa os modelos (pede confirmação) |

**Pesos:** os valores são normalizados. `0.5`, `0.4` e `0.3` equivalem a 42%, 33% e 25%; `60 40` dá 60% e 40%. Misturar vozes de idiomas diferentes (por exemplo `pf_dora` com `bm_daniel`) funciona, mas o programa avisa que pode soar estranho.

**Qual perfil vale na abertura:** a variável `JARVIS_VOZ` (testes) vence `dados/voz.json` (`/voz padrao`), que vence a constante `VOZ` de `jarvis.py`. Como o `Jarvis.bat escolher-voz` grava justamente essa constante, uma escolha feita antes com `/voz padrao` continua valendo por cima dela.

## ⚡ Desempenho (medido neste computador)

O Kokoro roda no CPU a cerca de **0,3× o tempo real**: o modelo carrega em ~2 s e uma **frase nova leva ~1,5 a 1,8 s** para ficar pronta. Isso é mais lento que o fluxo do Edge (~250 ms), por isso:

- **Cache:** cada frase vira um WAV em `dados/cache_voz/kokoro/`, por (modelo, mistura, idioma, velocidade, texto). Frase repetida toca em ~2 ms. Mudar mistura, idioma ou velocidade usa outra chave de cache.
- **Frase a frase:** textos com várias frases tocam a primeira enquanto a próxima é sintetizada.
- **Pré-aquecimento:** ao abrir o Jarvis (com o Kokoro ativo) e ao mudar a voz, as frases conhecidas são geradas em segundo plano (`/voz kokoro preaquecer off` desliga). Mudar a voz no meio cancela o trabalho antigo.

Use `/tempos` para ver a etapa `fala` ao longo do uso.

## 🔄 Segurança e fallback

- Biblioteca ausente, modelo ausente, voz inexistente, erro ao sintetizar, player que não inicia: o Kokoro devolve "não falei" e o Jarvis segue na cadeia antiga, sem mensagem de erro na sua cara. O último erro aparece em `/voz`.
- Se uma frase de várias partes falhar no meio, o Jarvis **não repete** o que já foi dito.
- Se o modelo falhar ao carregar, ele só tenta de novo depois de 60 s.
- O bot do Telegram (modo de captura) nunca usa o Kokoro.

## 🗂️ Onde fica cada coisa

```text
voz/config.py          dados/voz.json: motor, mistura, idioma, velocidade, presets, pronúncias
voz/kokoro_motor.py    síntese, mistura de estilos, cache em WAV, fala frase a frase, fallback
voz/comandos.py        o /voz e as sugestões do menu
voz/instalar.py        download verificado dos modelos (python -m voz.instalar)
requirements-kokoro.txt  dependências opcionais (kokoro-onnx e afins)
Instalar.bat kokoro    instala as dependências e, com confirmação, baixa os modelos
jarvis.py              gancho em _falar_audio, _tocar_wav, /voz, painel (_status_painel)
dados/modelos/kokoro/        modelos baixados          (ignorado pelo Git)
dados/voz.json               sua configuração de voz   (ignorado pelo Git)
dados/cache_voz/kokoro/      áudio gerado              (ignorado pelo Git)
```

## 🔤 Pronúncia

As frases do Jarvis saem **sem acento** (`Nao`, `Sao`, `Ola`). O espeak lê melhor com acento, então, **só em idioma `pt-*`**, uma lista de palavras é corrigida antes de sintetizar (`nao → não`, `voce → você`, `sao → são`, `ola → olá`...). Veja e edite com `/voz kokoro pronuncia`. Não afeta o texto exibido, nem o Edge.

## 🧪 Testes

`tests/test_voz.py` usa um Kokoro falso (sem baixar modelo nem tocar áudio): cobre a configuração, a mistura, o idioma explícito, o cache, o fallback, o `/voz`, o instalador (com adulteração de arquivo) e o gancho no `jarvis.py`. Sem `numpy` instalado, os testes que dependem dele são ignorados.

## 🩹 Solução de problemas

| Sintoma | O que fazer |
|---|---|
| `/voz usar kokoro` diz que não dá | Leia o motivo: normalmente falta rodar `Instalar.bat kokoro` ou `/voz kokoro instalar`. |
| A primeira fala depois de abrir demora | O modelo está carregando e aquecendo (~3 s). Depois disso fica mais rápido. |
| Frases novas demoram ~1,5 s | É o custo da síntese local; o cache resolve as repetidas. |
| Sotaque forte | Veja a seção sobre idioma e sotaque: aumente o peso de `pm_alex` (já está no padrão) ou inclua `pm_santa` ou `pf_dora` na mistura. |
| Uma palavra sai estranha | `/voz kokoro pronuncia palavra=como-ler`. |
| O Jarvis voltou sozinho para a voz padrão | O Kokoro falhou; veja o "último erro" em `/voz`. |
