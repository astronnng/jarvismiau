# 🎙️ Vozes

Perfis de voz, como escolher e como a voz fica rápida. A voz local opcional (Kokoro) tem guia próprio: [VOZ.md](VOZ.md).

## 🎙️ As vozes brasileiras (naturais)

O catálogo gratuito de vozes neurais tem **3 vozes brasileiras nativas** e várias vozes
**multilíngues** que também falam português. Todas foram testadas e estão prontas abaixo.

### Jeito mais fácil de escolher

Rode **`Jarvis.bat escolher-voz`**: ele toca uma frase de teste em cada voz, você digita o
número, e se gostar aperta `s`. O programa **grava a escolha sozinho** no `jarvis.py`. Não precisa
editar nada à mão.

Dentro do Jarvis em modo texto, `/voz padrao` lista os perfis e `/voz padrao NOME` troca na hora, sem
reiniciar. Essa escolha fica em `dados/voz.json` e **vence** a constante `VOZ` do `jarvis.py` (e, portanto,
o `Jarvis.bat escolher-voz`); só a variável de ambiente `JARVIS_VOZ`, usada para testes, vence o `dados/voz.json`.

Ou abra **`recursos/comparador-vozes.html`** para ouvir as oito vozes brasileiras de uma vez no navegador.

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

As amostras em áudio estão em `recursos/vozes-br/` (brasileiras) e `recursos/vozes/` (britânicas).

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

Instale com **`Instalar.bat kokoro`** (ele pede confirmação antes de baixar os modelos, cerca de
350 MB) e configure com `/voz` no `Jarvis.bat texto`. Guia completo: **`docs/VOZ.md`**.

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

- A pasta **`dados/cache_voz/`** guarda as frases prontas. Ao abrir, o Jarvis gera em segundo plano
  as frases mais usadas na voz escolhida, então depois de alguns instantes ele começa rápido.
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
- Para limpar o cache: apague a pasta `dados/cache_voz/`. Ela se reconstrói sozinha.
- Para diminuir ainda mais a espera depois que você fala, em `ouvir()` está
  `pause_threshold = 0.55`: é quanto silêncio ele espera para entender que você terminou.
  Baixar para `0.4` deixa mais rápido, mas pode cortar quem fala devagar.
