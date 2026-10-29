"""Conta le mutazioni del palco per 10 azioni comuni (proxy dei render completi)."""
import json

from playwright.sync_api import sync_playwright

URL = "file:///C:/Progetti/OPP/index.html"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(URL)
    pg.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    pg.evaluate(
        """() => {
          window.__muts = { stage: 0, layers: 0 };
          const stage = document.getElementById('elementsLayer');
          const layers = document.getElementById('layersList');
          new MutationObserver(ms => { window.__muts.stage += ms.length; })
            .observe(stage, { childList: true, subtree: true, attributes: true });
          new MutationObserver(ms => { window.__muts.layers += ms.length; })
            .observe(layers, { childList: true, subtree: true, attributes: true });
          window.__mark = () => { const m = { ...window.__muts }; window.__muts.stage = 0; window.__muts.layers = 0; return m; };
        }"""
    )

    def step(name, fn):
        pg.wait_for_timeout(120)
        pg.evaluate("() => window.__mark()")
        fn()
        pg.wait_for_timeout(220)
        m = pg.evaluate("() => window.__mark()")
        print(f"{name:34s} palco={m['stage']:4d} livelli={m['layers']:4d}")

    sel = pg.evaluate("() => OPP.currentSlide().elements[0] && OPP.currentSlide().elements[0].id")
    box = pg.evaluate(
        "(id) => { const n = document.querySelector('#elementsLayer .el[data-el-id=\"' + id + '\"]'); if(!n) return [400,300]; const r = n.getBoundingClientRect(); return [r.x + r.width/2, r.y + r.height/2]; }",
        sel,
    ) if sel else [400, 300]

    step("clic su un elemento", lambda: pg.mouse.click(box[0], box[1]))
    step("clic sul vuoto", lambda: pg.mouse.click(600, 700))
    step("cambio slide (2)", lambda: pg.click('#slidesList .slide-thumb[data-slide="1"]'))
    step("torna slide 1", lambda: pg.click('#slidesList .slide-thumb[data-slide="0"]'))
    step("inserisci testo (ribbon)", lambda: pg.click('#ribbon [data-command="insert.text"]'))
    pg.keyboard.type("PROVA")
    step("esci dall'editor (Ctrl+Invio)", lambda: pg.keyboard.press("Control+Enter"))
    step("annulla", lambda: pg.evaluate("() => OPP.runCommand('edit.undo', {})"))
    step("ripeti", lambda: pg.evaluate("() => OPP.runCommand('edit.redo', {})"))
    step("adatta allo schermo", lambda: pg.evaluate("() => OPP.runCommand('view.zoomFit', {})"))
    step("griglia on/off", lambda: pg.evaluate("() => OPP.runCommand('view.grid', {})"))
    b.close()
