"""Fase 3 — densità dell'interfaccia: comandi essenziali in evidenza, resto dietro "Altro".

Uso:  python tests/test_density.py [--solo NOME]
"""
from __future__ import annotations

import sys

from harness import Session, launch, main_runner

TABS = ["File", "Home", "Inserisci", "Disegna", "Foto", "Vettore", "Presentazione", "Video", "Revisione", "Visualizza"]
ESSENTIALS = {
    "File": ['[data-command="file.save"]', '[data-command="file.open"]'],
    "Home": ['[data-command="insert.text"]', '[data-command="slide.layout"]', '[data-command="view.present"]'],
    "Inserisci": ['[data-command="insert.text"]', '[data-tool="text"]', '[data-command="insert.image"]'],
    "Disegna": ['[data-tool="select"]', '[data-tool="brush"]'],
    "Foto": ['[data-command="image.adjust"]', '[data-command="image.crop"]'],
    "Vettore": ['[data-command="shape.union"]', '[data-command="shape.toPath"]'],
    "Presentazione": ['[data-command="view.present"]', '[data-command="slide.notes"]'],
    "Video": ['[data-command="timeline.play"]', '[data-command="export.webm"]'],
    "Revisione": ['[data-command="review.find"]', '[data-command="review.accessibility"]'],
    "Visualizza": ['[data-command="view.grid"]', '[data-command="view.zoomFit"]'],
}


def _open_tab(s: Session, tab: str) -> None:
    s.page.click(f'#tabs .tab[data-tab="{tab}"]')
    s.page.wait_for_timeout(60)


def _count(s: Session) -> int:
    return s.page.locator("#ribbon button").count()


def _set_density(s: Session, mode: str) -> None:
    if s.page.evaluate("OPP.state.settings.uiDensity") != mode:
        s.page.evaluate("() => OPP.runCommand('view.density', {})")
        s.page.wait_for_timeout(80)


def t01_semplice_default(s: Session) -> None:
    assert s.page.evaluate("OPP.state.settings.uiDensity") == "semplice"
    for tab in TABS:
        _open_tab(s, tab)
        n = _count(s)
        assert 1 <= n <= 20, f"{tab}: {n} pulsanti in modalità semplice"
        for sel in ESSENTIALS[tab]:
            assert s.page.locator(f"#ribbon {sel}").count() == 1, f"{tab}: manca {sel}"


def t02_completa_mostra_tutto(s: Session) -> None:
    _open_tab(s, "Inserisci")
    semplice = _count(s)
    assert s.page.locator('#ribbon [data-command="ai.art"]').count() == 0
    _set_density(s, "completa")
    _open_tab(s, "Inserisci")
    completa = _count(s)
    assert completa > semplice, (semplice, completa)
    assert s.page.locator('#ribbon [data-command="ai.art"]').count() == 1
    for tab in TABS:
        _open_tab(s, tab)
        assert _count(s) >= 1


def t03_altro_e_palette(s: Session) -> None:
    _open_tab(s, "Home")
    assert s.page.locator('#ribbon [data-command="help.commands"]').count() == 1
    assert s.page.locator('#ribbon [data-command="view.density"]').count() == 1
    s.page.evaluate("() => OPP.runCommand('help.commands', {})")
    s.page.wait_for_selector("#cmdSearch")
    assert s.page.evaluate("() => Object.keys(OPP.COMMANDS).length") >= 244
    s.page.click('#modalFoot [data-close]')


def t04_densita_persistente(s: Session) -> None:
    _set_density(s, "completa")
    s.page.wait_for_timeout(400)
    s.page.reload()
    s.page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    assert s.page.evaluate("OPP.state.settings.uiDensity") == "completa"
    _open_tab(s, "Home")
    assert _count(s) > 20


def t05_preferenze(s: Session) -> None:
    s.page.evaluate("() => OPP.runCommand('file.preferences', {})")
    s.page.wait_for_selector("#prefDensity")
    s.page.select_option("#prefDensity", "completa")
    s.page.click("#prefSave")
    s.page.wait_for_timeout(300)
    assert s.page.evaluate("OPP.state.settings.uiDensity") == "completa"
    _open_tab(s, "Home")
    assert _count(s) > 20


def t06_mobile(s: Session) -> None:
    assert s.page.evaluate("OPP.state.settings.uiDensity") == "semplice"
    _open_tab(s, "Home")
    larghezza = s.page.evaluate("document.documentElement.scrollWidth")
    assert larghezza <= 390 + 1, f"scorrimento orizzontale: {larghezza}"
    # la ribbon compatta non deve scorrere: tutti i pulsanti dentro lo schermo
    info = s.page.evaluate(
        """() => {
          const r = document.getElementById('ribbon');
          const fuori = [...r.querySelectorAll('button')]
            .filter(b => b.getBoundingClientRect().right > innerWidth + 1)
            .map(b => b.dataset.command || b.dataset.tool || '?');
          return { scroll: r.scrollWidth, client: r.clientWidth, fuori, n: r.querySelectorAll('button').length };
        }"""
    )
    assert info["scroll"] <= info["client"] + 1, f"la ribbon scorre ancora: {info}"
    assert info["fuori"] == [], f"pulsanti fuori dallo schermo: {info['fuori']}"
    assert info["n"] >= 14, info
    s.page.locator('#ribbon [data-command="insert.text"]').tap()
    s.wait_editor()
    s.type_text("MOBILE")
    s.exit_editor()
    assert "MOBILE" in (s.text_of(s.last_text()["id"]) or "")


def t07_stessa_lista_desktop_e_mobile(s: Session) -> None:
    _open_tab(s, "Home")
    desktop = sorted(s.page.evaluate(
        "[...document.querySelectorAll('#ribbon [data-command]')].map(b => b.dataset.command)"
    ))
    browser = s.context.browser
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(s.url)
    page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    page.click('#tabs .tab[data-tab="Home"]')
    page.wait_for_timeout(120)
    mobile = sorted(page.evaluate(
        "[...document.querySelectorAll('#ribbon [data-command]')].map(b => b.dataset.command)"
    ))
    ctx.close()
    assert desktop == mobile, (desktop, mobile)


def t08_avviso_una_tantum(s: Session) -> None:
    s.page.wait_for_selector("#densityNotice", timeout=8000)
    s.page.click("#densityNoticeOk")
    s.page.wait_for_timeout(200)
    assert s.page.locator("#densityNotice").count() == 0
    s.page.reload()
    s.page.wait_for_function("() => window.OPP && OPP.state.slides.length > 0")
    s.page.wait_for_timeout(3200)
    assert s.page.locator("#densityNotice").count() == 0, "l'avviso è ricomparso dopo la ricarica"


def t09_completa_identica_al_riferimento(s: Session) -> None:
    import json
    import pathlib
    baseline = json.loads((pathlib.Path(__file__).parent / "_ribbon_baseline.json").read_text(encoding="utf-8"))
    if s.page.evaluate("OPP.state.settings.uiDensity") != "completa":
        s.page.evaluate("() => OPP.runCommand('view.density', {})")
    for tab in TABS:
        _open_tab(s, tab)
        atteso = baseline[tab]["commands"]
        attuale = sorted(s.page.evaluate(
            "[...document.querySelectorAll('#ribbon [data-command]')].map(b => b.dataset.command)"
        ))
        assert attuale == atteso, (tab, set(atteso) ^ set(attuale))
        tools_atteso = baseline[tab]["tools"]
        tools_attuale = sorted(s.page.evaluate(
            "[...document.querySelectorAll('#ribbon [data-tool]')].map(b => b.dataset.tool + (b.dataset.kind ? '/' + b.dataset.kind : ''))"
        ))
        assert tools_attuale == tools_atteso, (tab, set(tools_atteso) ^ set(tools_attuale))


TESTS = [
    ("01 semplice di default", t01_semplice_default, False),
    ("02 completa mostra tutti i gruppi", t02_completa_mostra_tutto, False),
    ("03 Altro + palette completa", t03_altro_e_palette, False),
    ("04 densità persiste dopo la ricarica", t04_densita_persistente, False),
    ("05 densità dalle Preferenze", t05_preferenze, False),
    ("06 mobile: tutti gli essenziali visibili", t06_mobile, True),
    ("07 stessa lista desktop/mobile", t07_stessa_lista_desktop_e_mobile, False),
    ("08 avviso una tantum", t08_avviso_una_tantum, False),
    ("09 completa identica al riferimento", t09_completa_identica_al_riferimento, False),
]

if __name__ == "__main__":
    filtro = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None
    raise SystemExit(main_runner([t for t in TESTS if not filtro or filtro in t[0]]))
