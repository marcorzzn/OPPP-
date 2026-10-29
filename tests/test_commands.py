"""Regressione: ogni comando di OPP.COMMANDS viene eseguito senza argomento.

Un comando è "rotto" se lancia un'eccezione, se runCommand mostra
"Comando non disponibile" o se viene registrato un errore in console.
I comandi che aprono un selettore di file restano in attesa: non li aspettiamo.
"""
from __future__ import annotations

import json
import sys

from harness import Session, launch, main_runner


def tutti_i_comandi(s: Session) -> None:
    s.page.evaluate(
        """() => {
          window.__cmdErrors = [];
          const origError = console.error;
          console.error = (...a) => { window.__cmdErrors.push(a.map(String).join(' ')); origError(...a); };
          HTMLAnchorElement.prototype.click = function(){};
          window.print = () => {};
          HTMLInputElement.prototype.__origClick = HTMLInputElement.prototype.click;
          HTMLInputElement.prototype.click = function(){
            if (this.type === 'file') return;
            return this.__origClick();
          };
        }"""
    )
    chiavi = s.page.evaluate("() => Object.keys(OPP.COMMANDS).sort()")
    rotti = []
    for chiave in chiavi:
        esito = s.page.evaluate(
            """async (chiave) => {
              window.__cmdErrors.length = 0;
              document.getElementById('toastWrap').innerHTML = '';
              let eccezione = null;
              try {
                Promise.resolve(OPP.runCommand(chiave, {})).catch(e => { eccezione = String(e && e.message || e); });
              } catch (e) { eccezione = String(e && e.message || e); }
              await new Promise(r => setTimeout(r, 40));
              const modal = document.getElementById('modalBg');
              if (modal) modal.classList.remove('open');
              const testi = [...document.querySelectorAll('#toastWrap .toast')].map(t => t.textContent);
              return {
                eccezione,
                errori: window.__cmdErrors.slice(),
                toast: testi.filter(t => /non disponibile|Errore|non funzion/i.test(t))
              };
            }""",
            chiave,
        )
        if esito["eccezione"] or esito["errori"] or esito["toast"]:
            rotti.append({"comando": chiave, **esito})
    if rotti:
        raise AssertionError(f"{len(rotti)} comandi con problemi: " + json.dumps(rotti[:3], ensure_ascii=False))
    print(f"      {len(chiavi)} comandi eseguiti senza eccezioni")


TESTS = [("comandi eseguibili", tutti_i_comandi, False)]

if __name__ == "__main__":
    filtro = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None
    raise SystemExit(main_runner([t for t in TESTS if not filtro or filtro in t[0]]))
