/*
 * PAGINAS - o que roda DENTRO da pagina
 * -------------------------------------
 * `jarvisPagina(op, a)` e injetada pelo background.js com chrome.scripting.
 * Por ser serializada para dentro da pagina, ela precisa ser AUTOSSUFICIENTE:
 * nada aqui pode usar variaveis ou funcoes de fora dela.
 *
 * Operacoes (op):
 *   snapshot        lista numerada dos elementos clicaveis/digitaveis visiveis
 *   clicar          clica no elemento n do ultimo snapshot
 *   digitar         escreve no campo n (nunca em campos de senha)
 *   rolar           rola a pagina
 *   ler_texto       texto principal da pagina
 *   consultar       lista elementos por seletor CSS (com filtros)
 *   clicar_seletor  clica no N-esimo elemento de uma consulta
 *   video           controla o <video> principal da pagina
 *
 * Retorno: um objeto simples, ou { erro: "mensagem" } em caso de falha.
 * Nenhuma regra de site mora aqui: seletores e filtros vem do Python
 * (navegador/atalhos.py), onde e facil de manter.
 */
async function jarvisPagina(op, a) {
  "use strict";
  a = a || {};
  try {
    // Mapa n -> elemento do ultimo snapshot (persiste entre chamadas na mesma pagina).
    const mapa = (window.__jarvisMapa = window.__jarvisMapa || new Map());

    const limpar = (t, max) => String(t || "").replace(/\s+/g, " ").trim().slice(0, max || 120);

    const visivel = (el) => {
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return false;
      const s = getComputedStyle(el);
      return s.visibility !== "hidden" && s.display !== "none" && s.opacity !== "0";
    };

    const ehSenha = (el) => el.tagName === "INPUT" && String(el.type).toLowerCase() === "password";

    // Nome legivel do elemento. Nunca expoe o valor de campos de senha.
    const rotuloDe = (el) => {
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT") {
        const tipo = String(el.type || "").toLowerCase();
        const botao = ["submit", "button", "reset"].includes(tipo);
        return limpar(
          el.getAttribute("aria-label") || el.placeholder || el.title || el.name ||
          (botao ? el.value : "") || ""
        );
      }
      const img = el.querySelector ? el.querySelector("img[alt]") : null;
      return limpar(
        el.getAttribute("aria-label") || el.innerText || el.title || el.alt || (img && img.alt) || ""
      );
    };

    const tipoDe = (el) => {
      const tag = el.tagName;
      if (tag === "A") return "link";
      if (tag === "BUTTON" || el.getAttribute("role") === "button") return "botao";
      if (tag === "TEXTAREA" || el.isContentEditable) return "campo";
      if (tag === "SELECT") return "lista";
      if (tag === "INPUT") {
        const t = String(el.type || "text").toLowerCase();
        if (["submit", "button", "reset", "image"].includes(t)) return "botao";
        if (["checkbox", "radio"].includes(t)) return t;
        return ehSenha(el) ? "senha" : "campo";
      }
      return el.getAttribute("role") || "elemento";
    };

    const regiaoDe = (el) => {
      const r = el.closest(
        "nav,header,footer,aside,main,dialog,[role=navigation],[role=search],[role=main],[role=banner],[role=dialog]"
      );
      return r ? (r.getAttribute("role") || r.tagName).toLowerCase() : "";
    };

    const hrefDe = (el) => {
      const link = el.closest ? el.closest("a[href]") : null;
      return link && typeof link.href === "string" ? link.href : "";
    };

    // Coleta por seletor com os mesmos filtros para consultar e clicar_seletor.
    const coletar = (p) => {
      const achados = [];
      const limite = p.limite || 20;
      const filtro = p.filtro_href ? new RegExp(p.filtro_href) : null;
      for (const el of document.querySelectorAll(p.seletor)) {
        if (p.excluir && el.closest(p.excluir)) continue;
        if (!visivel(el)) continue;
        const href = hrefDe(el);
        if (filtro && !filtro.test(href)) continue;
        const origem = p.rotulo_seletor ? el.querySelector(p.rotulo_seletor) : el;
        const texto = origem
          ? limpar(origem.innerText || origem.getAttribute("aria-label") || origem.textContent, p.max_texto || 200)
          : "";
        if (p.exigir_texto !== false && !texto) continue;
        achados.push({ el, indice: achados.length, texto, href, classes: String(el.className || "") });
        if (achados.length >= limite) break;
      }
      return achados;
    };

    const alvoPorN = (n) => {
      const el = mapa.get(Number(n));
      if (!el || !el.isConnected) {
        throw new Error("o elemento " + n + " nao existe mais; peca um novo snapshot");
      }
      return el;
    };

    // Clica; com nova_aba, devolve a URL para o background abrir (a pagina nao cria abas).
    const clicarEl = (el, novaAba) => {
      const link = el.closest("a[href]");
      el.scrollIntoView({ block: "center", inline: "center" });
      if (novaAba && link && /^https?:/i.test(link.href)) {
        return { abrir_em: link.href, rotulo: rotuloDe(el) };
      }
      el.click();
      return { clicado: true, rotulo: rotuloDe(el) };
    };

    // ------------------------------------------------------------------
    if (op === "snapshot") {
      const SEL =
        'a[href],button,input:not([type=hidden]),textarea,select,summary,' +
        '[role=button],[role=link],[role=tab],[role=menuitem],[role=checkbox],[role=option],' +
        '[contenteditable=""],[contenteditable="true"],[onclick]';
      const altura = window.innerHeight;
      const candidatos = [];
      let ordem = 0;
      for (const el of document.querySelectorAll(SEL)) {
        ordem++;
        if (!visivel(el)) continue;
        const tipo = tipoDe(el);
        const rotulo = rotuloDe(el);
        if (!rotulo && (tipo === "link" || tipo === "botao")) continue;
        const r = el.getBoundingClientRect();
        const dist = r.bottom < 0 ? -r.bottom : r.top > altura ? r.top - altura : 0;
        candidatos.push({ el, tipo, rotulo, dist, ordem, naTela: dist === 0 });
      }
      // Prioriza o que esta na tela (ou perto dela) e volta para a ordem do documento.
      candidatos.sort((x, y) => x.dist - y.dist || x.ordem - y.ordem);
      const limite = a.limite || 80;
      const escolhidos = candidatos.slice(0, limite).sort((x, y) => x.ordem - y.ordem);

      mapa.clear();
      const itens = [];
      let anterior = "";
      for (const c of escolhidos) {
        const href = c.tipo === "link" ? hrefDe(c.el) : "";
        const chave = c.tipo + "|" + c.rotulo + "|" + href;
        if (chave === anterior) continue;
        anterior = chave;
        const n = itens.length + 1;
        mapa.set(n, c.el);
        const item = { n, tipo: c.tipo, rotulo: c.rotulo, regiao: regiaoDe(c.el), na_tela: c.naTela };
        if (href) item.href = href;
        itens.push(item);
      }
      return { titulo: document.title, url: location.href, itens, total: candidatos.length };
    }

    if (op === "clicar") {
      return clicarEl(alvoPorN(a.n), !!a.nova_aba);
    }

    if (op === "digitar") {
      const el = alvoPorN(a.n);
      if (ehSenha(el)) throw new Error("campos de senha nao sao preenchidos pelo Jarvis");
      const texto = String(a.texto == null ? "" : a.texto);
      el.scrollIntoView({ block: "center" });
      el.focus();
      if (el.isContentEditable) {
        document.execCommand("selectAll");
        document.execCommand("insertText", false, texto);
      } else {
        const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        // Setter nativo: frameworks (React etc.) ignoram atribuicao direta a .value.
        Object.getOwnPropertyDescriptor(proto, "value").set.call(el, texto);
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
      if (a.enviar) {
        if (el.form && typeof el.form.requestSubmit === "function") {
          el.form.requestSubmit();
        } else {
          for (const tipo of ["keydown", "keypress", "keyup"]) {
            el.dispatchEvent(new KeyboardEvent(tipo, {
              key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true,
            }));
          }
        }
      }
      return { digitado: true, rotulo: rotuloDe(el) };
    }

    if (op === "rolar") {
      const passo = Math.round(window.innerHeight * 0.85 * (a.quantidade || 1));
      const dir = a.direcao || "baixo";
      if (dir === "topo") window.scrollTo({ top: 0, behavior: "smooth" });
      else if (dir === "fim") window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
      else window.scrollBy({ top: dir === "cima" ? -passo : passo, behavior: "smooth" });
      return { rolado: dir };
    }

    if (op === "ler_texto") {
      const raiz = document.querySelector("main,article,[role=main]") || document.body;
      return { titulo: document.title, url: location.href, texto: limpar(raiz.innerText, a.limite || 4000) };
    }

    if (op === "consultar") {
      return {
        url: location.href,
        itens: coletar(a).map(({ indice, texto, href, classes }) => ({ indice, texto, href, classes })),
      };
    }

    if (op === "clicar_seletor") {
      const achados = coletar(Object.assign({}, a, { limite: (a.indice || 0) + 1 }));
      const alvo = achados[a.indice || 0];
      if (!alvo) throw new Error("nao encontrei o elemento pedido nesta pagina");
      return clicarEl(alvo.el, !!a.nova_aba);
    }

    if (op === "video") {
      const videos = [...document.querySelectorAll("video")].filter((v) => v.readyState > 0 || !v.paused);
      if (!videos.length) throw new Error("nao ha video nesta pagina");
      const area = (v) => { const r = v.getBoundingClientRect(); return r.width * r.height; };
      const v = videos.sort((x, y) => area(y) - area(x))[0];
      const valor = Number(a.valor);
      switch (a.acao) {
        case "alternar": if (v.paused) await v.play(); else v.pause(); break;
        case "play": await v.play(); break;
        case "pausa": v.pause(); break;
        case "velocidade": v.playbackRate = Math.min(4, Math.max(0.25, valor)); break;
        case "pular": v.currentTime = Math.max(0, v.currentTime + valor); break;
        case "mudo": v.muted = true; break;
        case "desmudo": v.muted = false; break;
        case "volume": v.volume = Math.min(1, Math.max(0, valor / 100)); break;
        default: throw new Error("controle de video desconhecido: " + a.acao);
      }
      return {
        pausado: v.paused, velocidade: v.playbackRate, mudo: v.muted,
        tempo: Math.round(v.currentTime), duracao: Math.round(v.duration || 0),
      };
    }

    throw new Error("operacao de pagina desconhecida: " + op);
  } catch (e) {
    return { erro: String((e && e.message) || e) };
  }
}
