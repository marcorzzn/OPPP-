"""Piccola libreria di supporto per i test Playwright di OverPowerPoint.

Contiene solo ciò che serve ai test: apertura dell'app in Chrome headless,
lettura del modello, coordinate degli elementi sul palco e raccolta errori.
"""
from __future__ import annotations

import os
import pathlib
from playwright.sync_api import Page, Browser, sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
_TARGET = os.environ.get("OPP_FILE", "index.html")
FILE = pathlib.Path(_TARGET) if pathlib.Path(_TARGET).is_absolute() else ROOT / _TARGET
URL = FILE.as_uri()


def start_http(port: int = 8799) -> str:
    """Serve la cartella su HTTP (serve per OPFS nei test dell'handle)."""
    import functools
    import http.server
    import threading

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}/" + FILE.name

STAGE_EL = '#elementsLayer .el[data-el-id="{id}"]'
EDITOR = '.txt-block[contenteditable="true"]'


class Session:
    """Una pagina aperta sull'app, con gli errori raccolti."""

    def __init__(self, browser: Browser, mobile: bool = False, url: str | None = None):
        if mobile:
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                has_touch=True,
                is_mobile=True,
                device_scale_factor=2,
            )
        else:
            context = browser.new_context(viewport={"width": 1440, "height": 900})
        self.context = context
        self.url = url or URL
        self.page = context.new_page()
        self.errors: list[str] = []
        self.page.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))
        self.page.on(
            "console",
            lambda m: self.errors.append(f"console.{m.type}: {m.text}")
            if m.type == "error"
            else None,
        )
        self.page.goto(self.url)
        self.page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")

    # ---- modello ----
    def elements(self) -> list[dict]:
        return self.page.evaluate(
            "() => OPP.currentSlide().elements.map(e => ({id:e.id, type:e.type, text:e.text, x:e.x, y:e.y}))"
        )

    def last_text(self) -> dict:
        candidates = [e for e in self.elements() if e["type"] == "text"]
        assert candidates, "nessun elemento di testo nella slide"
        return candidates[-1]

    def text_of(self, el_id: str) -> str | None:
        return self.page.evaluate(
            "(id) => { const e = OPP.currentSlide().elements.find(x => x.id === id); return e ? (e.text || '') : null; }",
            el_id,
        )

    def add_text_button(self) -> None:
        self.page.click('#ribbon [data-command="insert.text"]')

    def add_text_with_tool(self) -> None:
        """Strumento Testo dalla scorciatoia T, poi clic al centro della slide."""
        self.page.keyboard.press("t")
        box = self.page.locator("#slideSurface").bounding_box()
        self.page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    # ---- palco ----
    def stage_el(self, el_id: str):
        return self.page.locator(STAGE_EL.format(id=el_id))

    def center(self, el_id: str) -> tuple[float, float]:
        box = self.stage_el(el_id).bounding_box()
        assert box, f"elemento {el_id} non visibile sul palco"
        return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

    def editor_is_active_in_stage(self) -> bool:
        return self.page.evaluate(
            """() => {
              const a = document.activeElement;
              return !!a && a.classList.contains('txt-block') && !!a.closest('#elementsLayer')
                     && !a.closest('#slidesList');
            }"""
        )

    def wait_editor(self, timeout: int = 1500) -> None:
        self.page.wait_for_function(
            """() => {
              const a = document.activeElement;
              return !!a && a.classList.contains('txt-block') && !!a.closest('#elementsLayer');
            }""",
            timeout=timeout,
        )

    def type_text(self, text: str) -> None:
        self.page.keyboard.type(text)

    def exit_editor(self) -> None:
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(150)

    def editing_id(self) -> str | None:
        return self.page.evaluate("() => OPP.state.editingTextId || null")

    def close(self) -> None:
        self.context.close()


def launch(p):
    return p.chromium.launch(
        channel="chrome",
        headless=True,
        args=["--enable-precise-memory-info", "--js-flags=--expose-gc"],
    )


def main_runner(tests):
    results = []
    with sync_playwright() as p:
        browser = launch(p)
        for entry in tests:
            name, fn, mobile = entry[0], entry[1], entry[2]
            url = entry[3] if len(entry) > 3 else None
            session = Session(browser, mobile=mobile, url=url)
            ok, note = True, ""
            try:
                fn(session)
            except Exception as exc:  # noqa: BLE001 - il report vuole il messaggio
                ok, note = False, str(exc).split("\n")[0][:160]
            errs = [e for e in session.errors if "favicon" not in e.lower()]
            if errs:
                ok = False
                note = (note + " | " if note else "") + errs[0][:200]
            results.append((name, ok, note))
            session.close()
        browser.close()
    width = max(len(r[0]) for r in results) + 2
    for name, ok, note in results:
        print(f"{name.ljust(width)} {'OK  ' if ok else 'FAIL'} {note}")
    falliti = [r[0] for r in results if not r[1]]
    print(f"\n{len(results) - len(falliti)} test superati su {len(results)}")
    if falliti:
        print("falliti: " + ", ".join(falliti))
    return 1 if falliti else 0
