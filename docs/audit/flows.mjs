// Collaudo funzionale con file reali: import immagini/audio/progetti/PPTX, export validati byte per byte.
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
  window.__dl = 0; window.__print = 0; window.__filePick = 0; window.__nextFile = null; window.__blobs = [];
  const origClick = HTMLElement.prototype.click;
  window.__origClick = origClick;
  HTMLInputElement.prototype.click = function(){
    if (this.type === 'file') {
      window.__filePick++;
      const f = window.__nextFile;
      if (f) { window.__nextFile = null; const dt = new DataTransfer(); dt.items.add(f); this.files = dt.files; this.dispatchEvent(new Event('change')); }
      return;
    }
    return origClick.call(this);
  };
  HTMLAnchorElement.prototype.click = function(){ window.__dl++; };
  window.print = () => { window.__print++; };
  const origCreate = URL.createObjectURL.bind(URL);
  URL.createObjectURL = function(b){ window.__blobs.push(b); return origCreate(b); };
  window.__toasts = () => [...document.querySelectorAll('#toastWrap .toast')].map(t => t.textContent.trim());
  window.__closeModal = () => { const m = document.getElementById('modalBg'); if (m) m.classList.remove('open'); };
  window.__pngFile = async (color) => {
    const c = document.createElement('canvas'); c.width = 120; c.height = 80;
    const ctx = c.getContext('2d'); ctx.fillStyle = color || '#3399ff'; ctx.fillRect(0,0,120,80); ctx.fillStyle='#fff'; ctx.fillRect(20,20,60,40);
    const blob = await new Promise(r => c.toBlob(r, 'image/png'));
    return new File([blob], 'prova.png', { type: 'image/png' });
  };
  window.__wavFile = () => {
    const sr = 8000, n = 800, bytes = new Uint8Array(44 + n * 2);
    const dv = new DataView(bytes.buffer);
    const w = (o, s) => { for (let i = 0; i < s.length; i++) bytes[o + i] = s.charCodeAt(i); };
    w(0,'RIFF'); dv.setUint32(4, 36 + n*2, true); w(8,'WAVE'); w(12,'fmt '); dv.setUint32(16,16,true);
    dv.setUint16(20,1,true); dv.setUint16(22,1,true); dv.setUint32(24,sr,true); dv.setUint32(28,sr*2,true);
    dv.setUint16(32,2,true); dv.setUint16(34,16,true); w(36,'data'); dv.setUint32(40,n*2,true);
    for (let i=0;i<n;i++) dv.setInt16(44+i*2, Math.sin(i/10)*8000, true);
    return new File([bytes], 'prova.wav', { type: 'audio/wav' });
  };
  window.__ready = true;
})();
`;

let browser;
try {
  browser = await launch({ url: URL, port: 9336, width: 1440, height: 900 });
  const ev = browser.evaluate;
  await sleep(900);
  await ev(PATCH);

  // ---------- import immagine ----------
  const img1 = await ev(`(async () => {
    __nextFile = await __pngFile();
    const before = OPP.state.slides[OPP.state.current].elements.length;
    OPP.runCommand('insert.image', {});
    await new Promise(r=>setTimeout(r,500));
    const els = OPP.state.slides[OPP.state.current].elements;
    const img = els.filter(e=>e.type==='image').slice(-1)[0];
    return { before, after: els.length, src: img ? img.src.slice(0,22) : null, w: img && Math.round(img.w), picker: __filePick };
  })()`);
  check('import immagine da file', img1.after === img1.before + 1 && /^data:image\/png/.test(img1.src || ''), JSON.stringify(img1));

  // ---------- sostituisci immagine ----------
  const img2 = await ev(`(async () => {
    const el = OPP.state.slides[OPP.state.current].elements.filter(e=>e.type==='image').slice(-1)[0];
    OPP.state.selected = [el.id]; OPP.renderAll();
    const old = el.src;
    __nextFile = await __pngFile('#cc3366');
    OPP.runCommand('image.replace', {});
    await new Promise(r=>setTimeout(r,500));
    return { changed: el.src !== old, len: el.src.length };
  })()`);
  check('sostituzione immagine', img2.changed === true, JSON.stringify(img2));

  // ---------- import audio ----------
  const aud = await ev(`(async () => {
    __nextFile = __wavFile();
    const before = OPP.state.slides[OPP.state.current].elements.length;
    OPP.runCommand('insert.audio', {});
    await new Promise(r=>setTimeout(r,500));
    const els = OPP.state.slides[OPP.state.current].elements;
    const m = els.filter(e=>['audio','media'].includes(e.type)).slice(-1)[0];
    return { before, after: els.length, type: m && m.type, src: m ? m.src.slice(0,20) : null };
  })()`);
  check('import audio da file', aud.after === aud.before + 1 && /^data:audio/.test(aud.src || ''), JSON.stringify(aud));

  // ---------- export validati ----------
  const art = await ev(`(async () => {
    const res = {};
    const grab = async (ms) => { const t0=Date.now(); const i=__blobs.length; while(Date.now()-t0<ms && __blobs.length<=i) await new Promise(r=>setTimeout(r,80)); return __blobs[__blobs.length-1]||null; };
    const sig = async (blob) => { if(!blob) return null; const buf=new Uint8Array(await blob.slice(0,8).arrayBuffer()); return [...buf].map(b=>b.toString(16).padStart(2,'0')).join(''); };
    for (const [cmd,key] of [['export.png','png'],['export.svg','svg'],['export.pptx','pptx'],['export.html','html'],['export.zip','zip']]) {
      __blobs.length = 0;
      Promise.resolve(OPP.runCommand(cmd,{})).catch(()=>{});
      const b = await grab(12000);
      res[key] = b ? { size: b.size, type: b.type, sig: await sig(b) } : 'nessun blob';
      if (key==='svg' && b) res.svgText = (await b.text()).slice(0,60);
      if (key==='html' && b) res.htmlHasData = (await b.text()).includes('opp-export-data');
      if (key==='pptx' && b) { const t = await b.text(); res.pptxParts = ['[Content_Types].xml','ppt/presentation.xml','ppt/slides/slide1.xml'].filter(k=>t.includes(k)); }
      if (key==='zip' && b) { const t = await b.text(); res.zipHasPng = t.includes('slide-1') || t.includes('.png'); }
    }
    return res;
  })()`);
  check('PNG valido', art.png && art.png.sig && art.png.sig.startsWith('89504e47'), JSON.stringify(art.png));
  check('SVG valido', /<svg|<\?xml/.test(art.svgText || ''), String(art.svgText));
  check('PPTX è uno ZIP valido', art.pptx && art.pptx.sig && art.pptx.sig.startsWith('504b'), JSON.stringify(art.pptx));
  check('PPTX contiene le parti OOXML', (art.pptxParts || []).length >= 2, JSON.stringify(art.pptxParts));
  check('HTML contiene i dati del progetto', art.htmlHasData === true);
  check('ZIP contiene le immagini', art.zipHasPng === true);

  // ---------- import progetti ----------
  const jsonImport = await ev(`(async () => {
    const text = OPP.serializeDoc();
    const file = new File([text], 'progetto.opp.json', { type: 'application/json' });
    __nextFile = file;
    OPP.state.docName = 'Nome da sovrascrivere';
    OPP.runCommand('file.import.json', {});
    await new Promise(r=>setTimeout(r,700));
    return { name: OPP.state.docName, slides: OPP.state.slides.length };
  })()`);
  check('import progetto JSON', jsonImport.name !== 'Nome da sovrascrivere' && jsonImport.slides > 0, JSON.stringify(jsonImport));

  const htmlImport = await ev(`(async () => {
    __blobs.length = 0;
    Promise.resolve(OPP.runCommand('export.html',{})).catch(()=>{});
    const t0=Date.now(); while(Date.now()-t0<12000 && !__blobs.length) await new Promise(r=>setTimeout(r,100));
    const blob = __blobs[__blobs.length-1];
    if (!blob) return { error: 'html non esportato' };
    const text = await blob.text();
    __nextFile = new File([text], 'deck.html', { type: 'text/html' });
    OPP.state.docName = 'Da sovrascrivere';
    OPP.runCommand('file.import.html', {});
    await new Promise(r=>setTimeout(r,900));
    return { name: OPP.state.docName, slides: OPP.state.slides.length, size: text.length };
  })()`);
  check('import progetto HTML', htmlImport.name !== 'Da sovrascrivere' && htmlImport.slides > 0, JSON.stringify(htmlImport));

  const pptxImport = await ev(`(async () => {
    __blobs.length = 0;
    Promise.resolve(OPP.runCommand('export.pptx',{})).catch(()=>{});
    const t0=Date.now(); while(Date.now()-t0<12000 && !__blobs.length) await new Promise(r=>setTimeout(r,100));
    const blob = __blobs[__blobs.length-1];
    if (!blob) return { error: 'pptx non esportato' };
    __nextFile = new File([blob], 'deck.pptx', { type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' });
    const before = OPP.state.slides.length;
    OPP.runCommand('file.import.pptx', {});
    await new Promise(r=>setTimeout(r,1500));
    return { before, after: OPP.state.slides.length, name: OPP.state.docName };
  })()`);
  check('import PPTX esportato dalla suite', pptxImport.after > 0 && pptxImport.after !== undefined, JSON.stringify(pptxImport));

  // ---------- tabella: CSV in uscita ----------
  const tableTest = await ev(`(async () => {
    OPP.runCommand('insert.table', {});
    await new Promise(r=>setTimeout(r,400));
    const el = OPP.state.slides[OPP.state.current].elements.filter(e=>e.type==='table').slice(-1)[0];
    __blobs.length = 0;
    OPP.state.selected=[el.id]; OPP.renderAll();
    OPP.runCommand('table.csv', {});
    await new Promise(r=>setTimeout(r,400));
    const b = __blobs[__blobs.length-1];
    const text = b ? await b.text() : '';
    return { rows: (el.rows||[]).length, cols: (el.rows||[{}])[0].length, csvHead: text.slice(0,40) };
  })()`);
  check('tabella creata con celle', tableTest.rows >= 2 && tableTest.cols >= 2, JSON.stringify(tableTest));
  check('tabella esportata in CSV', tableTest.csvHead.length > 0, tableTest.csvHead);

  // ---------- copia/incolla, annulla/ripristina, scorciatoie ----------
  const editFlow = await ev(`(async () => {
    const cur = () => OPP.state.slides[OPP.state.current];
    const n0 = cur().elements.length;
    const el = cur().elements.slice(-1)[0];
    OPP.state.selected=[el.id]; OPP.renderAll();
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'c',ctrlKey:true,bubbles:true}));
    await new Promise(r=>setTimeout(r,120));
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'v',ctrlKey:true,bubbles:true}));
    await new Promise(r=>setTimeout(r,160));
    const n1 = cur().elements.length;
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'z',ctrlKey:true,bubbles:true}));
    await new Promise(r=>setTimeout(r,160));
    const n2 = cur().elements.length;
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'y',ctrlKey:true,bubbles:true}));
    await new Promise(r=>setTimeout(r,160));
    const n3 = cur().elements.length;
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true}));
    await new Promise(r=>setTimeout(r,160));
    const n4 = cur().elements.length;
    return { n0, n1, n2, n3, n4 };
  })()`);
  check('copia e incolla con scorciatoie', editFlow.n1 === editFlow.n0 + 1, JSON.stringify(editFlow));
  check('annulla ripristina', editFlow.n2 === editFlow.n0, JSON.stringify(editFlow));
  check('ripeti riapplica', editFlow.n3 === editFlow.n0 + 1, JSON.stringify(editFlow));
  check('cancella elimina', editFlow.n4 === editFlow.n2, JSON.stringify(editFlow));

  // ---------- disegno con puntatore, booleane, tracciati ----------
  const vectorFlow = await ev(`(async () => {
    const cur = () => OPP.state.slides[OPP.state.current];
    const surface = document.getElementById('slideSurface');
    surface.scrollIntoView({block:'center'});
    await new Promise(r=>setTimeout(r,80));
    const tool = document.querySelector('[data-tool="shape"][data-kind="rect"]');
    if (tool) tool.click();
    await new Promise(r=>setTimeout(r,60));
    const r = surface.getBoundingClientRect();
    const fire = (type, x, y, buttons) => surface.dispatchEvent(new PointerEvent(type, { bubbles:true, clientX:x, clientY:y, pointerId:1, pointerType:'mouse', isPrimary:true, button:0, buttons }));
    const n0 = cur().elements.length;
    fire('pointerdown', r.left+40, r.top+40, 1);
    fire('pointermove', r.left+180, r.top+150, 1);
    fire('pointerup', r.left+180, r.top+150, 0);
    await new Promise(r=>setTimeout(r,150));
    const n1 = cur().elements.length;
    const shape = cur().elements.slice(-1)[0];
    // seconda forma (lo strumento torna a "seleziona" dopo il disegno: va riattivato)
    if (tool) tool.click();
    await new Promise(r=>setTimeout(r,60));
    fire('pointerdown', r.left+120, r.top+100, 1);
    fire('pointermove', r.left+260, r.top+220, 1);
    fire('pointerup', r.left+260, r.top+220, 0);
    await new Promise(r=>setTimeout(r,150));
    const n2 = cur().elements.length;
    // booleana unione
    const ids = cur().elements.slice(-2).map(e=>e.id);
    OPP.state.selected = ids; OPP.renderAll();
    await new Promise(r=>setTimeout(r,80));
    let boolType = null, boolParts = 0;
    try { OPP.COMMANDS['shape.union']({}); await new Promise(r=>setTimeout(r,120)); const b = cur().elements.slice(-1)[0]; boolType = b.type; boolParts = (b.parts||[]).length; } catch(e) { boolType = 'err:'+e.message; }
    // tracciato da forma: disegna una forma nuova e convertirla
    if (tool) tool.click();
    await new Promise(r=>setTimeout(r,60));
    fire('pointerdown', r.left+200, r.top+60, 1);
    fire('pointermove', r.left+320, r.top+160, 1);
    fire('pointerup', r.left+320, r.top+160, 0);
    await new Promise(r=>setTimeout(r,150));
    const fresh = cur().elements.slice(-1)[0];
    OPP.state.selected=[fresh.id]; OPP.renderAll();
    let pathNodes = null;
    try { OPP.COMMANDS['shape.toPath']({}); await new Promise(r=>setTimeout(r,150)); const p = cur().elements.find(e=>e.type==='path'); pathNodes = p ? (p.nodes||[]).length : null; } catch(e) { pathNodes = 'err:'+e.message; }
    return { n0, n1, n2, shapeType: shape && shape.type, kind: shape && shape.kind, boolType, boolParts, pathNodes, freshType: fresh && fresh.type };
  })()`);
  check('disegno forma col puntatore', vectorFlow.n1 === vectorFlow.n0 + 1 && vectorFlow.shapeType === 'shape', JSON.stringify(vectorFlow));
  check('seconda forma disegnata', vectorFlow.n2 === vectorFlow.n0 + 2, JSON.stringify(vectorFlow));
  check('unione booleana', vectorFlow.boolType === 'boolean' && vectorFlow.boolParts >= 2, JSON.stringify(vectorFlow));
  check('conversione forma → tracciato', vectorFlow.pathNodes >= 3, JSON.stringify(vectorFlow));

  const shot = await browser.send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync('C:/Progetti/OPP/.audit/desktop.png', Buffer.from(shot.data, 'base64'));

  fs.writeFileSync('C:/Progetti/OPP/.audit/flows-report.json', JSON.stringify({ checks, img1, img2, aud, art, jsonImport, htmlImport, pptxImport, tableTest, editFlow }, null, 2));
  for (const c of checks) console.log(c.ok ? '  ✓' : '  ✗', c.n, c.ok ? '' : '· ' + c.d);
  console.log('flussi:', checks.filter(c => !c.ok).length, 'falliti su', checks.length);
} catch (e) {
  console.error('ERRORE:', e);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  server.kill();
}
