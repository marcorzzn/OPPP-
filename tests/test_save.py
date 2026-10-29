"""Fase 2 — salvataggio su file, autosalvataggio in IndexedDB, indicatore, export.

Uso:  python tests/test_save.py [--solo NOME]
"""
from __future__ import annotations

import json
import pathlib
import sys

from harness import Session, launch, main_runner, start_http

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROUNDTRIP = ROOT / "tests" / "_roundtrip.opp.json"
HTTP = start_http(8801)

STUBS = """
(() => {
  window.__dl = 0; window.__print = 0; window.__saved = null; window.__blobs = [];
  window.__nextFile = null;
  HTMLAnchorElement.prototype.click = function(){ window.__dl++; };
  HTMLInputElement.prototype.__origClick = HTMLInputElement.prototype.click;
  HTMLInputElement.prototype.click = function(){
    if (this.type === 'file' && window.__nextFile) {
      const f = window.__nextFile; window.__nextFile = null;
      const dt = new DataTransfer(); dt.items.add(f); this.files = dt.files;
      this.dispatchEvent(new Event('change')); return;
    }
    return HTMLElement.prototype.click.call(this);
  };
  window.print = () => { window.__print++; window.__printPages = document.querySelectorAll('#printArea .print-page').length; };
  const origCreate = URL.createObjectURL.bind(URL);
  URL.createObjectURL = function(b){ window.__blobs.push(b); return origCreate(b); };
  window.showSaveFilePicker = async (opts) => ({
    name: opts && opts.suggestedName || 'progetto.opp.json',
    async createWritable() {
      const parts = [];
      return {
        async write(b) { parts.push(b); },
        async close() { window.__saved = await new Blob(parts).text(); }
      };
    }
  });
  window.__toasts = () => [...document.querySelectorAll('#toastWrap .toast')].map(t => t.textContent);
  window.__badge = () => document.getElementById('autosaveText').textContent;
  window.__closeModal = () => { const m = document.getElementById('modalBg'); if (m) m.classList.remove('open'); };
  window.__idbHasAutosave = () => new Promise(res => {
    const req = indexedDB.open('opp.db');
    req.onerror = () => res(false);
    req.onsuccess = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains('autosave')) return res(false);
      const g = db.transaction('autosave').objectStore('autosave').get('current');
      g.onsuccess = () => res(!!g.result);
      g.onerror = () => res(false);
    };
  });
  window.__bigPng = () => new Promise(res => {
    const c = document.createElement('canvas'); c.width = 1400; c.height = 1000;
    const ctx = c.getContext('2d');
    const img = ctx.createImageData(c.width, c.height);
    for (let i = 0; i < img.data.length; i += 4) {
      img.data[i] = Math.random() * 255;
      img.data[i + 1] = Math.random() * 255;
      img.data[i + 2] = Math.random() * 255;
      img.data[i + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    c.toBlob(b => res(new File([b], 'grande.png', { type: 'image/png' })), 'image/png');
  });
  window.__ready = true;
})();
"""


def _patch(s: Session) -> None:
    s.page.evaluate(STUBS)


def _add_text(s: Session, testo: str) -> str:
    s.add_text_button()
    s.wait_editor()
    s.type_text(testo)
    s.exit_editor()
    return s.last_text()["id"]


def t01_autosave_indexeddb(s: Session) -> None:
    el = _add_text(s, "AUTOSAVE")
    s.page.wait_for_timeout(1600)  # attesa del debounce di 900 ms
    ok = s.page.evaluate(
        """() => new Promise(res => {
          const r = indexedDB.open('opp.db');
          r.onerror = () => res(false);
          r.onsuccess = () => {
            const db = r.result;
            if (!db.objectStoreNames.contains('autosave')) return res(false);
            const g = db.transaction('autosave').objectStore('autosave').get('current');
            g.onsuccess = () => res(!!g.result);
            g.onerror = () => res(false);
          };
        })"""
    )
    assert ok is True, "nessun autosalvataggio in IndexedDB"
    vecchio = s.page.evaluate("() => localStorage.getItem('opp.autosave.v2')")
    assert vecchio is None, "il vecchio salvataggio localStorage non è stato migrato"
    s.page.reload()
    s.page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    s.page.wait_for_timeout(400)
    presente = s.page.evaluate(
        "(id) => OPP.state.slides.some(sl => (sl.elements || []).some(e => e.id === id && (e.text || '').includes('AUTOSAVE')))",
        el,
    )
    assert presente is True, "il progetto non è stato ripristinato dopo la ricarica"


def t02_salva_su_file(s: Session) -> None:
    _patch(s)
    _add_text(s, "FILE")
    _save(s)
    s.page.wait_for_function("() => window.__saved !== null", timeout=8000)
    testo = s.page.evaluate("window.__saved")
    dati = json.loads(testo)
    assert dati.get("name") == s.page.evaluate("OPP.state.docName"), dati.get("name")
    assert len(dati.get("slides", [])) > 0
    assert s.page.evaluate("OPP.state.fileDirty") is False, "fileDirty non azzerato dopo il salvataggio"
    badge = s.page.evaluate("window.__badge()")
    assert badge.startswith("Salvato su file alle "), badge


def t03_avviso_modifiche(s: Session) -> None:
    _patch(s)
    _add_text(s, "NONSALVATO")
    assert s.page.evaluate("OPP.state.fileDirty") is True, "fileDirty non attivo dopo una modifica"
    _save(s)
    s.page.wait_for_function("() => window.__saved !== null", timeout=8000)
    assert s.page.evaluate("OPP.state.fileDirty") is False


def t04_indicatore_due_stati(s: Session) -> None:
    _patch(s)
    _add_text(s, "STATO")
    s.page.wait_for_timeout(1500)
    senza_file = s.page.evaluate("window.__badge()")
    assert "Autosalvato nel browser" in senza_file, senza_file
    _save(s)
    s.page.wait_for_function("() => window.__saved !== null", timeout=8000)
    s.page.wait_for_timeout(200)
    con_file = s.page.evaluate("window.__badge()")
    assert "Salvato su file alle " in con_file, con_file


def t05_progetto_pesante_roundtrip(s: Session) -> None:
    _patch(s)
    s.page.click('#tabs .tab[data-tab="Inserisci"]')
    s.page.evaluate("async () => { window.__nextFile = await window.__bigPng(); }")
    s.page.click('#ribbon [data-command="insert.image"]')
    s.page.wait_for_function("() => OPP.currentSlide().elements.some(e => e.type === 'image')", timeout=5000)
    # font incorporato (se c'è rete)
    s.page.evaluate("() => OPP.runCommand('font.manage', {})")
    s.page.wait_for_timeout(200)
    s.page.fill("#googleFontName", "Roboto")
    s.page.click("#fontGoogleAdd")
    s.page.wait_for_timeout(6000)
    font = s.page.evaluate("() => (OPP.state.fonts || []).map(f => f.family)")
    s.page.evaluate("() => { const m = document.getElementById('modalBg'); if (m) m.classList.remove('open'); }")

    dimensione = s.page.evaluate("() => OPP.serializeDoc().length")
    assert dimensione > 2_000_000, f"il progetto di prova è troppo leggero ({dimensione} caratteri)"

    _save(s)
    s.page.wait_for_function("() => window.__saved !== null", timeout=30000)
    testo = s.page.evaluate("window.__saved")
    ROUNDTRIP.write_text(testo, encoding="utf-8")
    salvato = json.loads(testo)
    assert len(testo) > 2_000_000, f"file salvato troppo piccolo ({len(testo)})"
    assert salvato["name"] == s.page.evaluate("OPP.state.docName")
    assert font == [] or (salvato.get("fonts") and salvato["fonts"][0]["family"] == "Roboto"), font

    # ricarica e riapri con il selettore file reale
    s.page.reload()
    s.page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    s.page.click('#tabs .tab[data-tab="File"]')
    with s.page.expect_file_chooser() as fc:
        s.page.click('#ribbon [data-command="file.open"]')
    fc.value.set_files(str(ROUNDTRIP))
    s.page.wait_for_timeout(2500)

    def riassunto():
        return s.page.evaluate(
            """() => {
              const d = JSON.parse(OPP.serializeDoc());
              return {
                name: d.name, W: d.W, H: d.H, slides: d.slides.length,
                elements: d.slides.map(s => s.elements.length),
                testi: d.slides.flatMap(s => s.elements.filter(e => e.type === 'text').map(e => e.text || '')),
                immagini: d.slides.flatMap(s => s.elements.filter(e => e.type === 'image').map(e => (e.src || '').length)),
                font: (d.fonts || []).map(f => f.family)
              };
            }"""
        )

    dopo = riassunto()
    assert dopo["name"] == salvato["name"], (dopo["name"], salvato["name"])
    assert dopo["W"] == salvato["W"] and dopo["H"] == salvato["H"]
    assert dopo["slides"] == len(salvato["slides"])
    assert dopo["elements"] == [len(sl["elements"]) for sl in salvato["slides"]]
    attese_immagini = [len(e.get("src", "")) for sl in salvato["slides"] for e in sl["elements"] if e["type"] == "image"]
    assert dopo["immagini"] == attese_immagini, (dopo["immagini"], attese_immagini)
    assert dopo["font"] == [f["family"] for f in salvato.get("fonts", [])], (dopo["font"], salvato.get("fonts"))


def t06_pannello_export(s: Session) -> None:
    _patch(s)
    s.page.click("#exportBtn")
    s.page.wait_for_selector("#expFormat")
    for sel in ("#expFormat", "#expRangeMode", "#expQuality"):
        assert s.page.locator(sel).count() == 1, f"manca {sel}"
    # PNG, solo slide 2
    s.page.select_option("#expRangeMode", "custom")
    s.page.fill("#expFrom", "2")
    s.page.fill("#expTo", "2")
    s.page.select_option("#expFormat", "png")
    s.page.evaluate("() => { window.__blobs.length = 0; }")
    s.page.click("#expRun")
    s.page.wait_for_function("() => window.__blobs.length > 0", timeout=20000)
    blob = s.page.evaluate("() => { const b = window.__blobs[window.__blobs.length - 1]; return { type: b.type, size: b.size }; }")
    assert blob["size"] > 2000, blob
    assert "png" in blob["type"], blob

    # PDF: invoca la stampa
    s.page.click("#exportBtn")
    s.page.wait_for_selector("#expFormat")
    s.page.select_option("#expFormat", "pdf")
    s.page.select_option("#expRangeMode", "all")
    s.page.click("#expRun")
    s.page.wait_for_timeout(4500)
    assert s.page.evaluate("window.__print") > 0, "la stampa PDF non è stata avviata"

    # WebM: apre la finestra di registrazione
    s.page.click("#exportBtn")
    s.page.wait_for_selector("#expFormat")
    s.page.select_option("#expFormat", "webm")
    s.page.click("#expRun")
    s.page.wait_for_selector("#webStart", timeout=5000)
    s.page.click('#modalFoot [data-close]')


def t07_modal_durante_editing(s: Session) -> None:
    el = _add_text(s, "BASE")
    x, y = s.center(el)
    s.page.mouse.dblclick(x, y)
    s.wait_editor()
    s.type_text("MODALE")
    s.page.click('#ribbon [data-command="slide.layout"]')
    s.page.wait_for_selector("#modalBody [data-layout]", timeout=3000)
    s.page.click('#modalFoot [data-close]')
    s.page.wait_for_timeout(300)
    testo = s.text_of(el) or ""
    assert "MODALE" in testo, testo
    assert s.page.evaluate("OPP.state.fileDirty") is True, "fileDirty non attivo dopo la modale"
    assert s.page.evaluate("OPP.state.editingTextId") is None


def t08_migrazione_vecchio_salvataggio(s: Session) -> None:
    vecchio = {
        "app": "OverPowerPointMega", "version": 2, "name": "Progetto vecchio",
        "W": 960, "H": 540, "current": 0, "selected": [],
        "slides": [{"id": "sl_old", "name": "Vecchia slide", "bg": {"type": "solid", "color": "#ffffff"},
                    "transition": "none", "elements": [], "notes": "", "duration": 3, "hidden": False,
                    "comments": [], "guides": {"h": [], "v": []}}],
        "brand": None, "assets": []
    }
    s.page.evaluate("(d) => localStorage.setItem('opp.autosave.v2', JSON.stringify(d))", vecchio)
    s.page.reload()
    s.page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    s.page.wait_for_timeout(600)
    assert s.page.evaluate("OPP.state.docName") == "Progetto vecchio", s.page.evaluate("OPP.state.docName")
    assert s.page.evaluate("() => localStorage.getItem('opp.autosave.v2')") is None, "il vecchio salvataggio non è stato spostato in IndexedDB"
    ok = s.page.evaluate(
        """() => new Promise(res => {
          const r = indexedDB.open('opp.db');
          r.onsuccess = () => {
            const g = r.result.transaction('autosave').objectStore('autosave').get('current');
            g.onsuccess = () => res(!!g.result && g.result.name === 'Progetto vecchio');
            g.onerror = () => res(false);
          };
          r.onerror = () => res(false);
        })"""
    )
    assert ok is True, "il progetto migrato non è in IndexedDB"


EXTRA = """
(() => {
  window.__zipInfo = async (blob) => {
    const buf = new Uint8Array(await blob.arrayBuffer());
    const dv = new DataView(buf.buffer);
    let eocd = -1;
    for (let i = buf.length - 22; i >= 0 && i > buf.length - 70000; i--) {
      if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) return null;
    const count = dv.getUint16(eocd + 10, true);
    const offset = dv.getUint32(eocd + 16, true);
    const names = []; let p = offset;
    for (let k = 0; k < count; k++) {
      if (dv.getUint32(p, true) !== 0x02014b50) break;
      const nlen = dv.getUint16(p + 28, true);
      const xlen = dv.getUint16(p + 30, true);
      const clen = dv.getUint16(p + 32, true);
      names.push(new TextDecoder().decode(buf.slice(p + 46, p + 46 + nlen)));
      p += 46 + nlen + xlen + clen;
    }
    return { count, names };
  };
  window.__opfsStub = async () => {
    window.__pickerCalls = (window.__pickerCalls || 0) + 1;
    const dir = await navigator.storage.getDirectory();
    return await dir.getFileHandle('progetto.opp.json', { create: true });
  };
  window.__opfsText = async () => {
    const dir = await navigator.storage.getDirectory();
    const h = await dir.getFileHandle('progetto.opp.json');
    return await (await h.getFile()).text();
  };
  window.showSaveFilePicker = window.__opfsStub;
  window.__ready = true;
})();
"""


def t09_handle_persistente(s: Session) -> None:
    s.page.evaluate(EXTRA)
    _add_text(s, "HANDLE")
    s.page.evaluate("() => localStorage.setItem('__prova', '1')")
    _save(s)
    s.page.wait_for_function("() => (window.__pickerCalls || 0) === 1", timeout=10000)
    s.page.wait_for_function("async () => (await window.__opfsText()).length > 100", timeout=10000)
    # rinomina per distinguere il contenuto dopo la ricarica
    s.page.fill("#docTitle", "Rinominato")
    s.page.press("#docTitle", "Enter")
    s.page.wait_for_timeout(1200)  # autosave + persistenza handle

    s.page.reload()
    s.page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    s.page.evaluate(EXTRA)
    s.page.evaluate(
        "() => { window.__pickerCalls = 0; window.showSaveFilePicker = async () => { window.__pickerCalls++; throw new Error('picker non atteso'); }; }"
    )
    _save(s)
    s.page.wait_for_function("() => (OPP.state.fileSavedAt || 0) > Date.now() - 20000", timeout=10000)
    chiamate = s.page.evaluate("window.__pickerCalls || 0")
    assert chiamate == 0, f"dopo la ricarica è stato riaperto il selettore ({chiamate} volte)"
    contenuto = s.page.evaluate("async () => await window.__opfsText()")
    assert "Rinominato" in contenuto, "il file non è stato riscritto"


def t10_nuovo_progetto_invalida_handle(s: Session) -> None:
    altro = ROOT / "tests" / "_altro.opp.json"
    altro.write_text(
        json.dumps(
            {
                "app": "OverPowerPointMega", "version": 2, "name": "Altro progetto",
                "W": 960, "H": 540, "current": 0, "selected": [],
                "slides": [{"id": "sl_altro", "name": "Slide", "bg": {"type": "solid", "color": "#ffffff"},
                            "transition": "none", "elements": [], "notes": "", "duration": 3, "hidden": False,
                            "comments": [], "guides": {"h": [], "v": []}}],
                "brand": None, "assets": [],
            }
        ),
        encoding="utf-8",
    )
    s.page.evaluate(EXTRA)
    _add_text(s, "PRIMO PROGETTO")
    _save(s)
    s.page.wait_for_function("() => (window.__pickerCalls || 0) === 1", timeout=10000)

    s.page.click('#tabs .tab[data-tab="File"]')
    with s.page.expect_file_chooser() as fc:
        s.page.click('#ribbon [data-command="file.open"]')
    fc.value.set_files(str(altro))
    s.page.wait_for_timeout(1500)
    assert s.page.evaluate("OPP.state.docName") == "Altro progetto"

    handle = s.page.evaluate(
        """() => new Promise(res => {
          const r = indexedDB.open('opp.db');
          r.onsuccess = () => {
            const g = r.result.transaction('autosave').objectStore('autosave').get('fsHandle');
            g.onsuccess = () => res(!!g.result);
            g.onerror = () => res(false);
          };
          r.onerror = () => res(false);
        })"""
    )
    assert handle is False, "l'handle del progetto precedente non è stato invalidato"

    s.page.evaluate("() => { window.__pickerCalls = 0; }")
    _save(s)
    s.page.wait_for_function("() => (window.__pickerCalls || 0) === 1", timeout=10000)


def t11_scaricare_non_e_salvare(s: Session) -> None:
    _patch(s)
    _add_text(s, "CONDIVISO")
    s.page.wait_for_timeout(1400)
    prima = s.page.evaluate("window.__badge()")
    assert "Autosalvato nel browser" in prima, prima
    s.page.click("#shareBtn")
    s.page.wait_for_selector("#shareDownload")
    s.page.click("#shareDownload")
    s.page.wait_for_timeout(400)
    dopo = s.page.evaluate("window.__badge()")
    assert "Salvato su file" not in dopo, "un download è stato segnato come salvataggio su file"
    assert s.page.evaluate("OPP.state.fileDirty") is True, "fileDirty spento dopo un semplice download"


def t12_salva_mentre_scriviamo(s: Session) -> None:
    _patch(s)
    _add_text(s, "PRIMO")
    el = s.last_text()["id"]
    s.page.click('#tabs .tab[data-tab="File"]')
    x, y = s.center(el)
    s.page.mouse.dblclick(x, y)
    s.wait_editor()
    s.type_text("AB")
    _save(s)
    s.page.wait_for_function("() => window.__saved !== null", timeout=10000)
    s.page.keyboard.type("CD")
    s.page.wait_for_timeout(200)
    testo = s.text_of(el) or ""
    assert testo == "PRIMOABCD", testo
    assert s.page.evaluate("OPP.state.fileDirty") is True, "fileDirty non attivo dopo aver scritto dopo il salvataggio"


def t13_intervalli_export(s: Session) -> None:
    _patch(s)
    s.page.evaluate(EXTRA)
    # PDF: pagine costruite solo per l'intervallo
    s.page.click("#exportBtn")
    s.page.wait_for_selector("#expFormat")
    s.page.select_option("#expFormat", "pdf")
    s.page.select_option("#expRangeMode", "custom")
    s.page.fill("#expFrom", "2")
    s.page.fill("#expTo", "3")
    s.page.click("#expRun")
    s.page.wait_for_timeout(5000)
    pagine = s.page.evaluate("window.__printPages || 0")
    assert pagine == 2, f"PDF: {pagine} pagine invece di 2"
    assert s.page.evaluate("window.__print") > 0

    # ZIP: due entry
    s.page.click("#exportBtn")
    s.page.wait_for_selector("#expFormat")
    s.page.select_option("#expFormat", "zip")
    s.page.select_option("#expRangeMode", "custom")
    s.page.fill("#expFrom", "2")
    s.page.fill("#expTo", "3")
    s.page.evaluate("() => { window.__blobs.length = 0; }")
    s.page.click("#expRun")
    s.page.wait_for_function("() => window.__blobs.length > 0", timeout=30000)
    info = s.page.evaluate("async () => await window.__zipInfo(window.__blobs[window.__blobs.length - 1])")
    assert info and info["count"] == 2, info

    # PPTX: solo le slide dell'intervallo
    s.page.click("#exportBtn")
    s.page.wait_for_selector("#expFormat")
    s.page.select_option("#expFormat", "pptx")
    s.page.select_option("#expRangeMode", "custom")
    s.page.fill("#expFrom", "2")
    s.page.fill("#expTo", "3")
    s.page.evaluate("() => { window.__blobs.length = 0; }")
    s.page.click("#expRun")
    s.page.wait_for_function("() => window.__blobs.length > 0", timeout=30000)
    info = s.page.evaluate("async () => await window.__zipInfo(window.__blobs[window.__blobs.length - 1])")
    nomi = info["names"] if info else []
    assert "ppt/slides/slide1.xml" in nomi and "ppt/slides/slide2.xml" in nomi, nomi
    assert "ppt/slides/slide3.xml" not in nomi, nomi


def _save(s: Session) -> None:
    if s.page.locator('#ribbon [data-command="file.save"]').count() == 0:
        s.page.click('#tabs .tab[data-tab="File"]')
    s.page.click('#ribbon [data-command="file.save"]')


TESTS = [
    ("01 autosalvataggio in IndexedDB", t01_autosave_indexeddb, False),
    ("02 salva su file (picker)", t02_salva_su_file, False),
    ("03 avviso modifiche non salvate", t03_avviso_modifiche, False),
    ("04 indicatore a due stati", t04_indicatore_due_stati, False),
    ("05 progetto pesante: salva, ricarica, riapri", t05_progetto_pesante_roundtrip, False),
    ("06 pannello Esporta (formato, intervallo, qualità)", t06_pannello_export, False),
    ("07 modale durante la modifica", t07_modal_durante_editing, False),
    ("08 migrazione del vecchio salvataggio", t08_migrazione_vecchio_salvataggio, False),
    ("09 handle persistente dopo la ricarica", t09_handle_persistente, False, HTTP),
    ("10 nuovo progetto invalida l'handle", t10_nuovo_progetto_invalida_handle, False, HTTP),
    ("11 scaricare non è salvare su file", t11_scaricare_non_e_salvare, False),
    ("12 salva mentre scriviamo", t12_salva_mentre_scriviamo, False),
    ("13 intervalli di export (PDF, ZIP, PPTX)", t13_intervalli_export, False),
]

if __name__ == "__main__":
    filtro = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None
    raise SystemExit(main_runner([t for t in TESTS if not filtro or filtro in t[0]]))
