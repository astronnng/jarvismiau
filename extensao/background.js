/*
 * BACKGROUND - a ponte entre o Jarvis e o navegador
 * --------------------------------------------------
 * Como funciona: o Jarvis (Python) abre um servidor HTTP em 127.0.0.1. Este service
 * worker fica perguntando "tem comando pra mim?" (long polling em /proximo), executa
 * e devolve o resultado em /resultado. Sem WebSocket e sem dependencias extras.
 *
 * Seguranca: todas as chamadas levam o token de config.local.js (gerado pelo Jarvis).
 * O servidor so atende 127.0.0.1 e recusa chamadas sem o token.
 *
 * Os comandos disponiveis estao no objeto COMANDOS, mais abaixo.
 */
"use strict";

importScripts("paginas.js");
try {
  importScripts("config.local.js"); // gerado pelo Jarvis: { porta, token }
} catch (e) {
  // ainda nao existe: abra o Jarvis uma vez e recarregue a extensao.
}

const CFG = Object.assign({ porta: 8765, token: "" }, self.JARVIS_CONFIG || {});
const BASE = "http://127.0.0.1:" + CFG.porta;
const CABECALHOS = { "X-Jarvis-Token": CFG.token };

const dormir = (ms) => new Promise((ok) => setTimeout(ok, ms));
let lacoAtivo = false;

// ---------------------------------------------------------------------------
// Laco principal
// ---------------------------------------------------------------------------
function marcar(conectado, texto) {
  chrome.action.setBadgeText({ text: conectado ? "ON" : texto || "" });
  chrome.action.setBadgeBackgroundColor({ color: conectado ? "#0a7d94" : "#8a2a2a" });
}

async function laco() {
  if (lacoAtivo) return;
  lacoAtivo = true;
  try {
    for (;;) {
      try {
        const r = await fetch(BASE + "/proximo", { headers: CABECALHOS });
        if (r.status === 200) {
          marcar(true);
          await tratar(await r.json());
        } else if (r.status === 204) {
          marcar(true);
        } else {
          marcar(false, "!"); // token errado: recarregue a extensao depois de abrir o Jarvis
          await dormir(10000);
        }
      } catch (e) {
        marcar(false); // Jarvis fechado
        await dormir(3000);
      }
    }
  } finally {
    lacoAtivo = false;
  }
}

async function tratar(comando) {
  let corpo;
  try {
    const fn = COMANDOS[comando.cmd];
    if (!fn) throw new Error("comando desconhecido: " + comando.cmd);
    corpo = { id: comando.id, ok: true, dados: await fn(comando.args || {}) };
  } catch (e) {
    corpo = { id: comando.id, ok: false, erro: String((e && e.message) || e) };
  }
  try {
    await fetch(BASE + "/resultado", {
      method: "POST",
      headers: Object.assign({ "Content-Type": "application/json" }, CABECALHOS),
      body: JSON.stringify(corpo),
    });
  } catch (e) {
    // Jarvis fechou no meio do comando: nada a fazer.
  }
}

// O service worker dorme; estes eventos o acordam e religam o laco.
chrome.alarms.create("jarvis-vivo", { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(laco);
chrome.runtime.onStartup.addListener(laco);
chrome.runtime.onInstalled.addListener(laco);
laco();

// ---------------------------------------------------------------------------
// Auxiliares de abas
// ---------------------------------------------------------------------------
async function abaAlvo(args) {
  if (args.aba != null) return chrome.tabs.get(args.aba);
  const [aba] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (!aba) throw new Error("nenhuma aba ativa");
  return aba;
}

const resumo = (t) => ({
  id: t.id,
  indice: t.index,
  titulo: t.title,
  url: t.url,
  ativa: t.active,
  audivel: !!t.audible, // tocando som agora
  mudo: !!(t.mutedInfo && t.mutedInfo.muted),
  fixada: !!t.pinned,
  janela: t.windowId,
});

// Abas repetidas (mesma URL): devolve as que sobram, mantendo a ativa (ou a primeira) de cada grupo.
function sobrasDuplicadas(abas) {
  const grupos = new Map();
  for (const aba of abas) {
    if (!aba.url) continue;
    if (!grupos.has(aba.url)) grupos.set(aba.url, []);
    grupos.get(aba.url).push(aba);
  }
  const sobras = [];
  for (const grupo of grupos.values()) {
    if (grupo.length < 2) continue;
    const fica = grupo.find((t) => t.active) || grupo[0];
    sobras.push(...grupo.filter((t) => t.id !== fica.id));
  }
  return sobras;
}

async function esperarCarregar(tabId, ms) {
  await dormir(300); // evita ler o "complete" da pagina anterior
  const fim = Date.now() + (ms || 10000);
  while (Date.now() < fim) {
    const aba = await chrome.tabs.get(tabId);
    if (aba.status === "complete") return aba;
    await dormir(200);
  }
  return chrome.tabs.get(tabId);
}

async function naPagina(args, op) {
  const aba = await abaAlvo(args);
  const [res] = await chrome.scripting.executeScript({
    target: { tabId: aba.id },
    func: jarvisPagina,
    args: [op, args],
  });
  const r = res && res.result;
  if (r && r.erro) throw new Error(r.erro);
  return r;
}

// clicar/clicar_seletor com nova_aba: a pagina devolve a URL e a aba e criada aqui.
async function clicarComAbas(args, op) {
  const r = await naPagina(args, op);
  if (r && r.abrir_em) {
    await COMANDOS.abrir_url({ url: r.abrir_em, nova_aba: true, segundo_plano: !!args.segundo_plano });
    r.aberto_em_nova_aba = true;
  }
  return r;
}

// ---------------------------------------------------------------------------
// COMANDOS (o que o Python pode pedir)
// ---------------------------------------------------------------------------
const COMANDOS = {
  async ping() {
    return { versao: chrome.runtime.getManifest().version };
  },

  // --- abas ---
  async abas_listar({ todas_janelas = false } = {}) {
    const abas = await chrome.tabs.query(todas_janelas ? {} : { lastFocusedWindow: true });
    return abas.map(resumo);
  },

  // Consulta SEM efeito colateral, para o Jarvis decidir/confirmar antes de agir em lote.
  // Filtros: texto (titulo/URL), duplicadas, audivel (tocando som). Sempre em todas as janelas.
  async abas_buscar({ texto, duplicadas, audivel } = {}) {
    let abas = await chrome.tabs.query({});
    if (texto) {
      const busca = String(texto).toLowerCase();
      abas = abas.filter((t) => ((t.title || "") + " " + (t.url || "")).toLowerCase().includes(busca));
    }
    if (audivel) abas = abas.filter((t) => t.audible);
    if (duplicadas) abas = sobrasDuplicadas(await chrome.tabs.query({}));
    return abas.map(resumo);
  },

  // Fecha uma ou varias abas (ids), ou a aba alvo. Recuperavel com aba_reabrir.
  async aba_fechar(args) {
    if (Array.isArray(args.ids)) {
      await chrome.tabs.remove(args.ids);
      return { fechadas: args.ids.length };
    }
    const aba = await abaAlvo(args);
    await chrome.tabs.remove(aba.id);
    return { fechada: resumo(aba) };
  },

  // Reabre a aba ou janela fechada mais recentemente.
  async aba_reabrir() {
    const sessao = await chrome.sessions.restore();
    const aba = sessao && sessao.tab;
    return aba ? resumo(aba) : { restaurada: true };
  },

  async aba_fixar({ fixar = true, ...args } = {}) {
    const aba = await abaAlvo(args);
    return resumo(await chrome.tabs.update(aba.id, { pinned: !!fixar }));
  },

  // mudo: true silencia, false volta o som. Sem aba, age na aba alvo (ativa).
  async aba_mudo({ mudo = true, ...args } = {}) {
    const aba = await abaAlvo(args);
    return resumo(await chrome.tabs.update(aba.id, { muted: !!mudo }));
  },

  // Junta abas (ids) num grupo nomeado. cor: grey|blue|red|yellow|green|pink|purple|cyan|orange
  async abas_agrupar({ ids, titulo, cor = "blue" }) {
    if (!Array.isArray(ids) || !ids.length) throw new Error("nenhuma aba para agrupar");
    const grupo = await chrome.tabs.group({ tabIds: ids });
    await chrome.tabGroups.update(grupo, { title: String(titulo || "Jarvis"), color: cor });
    return { grupo, abas: ids.length };
  },

  // --- historico e favoritos (leitura local, nada sai do computador) ---
  async historico_buscar({ texto = "", limite = 10, dias = 30 } = {}) {
    const itens = await chrome.history.search({
      text: String(texto),
      maxResults: Math.min(Number(limite) || 10, 50),
      startTime: Date.now() - Number(dias) * 86400000, // o padrao da API e so 24h
    });
    return itens.map((i) => ({
      titulo: i.title || i.url,
      url: i.url,
      visitas: i.visitCount,
      ultima_visita: new Date(i.lastVisitTime).toISOString(),
    }));
  },

  async favoritos_buscar({ texto = "", limite = 10 } = {}) {
    const itens = await chrome.bookmarks.search(String(texto));
    return itens
      .filter((i) => i.url)
      .slice(0, Math.min(Number(limite) || 10, 50))
      .map((i) => ({ titulo: i.title || i.url, url: i.url }));
  },

  // Salva a aba alvo nos favoritos.
  async favorito_criar(args) {
    const aba = await abaAlvo(args);
    const novo = await chrome.bookmarks.create({ title: aba.title, url: aba.url });
    return { titulo: novo.title, url: novo.url };
  },

  // alvo: id numerico, indice (1 = primeira aba) ou texto presente no titulo/URL.
  async aba_trocar({ id, indice, texto }) {
    let aba;
    if (id != null) {
      aba = await chrome.tabs.get(id);
    } else if (indice != null) {
      const abas = await chrome.tabs.query({ lastFocusedWindow: true });
      aba = abas[Number(indice) - 1];
    } else if (texto) {
      const busca = String(texto).toLowerCase();
      const todas = await chrome.tabs.query({});
      aba = todas.find((t) => ((t.title || "") + " " + (t.url || "")).toLowerCase().includes(busca));
    }
    if (!aba) throw new Error("nao encontrei essa aba");
    await chrome.tabs.update(aba.id, { active: true });
    await chrome.windows.update(aba.windowId, { focused: true });
    return resumo(aba);
  },

  async aba_duplicar(args) {
    const aba = await abaAlvo(args);
    return resumo(await chrome.tabs.duplicate(aba.id));
  },

  async abrir_url({ url, nova_aba = true, segundo_plano = false, aba }) {
    if (!/^https?:\/\//i.test(String(url || ""))) throw new Error("so abro enderecos http(s)");
    let alvo;
    if (nova_aba) {
      alvo = await chrome.tabs.create({ url, active: !segundo_plano });
    } else {
      alvo = await chrome.tabs.update((await abaAlvo({ aba })).id, { url, active: true });
      await chrome.windows.update(alvo.windowId, { focused: true });
    }
    return resumo(await esperarCarregar(alvo.id));
  },

  async navegar(args) {
    const aba = await abaAlvo(args);
    if (args.acao === "voltar") await chrome.tabs.goBack(aba.id);
    else if (args.acao === "avancar") await chrome.tabs.goForward(aba.id);
    else if (args.acao === "recarregar") await chrome.tabs.reload(aba.id);
    else throw new Error("acao de navegacao desconhecida: " + args.acao);
    return resumo(await esperarCarregar(aba.id));
  },

  // --- pagina (executadas por jarvisPagina em paginas.js) ---
  async snapshot(args) { return naPagina(args, "snapshot"); },
  async clicar(args) { return clicarComAbas(args, "clicar"); },
  async digitar(args) { return naPagina(args, "digitar"); },
  async rolar(args) { return naPagina(args, "rolar"); },
  async ler_texto(args) { return naPagina(args, "ler_texto"); },
  async consultar(args) { return naPagina(args, "consultar"); },
  async clicar_seletor(args) { return clicarComAbas(args, "clicar_seletor"); },
  async video(args) { return naPagina(args, "video"); },
};
