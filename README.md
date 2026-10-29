# OverPowerPoint Studio

Suite creativa offline in un unico file HTML: presentazioni, grafica, foto, vettoriale, video. Zero dipendenze, zero CDN, zero account. Funziona da `file://` o da GitHub Pages, ed è installabile come PWA.

## Demo

- **Web (PWA)**: https://marcorzzn.github.io/OverPowerPoint/
- **Locale**: doppio clic su `index.html`

## Caratteristiche

- Editor di presentazioni (slide, testi, forme, immagini, grafici, tabelle, tracciati).
- Strumenti immagine: ritaglio, filtri, maschere, rimozione sfondo, upscale.
- Sistema di **effetti modulari** (vedi [`docs/EFFECTS.md`](docs/EFFECTS.md)): aggiungi nuove schermate senza toccare l'app.
- Salvataggio su file (`showSaveFilePicker`, handle persistente) e autosalvataggio in IndexedDB.
- Export: PNG, JPG, WebP, SVG, PDF, PPTX, HTML, ZIP, WebM.
- 55 test automatici (Playwright), modalità densità ridotta, ribbon mobile compatta.
- PWA: manifest, service worker con cache `opp-vN`, icone generate.

## Struttura del repository

| Percorso | Cosa contiene |
|---|---|
| `index.html` | L'app completa: HTML, CSS, JS in un unico file |
| `manifest.json`, `sw.js` | Configurazione PWA e service worker |
| `icons/` | Icone generate da `tests/_generate_icons.py` |
| `effects/` | Effetti modulari: `manifest.json`, `sdk.js`, `_template.html`, gli effetti installati |
| `docs/` | Architettura, guida effetti, roadmap, archivio prove (`docs/audit/`) |
| `tests/` | Suite Playwright, baseline pre-modifiche, diagnostiche |

## Come si usa (utente)

1. Apri l'URL o il file.
2. Ribbon → schede Home / Inserisci / Foto / Effetti.
3. `Ctrl+K` per la palette comandi (246 comandi).
4. Salva con `Ctrl+S`, esporta con `Ctrl+E`.
5. Gli effetti si aprono dalla scheda **Effetti**: scegli una card, lavora, premi **Invia a OPP**.

## Come si sviluppa (contributore)

- Leggi [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) per la mappa del codice.
- Leggi [`docs/EFFECTS.md`](docs/EFFECTS.md) per aggiungere una nuova schermata di effetto.
- I test si lanciano con `python tests/test_text.py` (vedi [`tests/README.md`](tests/README.md)).
- Modifiche chirurgiche: niente refactoring non richiesti, niente nuove dipendenze runtime.
- Se modifichi `index.html` o `sw.js`, **incrementa `CACHE` in `sw.js`** (`opp-v1` → `opp-v2`), altrimenti i browser restano sulla versione vecchia.

## Licenza

Tutti i diritti riservati (nessuna licenza open source è stata concessa).

## Crediti

Ispirato a PowerPoint, Photoshop, Illustrator. Costruito con AI come pair programmer, con revisione umana di ogni riga.

