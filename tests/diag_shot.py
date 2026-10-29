"""Cattura screenshot delle due densità (desktop) e della modalità mobile."""
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / "index.html").as_uri()
OUT = ROOT / "docs/audit"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    pg.goto(URL)
    pg.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    pg.screenshot(path=str(OUT / "density-simple.png"))
    pg.evaluate("() => OPP.runCommand('view.density', {})")
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / "density-full.png"))
    ctx.close()

    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    pg = ctx.new_page()
    pg.goto(URL)
    pg.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    pg.screenshot(path=str(OUT / "density-mobile.png"))
    ctx.close()
    b.close()
print("screenshot in", OUT)
