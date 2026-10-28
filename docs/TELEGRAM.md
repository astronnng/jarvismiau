# Jarvis no celular pelo Telegram — guia completo

Com o bot, você usa o Jarvis **do celular**, de qualquer lugar, com a mesma voz
(Rémy, a que você escolheu). Ele responde por escrito **e em áudio**.

```
Celular (Telegram)  →  seu PC (bot rodando)  →  responde em texto + voz
```

**A única condição:** o PC precisa estar ligado e com internet. O bot roda nele.

---

## Passo 1 — Criar o bot no Telegram (2 minutos, grátis)

1. No Telegram, procure **@BotFather** (é o oficial, com selo azul).
2. Mande a mensagem: `/newbot`
3. Ele pergunta o **nome** do bot. Responda do jeito que quiser:
   `Jarvis do Bruno` (pode ser qualquer coisa)
4. Depois ele pede um **usuário**, que precisa terminar em `bot` e ser único:
   `jarvis_bruno_bot` (se já existir, tente outro)
5. Ele responde com uma linha assim:

```
Use this token to access the HTTP API:
1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Esse token é a senha do seu bot.** Guarde e não compartilhe. Quem tem o token
controla o bot.

6. Ainda no BotFather, mande `/setdescription` e escolha o seu bot, se quiser
   personalizar o texto. Opcional.

---

## Passo 2 — Ligar o bot no PC

1. Rode **`Jarvis.bat bot`**.
2. Na primeira vez, ele pede o token. **Cole com Ctrl+V** e aperte ENTER.
   (No prompt do Windows, Ctrl+V funciona; ou clique com o botão direito.)
3. Ele mostra:

```
==============================================================
   BOT ONLINE: @jarvis_bruno_bot
==============================================================
Voz: BR_REMY (fr-FR-RemyMultilingualNeural)
Abra o Telegram, encontre o bot e mande /start.
```

O token fica salvo em `dados/bot_config.json`. Nas próximas vezes, é só rodar `Jarvis.bat bot` de novo.

---

## Passo 3 — Usar

1. No Telegram, procure o `@` que você criou e mande `/start`.
2. O Jarvis responde:

> 🔐 Você é o dono deste Jarvis. Só este chat pode dar comandos.

Isso é a **proteção**: só esse seu chat pode mandar comandos. Qualquer outra
pessoa que achar o bot recebe "Este Jarvis é privado".

3. Agora teste:

| Você manda | Ele faz |
|---|---|
| `que horas são` | responde em texto **e em áudio** |
| `clima em Bariri` | consulta e fala |
| `abrir youtube` | **abre o navegador no seu PC**, não no celular |
| `abrir calculadora` | abre o programa no PC |
| `pesquisar preço do dólar` | pesquisa no PC |
| `bloquear o computador` | trava o PC |
| `/voz` | mostra a voz ativa (perfil Edge/Windows, usado no áudio das respostas) |
| `/id` | mostra o ID do chat |
| `/ajuda` | lista os comandos |

**Detalhe importante:** quando você pede "abrir youtube", ele abre **no PC**.
O celular recebe a confirmação em texto e voz. Isso é ótimo para chegar em casa
e mandar o PC abrir as coisas antes de sentar. Se quiser que ele abra sites no
**celular**, é outra configuração — me avise que eu ajusto.

**Voz Kokoro:** a voz Kokoro do terminal (`/voz` no `Jarvis.bat texto`, veja `docs/VOZ.md`) não é usada
pelo bot. O áudio que chega no Telegram continua sendo gerado com o perfil Edge, e o `/voz` do bot só
mostra esse perfil.

**Navegador:** os comandos do navegador (`docs/NAVEGADOR.md`) também funcionam pelo bot, com limites:

- Os que só abrem endereços (pesquisas, Maps, rastreio, GitHub) abrem no navegador padrão do PC.
- Os que leem ou clicam em páginas (abrir o segundo vídeo, abas, Gmail) precisam da extensão conectada
  ao programa que está usando a porta da ponte. O bot só sobe essa ponte quando é preciso e
  **se o Jarvis (`Jarvis.bat`, `Jarvis.bat texto`...) não estiver aberto**; com ele aberto, a porta já
  está em uso e o bot avisa que a ponte não está ativa. Na primeira tentativa, a extensão pode levar
  alguns segundos para reconectar.
- Passos sensíveis do modo genérico (enviar, comprar, pagar, excluir...) são recusados pelo Telegram,
  porque o bot não consegue pedir a confirmação.

---

## Deixar o bot mais rápido (recomendado)

O bot usa o mesmo cache de voz do Jarvis, então as respostas fixas já saem instantâneas.
Para as respostas imprevisíveis (hora, clima) ficarem rápidas também, instale o **ffmpeg**:

```
winget install ffmpeg
```

Depois **feche e abra** o bot. Isso tem dois efeitos: o áudio das respostas começa em
~130 ms em vez de ~1,2 s, e o bot passa a **entender mensagens de voz** que você mandar.

## Mensagem de voz (opcional)

Você pode **falar** com o bot em vez de escrever, mas isso exige o `ffmpeg`
(um conversor de áudio gratuito):

1. Abra o Prompt de Comando como administrador e rode:
   ```
   winget install ffmpeg
   ```
2. **Feche e abra novamente** a janela do bot.
3. Agora mande um áudio no Telegram: ele transcreve, executa e responde.

Sem o ffmpeg, o bot avisa e pede para você escrever. Tudo o mais funciona igual.

---

## Deixar o bot sempre ligado

O bot morre quando você fecha a janela ou desliga o PC. Duas opções:

### Simples: iniciar junto com o Windows

1. Clique com o botão direito em `Jarvis.bat` → *Enviar para* →
   *Área de trabalho (criar atalho)* (na verdade, crie o atalho onde quiser).
2. Clique com o botão direito no atalho → *Propriedades* e, no campo **Destino**, escreva ` bot`
   no fim (depois do caminho do `Jarvis.bat`).
3. Aperte `Win + R`, digite `shell:startup` e ENTER.
4. **Copie o atalho** (não o arquivo .bat) para a pasta que abriu.

Pronto: ao ligar o PC, o bot sobe sozinho, minimizado com a janela aberta.

### Melhor: rodar escondido

1. Crie um arquivo `iniciar_oculto.vbs` na pasta do Jarvis com o conteúdo:
   ```vbs
   Set obj = CreateObject("WScript.Shell")
   obj.Run """C:\jarvis\Jarvis.bat"" bot", 0, False
   ```
   (ajuste o caminho para onde você salvou a pasta)
2. Coloque um atalho **desse .vbs** na pasta `shell:startup`.

Assim ele roda sem janela atrapalhando. Para ver se está vivo, mande `/voz` no Telegram.

---

## Se algo der errado

| Problema | Causa e solução |
|---|---|
| `Não consegui falar com o Telegram` | Token errado ou incompleto. Apague o `dados/bot_config.json` e rode de novo. |
| O bot não responde | 1) A janela do bot está aberta? 2) O PC está ligado? 3) Confira se o `@` é o certo. |
| Responde "Este Jarvis é privado" | Você está em outra conta ou outro chat. Só o primeiro chat registrado manda comandos. Para trocar de dono: apague a linha dentro de `"donos": []` no `dados/bot_config.json` e mande `/start` de novo. |
| Chegam várias respostas repetidas | O Telegram reenvia atualizações não confirmadas. Feche e abra o bot; o controle de `offset` se resolve sozinho. |
| Sem áudio nas respostas | Só texto chegou porque a voz falhou (sem internet ou falta `edge-tts`). Rode o `Instalar.bat`. |
| Áudio do usuário não funciona | Falta o `ffmpeg` (veja a seção acima). |
| Quero apagar o bot | No BotFather: `/deletebot`. |

---

## Segurança — leia uma vez

- **O token é uma senha.** Não poste em print, vídeo ou grupo.
- O bot **só aceita comandos do seu chat**, e só executa a lista de ações do
  `jarvis.py`. Ele não apaga arquivos nem mexe em dinheiro.
- Você pode restringir ainda mais: em `jarvis.py`, apague das listas `PROGRAMAS`
  e `SITES` o que não quiser que seja acessível remotamente. Exemplo: tirar
  `bloquear o computador` evita que um comando errado trave o PC longe de casa.
- Se o PC for compartilhado, lembre que **qualquer pessoa na frente dele** pode
  usar o `Jarvis.bat` normalmente. A proteção do chat vale só para o Telegram.

---

## Próximos passos possíveis

Quando quiser ir além, eu monto:

- **Aviso dos lembretes no Telegram** — os lembretes e alarmes já existem ("me lembre em 10
  minutos de X"), mas o alarme toca e fala no PC; o aviso no celular ainda não.
- **Respostas com IA de verdade** — já funcionam: com a chave do Gemini configurada
  (`Jarvis.bat ia`, plano gratuito), o bot entende frases livres e conversa, mantendo os
  comandos do PC. Veja `IA.md`.
- **Notificações do PC no celular** (por exemplo, avisar quando um download
  termina ou quando alguém tenta errar a senha).
- **Botão de pânico / status do PC** ("como está a memória?", "que música está tocando?").
