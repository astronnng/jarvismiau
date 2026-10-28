# 🤖 Jarvis

Assistente pessoal simples para Windows, capaz de conversar por voz, responder a comandos básicos e executar tarefas no computador. 🖥️

O projeto roda localmente, sem exigir conta em nuvem ou chave de API. O reconhecimento de voz utiliza um serviço externo do Google, portanto é necessário ter conexão com a internet para usar o modo de voz. O cérebro de IA (Gemini) e a voz Kokoro são opcionais.

## ✨ Recursos

- 🕒 Consulta de hora e data.
- 🌦️ Consulta de clima por cidade.
- 🌐 Abertura de sites conhecidos, como YouTube, Google, WhatsApp, Gmail, GitHub e Netflix.
- 🧮 Abertura de programas do Windows, como Calculadora, Bloco de Notas, Paint e Explorador de Arquivos.
- 🔎 Pesquisa no Google.
- 🎵 Pesquisa de músicas e vídeos no YouTube.
- 🔒 Bloqueio do computador.
- 🔊 Controle de volume por comandos ou percentual.
- ⏰ Lembretes persistentes, com alarme repetido até confirmação.
- 🧠 Cérebro de IA opcional (Gemini) para frases livres. Veja [docs/IA.md](docs/IA.md).
- 🧭 Controle do seu Chrome/Edge (com a sessão logada): abrir o N-ésimo vídeo ou resultado, controlar o player, ler e-mails e tarefas em qualquer site. Veja [docs/NAVEGADOR.md](docs/NAVEGADOR.md).
- 🗣️ Fala natural tolerante, cache das frases já resolvidas pelo Gemini e medição de tempos. Veja [docs/FALA-E-DESEMPENHO.md](docs/FALA-E-DESEMPENHO.md).
- 🎙️ Voz Kokoro opcional (local, com mistura de vozes) e o comando `/voz`, sem alterar a voz e o fallback atuais. Veja [docs/VOZ.md](docs/VOZ.md).
- ⌨️ Modo texto para testar sem microfone.
- 🛠️ Catálogo editável de sites e programas, recarregado sem reiniciar.

## 📋 Requisitos

- 🪟 Windows.
- 🐍 Python 3.12.
- 🎙️ Microfone para o modo de voz.
- 🌐 Conexão com a internet para reconhecimento de voz, pesquisas e consulta do clima.

> O Python 3.12 é recomendado porque o `PyAudio` pode ser mais difícil de instalar em versões mais recentes do Python.

## 📦 Instalação

1. 🐍 Instale o [Python 3.12](https://www.python.org/downloads/).
2. ✅ Durante a instalação, marque a opção **Add python.exe to PATH**.
3. 📥 Baixe ou clone este repositório.
4. 📂 Abra a pasta do projeto.
5. ▶️ Execute `Instalar.bat`.

O script cria o ambiente virtual `.venv` e instala as dependências listadas em `requirements.txt`.

Recursos opcionais, cada um com seu guia:

- 🎙️ `Instalar.bat kokoro` instala a voz Kokoro (`requirements-kokoro.txt`) e, se você confirmar, baixa os modelos. Veja [docs/VOZ.md](docs/VOZ.md).
- 🧭 A extensão do Chrome/Edge fica em `extensao/` e é carregada pelo próprio navegador. Veja [docs/NAVEGADOR.md](docs/NAVEGADOR.md).
- 🧠 `Jarvis.bat ia` liga o cérebro de IA. Veja [docs/IA.md](docs/IA.md).

## 🚀 Uso

Depois da instalação, dê dois cliques em `Jarvis.bat`. Ele mostra um menu e, se você não apertar nenhuma tecla em 60 segundos, inicia o modo voz. Para ir direto a um modo, escreva o nome dele depois de `Jarvis.bat`:

| Comando | Modo |
|---|---|
| `Jarvis.bat` | menu (sem tecla em 60 segundos, inicia o modo voz) |
| `Jarvis.bat voz` | 🎙️ por voz: diga "Jarvis" e o comando |
| `Jarvis.bat texto` | ⌨️ modo texto, para usar sem microfone |
| `Jarvis.bat continuo` | atende qualquer fala, sem palavra de ativação |
| `Jarvis.bat enter` | aperta ENTER antes de falar |
| `Jarvis.bat bot` | liga o bot do Telegram |
| `Jarvis.bat ia` | configura o cérebro de IA |
| `Jarvis.bat testar-voz`, `Jarvis.bat escolher-voz` | testa e escolhe a voz |

`Jarvis.bat ajuda` lista os modos, e opções extras vão direto ao programa (por exemplo, `Jarvis.bat texto --sem-ia`). As opções antigas sem modo, como `Jarvis.bat --sem-ia`, continuam valendo.

No modo de voz, diga **"Jarvis"** seguido do comando e aguarde a resposta. Para apertar **ENTER** antes de falar, use `Jarvis.bat enter`; para ser atendido sem a palavra de ativação, use `Jarvis.bat continuo`.

No modo texto, digite frases normalmente ou comece com `/` para abrir o menu de atalhos. Use as setas para navegar e **Tab** para completar. Os alvos de `/abrir` acompanham o catálogo local. Para ver todos os comandos, use `/ajuda`; para encerrar, use:

```text
sair
```

Atalhos disponíveis: `/lembrete` ou `/lembretes`, `/volume 35`, `/aumentar-volume`, `/diminuir-volume`, `/silenciar`, `/play`, `/pausar`, `/proxima`, `/anterior`, `/parar`, `/abrir <alvo>`, `/confirmar <assunto>`, `/navegador [diagnostico]`, `/voz`, `/tempos`, `/cache [limpar]`, `/limpar` e `/sair`.

Também é possível executar diretamente pelo terminal:

```powershell
python jarvis.py
python jarvis.py --texto
```

## 💬 Exemplos de comandos

| Comando | Ação |
|---|---|
| `que horas são` | Informa a hora atual |
| `que dia é hoje` | Informa a data atual |
| `clima em Bariri` | Consulta o clima da cidade |
| `abrir youtube` | Abre o YouTube no navegador |
| `abrir calculadora` | Abre a Calculadora do Windows |
| `pesquisar receita de bolo` | Pesquisa no Google |
| `tocar Legião Urbana` | Pesquisa no YouTube |
| `volume em 35%` | Define o volume do Windows |
| `me lembre em 10 minutos de ver o arroz no fogo` | Cria um lembrete persistente |
| `listar lembretes` | Lista assunto, horário e estado |
| `confirmar arroz no fogo` | Para o alarme correspondente |
| `ok, verificado` ou `encerre` | Para o alarme que está tocando |
| `encerrar o lembrete` | Cancela um lembrete que ainda não venceu |
| `pesquisa lofi no youtube e abre o primeiro` | Pesquisa e abre o primeiro vídeo no seu navegador (precisa da extensão) |
| `abre o segundo em outra aba` | Abre o segundo resultado da última pesquisa em outra aba |
| `silencia a aba do youtube` | Silencia só aquela aba, sem mexer no volume do Windows |
| `quantos e-mails não lidos eu tenho` | Informa a contagem do Gmail (somente leitura) |
| `bloquear o computador` | Bloqueia o Windows |
| `sair` | Encerra o Jarvis |

## 🛠️ Personalização

Os catálogos padrão ficam em `recursos/config.example.json`. Na primeira execução, o Jarvis cria o arquivo local `dados/config.json`; edições nele são percebidas sem reiniciar. Esse arquivo é ignorado pelo Git para que os itens pessoais não sejam enviados junto com as alterações do projeto.

O próprio Jarvis também pode cadastrar entradas:

```text
adicionar site meu banco
adicionar programa meu editor
```

Ele pede a URL ou o caminho/URI do aplicativo, mostra os dados e só grava depois da confirmação. Para programas, informe um caminho absoluto para um executável existente ou uma URI de aplicativo, como `spotify:`.

Os lembretes ficam em `dados/lembretes.sqlite3`, também ignorado pelo Git. Eles continuam salvos depois de fechar o Jarvis; se vencerem enquanto ele estiver fechado, o alarme começa quando o Jarvis abrir. O alarme fala o assunto e toca um sinal a cada 30 segundos até você dizer, por exemplo, `confirmar arroz no fogo`, `ok, verifiquei`, `arroz verificado`, `ok, verificado` ou `encerre`. Se nada estiver tocando, `encerrar o lembrete` cancela o lembrete que ainda não venceu (o do assunto citado, ou o único pendente; havendo vários, o Jarvis pergunta qual).

O ajuste percentual do volume usa o dispositivo de saída padrão do Windows e precisa da dependência `pycaw`, instalada por `Instalar.bat`.

## 🩹 Solução de problemas

### ❌ O Python não foi encontrado

Reinstale o Python e marque **Add python.exe to PATH**. Depois, feche e abra o terminal novamente e execute `Instalar.bat`.

### 🎙️ Erro relacionado ao PyAudio

Confirme se está usando o Python 3.12 e execute `Instalar.bat` novamente.

### 🔇 O Jarvis não reconhece o microfone

Verifique se o microfone está selecionado como dispositivo padrão em **Configurações > Sistema > Som** e se o Windows permitiu o acesso ao microfone em **Configurações > Privacidade e segurança > Microfone**.

### 📡 O reconhecimento de voz falha

Fale mais perto do microfone, reduza o ruído ambiente e confira sua conexão com a internet.

### 🔊 O Jarvis não fala

O modo texto apenas imprime as respostas no terminal. No modo de voz, verifique o volume e o dispositivo de saída do Windows.

## 🛡️ Segurança e limitações

As ações executadas pelo Jarvis são baseadas em uma lista fixa de sites e programas. Ele não apaga arquivos, movimenta dinheiro ou envia mensagens automaticamente.

Com a extensão do navegador instalada, o Jarvis também consegue ler e clicar em páginas do seu Chrome/Edge, já logado. Nesse caso, passos sensíveis (enviar, comprar, pagar, excluir, confirmar...) só acontecem com o seu "sim", campos de senha nunca são preenchidos e o Gmail é somente leitura. Os detalhes estão em [docs/NAVEGADOR.md](docs/NAVEGADOR.md).

O projeto é específico para Windows e depende de serviços externos para reconhecimento de voz e consulta do clima.

## 📚 Documentação

Os guias ficam em [docs/](docs/README.md): [guia rápido](docs/GUIA-RAPIDO.md), [modo de voz](docs/MODO-DE-VOZ.md), [vozes](docs/VOZES.md), [voz Kokoro e `/voz`](docs/VOZ.md), [cérebro de IA](docs/IA.md), [controle do navegador](docs/NAVEGADOR.md), [fala natural e desempenho](docs/FALA-E-DESEMPENHO.md) e [Telegram](docs/TELEGRAM.md).

## 📁 Estrutura do projeto

```text
.
├── Jarvis.bat                      # ponto de entrada: menu e todos os modos
├── Instalar.bat                    # instalação (Instalar.bat kokoro: voz opcional)
├── lancador.py                     # menu e modos do Jarvis.bat
├── jarvis.py                       # o assistente (regras, voz, loop)
├── cli.py                          # interface do terminal (painel, menu de /)
├── acoes.py / acoes_navegador.py   # catálogo de ações (e as do navegador)
├── cerebro.py                      # cérebro de IA (Gemini)
├── cache_planos.py                 # cache das frases já resolvidas pela IA
├── linguagem.py                    # tolerância à fala natural nas regras locais
├── tempos.py                       # medição de tempos (/tempos)
├── lembretes.py                    # lembretes e alarmes persistentes
├── catalogo.py                     # sites e programas editáveis
├── caminhos.py                     # onde ficam os dados (dados/) e os recursos (recursos/)
├── telegram_bot.py                 # bot do Telegram
├── configurar_ia.py / escolher_voz.py
├── navegador/                      # ponte, atalhos por site e modo genérico
├── voz/                            # voz Kokoro opcional e o comando /voz
├── extensao/                       # extensão do Chrome/Edge
├── recursos/                       # config.example.json, comparador-vozes.html e amostras de voz
├── dados/                          # seus arquivos (ignorado pelo Git): config, lembretes, cache, modelos
├── docs/                           # guias (veja docs/README.md)
├── tests/
├── requirements.txt
├── requirements-kokoro.txt         # dependências opcionais da voz Kokoro
├── requirements-dev.txt            # ferramentas de desenvolvimento (cobertura de testes)
└── .gitignore
```

### 📂 `dados/` e `recursos/`

Tudo que o Jarvis grava no seu computador fica em `dados/` e **não vai para o Git**: `config.json`, `ia_config.json`, `bot_config.json`, `voz.json`, `navegador.json`, `lembretes.sqlite3`, `tempos.jsonl`, `cache_planos.json`, `cache_voz/` e `modelos/`. Para fazer backup ou começar do zero, basta copiar ou apagar essa pasta.

Versões antigas guardavam esses arquivos soltos na raiz. Na primeira abertura depois da atualização, o Jarvis **move** o que encontrar para `dados/`, sem sobrescrever nada: se um arquivo estiver em uso (por exemplo, o banco de lembretes com outro Jarvis aberto), ele continua no lugar antigo até a próxima abertura. A variável de ambiente `JARVIS_DADOS` usa outra pasta no lugar de `dados/`.

`recursos/` guarda o que faz parte do projeto: `config.example.json`, `comparador-vozes.html` e as amostras de voz (`vozes/` e `vozes-br/`).

## 🔗 Dependências

- [pyttsx3](https://pypi.org/project/pyttsx3/) — síntese de voz.
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) — reconhecimento de voz.
- [PyAudio](https://pypi.org/project/PyAudio/) — acesso ao microfone.
- [edge-tts](https://pypi.org/project/edge-tts/) — voz neural.
- [pygame](https://pypi.org/project/pygame/) — reprodução do áudio.
- [pycaw](https://pypi.org/project/pycaw/) — volume do Windows.
- [rich](https://pypi.org/project/rich/) e [prompt_toolkit](https://pypi.org/project/prompt-toolkit/) — interface do terminal.
- [kokoro-onnx](https://pypi.org/project/kokoro-onnx/) — voz Kokoro local (opcional, `requirements-kokoro.txt`).
