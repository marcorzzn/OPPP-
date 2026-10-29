"""Fase 0 — rete di sicurezza per il testo.

Flussi coperti con input reali del browser (mouse, tastiera, tocco):
 1. avvio senza errori
 2. inserimento dal pulsante "Casella testo" + scrittura + uscita
 3. strumento Testo (T) + clic sulla slide + scrittura
 4. doppio clic su un testo esistente
 5. selezione + F2
 6. menu contestuale > Modifica testo
 7. annulla dopo la modifica
 8. scenario touch 390x844

Uso:  python tests/test_text.py [--solo NOME]
"""
from __future__ import annotations

import sys

from harness import Session, launch, main_runner


# ---------------------------------------------------------------- test
def t01_avvio(s: Session) -> None:
    assert s.page.title().startswith("OverPowerPoint"), s.page.title()
    assert len(s.elements()) > 0, "la slide iniziale è vuota"


def t02_pulsante_testo(s: Session) -> None:
    s.add_text_button()
    s.wait_editor()
    el = s.last_text()
    s.type_text("ABC")
    s.exit_editor()
    assert "ABC" in (s.text_of(el["id"]) or ""), s.text_of(el["id"])


def t03_strumento_t(s: Session) -> None:
    s.add_text_with_tool()
    s.wait_editor()
    el = s.last_text()
    s.type_text("DEF")
    s.exit_editor()
    assert "DEF" in (s.text_of(el["id"]) or ""), s.text_of(el["id"])


def _new_text(s: Session, text: str) -> dict:
    s.add_text_button()
    s.wait_editor()
    el = s.last_text()
    s.type_text(text)
    s.exit_editor()
    return el


def t04_doppio_clic(s: Session) -> None:
    el = _new_text(s, "PRIMO")
    x, y = s.center(el["id"])
    s.page.mouse.dblclick(x, y)
    s.wait_editor()
    assert s.editor_is_active_in_stage(), "l'editor non è sul palco (miniatura?)"
    s.type_text("XYZ")
    s.exit_editor()
    testo = s.text_of(el["id"]) or ""
    assert "XYZ" in testo, testo
    sul_palco = s.page.locator(f'#elementsLayer .el[data-el-id="{el["id"]}"] .txt-block').inner_text()
    assert "XYZ" in sul_palco, sul_palco


def t05_f2(s: Session) -> None:
    el = _new_text(s, "PRIMO")
    x, y = s.center(el["id"])
    s.page.mouse.click(x, y)
    s.page.keyboard.press("F2")
    s.wait_editor()
    s.type_text("F2TXT")
    s.exit_editor()
    assert "F2TXT" in (s.text_of(el["id"]) or ""), s.text_of(el["id"])


def t06_menu_contestuale(s: Session) -> None:
    el = _new_text(s, "PRIMO")
    x, y = s.center(el["id"])
    s.page.mouse.click(x, y, button="right")
    s.page.wait_for_selector("#ctxMenu.open, .ctx-menu.open", timeout=1500)
    voce = s.page.locator('[data-cmd="text.edit"], .ctx-item:has-text("Modifica testo")').first
    voce.click()
    s.wait_editor()
    s.type_text("CTX")
    s.exit_editor()
    assert "CTX" in (s.text_of(el["id"]) or ""), s.text_of(el["id"])


def t07_annulla(s: Session) -> None:
    el = _new_text(s, "BASE")
    x, y = s.center(el["id"])
    s.page.mouse.dblclick(x, y)
    s.wait_editor()
    s.type_text("+EXTRA")
    s.exit_editor()
    assert "+EXTRA" in (s.text_of(el["id"]) or "")
    s.page.keyboard.press("Control+z")
    s.page.wait_for_timeout(300)
    dopo = s.text_of(el["id"]) or ""
    assert "+EXTRA" not in dopo, dopo


def t09_invio(s: Session) -> None:
    el = _new_text(s, "PRIMO")
    x, y = s.center(el["id"])
    s.page.mouse.click(x, y)
    s.page.keyboard.press("Enter")
    s.wait_editor()
    s.type_text("INVIO")
    s.exit_editor()
    assert "INVIO" in (s.text_of(el["id"]) or ""), s.text_of(el["id"])


def t10_esc_salva(s: Session) -> None:
    el = _new_text(s, "PRIMO")
    x, y = s.center(el["id"])
    s.page.mouse.dblclick(x, y)
    s.wait_editor()
    s.type_text("ESC")
    s.page.keyboard.press("Escape")
    s.page.wait_for_timeout(250)
    assert s.editing_id() is None, "la modifica non è terminata con Esc"
    assert "ESC" in (s.text_of(el["id"]) or ""), s.text_of(el["id"])


def t11_clic_fuori(s: Session) -> None:
    el = _new_text(s, "PRIMO")
    x, y = s.center(el["id"])
    s.page.mouse.dblclick(x, y)
    s.wait_editor()
    s.type_text("FUORI")
    box = s.page.locator("#slideSurface").bounding_box()
    s.page.mouse.click(box["x"] + 12, box["y"] + 12)
    s.page.wait_for_timeout(300)
    assert s.editing_id() is None, "il clic fuori non ha chiuso la modifica"
    assert "FUORI" in (s.text_of(el["id"]) or ""), s.text_of(el["id"])


def t12_cambio_slide(s: Session) -> None:
    el = _new_text(s, "PRIMO")
    x, y = s.center(el["id"])
    s.page.mouse.dblclick(x, y)
    s.wait_editor()
    s.type_text("PERSO")
    s.page.click("#slidesList .slide-thumb:nth-child(2)")
    s.page.wait_for_timeout(350)
    assert s.editing_id() is None, "lo stato di modifica è rimasto attivo"
    tornato = s.page.evaluate(
        "(id) => { const e = OPP.state.slides[0].elements.find(x => x.id === id); return e ? (e.text || '') : null; }",
        el["id"],
    )
    assert "PERSO" in (tornato or ""), tornato


def t13_segnaposto(s: Session) -> None:
    s.add_text_button()
    s.wait_editor()
    el = s.last_text()
    s.type_text("X")
    s.exit_editor()
    assert (s.text_of(el["id"]) or "") == "X", s.text_of(el["id"])


def t14_pulsante_strumento(s: Session) -> None:
    s.page.click('#tabs .tab[data-tab="Inserisci"]')
    s.page.click('#ribbon [data-tool="text"]')
    box = s.page.locator("#slideSurface").bounding_box()
    s.page.mouse.click(box["x"] + box["width"] * 0.35, box["y"] + box["height"] * 0.7)
    s.wait_editor()
    el = s.last_text()
    s.type_text("STRUMENTO")
    s.exit_editor()
    assert "STRUMENTO" in (s.text_of(el["id"]) or ""), s.text_of(el["id"])


def t15_grassetto_durante_modifica(s: Session) -> None:
    el = _new_text(s, "PRIMO")
    x, y = s.center(el["id"])
    s.page.mouse.dblclick(x, y)
    s.wait_editor()
    s.type_text("CIAO")
    s.page.click('#propertiesBody [data-command="text.bold"]')
    s.page.wait_for_timeout(300)
    atteso = "PRIMOCIAO"
    assert (s.text_of(el["id"]) or "") == atteso, s.text_of(el["id"])
    grassetto = s.page.evaluate(
        "(id) => { const e = OPP.currentSlide().elements.find(x => x.id === id); return !!(e && e.bold); }",
        el["id"],
    )
    assert grassetto is True, "il grassetto non è stato applicato"
    s.wait_editor()
    s.type_text("!")
    s.exit_editor()
    assert (s.text_of(el["id"]) or "").endswith(atteso + "!"), s.text_of(el["id"])


def t16_clic_vuoto_reset(s: Session) -> None:
    el = _new_text(s, "PRIMO")
    x, y = s.center(el["id"])
    box = s.page.locator("#slideSurface").bounding_box()
    s.page.mouse.click(x, y)
    s.page.wait_for_timeout(80)
    s.page.mouse.click(box["x"] + 10, box["y"] + box["height"] - 10)
    s.page.wait_for_timeout(80)
    s.page.mouse.click(x, y)
    s.page.wait_for_timeout(300)
    assert s.editing_id() is None, "due clic separati da un clic vuoto sono stati letti come doppio clic"


def t08_touch(s: Session) -> None:
    s.page.locator('#ribbon [data-command="insert.text"]').tap()
    s.wait_editor()
    el = s.last_text()
    s.type_text("TOCCO")
    s.exit_editor()
    assert "TOCCO" in (s.text_of(el["id"]) or ""), s.text_of(el["id"])

    x, y = s.center(el["id"])
    s.page.touchscreen.tap(x, y)
    s.page.wait_for_timeout(90)
    s.page.touchscreen.tap(x, y)
    s.wait_editor()
    s.type_text("2")
    s.exit_editor()
    assert "2" in (s.text_of(el["id"]) or ""), s.text_of(el["id"])


TESTS = [
    ("01 avvio", t01_avvio, False),
    ("02 pulsante Casella testo", t02_pulsante_testo, False),
    ("03 strumento T + clic", t03_strumento_t, False),
    ("04 doppio clic", t04_doppio_clic, False),
    ("05 selezione + F2", t05_f2, False),
    ("06 menu contestuale", t06_menu_contestuale, False),
    ("07 annulla (Ctrl+Z)", t07_annulla, False),
    ("08 touch 390x844", t08_touch, True),
    ("09 Invio su selezione", t09_invio, False),
    ("10 Esc chiude e salva", t10_esc_salva, False),
    ("11 clic fuori salva", t11_clic_fuori, False),
    ("12 cambio slide non perde", t12_cambio_slide, False),
    ("13 segnaposto sostituito", t13_segnaposto, False),
    ("14 pulsante Strumento testo", t14_pulsante_strumento, False),
    ("15 grassetto durante la modifica", t15_grassetto_durante_modifica, False),
    ("16 clic vuoto azzera il doppio clic", t16_clic_vuoto_reset, False),
]

if __name__ == "__main__":
    filtro = None
    if "--solo" in sys.argv:
        filtro = sys.argv[sys.argv.index("--solo") + 1]
    scelti = [t for t in TESTS if filtro is None or filtro in t[0]]
    raise SystemExit(main_runner(scelti))
