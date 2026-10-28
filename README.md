# 🤖 Jarvis

Assistente pessoal simples para Windows, capaz de conversar por voz, responder a comandos básicos e executar tarefas no computador. 🖥️

O projeto roda localmente, sem exigir conta em nuvem ou chave de API. O reconhecimento de voz utiliza um serviço externo do Google, portanto é necessário ter conexão com a internet para usar o modo de voz.

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
5. ▶️ Execute `instalar.bat`.

O script cria o ambiente virtual `.venv` e instala as dependências listadas em `requirements.txt`.

## 🚀 Uso

Depois da instalação:

- 🎙️ Execute `Jarvis.bat` para usar o assistente por voz.
- ⌨️ Execute `Jarvis-texto.bat` para usar o modo texto.

No modo de voz, pressione **ENTER**, fale o comando e aguarde a resposta.

No modo texto, digite frases normalmente ou comece com `/` para abrir o menu de atalhos. Use as setas para navegar e **Tab** para completar. Os alvos de `/abrir` acompanham o catálogo local. Para ver todos os comandos, use `/ajuda`; para encerrar, use:

```text
sair
```

Atalhos disponíveis: `/lembretes`, `/volume 35`, `/aumentar-volume`, `/diminuir-volume`, `/silenciar`, `/play`, `/pausar`, `/proxima`, `/anterior`, `/parar`, `/abrir <alvo>`, `/confirmar <assunto>`, `/limpar` e `/sair`.

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
| `bloquear o computador` | Bloqueia o Windows |
| `sair` | Encerra o Jarvis |

## 🛠️ Personalização

Os catálogos padrão ficam em `config.example.json`. Na primeira execução, o Jarvis cria o arquivo local `config.json`; edições nele são percebidas sem reiniciar. Esse arquivo é ignorado pelo Git para que os itens pessoais não sejam enviados junto com as alterações do projeto.

O próprio Jarvis também pode cadastrar entradas:

```text
adicionar site meu banco
adicionar programa meu editor
```

Ele pede a URL ou o caminho/URI do aplicativo, mostra os dados e só grava depois da confirmação. Para programas, informe um caminho absoluto para um executável existente ou uma URI de aplicativo, como `spotify:`.

Os lembretes ficam em `lembretes.sqlite3`, também ignorado pelo Git. Eles continuam salvos depois de fechar o Jarvis; se vencerem enquanto ele estiver fechado, o alarme começa quando o Jarvis abrir. O alarme fala o assunto e toca um sinal a cada 30 segundos até você dizer, por exemplo, `confirmar arroz no fogo`.

O ajuste percentual do volume usa o dispositivo de saída padrão do Windows e precisa da dependência `pycaw`, instalada por `instalar.bat`.

## 🩹 Solução de problemas

### ❌ O Python não foi encontrado

Reinstale o Python e marque **Add python.exe to PATH**. Depois, feche e abra o terminal novamente e execute `instalar.bat`.

### 🎙️ Erro relacionado ao PyAudio

Confirme se está usando o Python 3.12 e execute `instalar.bat` novamente.

### 🔇 O Jarvis não reconhece o microfone

Verifique se o microfone está selecionado como dispositivo padrão em **Configurações > Sistema > Som** e se o Windows permitiu o acesso ao microfone em **Configurações > Privacidade e segurança > Microfone**.

### 📡 O reconhecimento de voz falha

Fale mais perto do microfone, reduza o ruído ambiente e confira sua conexão com a internet.

### 🔊 O Jarvis não fala

O modo texto apenas imprime as respostas no terminal. No modo de voz, verifique o volume e o dispositivo de saída do Windows.

## 🛡️ Segurança e limitações

As ações executadas pelo Jarvis são baseadas em uma lista fixa de sites e programas. Ele não apaga arquivos, movimenta dinheiro ou envia mensagens automaticamente.

O projeto é específico para Windows e depende de serviços externos para reconhecimento de voz e consulta do clima.

## 📁 Estrutura do projeto

```text
.
├── jarvis.py
├── requirements.txt
├── instalar.bat
├── Jarvis.bat
├── Jarvis-texto.bat
├── README.md
├── LEIA-ME.md
└── .gitignore
```

## 🔗 Dependências

- [pyttsx3](https://pypi.org/project/pyttsx3/) — síntese de voz.
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) — reconhecimento de voz.
- [PyAudio](https://pypi.org/project/PyAudio/) — acesso ao microfone.
