"""Avvio rapido: controlla errori di pagina e stato iniziale."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page()
    pg.on("pageerror", lambda e: print("PAGEERROR:", e))
    pg.on("console", lambda m: print("CONSOLE", m.type, m.text) if m.type == "error" else None)
    pg.goto("file:///C:/Progetti/OPP/index.html")
    pg.wait_for_timeout(1200)
    print("OPP:", pg.evaluate("typeof window.OPP"))
    print("slides:", pg.evaluate("window.OPP ? OPP.state.slides.length : -1"))
    print("densita:", pg.evaluate("OPP.state.settings.uiDensity"))
    print("pulsanti Home:", pg.evaluate("document.querySelectorAll('#ribbon button').length"))
    b.close()
