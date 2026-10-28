# Jarvis autônomo — o cérebro de IA

Até aqui o Jarvis era um **executor de comandos**: ele reconhecia frases que já estavam
programadas ("que horas são", "abrir youtube"). Agora ele ganhou duas coisas:

1. **Um catálogo de ações** que ele sabe executar no PC (mídia, volume, lembretes, sistema…)
2. **Um cérebro de IA** que lê a sua frase, entende o que você quer e **escolhe as ações sozinho**

O resultado é o que você pediu: *"dar play no spotify"* funciona, e ele decide como fazer.

---

## Como ligar (5 minutos, grátis)

### 1. Pegue a chave gratuita

1. Abra **https://aistudio.google.com/apikey**
2. Entre com sua conta Google
3. Clique em **"Create API key"**
4. Copie a chave (começa com `AIza…` e tem ~39 caracteres)

Não precisa de cartão de crédito. O plano gratuito do Gemini cobre milhares de comandos por dia.

### 2. Configure

Rode **`Jarvis.bat ia`** → cole a chave → ENTER.

O configurador **testa os modelos gratuitos na sua chave** e escolhe o que funcionar
(hoje: `gemini-3.5-flash-lite`, `gemini-3.8-flash`, `gemini-3.1-flash-lite`…).
Ele grava tudo em `dados/ia_config.json`.

### 3. Use

Abra o **`Jarvis.bat`** normalmente. Você verá:

```
(cerebro de IA ativo: entendo frases livres e decido as acoes)
```

Agora fale do jeito que quiser:

| Você diz | O que ele faz |
|---|---|
| "dar play no spotify" | abre o Spotify e dá play |
| "pausa a música" | pausa o player (Spotify, YouTube, qualquer um) |
| "próxima música" | pula a faixa |
| "aumenta o volume" | sobe o volume do Windows |
| "abre o netflix **e** aumenta o volume" | executa as **duas** coisas em sequência |
| "quanto tá o dólar" | pesquisa |
| "quanto é 15% de 340" | responde **51** (conversa, sem abrir nada) |
| "me lembra em 10 minutos de tirar o bolo" | cria lembrete persistente e avisa por voz |
| "listar lembretes" | mostra assunto, horário e estado |
| "confirmar tirar o bolo" | para o alarme desse lembrete |
| "ok, verificado" ou "encerre" | para o alarme que está tocando |
| "encerrar o lembrete" | cancela um lembrete que ainda não venceu |
| "pesquisa lofi no youtube e abre o segundo" | pesquisa e abre o segundo vídeo no seu navegador (precisa da extensão) |
| "silencia a aba do youtube" | silencia só aquela aba |
| "como está a memória do PC" | lê memória, disco e bateria |
| "desliga o computador" | pede confirmação antes |
| "deleta a pasta tal" | recusa — não existe essa ação no catálogo |

---

## Como funciona por dentro

```
Você fala
   │
   ├─ 1. REGRAS LOCAIS (instantâneo, sem internet)
   │      "que horas são", "abrir youtube", "dar play", "próxima música",
   │      "abre o segundo vídeo"
   │      → executa direto, sem gastar IA
   │
   ├─ 2. CACHE (instantâneo, sem internet)
   │      frase que a IA já resolveu antes → reaproveita o plano
   │
   ├─ 3. IA (1–2 segundos, precisa de internet)
   │      frase livre → catálogo de ações → plano em JSON → executa
   │      (se der certo, o plano é guardado no cache)
   │
   └─ 4. NADA FUNCIONOU
          pergunta se pode pesquisar no Google
```

Para acelerar a etapa 3, o prompt começa pela parte que não muda (o Gemini reaproveita esse
trecho) e, quando a frase não fala de navegador, leva só as ações que não são do navegador.
Veja **`docs/FALA-E-DESEMPENHO.md`**.

O truque central: **a IA não ganha acesso ao computador**. Ela só pode escolher nomes
de ações de uma lista fechada (`acoes.py`), com parâmetros validados. Tudo que não está
no catálogo é rejeitado na hora:

```
Voce: deleta a pasta toda
   (IA sugeriu acao desconhecida: apagar_tudo - ignorada)
Jarvis: Nao tenho permissao para apagar arquivos, senhor.
```

### As ações disponíveis hoje (59)

| Categoria | Ações |
|---|---|
| **Mídia** | play/pausa, próxima, anterior, parar, Spotify (abrir/buscar), YouTube |
| **Som** | volume aumentar/diminuir, percentual de 0 a 100, mudo |
| **Apps e sites** | abrir programa, abrir site, abrir URL, pesquisar no Google |
| **Informação** | horas, data, clima de qualquer cidade, status do PC |
| **Rotina** | lembretes persistentes, listar e confirmar alarmes pelo assunto, cancelar lembretes que ainda não venceram |
| **Sistema** | bloquear, desligar ⚠️, reiniciar ⚠️, hibernar ⚠️, cancelar desligamento |
| **Navegador** (35 ações, precisam da extensão) | abas (listar, trocar, fechar em lote, silenciar, agrupar), YouTube, Google, Gmail em leitura, Spotify Web e YouTube Music, histórico e favoritos, Maps, rastreio, GitHub e um modo genérico para qualquer site (`docs/NAVEGADOR.md`) |

⚠️ = pede confirmação ("Isso vai DESLIGAR o computador. Confirma?").

---

## Segurança: o que mantém o controle na sua mão

| Risco | Proteção |
|---|---|
| A IA "inventar" comandos perigosos | Só executa o que está em `acoes.py`. Ações desconhecidas são descartadas. |
| Desligar o PC por acidente | Ações marcadas como risco **sempre** pedem confirmação falada | 
| Alguém desligar o PC pelo Telegram | **Bloqueado**: ações de risco só funcionam no terminal do PC |
| A IA ser convencida a "apagar tudo" | Não existe ação de apagar arquivos, nem de executar comandos livres |
| Chave vazando | Fica em `dados/ia_config.json`, local. Não vai para nenhum servidor seu. |
| Custo | Plano gratuito. Se estourar o limite, ele volta às regras locais sozinho. |
| A IA clicar em algo sensível numa página | No modo genérico do navegador, passos como enviar, comprar, pagar, excluir e confirmar pedem o seu "sim"; campos de senha nunca são preenchidos. Pelo Telegram, esses passos são recusados. |
| Uma frase guardada no cache executar a coisa errada | Planos que falham são esquecidos na hora; ações de risco e frases que dependem do contexto nunca entram no cache; `/cache limpar` esquece tudo. |

O que a IA **não** faz, por decisão de projeto: apagar/mover arquivos, mexer em dinheiro,
enviar mensagens em seu nome, instalar programas, alterar o próprio código. No navegador,
o Gmail é somente leitura e nada sensível acontece sem a sua confirmação.

---

## Limites honestos (para você não se decepcionar)

- **Não é o JARVIS do filme.** Ele não tem consciência, não aprende preferências sozinho com o
  uso (só guarda no cache as frases que a IA já resolveu) e não toma iniciativa sem você pedir algo.
- **Cada frase livre nova custa 1–2 segundos** (ida e volta à internet). Comandos conhecidos
  continuam instantâneos porque passam pelas regras locais, e uma frase repetida sai do cache.
- **Precisa de internet** para a IA. Sem conexão, ele volta a ser o executor de regras.
- **O Spotify abre na busca, não toca a música exata.** "Tocar X" no Spotify exige a API
  oficial do Spotify (autenticação do usuário). Por isso o padrão para "tocar uma música X"
  é o YouTube, que funciona sempre. Play/pausa/próxima funcionam no Spotify via teclas de mídia.
- **Entende o que está no catálogo.** Se você pedir "manda um e-mail pro meu chefe", ele vai
  dizer que não tem essa ação (e não vai improvisar).

---

## Se algo der errado

| Problema | Solução |
|---|---|
| "IA desligada: sem chave" | Rode `Jarvis.bat ia`. |
| "IA indisponível: HTTP 429" | Você estourou o limite gratuito do dia. Volta a funcionar amanhã, ou troca o modelo no `dados/ia_config.json`. |
| "IA indisponível: HTTP 404" | Modelo não existe na sua chave. Rode `Jarvis.bat ia` de novo: ele testa e escolhe um válido. |
| Ele erra o comando com frequência | Fale de forma mais específica ("abrir o Bloco de Notas" em vez de "abre aí"). O modelo pequeno é rápido, mas menos esperto que os grandes. |
| Ele repete sempre a mesma ação errada para uma frase | Pode ser um plano guardado no cache. Use `/cache limpar` no modo texto. |
| Quero ver onde o tempo dos comandos está indo | Use `/tempos` no modo texto (atalho, cache ou IA, e o tempo de cada etapa). |
| Quero desligar a IA | `Jarvis.bat --sem-ia`, ou apague `dados/ia_config.json`. |
| Quero ver o diagnóstico | No terminal: `python jarvis.py --ia-status` |

---

## Ensinar ações novas (é fácil)

Abra `acoes.py` e adicione uma função com o decorador:

```python
@acao("abrir_pasta", "Abre uma pasta do computador", "nome: documentos, downloads, fotos")
def abrir_pasta(ctx, nome="", **kw):
    pastas = {"documentos": "C:\\Users\\SEU_USUARIO\\Documents",
              "downloads": "C:\\Users\\SEU_USUARIO\\Downloads"}
    caminho = pastas.get(ctx.normalizar(nome))
    if not caminho:
        return None
    subprocess.Popen(f'explorer "{caminho}"')
    return f"Abrindo a pasta {nome}, senhor."
```

Salve e pronto: a IA passa a enxergar a ação automaticamente, porque o catálogo é gerado
a partir do decorador. **Você não precisa mexer no prompt.**

Ações novas ficam no grupo `geral` e vão em toda chamada. As do navegador ficam em
`acoes_navegador.py` (grupo `navegador`) e só vão ao prompt quando a frase fala de navegador;
veja `docs/NAVEGADOR.md` e `docs/FALA-E-DESEMPENHO.md`.

---

## Próximos passos possíveis

Ideias que fazem sentido depois, se você quiser:

- **Memória de preferências** ("toda vez que eu disser 'modo trabalho', abre o Word e o Teams")
- **Rotinas nomeadas** ("modo cinema": fecha apps, abre Netflix, abaixa a luz)
- **Controle de casa** com ESPHome/Home Assistant
- **Visão de tela** (mandar um print para a IA e perguntar "o que está errado aqui?")
- **Agente de tarefas longas** ("organiza meus downloads por tipo") — possível, mas exige
  mais camadas de segurança e confirmação passo a passo
