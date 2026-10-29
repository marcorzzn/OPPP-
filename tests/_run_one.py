"""Esegue un singolo test di un file, con traceback completo."""
import sys
import traceback

import harness

nome_file = sys.argv[1]
nome_test = sys.argv[2]
mod = __import__(nome_file)
scelto = [t for t in mod.TESTS if nome_test in t[0]][0]
with harness.sync_playwright() as p:
    browser = harness.launch(p)
    s = harness.Session(browser, mobile=scelto[2])
    try:
        scelto[1](s)
        print("OK")
    except Exception:
        traceback.print_exc()
    finally:
        s.close()
        browser.close()
