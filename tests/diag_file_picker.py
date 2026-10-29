"""Diagnostica mirata su file://: showSaveFilePicker apre il dialogo o fallisce?

Apre Chrome visibile, aggiunge un pulsante che chiama l'API dentro un gesto
utente e registra esito o errore. Stampa i titoli delle finestre per capire se
il dialogo esiste davvero.
"""
from __future__ import annotations

import ctypes
import json
import pathlib
import subprocess
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / "index.html").as_uri()


def titles() -> list[str]:
    out: list[str] = []
    u = ctypes.windll.user32

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, _):
        n = u.GetWindowTextLengthW(h)
        if n:
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            out.append(b.value)
        return True

    u.EnumWindows(cb, 0)
    return out


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False, args=["--no-first-run"])
    page = b.new_page(viewport={"width": 1100, "height": 760})
    page.goto(URL)
    page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    print("finestre iniziali con 'chrome':", [t for t in titles() if "chrome" in t.lower()][:5])

    page.evaluate(
        """() => {
          window.__r = 'in-attesa';
          const btn = document.createElement('button');
          btn.id = 'probe-picker';
          btn.textContent = 'prova picker';
          btn.style.cssText = 'position:fixed;left:10px;top:10px;z-index:99999;padding:8px';
          btn.onclick = async () => {
            try { const h = await window.showSaveFilePicker({ suggestedName: 'prova.txt' }); window.__r = 'ok:' + h.name; }
            catch (e) { window.__r = 'err:' + e.name + ':' + (e.message || ''); }
          };
          document.body.appendChild(btn);
        }"""
    )
    page.click("#probe-picker")
    time.sleep(2)
    print("titoli dopo clic:", [t for t in titles() if t.strip()][:25])
    print("esito:", page.evaluate("window.__r"))
    # chiude un eventuale dialogo
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "$w = New-Object -ComObject WScript.Shell; $w.SendKeys('{ESC}')"],
        capture_output=True, timeout=20,
    )
    time.sleep(1)
    print("esito dopo ESC:", page.evaluate("window.__r"))
    b.close()
