"""Verifica post-deploy su GitHub Pages: errori, PWA, scheda Effetti, iframe."""
from playwright.sync_api import sync_playwright

URL = "https://marcorzzn.github.io/OverPowerPoint/"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    ctx = b.new_context()
    pg = ctx.new_page()
    errori, console = [], []
    pg.on("pageerror", lambda e: errori.append(str(e)))
    pg.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="load")
    pg.wait_for_function("() => window.OPP && OPP.state.slides.length > 0", timeout=20000)
    print("app avviata; schede:", pg.evaluate("OPP.state.slides.length"))
    try:
        pg.wait_for_function(
            "() => navigator.serviceWorker && navigator.serviceWorker.ready.then(r => r.active && r.active.state === 'activated')",
            timeout=15000,
        )
        print("service worker: activated")
    except Exception:
        print("service worker: NON attivato")
    print("manifest link:", pg.evaluate("() => document.querySelector('link[rel=manifest]').href"))
    pg.click('#tabs .tab[data-tab="Effetti"]')
    pg.wait_for_timeout(600)
    print("card effet:", pg.locator(".effect-card").count())
    pg.click('.effect-card[data-effect-open="poster-vintage"]')
    pg.wait_for_selector("#effectFrame")
    pg.wait_for_timeout(2500)
    frames = [f for f in pg.frames if "poster-vintage" in f.url]
    print("iframe caricato:", bool(frames), "| embed:", frames[0].evaluate("() => document.body.classList.contains('embed')") if frames else None)
    pg.keyboard.press("Escape")
    print("pageerror:", errori)
    print("console error:", console[:5])
    b.close()
