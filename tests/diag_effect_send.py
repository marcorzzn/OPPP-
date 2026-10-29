"""Verifica il flusso completo: effetto → Invia a OPP → imageElement nella slide."""
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "file:///C:/Progetti/OPP/index.html"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1400, "height": 900})
    pg.on("pageerror", lambda e: print("PAGEERROR:", e))
    pg.goto(URL)
    pg.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    prima = pg.evaluate("OPP.currentSlide().elements.length")
    pg.click('#tabs .tab[data-tab="Effetti"]')
    pg.click('.effect-card[data-effect-open="poster-vintage"]')
    pg.wait_for_selector("#effectFrame")
    pg.wait_for_timeout(800)
    fr = pg.frame_locator("#effectFrame")
    fr.locator("#file").set_input_files(str(ROOT / "icons" / "icon-192.png"))
    fr.locator('button:has-text("Invia a OPP")').wait_for(timeout=20000)
    fr.locator('button:has-text("Invia a OPP")').click()
    pg.wait_for_timeout(1500)
    dopo = pg.evaluate("OPP.currentSlide().elements.length")
    tipi = pg.evaluate("OPP.currentSlide().elements.map(e => e.type)")
    print("elementi prima/dopo:", prima, dopo, "tipi:", tipi)
    print("modale aperta:", pg.evaluate("document.getElementById('modalBg').classList.contains('open')"))
    print("commit label:", pg.evaluate("OPP.state.historyLabels.slice(-1)[0]"))
    b.close()
