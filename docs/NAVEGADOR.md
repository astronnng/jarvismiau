# 🌐 Controle do navegador

O Jarvis consegue controlar o **seu** Chrome ou Edge, com a sua sessão já logada, por meio de uma pequena extensão que fica nesta pasta (`extensao/`). Dá para pedir coisas como:

- "pesquisa receita de pão no YouTube, abre o primeiro vídeo e o segundo em outra aba"
- "pausa o vídeo", "velocidade 1.5", "pula o anúncio"
- "quantos e-mails não lidos eu tenho?", "lê os 3 primeiros e-mails"
- "pesquisa X no Google e abre o terceiro resultado"
- "em qualquer site: abre a aba de preços e clica no plano mensal" (modo genérico)

> Não usa navegador de depuração nem perfil separado. O Chrome 136+ bloqueia a porta de depuração no perfil normal, e esta solução não precisa dela.

## 🧩 Como funciona

```text
Você ──► Jarvis ──► Gemini escolhe uma ação do catálogo
                         │
          acoes_navegador.py   (nomes e descrições que a IA enxerga)
                         │
     ┌───────────────────┴───────────────────┐
     │ navegador/atalhos.py   fluxos exatos  │   navegador/generico.py
     │ YouTube, Google, Gmail, URLs          │   qualquer site, via Gemini
     └───────────────────┬───────────────────┘
                         │  navegador.enviar("clicar", n=3)
                 navegador/ponte.py   servidor HTTP em 127.0.0.1
                         │  (long polling, com token)
                 extensao/background.js   service worker
                         │  chrome.scripting
                 extensao/paginas.js      roda dentro da página
```

A extensão **não conhece nenhum site**. Ela só oferece operações genéricas; todo o conhecimento de sites (seletores, URLs) fica em Python, em `navegador/atalhos.py`.

## 📥 Instalação (uma vez)

1. Abra o Jarvis uma vez (`Jarvis.bat texto`). Ele cria `dados/navegador.json` (porta e token) e `extensao/config.local.js` (cópia para a extensão). Ambos são ignorados pelo Git.
2. No Chrome acesse `chrome://extensions` (no Edge, `edge://extensions`).
3. Ative o **Modo do desenvolvedor**.
4. Clique em **Carregar sem compactação** e escolha a pasta `extensao/` deste projeto.
5. O ícone da extensão mostra o selo **ON** quando está conectada ao Jarvis. No Jarvis, o comando `/navegador` também informa o estado.

Se o selo mostrar `!`, o token mudou: recarregue a extensão em `chrome://extensions`.
Se a porta 8765 estiver ocupada, defina `JARVIS_NAVEGADOR_PORTA` antes de abrir o Jarvis e recarregue a extensão.

## 🗣️ O que dá para pedir

| Ação do catálogo | Exemplo de frase |
|---|---|
| `youtube_pesquisar` + `youtube_abrir_resultado` | "pesquisa lofi no YouTube e abre o primeiro" |
| `youtube_abrir_resultado` com `nova_aba` | "abre o segundo em outra aba" |
| `youtube_abrir_varios` | "abre os 3 primeiros vídeos" |
| `resultado_abrir` | "abre o segundo", "abre o último", "abre o terceiro em outra aba" (descobre sozinho se é da última pesquisa do YouTube, do Google, do histórico ou dos favoritos) |
| `youtube_player` | "pausa", "próximo vídeo", "velocidade 1.5", "pula o anúncio", "legendas" |
| `google_pesquisar` + `google_abrir_resultado` | "pesquisa X e abre o segundo resultado" |
| `gmail_nao_lidos`, `gmail_listar`, `gmail_abrir` | "quantos e-mails não lidos?", "abre o primeiro e-mail" |
| `maps_buscar`, `maps_rota` | "rota para o aeroporto" |
| `rastrear_encomenda`, `github_abrir` | "rastreia AA123456789BR", "abre minhas notificações do GitHub" |
| `aba_listar`, `aba_trocar`, `aba_fechar`, `aba_duplicar` | "troca para a aba do Gmail", "fecha essa aba" |
| `abas_som`, `aba_silenciar` | "qual aba está tocando?", "silencia a aba do YouTube", "religa o som da aba do Spotify" |
| `abas_fechar`, `aba_reabrir`, `aba_fixar`, `abas_agrupar` | "fecha as abas duplicadas", "fecha todas as abas do YouTube", "reabre a última aba", "fixa essa aba" |
| `musica_controle`, `musica_tocando` | "próxima música no Spotify", "o que está tocando?" (age no Spotify Web ou YouTube Music, mesmo em outra aba) |
| `historico_buscar`, `favoritos_buscar` + `resultado_abrir` | "procura no histórico receita de pão" e depois "abre o segundo" |
| `favorito_salvar` | "salva essa página nos favoritos" |
| `pagina_navegar`, `pagina_rolar`, `pagina_resumir` | "volta", "rola pra baixo", "resume essa página" |
| `navegador_diagnostico` | "faz o diagnóstico do navegador" ou `/navegador diagnostico` |
| `navegador_tarefa` | qualquer site sem atalho (modo genérico) |

**Abas em lote e fechamento:** fechar mais de 3 abas de uma vez pede um "sim". Abas **fixadas nunca são fechadas** por comando em lote. O fechamento é recuperável: "reabre a última aba" usa o histórico de abas fechadas do navegador.

**Som por aba:** `aba_silenciar` mexe só na aba, não no volume do Windows. Sem dizer qual aba, silencia tudo que estiver tocando. O play/pause global por tecla de mídia ("pausa") continua existindo; use `musica_controle` quando quiser agir num player específico.

**Histórico e favoritos:** a leitura é local (a extensão consulta o navegador) e nada é enviado a ninguém. Depois de uma busca, "abre o segundo" vale para aquela lista por 2 minutos; passado esse tempo, volta a valer a lista de resultados de YouTube ou Google.

**Diagnóstico:** quando um atalho não achar nada, `/navegador diagnostico` testa os seletores da aba aberta (YouTube, Google, Gmail, Spotify, YouTube Music) e diz o que parou de funcionar.

**Lista de resultados em memória:** depois de pesquisar no YouTube ou no Google, o Jarvis guarda os resultados por 15 minutos. Assim "abre o primeiro" seguido de "abre o segundo em outra aba" funciona mesmo que você já tenha saído da página de resultados. Uma nova pesquisa descarta a lista antiga.

**Aba reaproveitada:** uma pesquisa nova usa a aba do YouTube (ou do Google) que já estiver aberta, em vez de criar outra. Só abre aba nova se não houver nenhuma do site ou se você pedir "em outra aba". Abrir o N-ésimo resultado usa a mesma aba por padrão no YouTube e uma aba nova no Google, e "ao lado", "em paralelo" ou "em segundo plano" também são entendidos.

**Fala natural e rapidez:** os comandos mais comuns (pesquisar e abrir por posição, controles do player, e-mails, abas, histórico, favoritos) são resolvidos por regras locais, sem passar pelo Gemini, e toleram cortesia e variações ("por favor, pode abrir o segundo vídeo pra mim?", "bota o último", "pesquisa lofi no yt"). O que não casa vai ao Gemini, que conhece todas as ações. Veja [FALA-E-DESEMPENHO.md](FALA-E-DESEMPENHO.md).

**Sem a extensão:** as ações que só abrem endereços (pesquisas, Maps, rastreio, GitHub) caem no navegador padrão do Windows. As que precisam ler ou clicar na página avisam que a extensão não está conectada.

## 🤖 Modo genérico (`navegador_tarefa`)

Para sites sem atalho, o Jarvis repete até 6 vezes:

1. tira um **snapshot** da aba: lista numerada de links, botões e campos visíveis;
2. manda a tarefa + a lista ao Gemini, que responde **um** passo em JSON (`clicar`, `digitar`, `rolar`, `abrir_url`, `voltar`, `concluir` ou `falhar`);
3. executa o passo e repete.

A IA só escolhe números da lista; não executa nada fora desses passos.

## 🔒 Segurança

- O servidor só escuta em `127.0.0.1`, exige o token em todas as chamadas, valida o `Host` (contra DNS rebinding) e recusa qualquer `Origin` que não seja de extensão. Páginas comuns não conseguem usá-lo.
- **Passos sensíveis pedem "sim"** no modo genérico: clicar em algo com rótulo como enviar, comprar, pagar, excluir, confirmar, publicar, assinar, sair. Sem confirmação, o passo não acontece (ver `SENSIVEL` em `navegador/generico.py`).
- **Campos de senha nunca são preenchidos**, e o Gemini só vê rótulos dos elementos, nunca valores digitados.
- O Gmail é **somente leitura**: não envia, não apaga, não arquiva.
- A extensão só abre endereços `http(s)`.
- **Permissões da extensão** (`manifest.json`): `tabs`, `scripting`, `alarms`, `tabGroups`, `sessions`, `history`, `bookmarks` e acesso a todos os sites (para ler e clicar nas páginas). Não há permissão de cookies, downloads nem área de transferência de propósito.
- Os novos atalhos de Spotify Web e YouTube Music (`_PLAYERS` em `navegador/atalhos.py`) usam seletores que **não foram testados nos sites reais**: se algum falhar, use o diagnóstico.
- **Pelo Telegram:** o bot usa as mesmas ações, mas só sobe a ponte se nenhum Jarvis estiver aberto (a porta é uma só), e recusa os passos sensíveis do modo genérico, porque não consegue pedir a confirmação. Veja `TELEGRAM.md`.

## 🛠️ Como estender

### Novo atalho para um site

1. **Funções** em `navegador/atalhos.py`, usando `enviar(...)`. Exemplo de busca de elementos:
   ```python
   itens = _aguardar_itens(seletor='a.titulo', excluir='.anuncio', filtro_href=r'/produto/', limite=20)
   ```
2. **Ação** em `acoes_navegador.py` com `@acao(nome, descrição, parâmetros)` e `@_seguro` (este converte `ErroNavegador` na frase falada).
3. **Regra** no prompt de `cerebro.py` (`REGRA_NAVEGADOR`), se a IA precisar de uma dica de quando usar. Ações registradas em `acoes_navegador.py` entram sozinhas no grupo `navegador`; se a frase do novo site usar palavras que ainda não estão em `R_FALA_DE_NAVEGADOR` (em `jarvis.py`), acrescente-as ali.
4. **Frase rápida (opcional):** se o comando for muito usado, trate-o em `_atalho_navegador` (`jarvis.py`), para ele não depender do Gemini.
5. **Teste** em `tests/test_navegador.py`, com a `PonteFalsa` (não precisa de navegador).

Quando um site mudar o HTML e um atalho parar de achar elementos, só o seletor em `atalhos.py` precisa mudar (por exemplo `_YT_SELETOR`, `_GOOGLE_SELETOR`, `_GMAIL_LINHA`).

### Novo comando para a extensão

Adicione uma entrada em `COMANDOS` no `extensao/background.js` (e, se rodar na página, uma operação em `jarvisPagina` de `extensao/paginas.js`; ela é **autossuficiente**, pois é serializada para dentro da página). Depois, recarregue a extensão.

### Operações disponíveis na extensão

| Comando | Parâmetros principais |
|---|---|
| `abas_listar` | `todas_janelas`; cada aba traz `audivel`, `mudo`, `fixada`, `janela` |
| `abas_buscar` | `texto`, `duplicadas`, `audivel` (consulta sem efeito; o Python decide e confirma) |
| `aba_trocar`, `aba_duplicar` | `id`, `indice` (1 = primeira) ou `texto` |
| `aba_fechar` | `ids` (lote) ou a aba alvo |
| `aba_reabrir`, `aba_fixar`, `aba_mudo`, `abas_agrupar` | `fixar`, `mudo`, `ids` + `titulo` + `cor` |
| `historico_buscar` | `texto`, `dias`, `limite` |
| `favoritos_buscar`, `favorito_criar` | `texto`, `limite` / aba alvo |
| `ping` | devolve a versão da extensão |
| `abrir_url` | `url`, `nova_aba`, `segundo_plano` |
| `navegar` | `acao`: `voltar`, `avancar`, `recarregar` |
| `snapshot` | `limite` |
| `clicar`, `digitar` | `n` (do último snapshot), `texto`, `enviar`, `nova_aba` |
| `consultar`, `clicar_seletor` | `seletor`, `excluir`, `filtro_href`, `rotulo_seletor`, `limite`, `indice` |
| `rolar`, `ler_texto` | `direcao`, `quantidade`, `limite` |
| `video` | `acao`: `alternar`, `play`, `pausa`, `velocidade`, `pular`, `mudo`, `volume` |

## 🧪 Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

`tests/test_navegador.py` cobre a ponte HTTP real (com uma extensão simulada), os atalhos, o modo genérico e as frases locais, tudo sem abrir navegador. As variações de fala natural ficam em `tests/test_naturalidade.py`.

## 🩹 Solução de problemas

| Sintoma | O que fazer |
|---|---|
| "A extensão do navegador não está conectada" | Jarvis aberto? Extensão carregada em `chrome://extensions`? Selo **ON** no ícone? Abra o Jarvis antes e recarregue a extensão. |
| Selo `!` no ícone | Token desatualizado: recarregue a extensão. |
| "a ponte ... não está ativa" | A porta está em uso (outro Jarvis aberto?). Use `JARVIS_NAVEGADOR_PORTA`. |
| "Peça primeiro para pesquisar" | O atalho precisa de uma lista: peça a pesquisa antes de pedir "abre o primeiro". |
| Um atalho deixou de achar vídeos, resultados ou e-mails | O site mudou o HTML: ajuste o seletor em `navegador/atalhos.py`. |
| Não funciona em `chrome://`, Chrome Web Store ou PDF | O Chrome não permite extensões nessas páginas. |
| Comando novo "não faz nada" depois de atualizar o projeto | A extensão não foi recarregada. Em `chrome://extensions`, recarregue-a (versões novas pedem permissões novas, e o navegador pode pedir para você aprovar). |
| Um atalho de site parou de achar elementos | `/navegador diagnostico` na aba do site mostra qual seletor falhou. |
