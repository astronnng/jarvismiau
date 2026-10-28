# 🎧 Modo de voz

Como o Jarvis escuta: palavra de ativação, modos de escuta, confirmação por voz e ajustes de sensibilidade.

## 🎧 Palavra de ativação "Jarvis"

O **`Jarvis.bat`** fica com o microfone aberto o tempo todo, mas **só atende quando você diz "Jarvis"**.
A janela do terminal precisa estar aberta.

```
(modo palavra de ativacao: comece a fala dizendo "jarvis")

Voce: você viu o jogo ontem
   (sem a palavra de ativacao, ignorado)

Voce: Jarvis, que horas são
Jarvis: Sao 16 horas e 0 minutos, senhor.
```

### Como falar com ele

| Você diz | O que acontece |
|---|---|
| "Jarvis, que horas são" | responde |
| "Ei Jarvis, abrir youtube" | responde (aceita "ei", "oi", "ok" antes) |
| "Jarvis" (sozinho) | responde "Pode falar, senhor" e **aceita o comando seguinte** sem repetir a palavra |
| "que horas são" (sem "Jarvis") | ignora — a menos que esteja nos **6 segundos seguintes** a uma resposta dele |
| "sair" (sozinho) | encerra, mesmo sem a palavra |

**Janela de acompanhamento:** depois que ele responde, você tem **6 segundos** para continuar
a conversa sem repetir "Jarvis". Exemplo:

```
Voce: Jarvis, clima em Bariri
Jarvis: Em Bariri esta 23 graus e ensolarado.
Voce: abrir youtube
   (dentro da janela de acompanhamento: aceito)
Jarvis: Abrindo youtube, senhor.
```

### Ele entende "Jarvis" mesmo quando o reconhecedor erra

O Google costuma devolver "Jávis", "Jarves" ou "Jarbis". Estas variantes são aceitas
automaticamente: `jarvis, javis, jarves, jarbis, jarvi, jarve, charvis`.
Para adicionar outras, edite `VARIANTES_ATIVACAO` no topo do `jarvis.py`.

### Os três modos de escuta

| Atalho | Como funciona | Quando usar |
|---|---|---|
| **`Jarvis.bat`** | Ouve sempre, atende só com "Jarvis" | Padrão — tem gente/TV por perto |
| **`Jarvis.bat continuo`** | Atende qualquer fala | Você sozinho no ambiente |
| **`Jarvis.bat enter`** | Aperta ENTER, fala, ele responde | Microfone ruim ou ambiente barulhento |

### ✅ Confirmar por voz ("sim" / "não")

Quando ele não sabe algo, pergunta: *"Pesquisar no Google? Diga sim ou nao."* — e agora ele
**realmente escuta a resposta**:

```
Voce: Jarvis, quem descobriu o brasil
Jarvis: Ainda nao fui programado para isso, senhor. Pesquisar no Google? Diga sim ou nao.
Voce: sim
Jarvis: Pesquisando quem descobriu o brasil, senhor.
```

O que ele aceita como **sim**: sim, s, claro, pode, isso, quero, manda, yes.
Como **não**: não, n, no, deixa, deixa pra lá, não precisa, cancelar.

Detalhes testados: se você ficar em silêncio ele tenta de novo (até 3 vezes); se responder algo
confuso, ele repete "Sim ou não, senhor?"; e o "sim" **não precisa** da palavra "Jarvis" antes.

### O que foi feito para isso funcionar bem

| Risco | Solução |
|---|---|
| Ele ouvir a própria voz e responder a si mesmo | O microfone é **purgado** antes de cada escuta; ele não escuta enquanto fala |
| Terminal travado para sempre se der erro de rede | Erro isolado: espera 2 s e volta. Erro repetido: **cai para o modo digitado**, avisando |
| Microfone inexistente ou bloqueado pelo Windows | Cai para o modo digitado em vez de ficar em silêncio |
| Responder a conversa de outra pessoa | Só atende com a palavra de ativação (e a janela de 6 s após uma resposta) |
| Calibrar o ruído a cada comando | Calibra **uma vez** ao iniciar |

### Ajustar a sensibilidade

No topo do `jarvis.py`:

```python
SEGUNDOS_SILENCIO = 0.55    # silêncio que marca o fim da sua fala
LIMITE_FRASE = 8            # tempo máximo de uma fala
JANELA_SEGUIMENTO = 6       # segundos após responder em que aceita comandos sem "Jarvis"
```

- **Corta você no meio da frase:** aumente `SEGUNDOS_SILENCIO` para `0.8`.
- **Demora após você calar:** diminua para `0.4`.
- **Dispara com ventilador/TV:** em `_preparar_microfone()` aumente `energy_threshold` de `300` para `500`.
- **Não escuta voz baixa:** diminua `energy_threshold` para `180`.
- **Janela de acompanhamento longa demais:** reduza `JANELA_SEGUIMENTO` para `3` ou `0`.

### Aviso de privacidade

Microfone ligado enquanto o terminal estiver aberto (o Windows mostra o ícone na barra).
O áudio **não é gravado**: cada fala vira texto pelo Google e é descartada. O consumo de CPU é
baixo, porque ele só transcreve quando detecta fala. Para silêncio absoluto, feche a janela.
