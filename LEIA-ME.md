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

- **`Jarvis.bat`** → abre o Jarvis por voz. Aperte **ENTER** e fale.
- **`Jarvis-texto.bat`** → digite os comandos (útil para testar sem microfone).
- **`Testar-voz.bat`** → fala uma frase de teste, para você conferir a voz escolhida.
- **`Escolher-voz.bat`** → toca todas as vozes e grava a sua favorita automaticamente.
- **`comparador-vozes.html`** → compare as 8 vozes brasileiras no navegador.

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
| "sair" | encerra o Jarvis |

Se ele não souber algo, oferece pesquisar no Google para você.

---

## Como ensinar coisas novas

Abra `jarvis.py` no Bloco de Notas (botão direito → *Abrir com* → *Notepad*) e edite as listas no topo:

```python
SITES = {
    "meu banco": "https://www.bb.com.br",
    "meu trabalho": "https://intranet.minhaempresa.com",
}

PROGRAMAS = {
    "meu jogo": "start steam://rungameid/123456",
}
```

Salve e abra o Jarvis de novo. Pronto: "abrir meu banco" já funciona.

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

**Dica de segurança:** este Jarvis só executa ações de uma lista fixa. Nada de apagar arquivos, mexer em dinheiro ou enviar mensagens sem você confirmar. Mantenha assim.

---

## Próximo passo: o celular

O jeito mais simples de ter o mesmo Jarvis no celular, sem reescrever nada, é:

1. Criar um **bot no Telegram** (5 minutos, grátis, com o `@BotFather`).
2. Rodar um pequeno script no PC que escuta as mensagens do bot e responde usando a mesma lógica do `jarvis.py`.
3. Você usa o Telegram no celular como se fosse o Jarvis — inclusive fora de casa, desde que o PC esteja ligado.

Quando quiser, peço para eu montar essa parte: o arquivo do bot já vem pronto para usar a mesma lista de comandos.
