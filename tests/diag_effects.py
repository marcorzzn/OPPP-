"""Verifica veloce della scheda Effetti e dell'iframe embed (file://)."""
from playwright.sync_api import sync_playwright

URL = "file:///C:/Progetti/OPP/index.html"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1400, "height": 900})
    pg.on("pageerror", lambda e: print("PAGEERROR:", e))
    pg.goto(URL)
    pg.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    print("tab Effetti:", pg.locator('#tabs .tab[data-tab="Effetti"]').count())
    pg.click('#tabs .tab[data-tab="Effetti"]')
    pg.wait_for_timeout(300)
    print("card:", pg.locator(".effect-card").count())
    print("nomi:", pg.evaluate("[...document.querySelectorAll('.effect-card .ec-label')].map(x=>x.textContent)"))
    pg.click('.effect-card[data-effect-open="poster-vintage"]')
    pg.wait_for_selector("#effectFrame")
    pg.wait_for_timeout(1500)
    fr = pg.frame_locator("#effectFrame")
    print("embed class:", pg.frames[1].evaluate("() => document.body.classList.contains('embed')") if len(pg.frames) > 1 else "no-frame")
    print("h1 visibile:", fr.locator("h1").is_visible() if fr.locator("h1").count() else "assente")
    print("input file presente:", fr.locator("#file").count())
    pg.keyboard.press("Escape")
    b.close()
