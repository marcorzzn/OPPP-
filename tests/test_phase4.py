"""Fase 4 — robustezza: priorità ribbon (già in test_density), iniezione, DOM mirati, cronologia.

Uso:  python tests/test_phase4.py [--solo NOME]
"""
from __future__ import annotations

import json
import pathlib
import sys

from harness import Session, launch, main_runner

ROOT = pathlib.Path(__file__).resolve().parent.parent
XSS = ROOT / "tests" / "_xss_probe.opp.json"

STUB = """
(() => {
  window.__nextFile = null;
  HTMLInputElement.prototype.__origClick = HTMLInputElement.prototype.click;
  HTMLInputElement.prototype.click = function(){
    if (this.type === 'file' && window.__nextFile) {
      const f = window.__nextFile; window.__nextFile = null;
      const dt = new DataTransfer(); dt.items.add(f); this.files = dt.files;
      this.dispatchEvent(new Event('change')); return;
    }
    return HTMLElement.prototype.click.call(this);
  };
  HTMLAnchorElement.prototype.click = function(){};
  window.print = () => {};
  window.__bigPng = () => new Promise(res => {
    const c = document.createElement('canvas'); c.width = 1200; c.height = 900;
    const ctx = c.getContext('2d'); const img = ctx.createImageData(c.width, c.height);
    for (let i = 0; i < img.data.length; i += 4) {
      const v = (Math.random() * 255) | 0;
      img.data[i] = v; img.data[i + 1] = 255 - v; img.data[i + 2] = v; img.data[i + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    c.toBlob(b => res(new File([b], 'big.png', { type: 'image/png' })), 'image/png');
  });
})();
"""


def t01_click_non_ridisegna(s: Session) -> None:
    s.page.evaluate(STUB)
    s.add_text_button()
    s.wait_editor()
    s.exit_editor()
    el = s.last_text()["id"]
    x, y = s.center(el)
    s.page.mouse.click(x, y)
    s.page.wait_for_timeout(150)
    s.page.evaluate("() => { window.__node = document.querySelector('#elementsLayer .el'); }")
    s.page.mouse.click(x, y)
    s.page.wait_for_timeout(250)
    assert s.page.evaluate("() => !!(window.__node && window.__node.isConnected)"), "il clic ha sostituito il nodo DOM"


def t02_cronologia_a_budget(s: Session) -> None:
    s.page.evaluate(STUB)
    s.page.click('#tabs .tab[data-tab="Inserisci"]')
    s.page.evaluate("async () => { window.__nextFile = await window.__bigPng(); }")
    s.page.click('#ribbon [data-command="insert.image"]')
    s.page.wait_for_function("() => OPP.currentSlide().elements.some(e => e.type === 'image')", timeout=8000)
    for _ in range(12):
        s.page.evaluate("() => OPP.runCommand('insert.text', {})")
        s.page.wait_for_timeout(60)
    stats = s.page.evaluate(
        """() => {
          const h = OPP.state.history.map(s => s.length);
          return { n: h.length, tot: h.reduce((a, b) => a + b, 0), max: Math.max(...h) };
        }"""
    )
    limite = 24 * 1024 * 1024
    assert stats["tot"] <= limite + stats["max"], stats
    assert stats["n"] < 14, stats
    prima = s.page.evaluate("OPP.currentSlide().elements.length")
    s.page.evaluate("() => OPP.runCommand('edit.undo', {})")
    s.page.wait_for_timeout(150)
    dopo = s.page.evaluate("OPP.currentSlide().elements.length")
    assert dopo == prima - 1, (prima, dopo)


def t03_iniezione_da_progetto(s: Session) -> None:
    payload = '<img src=x onerror="window.__xss=1">'
    doc = {
        "app": "OverPowerPointMega", "version": 2, "name": "Progetto " + payload,
        "W": 960, "H": 540, "current": 0, "selected": [],
        "slides": [{
            "id": "sl_x", "name": payload, "notes": payload,
            "bg": {"type": "solid", "color": "#ffffff"}, "transition": "none",
            "hidden": False, "duration": 3,
            "comments": [{"id": "c1", "x": 10, "y": 10, "text": payload, "author": payload, "resolved": False, "replies": []}],
            "elements": [
                {"id": "e1", "type": "text", "text": payload, "name": payload, "x": 40, "y": 40, "w": 300, "h": 80,
                 "font": "Calibri", "fontSize": 24, "color": "#111111", "fill": "#111111", "align": "left", "valign": "top"},
                {"id": "e2", "type": "image", "src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PzWvWQAAAABJRU5ErkJggg==",
                 "name": payload, "alt": payload, "x": 40, "y": 200, "w": 60, "h": 60},
                {"id": "e3", "type": "audio", "src": "data:audio/wav;base64,UklGRiQAAABXQVZF", "mediaName": payload, "name": payload,
                 "x": 400, "y": 300, "w": 200, "h": 80}
            ]
        }],
        "brand": {"name": payload, "colors": ["#112233", "#445566", "#778899", "#ffffff"], "fonts": ["Calibri", "Georgia"], "logo": None},
        "assets": [], "fonts": [{"id": "f1", "family": payload, "source": "file", "faces": []}]
    }
    XSS.write_text(json.dumps(doc), encoding="utf-8")
    s.page.click('#tabs .tab[data-tab="File"]')
    with s.page.expect_file_chooser() as fc:
        s.page.click('#ribbon [data-command="file.open"]')
    fc.value.set_files(str(XSS))
    s.page.wait_for_timeout(1500)
    assert s.page.evaluate("() => window.__xss === undefined"), "payload eseguito durante il caricamento"
    # testo mostrato letteralmente sul palco
    palco = s.page.evaluate("() => { const b = document.querySelector('#elementsLayer .txt-block'); return b ? b.textContent : ''; }")
    assert "<img" in palco, palco
    # nessun img iniettata nei livelli o nei commenti
    assert s.page.evaluate("() => document.querySelectorAll('#layersList img').length") == 0
    s.page.evaluate("() => OPP.runCommand('comment.list', {})")
    s.page.wait_for_timeout(300)
    assert s.page.evaluate("() => document.querySelectorAll('#modalBody img').length") == 0
    s.page.click('#modalFoot [data-close]')
    # apri anche le risorse/brand se presenti
    s.page.evaluate("() => OPP.runCommand('panel.assets', {})")
    s.page.wait_for_timeout(200)
    assert s.page.evaluate("() => document.querySelectorAll('#assetsBody img').length") == 0
    # brand kit
    s.page.evaluate("() => OPP.runCommand('brand.open', {})")
    s.page.wait_for_timeout(400)
    assert s.page.evaluate("() => document.querySelectorAll('#modalBody script, #modalBody img').length") == 0
    s.page.click('#modalFoot [data-close]')
    # livelli: nessun markup dal nome slide
    assert s.page.evaluate("() => document.querySelectorAll('#layersList svg, #layersList img').length") == 0
    # export HTML: payload non esce dal JSON incorporato
    s.page.evaluate(
        """() => {
          window.__blob = null;
          const orig = URL.createObjectURL.bind(URL);
          URL.createObjectURL = b => { window.__blob = b; return orig(b); };
          window.open = () => null;
        }"""
    )
    s.page.evaluate("() => OPP.runCommand('export.html', {})")
    s.page.wait_for_timeout(1200)
    html_export = s.page.evaluate("async () => window.__blob ? await window.__blob.text() : ''")
    assert html_export, "export HTML non prodotto"
    assert "<img src=x onerror" not in html_export, "payload grezzo nell'HTML esportato"
    assert "<script>alert" not in html_export, "script grezzo nell'HTML esportato"


def t04_tip_mobile_una_tantum(s: Session) -> None:
    s.page.wait_for_function(
        "() => document.querySelector('#toastWrap') && document.querySelector('#toastWrap').textContent.includes('Tieni premuto')",
        timeout=12000,
    )
    assert s.page.evaluate("OPP.state.settings.touchTipSeen") is True
    s.page.reload()
    s.page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    # dopo la ricarica il suggerimento non deve più comparire
    try:
        s.page.wait_for_function(
            "() => document.querySelector('#toastWrap') && document.querySelector('#toastWrap').textContent.includes('Tieni premuto')",
            timeout=7000,
        )
        raise AssertionError("il suggerimento touch è ricomparso dopo la ricarica")
    except Exception as e:
        if isinstance(e, AssertionError):
            raise


def t05_export_html_sicuro(s: Session) -> None:
    """Apre davvero l'HTML esportato in un contesto nuovo e verifica che il payload non esegua."""
    payload = '<img src=x onerror="window.__xss=1"><script>window.__xss2=1</script>'
    s.page.evaluate("(p) => { OPP.currentSlide().elements[0].text = p; }", payload)
    s.page.evaluate("() => OPP.renderAll()")
    s.page.evaluate(
        """() => {
          window.__blob = null;
          const orig = URL.createObjectURL.bind(URL);
          URL.createObjectURL = b => { window.__blob = b; return orig(b); };
          window.open = () => null;
        }"""
    )
    s.page.evaluate("() => OPP.runCommand('export.html', {})")
    s.page.wait_for_function("() => !!window.__blob", timeout=8000)
    b64 = s.page.evaluate(
        "async () => { const buf = new Uint8Array(await window.__blob.arrayBuffer()); let s=''; for (const b of buf) s += String.fromCharCode(b); return btoa(s); }"
    )
    import base64
    out = ROOT / "tests" / "_export_probe.html"
    out.write_bytes(base64.b64decode(b64))
    browser = s.context.browser
    ctx = browser.new_context()
    page = ctx.new_page()
    errori: list[str] = []
    page.on("pageerror", lambda e: errori.append(str(e)))
    page.goto(out.as_uri())
    page.wait_for_timeout(2000)
    assert page.evaluate("() => window.__xss") is None, "payload eseguito nell'HTML esportato"
    assert page.evaluate("() => window.__xss2") is None, "script eseguito nell'HTML esportato"
    assert errori == [], errori
    ctx.close()


def t06_memoria_cronologia(s: Session) -> None:
    """28 commit con immagine grande, GC forzato: oltre il tetto la memoria non cresce."""
    s.page.evaluate(STUB)
    s.page.click('#tabs .tab[data-tab="Inserisci"]')
    s.page.evaluate("async () => { window.__nextFile = await window.__bigPng(); }")
    s.page.click('#ribbon [data-command="insert.image"]')
    s.page.wait_for_function("() => OPP.currentSlide().elements.some(e => e.type === 'image')", timeout=10000)
    misure = {}
    for i in range(28):
        s.page.evaluate("() => OPP.runCommand('insert.text', {})")
        s.page.wait_for_timeout(90)
        if i + 1 in (10, 20, 28):
            s.page.evaluate("() => window.gc && window.gc()")
            misure[i + 1] = s.page.evaluate("() => performance.memory ? performance.memory.usedJSHeapSize / 1048576 : -1")
    lunghezza = s.page.evaluate("OPP.state.history.length")
    assert lunghezza <= 28, lunghezza
    assert misure[10] <= misure[20] * 1.2, misure
    assert misure[20] <= misure[28] * 1.2, misure
    assert misure[28] < 250, misure
    print("   memoria MB a 10/20/28 commit (GC forzato):", [round(m, 1) for m in misure.values()], "stati:", lunghezza)


TESTS = [
    ("01 clic non ridisegna il palco", t01_click_non_ridisegna, False),
    ("02 cronologia con limite di memoria", t02_cronologia_a_budget, False),
    ("03 nessuna iniezione da progetto importato", t03_iniezione_da_progetto, False),
    ("04 suggerimento touch una tantum", t04_tip_mobile_una_tantum, True),
    ("05 export HTML sicuro aperto nel browser", t05_export_html_sicuro, False),
    ("06 memoria piatta con 28 commit (GC)", t06_memoria_cronologia, False),
]

if __name__ == "__main__":
    filtro = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None
    raise SystemExit(main_runner([t for t in TESTS if not filtro or filtro in t[0]]))
