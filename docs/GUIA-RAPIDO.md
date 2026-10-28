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
2. Dê **dois cliques em `Instalar.bat`**.
3. Ele cria um ambiente isolado e baixa as bibliotecas de voz. Aguarde 1–3 minutos.

## Passo 3 — Usar

Dê dois cliques em **`Jarvis.bat`**: ele mostra um menu e, se você não apertar nenhuma tecla em 60 segundos, inicia o modo voz. Para ir direto a um modo, escreva o nome dele depois de `Jarvis.bat`:

- **`Jarvis.bat`** → menu; sem tecla em 60 segundos, escuta sempre, mas só atende quando ouve **"Jarvis"**.
- **`Jarvis.bat continuo`** → escuta e atende qualquer fala, sem palavra de ativação.
- **`Jarvis.bat enter`** → modo antigo: aperta ENTER e fala.
- **`Jarvis.bat texto`** → digite os comandos (útil para testar sem microfone).
- **`Jarvis.bat testar-voz`** → fala uma frase de teste, para você conferir a voz escolhida.
- **`Jarvis.bat escolher-voz`** → toca todas as vozes e grava a sua favorita automaticamente.
- **`recursos/comparador-vozes.html`** → compare as 8 vozes brasileiras no navegador.
- **`Jarvis.bat bot`** → liga o Jarvis no Telegram (guia: [TELEGRAM.md](TELEGRAM.md)).
- **`Jarvis.bat ia`** → liga o cérebro de IA, que entende frases livres (guia: [IA.md](IA.md)).
- **`Instalar.bat kokoro`** → instala a voz Kokoro, opcional e local (guia: [VOZ.md](VOZ.md)).

`Jarvis.bat ajuda` lista todos os modos, e opções extras vão direto ao programa (por exemplo, `Jarvis.bat texto --sem-ia`). As opções antigas sem modo, como `Jarvis.bat --sem-ia`, continuam valendo e iniciam o modo voz.

Na primeira vez o Windows pode pedir permissão para usar o microfone: clique em **Permitir**.

> Dica: clique com o botão direito em `Jarvis.bat` → *Enviar para* → *Área de trabalho (criar atalho)*.
> Depois clique com o botão direito no atalho → *Propriedades* → *Avançado* → marque **Executar como administrador** (necessário só se você usar o comando de bloquear o PC).
> Para um atalho que abra direto num modo, acrescente o nome dele no destino do atalho (por exemplo, `...\Jarvis.bat texto`).

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

O catálogo padrão está em `recursos/config.example.json`; o Jarvis cria `dados/config.json` local na primeira execução e recarrega as mudanças automaticamente. Esse arquivo é ignorado pelo Git.

Você também pode pedir:

```text
adicionar site meu banco
adicionar programa meu editor
```

O Jarvis pede a URL ou o caminho/URI do aplicativo, mostra o que será salvo e espera sua confirmação. Programas novos aceitam caminho absoluto para executável existente ou URI registrada pelo aplicativo, como `spotify:`.

Os lembretes são salvos em `dados/lembretes.sqlite3` e continuam depois que o Jarvis fecha. Se um lembrete vencer enquanto o app estiver fechado, o alarme começa quando ele abrir e repete a cada 30 segundos até você confirmar pelo assunto ou, com ele tocando, dizer algo como "ok, verificado" ou "encerre". Quando nada está tocando, "encerrar o lembrete" cancela o lembrete que ainda não venceu (o do assunto citado, ou o único pendente; havendo vários, ele pergunta qual).

---

## Se algo não funcionar

| Problema | Solução |
|---|---|
| `Instalar.bat` diz que o Python não foi encontrado | Reinstale o Python marcando **Add python.exe to PATH**. |
| Erro falando de **PyAudio** | Instale o **Python 3.12** (tem instalador pronto). Nas versões mais novas do Python, às vezes é preciso compilar, o que é mais chato. |
| Ele abre, mas não ouve nada | Confira o microfone padrão em *Configurações → Sistema → Som*, e permita o microfone em *Configurações → Privacidade → Microfone*. |
| Ele ouve errado e responde "não entendi" | Fale mais perto do microfone e sem barulho de fundo. O reconhecimento usa a internet. |
| Não fala em voz alta | No modo texto ele só imprime. No `Jarvis.bat` ele fala; se ficar mudo, verifique o volume e o dispositivo de saída. |
| A voz neural não sai | Ela precisa de internet e de `edge-tts` + `pygame` instalados (o `Instalar.bat` já instala). Sem internet, o Jarvis cai automaticamente para a voz do Windows. |
| A voz neural demora ~1s para começar | Normal: o texto é gerado na hora. Frases curtas (como as deste Jarvis) levam menos de 1 segundo. |
| Ativei o Kokoro e o Jarvis voltou para a voz de antes | Ele cai sozinho para a voz padrão quando o Kokoro falha. Digite `/voz`: o "último erro" mostra o motivo. Guia: `docs/VOZ.md`. |
| Comandos do navegador dizem que a extensão não está conectada | Abra o Jarvis, recarregue a extensão em `chrome://extensions` e veja o selo **ON**. Guia: `docs/NAVEGADOR.md`. |

**Dica de segurança:** este Jarvis só executa ações de uma lista fixa. Nada de apagar arquivos, mexer em dinheiro ou enviar mensagens sem você confirmar. Mantenha assim.

## 🧠 Cérebro de IA (frases livres)

Sem IA, ele entende comandos conhecidos. **Com IA, ele entende o que você quiser dizer** e
decide sozinho quais ações executar no PC.

**Ligar (5 min, grátis):**

1. Pegue uma chave em **https://aistudio.google.com/apikey** (sem cartão de crédito)
2. Rode **`Jarvis.bat ia`** → cole a chave
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

Detalhes, limites honestos e como adicionar ações novas: **`IA.md`**.
Para desligar a IA: `Jarvis.bat --sem-ia` ou apague o `dados/ia_config.json`.
Diagnóstico: `python jarvis.py --ia-status`.

---

## 📱 No celular (Telegram) — pronto

O bot já está montado. Guia completo em **`TELEGRAM.md`**, resumo:

1. No Telegram, fale com **@BotFather** → `/newbot` → copie o token.
2. Rode **`Jarvis.bat bot`** → cole o token.
3. Mande `/start` para o seu bot. Ele responde em texto **e em voz**.

O primeiro chat que falar com o bot vira o **dono** — qualquer outro chat é
ignorado. O bot roda no seu PC, então ele precisa estar ligado.
