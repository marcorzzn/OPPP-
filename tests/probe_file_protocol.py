"""Prova su file:// (Chrome visibile): salvataggio reale dal picker e persistenza handle.

Automatizza il dialogo di Windows con SendKeys (nessuno stub). Misura:
 1. il picker si apre su file://;
 2. il file viene scritto;
 3. l'handle entra in IndexedDB;
 4. dopo la ricarica l'handle è ancora lì e «Salva» riscrive senza dialogo.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / "index.html").as_uri()
TARGET = ROOT / "tests" / "_filesave_probe.opp.json"
if TARGET.exists():
    TARGET.unlink()


def keys(seq: str) -> None:
    safe = seq.replace("+", "{+}").replace("^", "{^}").replace("%", "{%}").replace("~", "{~}")
    script = f"$w = New-Object -ComObject WScript.Shell; $w.SendKeys('{safe}')"
    subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, timeout=30)


def read_handle(page) -> str:
    return page.evaluate(
        """() => new Promise(res => {
          const r = indexedDB.open('opp.db');
          r.onsuccess = () => {
            if (!r.result.objectStoreNames.contains('autosave')) return res('no-store');
            const g = r.result.transaction('autosave').objectStore('autosave').get('fsHandle');
            g.onsuccess = () => { const h = g.result; res(h ? typeof h.createWritable : 'assente'); };
            g.onerror = () => res('errore');
          };
          r.onerror = () => res('open-fail');
        })"""
    )


out: dict = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False, args=["--no-first-run", "--no-default-browser-check"])
    page = b.new_page(viewport={"width": 1280, "height": 820})
    page.goto(URL)
    page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    out["picker"] = page.evaluate("() => typeof window.showSaveFilePicker")

    page.click('#tabs .tab[data-tab="File"]')
    page.click('#ribbon [data-command="file.save"]')
    time.sleep(2)
    keys(str(TARGET))
    time.sleep(0.4)
    keys("{ENTER}")
    try:
        page.wait_for_function("() => (OPP.state.fileSavedAt || 0) > 0", timeout=20000)
        out["savedOnce"] = True
    except Exception:
        out["savedOnce"] = False
    out["fileExists"] = TARGET.exists()
    if TARGET.exists():
        out["fileBytes"] = TARGET.stat().st_size
        out["hasName"] = "Benvenuto" in TARGET.read_text(encoding="utf-8")[:4000]
    out["handleInDb"] = read_handle(page)

    page.fill("#docTitle", "Seconda scrittura")
    page.press("#docTitle", "Enter")
    page.wait_for_timeout(400)
    page.reload()
    page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    out["handleAfterReload"] = read_handle(page)
    page.click('#tabs .tab[data-tab="File"]')
    page.click('#ribbon [data-command="file.save"]')
    try:
        page.wait_for_function("() => (OPP.state.fileSavedAt || 0) > Date.now() - 15000", timeout=8000)
        out["savedAfterReloadWithoutDialog"] = True
    except Exception:
        out["savedAfterReloadWithoutDialog"] = False
    if TARGET.exists():
        out["containsNewName"] = "Seconda scrittura" in TARGET.read_text(encoding="utf-8")
    b.close()

print(json.dumps(out, ensure_ascii=False, indent=2))
