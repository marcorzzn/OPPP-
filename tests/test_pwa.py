"""Fase 6 — PWA, service worker, effetti modulari.

Uso:  python tests/test_pwa.py [--solo N]
Richiede l'app servita in HTTP (mini server locale) per il service worker.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
CHAOS = ["--enable-precise-memory-info"]


def serve() -> None:
    import functools
    import http.server
    import threading

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def wait_sw(page) -> bool:
    try:
        page.wait_for_function(
            "() => navigator.serviceWorker && navigator.serviceWorker.ready.then(r => r.active && r.active.state === 'activated')",
            timeout=15000,
        )
        return True
    except Exception:
        return False


def t01_manifest_servito(ctx) -> None:
    data = json.loads(urllib.request.urlopen(BASE + "/manifest.json", timeout=10).read())
    assert data["name"] and data["start_url"] and data["display"] == "standalone", data
    assert len(data["icons"]) >= 3, data["icons"]
    for ico in data["icons"]:
        code = urllib.request.urlopen(BASE + "/" + ico["src"], timeout=10).status
        assert code == 200, ico


def t02_sw_registrato(browser) -> None:
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(BASE + "/index.html")
    page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    assert wait_sw(page), "service worker non attivato"
    n = page.evaluate("() => navigator.serviceWorker.getRegistrations().then(r => r.length)")
    assert n >= 1, n
    ctx.close()


def t03_installabile(browser) -> None:
    ctx = browser.new_context()
    page = ctx.new_page()
    page.add_init_script("window.__bip = false; window.addEventListener('beforeinstallprompt', () => { window.__bip = true; });")
    page.goto(BASE + "/index.html")
    page.wait_for_timeout(3500)
    fired = page.evaluate("() => window.__bip")
    print("   beforeinstallprompt:", "sì" if fired else "no (non verificabile in headless)")
    ctx.close()


def t04_offline(browser) -> None:
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(BASE + "/index.html")
    page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    assert wait_sw(page), "SW non attivo prima dell'offline"
    ctx.set_offline(True)
    try:
        page.reload()
        page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0", timeout=15000)
        page.click('#tabs .tab[data-tab="Effetti"]')
        page.wait_for_timeout(300)
        n = page.locator(".effect-card").count()
        assert n >= 2, n
    finally:
        ctx.set_offline(False)
        ctx.close()


def t05_scheda_effetti(browser) -> None:
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(BASE + "/index.html")
    page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    page.click('#tabs .tab[data-tab="Effetti"]')
    page.wait_for_timeout(400)
    nomi = page.evaluate("[...document.querySelectorAll('.effect-card .ec-label')].map(x => x.textContent)")
    assert "Poster Vintage" in nomi and "Splitta in pannelli" in nomi, nomi
    ctx.close()


def t06_iframe(browser) -> None:
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(BASE + "/index.html")
    page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    page.click('#tabs .tab[data-tab="Effetti"]')
    page.click('.effect-card[data-effect-open="poster-vintage"]')
    page.wait_for_selector("#effectFrame")
    page.wait_for_timeout(1200)
    src = page.evaluate("() => document.getElementById('effectFrame').getAttribute('src')")
    assert src == "effects/poster-vintage.html?embed=1", src
    frames = [f for f in page.frames if "poster-vintage" in f.url]
    assert frames, "iframe non caricato"
    assert frames[0].evaluate("() => document.body.classList.contains('embed')"), "classe embed assente"
    assert not frames[0].locator("h1").is_visible(), "h1 visibile in embed"
    ctx.close()


def t07_invio_risultato(browser) -> None:
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(BASE + "/index.html")
    page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    prima = page.evaluate("OPP.currentSlide().elements.length")
    page.click('#tabs .tab[data-tab="Effetti"]')
    page.click('.effect-card[data-effect-open="poster-vintage"]')
    page.wait_for_selector("#effectFrame")
    page.wait_for_timeout(800)
    fr = page.frame_locator("#effectFrame")
    fr.locator("#file").set_input_files(str(ROOT / "icons" / "icon-192.png"))
    fr.locator('button:has-text("Invia a OPP")').wait_for(timeout=25000)
    fr.locator('button:has-text("Invia a OPP")').click()
    page.wait_for_timeout(1500)
    dopo = page.evaluate("OPP.currentSlide().elements.length")
    tipi = page.evaluate("OPP.currentSlide().elements.map(e => e.type)")
    assert dopo == prima + 1 and tipi[-1] == "image", (prima, dopo, tipi)
    assert not page.evaluate("document.getElementById('modalBg').classList.contains('open')")
    assert "Effetto" in page.evaluate("OPP.state.historyLabels.slice(-1)[0]")
    ctx.close()


def t08_standalone(browser) -> None:
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto((ROOT / "effects" / "poster-vintage.html").as_uri())
    page.wait_for_timeout(600)
    assert page.locator("h1").is_visible(), "h1 non visibile standalone"
    assert not page.evaluate("document.body.classList.contains('embed')")
    assert page.locator('button:has-text("Invia a OPP")').count() == 0
    assert page.locator('button:has-text("Scarica PNG")').count() == 0  # appare dopo un'immagine
    ctx.close()


def t09_fallback_catalogo(browser) -> None:
    ctx = browser.new_context(service_workers="block")
    page = ctx.new_page()
    page.route("**/effects/manifest.json", lambda route: route.abort())
    page.goto(BASE + "/index.html")
    page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    page.click('#tabs .tab[data-tab="Effetti"]')
    page.wait_for_timeout(600)
    testo = page.evaluate("() => document.querySelector('#ribbon').textContent")
    assert "Catalogo non disponibile" in testo, testo[:200]
    ctx.close()


def t10_regressioni(browser) -> None:
    env = dict(**__import__("os").environ)
    env["TEMP"] = str(ROOT / ".tmp")
    env["TMP"] = str(ROOT / ".tmp")
    env["OPP_FILE"] = "index.html"
    for suite in ("test_text.py", "test_save.py", "test_commands.py", "test_density.py", "test_phase4.py"):
        r = subprocess.run([sys.executable, str(ROOT / "tests" / suite)], cwd=str(ROOT), env=env, capture_output=True, text=True)
        tail = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else ""
        print(f"   {suite}: exit {r.returncode} — {tail}")
        assert r.returncode == 0, f"{suite} fallita"


TESTS = [
    ("01 manifest servito", t01_manifest_servito, False),
    ("02 service worker registrato", t02_sw_registrato, True),
    ("03 installabilità (best effort)", t03_installabile, True),
    ("04 offline funziona", t04_offline, True),
    ("05 scheda Effetti", t05_scheda_effetti, True),
    ("06 effetto in iframe", t06_iframe, True),
    ("07 invio risultato a OPP", t07_invio_risultato, True),
    ("08 effetto standalone", t08_standalone, True),
    ("09 fallback catalogo", t09_fallback_catalogo, True),
    ("10 regressioni 45 test", t10_regressioni, True),
]

if __name__ == "__main__":
    filtro = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None
    serve()
    time.sleep(0.4)
    risultati = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True, args=CHAOS)
        for nome, fn, needs_browser in TESTS:
            if filtro and filtro not in nome:
                continue
            try:
                if nome.startswith("01"):
                    fn(None)
                else:
                    fn(browser)
                print(f"{nome:34s} OK")
                risultati.append(True)
            except Exception as e:
                print(f"{nome:34s} FAIL {e}")
                risultati.append(False)
        browser.close()
    print(f"\n{sum(risultati)} test superati su {len(risultati)}")
    raise SystemExit(0 if all(risultati) else 1)
