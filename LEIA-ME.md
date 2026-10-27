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

Na primeira vez o Windows pode pedir permissão para usar o microfone: clique em **Permitir**.

> Dica: clique com o botão direito em `Jarvis.bat` → *Enviar para* → *Área de trabalho (criar atalho)*.
> Depois clique com o botão direito no atalho → *Propriedades* → *Avançado* → marque **Executar como administrador** (necessário só se você usar o comando de bloquear o PC).

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

**Dica de segurança:** este Jarvis só executa ações de uma lista fixa. Nada de apagar arquivos, mexer em dinheiro ou enviar mensagens sem você confirmar. Mantenha assim.

---

## Próximo passo: o celular

O jeito mais simples de ter o mesmo Jarvis no celular, sem reescrever nada, é:

1. Criar um **bot no Telegram** (5 minutos, grátis, com o `@BotFather`).
2. Rodar um pequeno script no PC que escuta as mensagens do bot e responde usando a mesma lógica do `jarvis.py`.
3. Você usa o Telegram no celular como se fosse o Jarvis — inclusive fora de casa, desde que o PC esteja ligado.

Quando quiser, peço para eu montar essa parte: o arquivo do bot já vem pronto para usar a mesma lista de comandos.
