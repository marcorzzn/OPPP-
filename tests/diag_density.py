"""Misura la densità del ribbon: pulsanti per scheda in semplice e completa."""
import json

from playwright.sync_api import sync_playwright

URL = "file:///C:/Progetti/OPP/index.html"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("pageerror", lambda e: print("PAGEERROR", e))
    pg.goto(URL)
    pg.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    out = {"densita": pg.evaluate("OPP.state.settings.uiDensity"), "schede": {}}
    tabs = pg.evaluate("[...document.querySelectorAll('#tabs .tab')].map(t=>t.dataset.tab)")
    for mode in ("semplice", "completa"):
        if pg.evaluate("OPP.state.settings.uiDensity") != mode:
            pg.evaluate("() => OPP.runCommand('view.density', {})")
        out["schede"][mode] = {}
        for tab in tabs:
            pg.click(f'#tabs .tab[data-tab="{tab}"]')
            pg.wait_for_timeout(60)
            out["schede"][mode][tab] = pg.locator("#ribbon button").count()
    out["essenziali_home"] = pg.evaluate(
        "() => { OPP.runCommand('view.density', {}); return null; }"
    )
    pg.click('#tabs .tab[data-tab="Home"]')
    pg.wait_for_timeout(80)
    out["home_cmds"] = pg.evaluate(
        "[...document.querySelectorAll('#ribbon [data-command]')].map(b=>b.dataset.command)"
    )
    out["modo_finale"] = pg.evaluate("OPP.state.settings.uiDensity")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    b.close()
