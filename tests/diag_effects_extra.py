"""Verifica extra: template standalone e split-image in embed."""
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = str(ROOT / "icons" / "icon-192.png")

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    # template standalone
    pg = b.new_page()
    pg.on("pageerror", lambda e: print("TEMPLATE PAGEERROR:", e))
    pg.goto((ROOT / "effects" / "_template.html").as_uri())
    pg.set_input_files("#file", IMG)
    pg.wait_for_timeout(600)
    px = pg.evaluate("() => { const c=document.getElementById('canvas'); const d=c.getContext('2d').getImageData(0,0,1,1).data; return [d[0],d[1],d[2],d[3]] }")
    print("template pixel in alto a sinistra:", px, "| canvas:", pg.evaluate("() => [document.getElementById('canvas').width, document.getElementById('canvas').height]"))
    # split-image dentro OPP via http (serve il SW solo per coerenza, qui non serve)
    ctx = b.new_context()
    pg2 = ctx.new_page()
    errs = []
    pg2.on("pageerror", lambda e: errs.append(str(e)))
    pg2.goto((ROOT / "index.html").as_uri())
    pg2.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    pg2.click('#tabs .tab[data-tab="Effetti"]')
    pg2.click('.effect-card[data-effect-open="split-image"]')
    pg2.wait_for_selector("#effectFrame")
    pg2.wait_for_timeout(800)
    fr = pg2.frame_locator("#effectFrame")
    fr.locator("#fileInput").set_input_files(IMG)
    fr.locator('button:has-text("Invia a OPP")').first.wait_for(timeout=15000)
    print("split embed: pulsanti Invia =", fr.locator('button:has-text("Invia a OPP")').count(), "| errori:", errs)
    b.close()

