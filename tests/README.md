# Test di OverPowerPoint

Suite Playwright (Python) che pilotano l'app reale in Chrome headless, su `file://`,
con un piccolo servizio HTTP locale per i test che richiedono un'origine `http(s)`
(service worker, handle del file, OPFS).

## Prerequisiti

- Windows, Python 3.11+.
- Chrome installato (`channel="chrome"`).
- Dipendenze Python nella virtualenv locale del progetto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chrome
```

La suite **non** usa browser diversi da Chrome: i test di `showSaveFilePicker`,
OPFS e service worker richiedono Chromium.

## Esecuzione

Dalla radice del progetto:

```powershell
$env:TEMP='C:\Progetti\OPP\.tmp'; $env:TMP='C:\Progetti\OPP\.tmp'
$env:OPP_FILE='index.html'

.\.venv\Scripts\python.exe tests\test_text.py
.\.venv\Scripts\python.exe tests\test_save.py
.\.venv\Scripts\python.exe tests\test_commands.py
.\.venv\Scripts\python.exe tests\test_density.py
.\.venv\Scripts\python.exe tests\test_phase4.py
.\.venv\Scripts\python.exe tests\test_pwa.py
```

Note:

- `TEMP`/`TMP` vanno rediretti in `.tmp/` perché Chrome, sotto la sandbox DSH,
  non riesce a creare la propria directory temporanea altrove.
- `OPP_FILE` seleziona il file da testare (default `index.html`);
  utile per confrontare con i backup o con la baseline.
- `test_pwa.py` avvia da solo un mini server su `http://127.0.0.1:8765/`
  (equivalente a `python -m http.server`, in-process). Serve perché il service
  worker richiede un'origine `http(s)`: non aprirlo a mano.
- `test_pwa.py` include il test 10 che rilancia le altre 5 suite; per una
  verifica veloce: `python tests/test_pwa.py --solo 05`.
- Un singolo test delle altre suite: `python tests/test_text.py --solo 04`.

## Copertura

| File | Contenuto |
|---|---|
| `test_text.py` | 16 test sull'editor di testo: doppio clic, F2, Invio, menu contestuale, strumento T, touch 390×844, Esc/clic fuori/salvataggio, segnaposto, console errori |
| `test_save.py` | 13 test su autosalvataggio IndexedDB, salvataggio su file con `showSaveFilePicker` (stub), badge a due stati, roundtrip 12 MB, pannello export, migrazione da localStorage, handle persistente (origine HTTP + OPFS), invalidazione handle, download ≠ salvataggio, salvataggio durante editing, intervalli di export |
| `test_commands.py` | esegue ogni comando di `OPP.COMMANDS` e conta eccezioni/errori console/toast |
| `test_density.py` | densità interfaccia (semplice/completa), filtro priorità ribbon, confronto con `_ribbon_baseline.json`, mobile senza overflow, avviso una tantum |
| `test_phase4.py` | clic che non ridisegna, cronologia a budget di memoria, iniezione da progetto importato, export HTML aperto davvero, memoria stabile oltre il tetto |
| `test_pwa.py` | manifest, service worker, installabilità (best effort), offline, scheda Effetti, iframe, invio immagine a OPP, effetto standalone, fallback catalogo, regressioni |

`harness.py` contiene le utility condivise: apertura pagina, helper DOM,
`start_http` per l'origine HTTP dei test sull'handle.

## Fixture e riferimenti

- **Rigenerabili dai test** (vengono riscritti a ogni esecuzione): `_xss_probe.opp.json`,
  `_export_probe.html`, `_roundtrip.opp.json`, `_altro.opp.json`. Possono essere
  cancellati: i test li ricreano.
- **Da conservare**: `_ribbon_baseline.json` è il riferimento del test 09
  (modalità completa identica a prima del refactoring delle priorità). Per
  rigenerarlo usare `tests/baseline_ribbon.py` **solo** su una versione che
  deve diventare il nuovo riferimento.
- **Icone PWA**: `python tests/_generate_icons.py` (richiede Pillow, incluso
  nell'ambiente Python fornito con DSH; non è una dipendenza dell'app). Va
  rilanciato solo se cambiano i colori brand.
- **Rete**: `test_save.py` (test sull'upload di un Google Font) prova a scaricare
  `Roboto` da `fonts.googleapis.com`; senza rete il test è tollerante
  (accetta che il font non venga salvato), ma la copertura reale richiede rete.

## Limiti noti

- Il dialogo di salvataggio nativo è **stubbato**: i test verificano la logica
  dell'handle, non il dialogo di Windows.
- La verifica dell'handle persistente usa un'origine HTTP locale
  (`http://127.0.0.1:8801`) perché OPFS è bloccato su `file://`; la prova reale
  su `file://` è stata fatta a mano in Fase 2 (picker e persistenza funzionano).
- `beforeinstallprompt` e il banner "Aggiungi a schermata Home" variano per
  browser e non sono verificabili in headless: il test 03 è best effort.
- `serializeDoc()` genera id casuali: confronti testuali fra due caricamenti
  vanno normalizzati prima del confronto.
- Le misure di memoria usano `performance.memory` (Chromium, avviato con
  `--enable-precise-memory-info` e `--js-flags=--expose-gc`); il test 06 di
  `test_phase4.py` forza `gc()` prima dei campioni e verifica che la memoria
  resti piatta oltre il tetto. I valori in MB restano indicativi (dipendono dal
  GC); l'asserzione forte è su `state.history.length` e sul budget di caratteri.
- Il service worker non è testato su Safari/Firefox.

## Il progetto

Il progetto è consegnato come singolo `index.html` autonomo (nessuna libreria, nessuna CDN).
La versione originale pre-modifiche (Fase 0) è conservata in `tests/baseline/OverPowerPoint.v0-pre-modifiche.html`:
serve solo come riferimento di confronto (`git diff --no-index`), **non** è parte dell'app.
Le funzioni delle Fasi 1–5 sono verificate dalle 45 asserzioni delle suite, la Fase 6
(PWA ed effetti) dalle 10 asserzioni di `test_pwa.py`.
