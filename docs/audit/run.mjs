// Banco di prova runtime v2: comandi, pulsanti, strumenti, testo/font, livelli, export.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import { launch, sleep } from './cdp.mjs';

const URL = 'http://127.0.0.1:8765/OverPowerPoint.html';
const report = { when: new Date().toISOString(), phases: {} };
const server = spawn(process.execPath, ['C:/Progetti/OPP/.audit/server.mjs'], { stdio: 'ignore' });
await sleep(600);

const PATCH = `
(() => {
  window.__dl = 0; window.__print = 0; window.__filePick = 0;
  HTMLAnchorElement.prototype.click = function(){ window.__dl++; };
  const origClick = HTMLElement.prototype.click;
  HTMLInputElement.prototype.click = function(){ if(this.type === 'file'){ window.__filePick++; return; } return origClick.call(this); };
  window.print = () => { window.__print++; };
  try { delete navigator.share; } catch {}
  window.__toasts = () => [...document.querySelectorAll('#toastWrap .toast')].map(t => t.textContent.trim());
  window.__clearToasts = () => { const w = document.getElementById('toastWrap'); if (w) w.innerHTML = ''; };
  window.__modalOpen = () => { const m = document.getElementById('modalBg'); return !!m && m.classList.contains('open'); };
  window.__closeModal = () => { const m = document.getElementById('modalBg'); if (m) m.classList.remove('open'); };
  window.__ready = true;
})();
`;

let browser;
const checks = [];
const check = (name, ok, detail = '') => checks.push({ name, ok: !!ok, detail });

try {
  browser = await launch({ url: URL, port: 9333, width: 1440, height: 900 });
  const ev = browser.evaluate;

  const smoke = await ev(`(() => ({ title:document.title, opp:typeof window.OPP, version:window.OPP&&OPP.version,
    slides:OPP.state.slides.length, commands:Object.keys(OPP.COMMANDS).length,
    scrollW:document.documentElement.scrollWidth, innerW:innerWidth }))()`);
  report.phases.smoke = smoke;
  await ev(PATCH);
  check('avvio senza eccezioni', browser.events.exceptions.length === 0, JSON.stringify(browser.events.exceptions.slice(0, 3)));

  // ---------- comandi ----------
  const keys = await ev(`Object.keys(OPP.COMMANDS).sort()`);
  const cmdResults = [];
  for (const key of keys) {
    const before = browser.events.exceptions.length;
    let out;
    try {
      out = await ev(`(async () => {
        __clearToasts();
        const r = { key: ${JSON.stringify(key)}, threw: null, toasts: [], modal: false };
        try {
          await Promise.race([
            Promise.resolve(OPP.runCommand(${JSON.stringify(key)}, {})),
            new Promise(res => setTimeout(res, 450))
          ]);
        } catch (e) { r.threw = String(e && e.message || e); }
        await new Promise(res => setTimeout(res, 60));
        r.toasts = __toasts(); r.modal = __modalOpen();
        r.slides = OPP.state.slides.length;
        r.elements = OPP.state.slides.reduce((n,s)=>n+(s.elements||[]).length,0);
        return r;
      })()`);
    } catch (e) { out = { key, threw: 'fatal: ' + e.message, toasts: [] }; }
    const exc = browser.events.exceptions.slice(before).map(x => x.text);
    cmdResults.push({ ...out, exceptions: exc });
    await ev(`__closeModal()`).catch(() => {});
    await sleep(30);
  }
  const bad = cmdResults.filter(r => r.threw || r.exceptions.length || r.toasts.some(t => /Errore|non funzion/i.test(t)));
  report.phases.commands = { total: cmdResults.length, failing: bad };
  check('tutti i comandi eseguibili', bad.length === 0, bad.map(b => b.key + ':' + (b.threw || b.exceptions[0] || b.toasts.join('|'))).join('; '));

  // ---------- ribbon ----------
  const tabs = await ev(`[...document.querySelectorAll('.tab[data-tab]')].map(t=>t.dataset.tab)`);
  const ribbonResults = [];
  for (const tab of tabs) {
    await ev(`document.querySelector('.tab[data-tab=${JSON.stringify(tab)}]').click()`);
    await sleep(100);
    const count = await ev(`document.querySelectorAll('#ribbon [data-command]').length`);
    for (let i = 0; i < count; i++) {
      const before = browser.events.exceptions.length;
      const info = await ev(`(() => {
        const b = document.querySelectorAll('#ribbon [data-command]')[${i}];
        if (!b) return null;
        __clearToasts(); const cmd = b.dataset.command; b.click(); return { cmd };
      })()`);
      await sleep(50);
      const toasts = await ev(`__toasts()`);
      const exc = browser.events.exceptions.slice(before).map(x => x.text);
      if (info) ribbonResults.push({ tab, ...info, toasts, exceptions: exc });
      await ev(`__closeModal()`).catch(() => {});
    }
  }
  const badBtn = ribbonResults.filter(r => r.exceptions.length);
  report.phases.ribbon = { tabs, clicked: ribbonResults.length, failing: badBtn };
  check('tutti i pulsanti del ribbon senza errori', badBtn.length === 0, badBtn.slice(0, 6).map(b => b.tab + '/' + b.cmd + ':' + b.exceptions[0]).join('; '));

  // ---------- strumenti (tutte le schede) ----------
  const toolResults = [];
  for (const tab of tabs) {
    await ev(`document.querySelector('.tab[data-tab=${JSON.stringify(tab)}]').click()`);
    await sleep(80);
    const n = await ev(`document.querySelectorAll('#ribbon [data-tool]').length`);
    for (let i = 0; i < n; i++) {
      const before = browser.events.exceptions.length;
      const info = await ev(`(() => { const b=document.querySelectorAll('#ribbon [data-tool]')[${i}]; if(!b) return null; b.click(); return { tool:b.dataset.tool, kind:b.dataset.kind||null, active:OPP.state.tool, shapeKind:OPP.state.shapeKind }; })()`);
      await sleep(30);
      const exc = browser.events.exceptions.slice(before).map(x => x.text);
      if (info) toolResults.push({ tab, ...info, ok: info.active === info.tool && !exc.length, exceptions: exc });
    }
  }
  report.phases.tools = { total: toolResults.length, failing: toolResults.filter(t => !t.ok) };
  check('tutti gli strumenti attivabili', toolResults.every(t => t.ok), JSON.stringify(toolResults.filter(t => !t.ok).slice(0, 5)));

  // ---------- testo e font ----------
  const textTest = await ev(`(async () => {
    const s0 = OPP.state.slides[OPP.state.current].elements.length;
    OPP.runCommand('insert.text', {});
    await new Promise(r=>setTimeout(r,80));
    const el = OPP.state.slides[OPP.state.current].elements.slice(-1)[0];
    const selCount = document.querySelectorAll('[data-prop="font"] option').length;
    // cambia font dalla finestra proprietà
    OPP.state.selected=[el.id];
    const props = document.getElementById('propsBody');
    let changed=null;
    const sel = document.querySelector('[data-prop="font"]');
    if (sel) { sel.value='Georgia'; sel.dispatchEvent(new Event('change',{bubbles:true})); changed = el.font; }
    // apri gestore font
    OPP.runCommand('font.manage', {});
    await new Promise(r=>setTimeout(r,120));
    const hasModal = !!document.getElementById('googleFontName');
    document.getElementById('modalBg').classList.remove('open');
    return { before:s0, after:OPP.state.slides[OPP.state.current].elements.length, type:el.type, fontOptions:selCount, fontChanged:changed, fontManagerOpens:hasModal, fontsStored:(OPP.state.fonts||[]).length };
  })()`);
  report.phases.text = textTest;
  check('inserimento testo', textTest.after === textTest.before + 1 && textTest.type === 'text', JSON.stringify(textTest));
  check('selettore font con opzioni', textTest.fontOptions >= 23, String(textTest.fontOptions));
  check('cambio font applicato', textTest.fontChanged === 'Georgia', String(textTest.fontChanged));
  check('gestore font si apre', textTest.fontManagerOpens === true);

  // font da Google (rete) — se offline si segnala come saltato
  const fontOnline = await ev(`(async () => {
    try {
      OPP.runCommand('font.manage', {});
      await new Promise(r=>setTimeout(r,150));
      const inp = document.getElementById('googleFontName');
      if (!inp) return { error: 'modale non aperto' };
      inp.value = 'Roboto';
      document.getElementById('fontGoogleAdd').click();
      await new Promise(r=>setTimeout(r,7000));
      const families = (OPP.state.fonts||[]).map(f=>f.family);
      const registered = [...document.fonts].filter(f=>f.family==='Roboto').length;
      const modal = document.getElementById('modalBg');
      if (modal) modal.classList.remove('open');
      return { families, registered, online: navigator.onLine };
    } catch(e) { return { error: String(e.message) }; }
  })()`);
  report.phases.googleFont = fontOnline;
  check('font Google scaricato e incorporato', Array.isArray(fontOnline.families) && fontOnline.families.includes('Roboto'), JSON.stringify(fontOnline));

  // ---------- persistenza font e funzionamento offline ----------
  const waitReady = async (ms = 12000) => {
    const t0 = Date.now();
    while (Date.now() - t0 < ms) {
      try { if (await ev(`typeof window.OPP === 'object' && OPP.state && OPP.state.slides.length > 0`) === true) return true; } catch {}
      await sleep(200);
    }
    return false;
  };
  await sleep(1400); // lascia scattare l'autosalvataggio
  await browser.send('Page.navigate', { url: URL });
  const reloaded = await waitReady();
  if (!reloaded) {
    const diag = await ev(`({ href: location.href, ready: document.readyState, title: document.title, hasOPP: typeof window.OPP, bodyLen: document.body ? document.body.innerHTML.length : -1 })`).catch(e => ({ error: e.message }));
    console.log('DIAGNOSTICA RICARICA:', JSON.stringify(diag));
    console.log('eccezioni:', JSON.stringify(browser.events.exceptions.slice(-5)));
    console.log('console:', JSON.stringify(browser.events.console.slice(-8)));
  }
  await sleep(600);
  const afterReload = await ev(`(() => ({ fonts:(OPP.state.fonts||[]).map(f=>f.family), roboto:[...document.fonts].filter(f=>f.family==='Roboto').length, slides:OPP.state.slides.length }))()`);
  report.phases.afterReload = { reloaded, ...afterReload };
  check('font conservato dopo la ricarica', afterReload.roboto > 0, JSON.stringify(afterReload));

  await browser.send('Network.enable');
  await browser.send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  const projectWithFont = await ev(`OPP.serializeDoc()`);
  fs.writeFileSync('C:/Progetti/OPP/.audit/project-with-font.json', projectWithFont);
  await browser.send('Page.navigate', { url: 'file:///C:/Progetti/OPP/OverPowerPoint.html' });
  const offlineReady = await waitReady();
  await sleep(400);
  const embeddedOk = await ev(`(async () => {
    const data = ${JSON.stringify(projectWithFont)};
    OPP.loadProjectData(JSON.parse(data), { historyLabel:'test offline', silent:true });
    await new Promise(r=>setTimeout(r,900));
    return { fonts:(OPP.state.fonts||[]).map(f=>f.family), roboto:[...document.fonts].filter(f=>f.family==='Roboto').length, slides:OPP.state.slides.length, commands:Object.keys(OPP.COMMANDS).length, fontsReady:document.fonts.status };
  })()`);
  report.phases.offline = { offlineReady, ...embeddedOk };
  check('suite caricata offline da file locale', offlineReady === true, JSON.stringify({ offlineReady }));
  check('font incorporato nel progetto funziona offline', embeddedOk.roboto > 0, JSON.stringify(embeddedOk));
  check('comandi disponibili offline', embeddedOk.commands > 200, String(embeddedOk.commands));
  await browser.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  await browser.send('Page.navigate', { url: URL });
  await waitReady();
  await ev(PATCH);

  // ---------- livelli ----------
  const layerTest = await ev(`(async () => {
    const s = OPP.state.current;
    const slide = OPP.state.slides[s];
    for (let i=0;i<3;i++) { OPP.runCommand('insert.text', {}); await new Promise(r=>setTimeout(r,50)); }
    const ids = slide.elements.map(e=>e.id);
    OPP.state.selected=[ids[0]];
    OPP.renderAll();
    await new Promise(r=>setTimeout(r,60));
    const rows = document.querySelectorAll('#layersList .layer-row');
    const rowEl = document.querySelector('#layersList .layer-row[data-layer-id="'+ids[0]+'"]');
    const up = rowEl && rowEl.querySelector('[data-move="up"]');
    if (up) up.click();
    await new Promise(r=>setTimeout(r,60));
    const orderAfter = OPP.state.slides[OPP.state.current].elements.map(e=>e.id).join(',');
    const eye = document.querySelector('#layersList .layer-row[data-layer-id="'+ids[0]+'"] [data-eye]');
    const visBefore = OPP.state.slides[OPP.state.current].elements.find(e=>e.id===ids[0]).visible;
    if (eye) eye.click();
    await new Promise(r=>setTimeout(r,60));
    const visAfter = OPP.state.slides[OPP.state.current].elements.find(e=>e.id===ids[0]).visible;
    // raggruppa
    OPP.state.selected = OPP.state.slides[OPP.state.current].elements.slice(0,2).map(e=>e.id);
    OPP.renderAll();
    const g = OPP.COMMANDS['arrange.group'];
    let grouped=null;
    try { g({}); grouped = OPP.state.slides[OPP.state.current].elements.filter(e=>e.groupId).length; } catch(e){ grouped='err:'+e.message; }
    return { rows:rows.length, moved:orderAfter.split(',')[0]!==ids[0], visBefore, visAfter, grouped };
  })()`);
  report.phases.layers = layerTest;
  check('pannello livelli con righe', layerTest.rows >= 3, String(layerTest.rows));
  check('pulsante ▲ riordina il livello', layerTest.moved === true);
  check('occhio mostra/nasconde', layerTest.visBefore !== layerTest.visAfter, `${layerTest.visBefore}→${layerTest.visAfter}`);
  check('raggruppamento', layerTest.grouped >= 2, String(layerTest.grouped));

  // ---------- export ----------
  const exportTest = await ev(`(async () => {
    __dl=0; __print=0;
    const out = {};
    const wait = async (ms) => { const t0=Date.now(); while (Date.now()-t0 < ms && __dl===0) await new Promise(r=>setTimeout(r,80)); };
    for (const k of ['export.png','export.svg','export.pptx','export.html','export.zip']) {
      __dl=0;
      try { Promise.resolve(OPP.runCommand(k,{})).catch(()=>{}); } catch(e){ out[k]='err:'+e.message; continue; }
      await wait(9000);
      out[k] = __dl;
    }
    __print=0; OPP.runCommand('export.print',{}); await new Promise(r=>setTimeout(r,4000)); out.print=__print;
    return out;
  })()`);
  report.phases.export = exportTest;
  check('export PNG scarica un file', exportTest['export.png'] > 0, JSON.stringify(exportTest));
  check('export SVG scarica un file', exportTest['export.svg'] > 0);
  check('export PPTX scarica un file', exportTest['export.pptx'] > 0);
  check('export HTML scarica un file', exportTest['export.html'] > 0);
  check('export ZIP scarica un file', exportTest['export.zip'] > 0);
  check('stampa/PDF invoca la stampa', exportTest.print > 0, String(exportTest.print));

  fs.writeFileSync('C:/Progetti/OPP/.audit/report.json', JSON.stringify({ report, checks }, null, 2));
  console.log('== SMOKE ==', JSON.stringify(smoke));
  console.log('== COMANDI ==', report.phases.commands.total, 'testati,', bad.length, 'con problemi');
  for (const d of bad) console.log('  ✗', d.key, '|', d.threw || d.exceptions[0] || d.toasts.join('|'));
  console.log('== RIBBON ==', ribbonResults.length, 'pulsanti,', badBtn.length, 'con errori');
  for (const d of badBtn.slice(0, 10)) console.log('  ✗', d.tab, d.cmd, d.exceptions[0]);
  console.log('== TOOL ==', toolResults.length, 'strumenti,', report.phases.tools.failing.length, 'non attivi');
  for (const d of report.phases.tools.failing) console.log('  ✗', d.tab, d.tool, d.kind || '', '→', d.active, d.active===d.tool);
  console.log('== CHECK ==');
  for (const c of checks) console.log(c.ok ? '  ✓' : '  ✗', c.name, c.ok ? '' : '· ' + c.detail);
  console.log('esito:', checks.filter(c => !c.ok).length, 'falliti su', checks.length);
} catch (e) {
  console.error('ERRORE RUNNER:', e);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  server.kill();
}
