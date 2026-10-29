"""Cattura la lista dei comandi del ribbon (modalità completa) come riferimento.

Serve al refactoring delle priorità: dopo il refactoring la lista in modalità
completa deve essere identica a questa.
"""
import json
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / "index.html").as_uri()
OUT = ROOT / "tests" / "_ribbon_baseline.json"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(URL)
    pg.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    if pg.evaluate("OPP.state.settings.uiDensity") == "semplice":
        pg.evaluate("() => OPP.runCommand('view.density', {})")
    pg.wait_for_timeout(150)
    assert pg.evaluate("OPP.state.settings.uiDensity") == "completa"
    tabs = pg.evaluate("[...document.querySelectorAll('#tabs .tab')].map(t=>t.dataset.tab)")
    data = {}
    for tab in tabs:
        pg.click(f'#tabs .tab[data-tab="{tab}"]')
        pg.wait_for_timeout(50)
        data[tab] = {
            "commands": sorted(pg.evaluate(
                "[...document.querySelectorAll('#ribbon [data-command]')].map(b => b.dataset.command)"
            )),
            "tools": sorted(pg.evaluate(
                "[...document.querySelectorAll('#ribbon [data-tool]')].map(b => b.dataset.tool + (b.dataset.kind ? '/' + b.dataset.kind : ''))"
            )),
        }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("riferimento scritto:", OUT, "schede:", len(data))
    b.close()
