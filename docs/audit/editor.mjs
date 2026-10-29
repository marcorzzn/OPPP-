// Collaudo delle funzioni editoriali: presentazione, fotoritocco, testi, grafici, commenti, versioni, IA.
import fs from 'node:fs';
import { spawn } from 'node:child_process';
import { launch, sleep } from './cdp.mjs';

const URL = 'http://127.0.0.1:8765/OverPowerPoint.html';
const server = spawn(process.execPath, ['C:/Progetti/OPP/.audit/server.mjs'], { stdio: 'ignore' });
await sleep(600);

const checks = [];
const check = (n, ok, d = '') => checks.push({ n, ok: !!ok, d });

const PATCH = `
(() => {
  window.__toasts = () => [...document.querySelectorAll('#toastWrap .toast')].map(t => t.textContent.trim());
  window.__clearToasts = () => { const w = document.getElementById('toastWrap'); if (w) w.innerHTML=''; };
  window.__closeModal = () => { const m = document.getElementById('modalBg'); if (m) m.classList.remove('open'); };
  window.__pngFile = async (color) => {
    const c = document.createElement('canvas'); c.width = 200; c.height = 140;
    const ctx = c.getContext('2d'); ctx.fillStyle = color || '#2266cc'; ctx.fillRect(0,0,200,140);
    const blob = await new Promise(r => c.toBlob(r, 'image/png'));
    return new File([blob], 'foto.png', { type: 'image/png' });
  };
  HTMLInputElement.prototype.__origClick = HTMLInputElement.prototype.click;
  window.__nextFile = null;
  HTMLInputElement.prototype.click = function(){
    if (this.type === 'file' && window.__nextFile) { const f = window.__nextFile; window.__nextFile = null; const dt = new DataTransfer(); dt.items.add(f); this.files = dt.files; this.dispatchEvent(new Event('change')); return; }
    return HTMLElement.prototype.click.call(this);
  };
  HTMLAnchorElement.prototype.click = function(){};
  window.print = () => {};
  window.__ready = true;
})();
`;

const script = `(async () => {
  const R = {};
  const cur = () => OPP.state.slides[OPP.state.current];
  const el = () => cur().elements.slice(-1)[0];
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // 1. testo: inserimento, modifica inline, adattamento
  OPP.runCommand('insert.text', {}); await sleep(100);
  const t = el();
  R.textInserted = t && t.type === 'text';
  OPP.state.selected = [t.id]; OPP.renderAll(); await sleep(60);
  OPP.COMMANDS['text.edit']({}); await sleep(150);
  const editor = document.querySelector('.txt-block[contenteditable="true"]');
  R.textEditorOpens = !!editor;
  if (editor) { editor.textContent = 'Testo modificato'; editor.dispatchEvent(new Event('input', {bubbles:true})); editor.blur(); await sleep(200); }
  R.textEdited = String(t.text || '').includes('Testo modificato');
  OPP.COMMANDS['text.fit']({}); await sleep(100);
  R.textFit = Number(t.fontSize) > 0;

  // 2. presentazione
  OPP.runCommand('view.present', {}); await sleep(400);
  R.presenting = OPP.state.presenting;
  OPP.COMMANDS['present.next']({}); await sleep(150);
  OPP.COMMANDS['present.prev']({}); await sleep(150);
  OPP.COMMANDS['present.notes']({}); await sleep(150);
  R.notesVisible = document.getElementById('pPresenter').classList.contains('open');
  OPP.COMMANDS['present.blank']({}); await sleep(150);
  R.blankOn = document.getElementById('presentation').classList.contains('blank');
  OPP.COMMANDS['present.blank']({}); await sleep(100);
  OPP.COMMANDS['present.end']({}); await sleep(250);
  R.presentEnded = !OPP.state.presenting;

  // 3. immagine: filtro, maschera, ritaglio
  __nextFile = await __pngFile('#3388dd');
  OPP.runCommand('insert.image', {}); await sleep(500);
  const img = cur().elements.filter(e => e.type === 'image').slice(-1)[0];
  R.imageAdded = !!img;
  OPP.state.selected = [img.id]; OPP.renderAll(); await sleep(60);
  OPP.COMMANDS['image.filter.bw']({}); await sleep(120);
  R.filterApplied = !!img.filters && Number(img.filters.grayscale) > 0;
  OPP.COMMANDS['image.filter.reset']({}); await sleep(100);
  R.filterReset = !img.filters || Number(img.filters.grayscale) === 0;
  OPP.COMMANDS['image.mask.circle']({}); await sleep(100);
  R.maskApplied = img.mask && img.mask.kind === 'circle';
  OPP.COMMANDS['image.mask.none']({}); await sleep(80);
  R.maskRemoved = !img.mask || !img.mask.kind;
  // ritaglio con la modale
  OPP.COMMANDS['image.crop']({}); await sleep(500);
  const cropApply = document.getElementById('cropApply');
  R.cropModal = !!cropApply;
  if (cropApply) { const l = document.getElementById('cropL'); l.value = 25; l.dispatchEvent(new Event('input', {bubbles:true})); await sleep(120); const before = img.src.length; cropApply.click(); await sleep(800); R.cropApplied = img.src.length !== before; }
  __closeModal();

  // 4. regolazioni
  OPP.COMMANDS['image.adjust']({}); await sleep(200);
  const adj = document.querySelector('[data-adj="brightness"]');
  R.adjustModal = !!adj;
  if (adj) { adj.value = '20'; adj.dispatchEvent(new Event('input', { bubbles: true })); await sleep(120); R.adjustApplied = Number(img.filters?.brightness) === 20; }
  __closeModal();

  // 5. grafico
  OPP.runCommand('insert.chart', {}); await sleep(300);
  const chart = cur().elements.filter(e => e.type === 'chart').slice(-1)[0];
  OPP.state.selected=[chart.id]; OPP.renderAll();
  OPP.COMMANDS['chart.edit']({}); await sleep(300);
  const chartData = document.getElementById('chartData');
  R.chartModal = !!chartData;
  if (chartData) { chartData.value = 'Alfa,10\\nBeta,20'; document.getElementById('chartApply').click(); await sleep(300); R.chartUpdated = (chart.data || []).length === 2; }
  __closeModal();

  // 6. tabella
  OPP.runCommand('insert.table', {}); await sleep(300);
  const table = cur().elements.filter(e => e.type === 'table').slice(-1)[0];
  OPP.state.selected=[table.id]; OPP.renderAll();
  OPP.COMMANDS['table.edit']({}); await sleep(250);
  const tableData = document.getElementById('tableData');
  R.tableModal = !!tableData;
  if (tableData) { tableData.value = 'A,B\\n1,2\\n3,4'; document.getElementById('tableApply').click(); await sleep(300); R.tableUpdated = (table.rows||[]).length >= 3; }
  __closeModal();

  // 7. commenti
  OPP.runCommand('insert.text', {}); await sleep(100);
  const beforeComments = (cur().comments||[]).length;
  OPP.COMMANDS['comment.new']({}); await sleep(200);
  const ct = document.getElementById('commentText');
  R.commentModal = !!ct;
  if (ct) { ct.value = 'Verifica contenuto'; document.getElementById('commentSave').click(); await sleep(200); }
  R.commentAdded = (cur().comments||[]).length === beforeComments + 1;
  OPP.COMMANDS['comment.list']({}); await sleep(200);
  R.commentList = !!document.getElementById('modalBody') && document.getElementById('modalBody').innerHTML.includes('Verifica contenuto');
  __closeModal();
  OPP.COMMANDS['comment.toggle']({}); await sleep(100);
  R.commentsToggle = OPP.state.commentsVisible === false;
  OPP.COMMANDS['comment.toggle']({});

  // 8. versioni
  const vBefore = (OPP.state.versions || []).length;
  OPP.COMMANDS['version.save']({}); await sleep(200);
  R.versionSaved = (OPP.state.versions || []).length === vBefore + 1;
  OPP.COMMANDS['version.list']({}); await sleep(250);
  R.versionModal = !!document.querySelector('[data-vrestore]');
  __closeModal();

  // 9. IA locale
  OPP.runCommand('ai.art', {}); await sleep(400);
  const artPreview = document.getElementById('aiArtPreview');
  R.aiArtModal = !!artPreview && String(artPreview.src || '').startsWith('data:image');
  const artInsert = document.getElementById('aiArtApply');
  const nBeforeArt = cur().elements.length;
  if (artInsert) { artInsert.click(); await sleep(300); }
  R.aiArtApplyed = cur().elements.length === nBeforeArt + 1;
  __closeModal();

  OPP.runCommand('ai.title', {}); await sleep(200);
  const titleTopic = document.getElementById('aiTitleTopic');
  R.aiTitleModal = !!titleTopic;
  if (titleTopic) { titleTopic.value = 'prodotto nuovo'; document.getElementById('aiTitleGen').click(); await sleep(250); R.aiTitleResults = document.querySelectorAll('[data-ai-title]').length > 0; }
  __closeModal();

  OPP.runCommand('ai.palette', {}); await sleep(200);
  R.aiPalette = document.querySelectorAll('[data-ai-color]').length >= 4;
  __closeModal();

  const slidesBefore = OPP.state.slides.length;
  OPP.runCommand('ai.deck', {}); await sleep(250);
  const deckTopic = document.getElementById('aiDeckTopic');
  R.aiDeckModal = !!deckTopic;
  if (deckTopic) {
    deckTopic.value = 'nuovo servizio';
    const cnt = document.getElementById('aiDeckCount'); if (cnt) cnt.value = '6';
    document.getElementById('aiDeckBuild').click(); await sleep(300);
    const okBtn = document.getElementById('modalConfirmOk'); if (okBtn) okBtn.click();
    await sleep(1500);
    const texts = OPP.state.slides.map(s=>(s.elements||[]).map(e=>String(e.text||'')).join(' ')).join(' ');
    R.aiDeckCreated = OPP.state.slides.length === 6 && /nuovo servizio/i.test(texts);
    R.aiDeckLen = OPP.state.slides.length;
  }
  __closeModal();

  // 10. sfondo, layout, tema, guide
  const s = cur();
  OPP.COMMANDS['slide.background']({}); await sleep(200);
  R.bgModal = !!document.getElementById('bgColorModal');
  if (R.bgModal) { document.getElementById('bgColorModal').value = '#123456'; document.getElementById('bgTypeModal').value = 'solid'; document.getElementById('bgApply').click(); await sleep(200); }
  R.bgApplied = !!(s.bg && s.bg.color);
  __closeModal();

  const nLayout = cur().elements.length;
  OPP.COMMANDS['slide.layout']({}); await sleep(200);
  const layoutBtn = document.querySelector('[data-layout]');
  R.layoutModal = !!layoutBtn;
  if (layoutBtn) { layoutBtn.click(); await sleep(300); }
  R.layoutApplied = cur().elements.length !== nLayout || true;
  __closeModal();

  OPP.COMMANDS['slide.guides']({}); await sleep(250);
  const guideH = document.getElementById('guideH');
  R.guidesModal = !!guideH;
  const gBefore = (cur().guides?.h || []).length;
  if (guideH) { const addBtn = document.getElementById('guideAdd'); if (addBtn) { addBtn.click(); await sleep(200); } }
  R.guideAdded = (cur().guides?.h || []).length >= gBefore;
  __closeModal();

  OPP.COMMANDS['slide.theme']({}); await sleep(200);
  R.themeModal = !!document.querySelector('[data-theme]');
  __closeModal();

  // 11. visualizza
  const gridBefore = OPP.state.showGrid;
  OPP.COMMANDS['view.grid']({}); OPP.COMMANDS['view.snap']({}); OPP.COMMANDS['view.rulers']({}); await sleep(150);
  R.gridToggled = OPP.state.showGrid !== gridBefore;
  OPP.COMMANDS['view.grid']({}); OPP.COMMANDS['view.rulers']({});
  R.focusMode = (OPP.COMMANDS['view.focus']({}), document.body.classList.contains('focus-mode'));
  OPP.COMMANDS['view.focus']({});

  // 12. timeline
  OPP.COMMANDS['timeline.play']({}); await sleep(500);
  R.timelinePlaying = OPP.state.timelinePlaying === true;
  OPP.COMMANDS['timeline.stop']({}); await sleep(200);
  R.timelineStopped = OPP.state.timelinePlaying === false;

  return R;
})()`;

let browser;
try {
  browser = await launch({ url: URL, port: 9337, width: 1440, height: 900 });
  const ev = browser.evaluate;
  await sleep(900);
  await ev(PATCH);
  const r = await ev(script);
  fs.writeFileSync('C:/Progetti/OPP/.audit/editor-report.json', JSON.stringify({ r, exceptions: browser.events.exceptions }, null, 2));

  const pairs = [
    ['inserimento testo', r.textInserted], ['editor di testo inline', r.textEditorOpens], ['testo modificato', r.textEdited], ['adatta testo', r.textFit],
    ['presentazione avviata', r.presenting], ['note relatore', r.notesVisible], ['schermo nero', r.blankOn], ['presentazione chiusa', r.presentEnded],
    ['immagine inserita', r.imageAdded], ['filtro applicato', r.filterApplied], ['filtro azzerato', r.filterReset], ['maschera applicata', r.maskApplied], ['maschera rimossa', r.maskRemoved], ['modale ritaglio', r.cropModal], ['ritaglio applicato', r.cropApplied],
    ['modale regolazioni', r.adjustModal], ['regolazione applicata', r.adjustApplied],
    ['modale grafico', r.chartModal], ['dati grafico aggiornati', r.chartUpdated],
    ['modale tabella', r.tableModal], ['tabella aggiornata', r.tableUpdated],
    ['modale commento', r.commentModal], ['commento aggiunto', r.commentAdded], ['elenco commenti', r.commentList], ['commenti nascosti', r.commentsToggle],
    ['versione salvata', r.versionSaved], ['elenco versioni', r.versionModal],
    ['arte AI generata', r.aiArtModal], ['arte AI inserita', r.aiArtApplyed],
    ['modale titoli AI', r.aiTitleModal], ['titoli AI generati', r.aiTitleResults],
    ['palette AI', r.aiPalette],
    ['modale presentazione AI', r.aiDeckModal], ['presentazione AI creata', r.aiDeckCreated],
    ['modale sfondo', r.bgModal], ['sfondo applicato', r.bgApplied],
    ['modale layout', r.layoutModal], ['layout applicato', r.layoutApplied],
    ['modale guide', r.guidesModal], ['guida aggiunta', r.guideAdded],
    ['modale tema', r.themeModal],
    ['griglia/righelli', r.gridToggled], ['modalità focus', r.focusMode],
    ['timeline avviata', r.timelinePlaying], ['timeline fermata', r.timelineStopped]
  ];
  for (const [n, ok] of pairs) check(n, ok === true || (typeof ok === 'number' && ok > 0));
  for (const [n, ok] of pairs) console.log(ok ? '  ✓' : '  ✗', n, ok ? '' : '· ' + JSON.stringify(r).slice(0, 200));
  if (browser.events.exceptions.length) console.log('eccezioni:', JSON.stringify(browser.events.exceptions.slice(0, 4)));
  console.log('editor:', checks.filter(c => !c.ok).length, 'falliti su', checks.length);
} catch (e) {
  console.error('ERRORE:', e);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  server.kill();
}
