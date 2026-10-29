// Collaudo mobile: viewport telefono, controlli tattili, flussi principali.
import fs from 'node:fs';
import { spawn } from 'node:child_process';
import { launch, sleep } from './cdp.mjs';

const URL = 'http://127.0.0.1:8765/OverPowerPoint.html';
const server = spawn(process.execPath, ['C:/Progetti/OPP/.audit/server.mjs'], { stdio: 'ignore' });
await sleep(600);

const checks = [];
const check = (n, ok, d = '') => checks.push({ n, ok: !!ok, d });
let browser;
try {
  browser = await launch({ url: URL, port: 9334, width: 390, height: 844, mobile: true });
  const ev = browser.evaluate;
  await sleep(900);

  const layout = await ev(`(() => {
    const de = document.documentElement;
    const scrollableAncestor = el => {
      let n = el.parentElement;
      while (n && n !== document.body) {
        const st = getComputedStyle(n);
        if (/(auto|scroll)/.test(st.overflowX) && n.scrollWidth > n.clientWidth) return true;
        if (/(hidden|clip)/.test(st.overflowX) || /(hidden|clip)/.test(st.overflowY)) return true;
        n = n.parentElement;
      }
      return false;
    };
    const over = [...document.querySelectorAll('body *')].filter(el => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.right > innerWidth + 2 && getComputedStyle(el).position !== 'fixed' && !scrollableAncestor(el);
    }).slice(0, 8).map(el => (el.id || el.className || el.tagName).toString().slice(0, 40) + ':' + Math.round(el.getBoundingClientRect().right));
    const lp = document.getElementById('leftPanel'), rp = document.getElementById('rightPanel');
    return { innerW: innerWidth, innerH: innerHeight, scrollW: de.scrollWidth, scrollH: de.scrollHeight,
      panelsCollapsed: lp.classList.contains('collapsed') && rp.classList.contains('collapsed'),
      overflowing: over, backdrop: !!document.getElementById('panelBackdrop') };
  })()`);
  check('nessuno scorrimento orizzontale', layout.scrollW <= layout.innerW + 1, JSON.stringify(layout));
  check('nessun elemento fuori dal bordo', layout.overflowing.length === 0, JSON.stringify(layout.overflowing));
  check('pannelli chiusi all’avvio su mobile', layout.panelsCollapsed === true);
  check('esiste lo sfondo per chiudere i pannelli', layout.backdrop === true);

  const tabs = await ev(`[...document.querySelectorAll('.tab[data-tab]')].map(t=>t.dataset.tab)`);
  let ribbonOk = true, details = [];
  for (const tab of tabs) {
    const info = await ev(`(() => {
      document.querySelector('.tab[data-tab=${JSON.stringify(tab)}]').click();
      const r = document.getElementById('ribbon');
      const n = r.querySelectorAll('button').length;
      return { n, scrollable: r.scrollWidth > r.clientWidth, h: r.clientHeight };
    })()`);
    if (info.n < 1) { ribbonOk = false; details.push(tab + ':vuoto'); }
  }
  check('ribbon popolato su tutte le schede', ribbonOk, details.join(','));

  const tap = await ev(`(() => {
    document.querySelector('.tab[data-tab="Home"]').click();
    const small = [...document.querySelectorAll('#ribbon button, .titlebar button, .tab')]
      .map(b => ({ n: (b.textContent || b.title || '').trim().slice(0, 14), h: Math.round(b.getBoundingClientRect().height), w: Math.round(b.getBoundingClientRect().width) }))
      .filter(b => b.h > 0 && b.h < 30);
    return { small: small.slice(0, 8), total: small.length };
  })()`);
  check('bersagli tattili ≥ 30px', tap.total === 0, JSON.stringify(tap.small));

  const flow = await ev(`(async () => {
    const cur = () => OPP.state.slides[OPP.state.current];
    const n0 = cur().elements.length;
    // inserisci testo dal ribbon (tap simulato)
    document.querySelector('.tab[data-tab="Inserisci"]').click();
    await new Promise(r => setTimeout(r, 80));
    const btn = [...document.querySelectorAll('#ribbon [data-command]')].find(b => b.dataset.command === 'insert.text');
    if (btn) btn.click();
    await new Promise(r => setTimeout(r, 120));
    const n1 = cur().elements.length;
    // pannello livelli: i pulsanti ▲▼ devono essere presenti e cliccabili
    const row = document.querySelector('#layersList .layer-row[data-layer-id]');
    const up = row && row.querySelector('[data-move="up"]');
    const upRect = up ? up.getBoundingClientRect() : null;
    if (up) up.click();
    // pannello proprietà: apri con il toggle (drawer)
    document.getElementById('rightToggleBtn').click();
    await new Promise(r => setTimeout(r, 120));
    const propsVisible = !!document.querySelector('#propertiesBody select, #propertiesBody input');
    const backdropOpen = document.getElementById('panelBackdrop').classList.contains('open');
    const rightW = Math.round(document.getElementById('rightPanel').getBoundingClientRect().width);
    document.getElementById('panelBackdrop').click();
    await new Promise(r => setTimeout(r, 120));
    const closedByBackdrop = document.getElementById('rightPanel').classList.contains('collapsed');
    // modale a misura di telefono
    OPP.runCommand('file.preferences', {});
    await new Promise(r => setTimeout(r, 150));
    const modal = document.querySelector('#modalShell') || document.getElementById('modalBg');
    const mw = modal ? Math.round(modal.getBoundingClientRect().width) : 0;
    document.getElementById('modalBg').classList.remove('open');
    // presentazione su mobile + uscita
    OPP.runCommand('view.present', {});
    await new Promise(r => setTimeout(r, 400));
    const presenting = OPP.state.presenting;
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await new Promise(r => setTimeout(r, 250));
    const ended = !OPP.state.presenting;
    return { n0, n1, inserted: n1 === n0 + 1, layerButtons: !!up, upSize: upRect ? Math.round(upRect.width) + 'x' + Math.round(upRect.height) : null, propsVisible, backdropOpen, rightW, closedByBackdrop, modalW: mw, innerW: innerWidth, presenting, ended };
  })()`);
  check('tap sul ribbon inserisce testo', flow.inserted === true, JSON.stringify(flow));
  check('pulsanti livello presenti su touch', flow.layerButtons === true, String(flow.upSize));
  check('pannello proprietà apribile come drawer', flow.propsVisible === true && flow.backdropOpen === true, JSON.stringify({ p: flow.propsVisible, b: flow.backdropOpen, w: flow.rightW }));
  check('drawer si chiude toccando lo sfondo', flow.closedByBackdrop === true);
  check('modale entro la larghezza', flow.modalW <= flow.innerW, flow.modalW + 'px');
  check('presentazione avviabile e chiudibile', flow.presenting && flow.ended, JSON.stringify({ p: flow.presenting, e: flow.ended }));

  const shot = await browser.send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync('C:/Progetti/OPP/.audit/mobile.png', Buffer.from(shot.data, 'base64'));

  fs.writeFileSync('C:/Progetti/OPP/.audit/mobile-report.json', JSON.stringify({ layout, tap, flow, checks }, null, 2));
  for (const c of checks) console.log(c.ok ? '  ✓' : '  ✗', c.n, c.ok ? '' : '· ' + c.d);
  console.log('mobile:', checks.filter(c => !c.ok).length, 'falliti su', checks.length);
} catch (e) {
  console.error('ERRORE:', e);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  server.kill();
}
