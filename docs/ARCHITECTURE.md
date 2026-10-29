# Architettura di OverPowerPoint

Mappa del codice per rispondere alla domanda: **«se voglio toccare X, dove guardo?»**. Tutto il codice dell'app vive dentro `index.html` in un'unica IIFE `(() => { ... })()`.

## 1. Stato

Un solo oggetto `state` contiene tutto: documento (`slides`, `current`, `selected`), preferenze (`settings`), strumenti, cronologia (`history`, `historyIndex`), cache degli effetti (`effects`). `serializeDoc()` produce lo snapshot JSON salvato su file; `loadProjectData()` lo ripristina.

**Da sapere:** `serializeDoc()` genera id casuali per gli elementi a ogni caricamento: confronti testuali tra due sessioni vanno normalizzati.

## 2. Comandi

Ogni azione utente passa da `COMMANDS` (oggetto `nome → funzione`) e viene eseguita da `runCommand(name, arg)`. I pulsanti usano `[data-command]` con delega eventi (un solo listener su document). La palette comandi (`Ctrl+K`) elenca tutte le chiavi.

**Aggiungere un comando:** una voce in uno dei blocchi `Object.assign(COMMANDS, {...})` e, se serve un pulsante, `ribbonBtn(icona, etichetta, "nome.comando", {p:1})` (p:1 = essenziale in modalità semplice, p:2 = solo completa).

## 3. Rendering

```
renderAll()
 ├─ renderSlidesList()      miniature a sinistra
 ├─ renderCurrentSlide()    ricostruisce #elementsLayer
 ├─ renderLayers()          pannello livelli
 ├─ renderTimeline()
 ├─ renderProperties()
 ├─ renderColorPanel()
 └─ renderStatus()
```

`renderCurrentSlide()` è il costo maggiore: evita di chiamarlo per sole selezioni. Il clic semplice aggiorna solo la sovrapposizione (vedi `onWindowPointerUp`).

**Elementi:** `buildElementNode(el)` crea il nodo DOM per tipo (text, shape, image, chart, table, media, path, boolean, sticker). I testi sono `contenteditable` solo durante l'editing (`startTextEdit`/`finishTextEdit`).

## 4. Persistenza

| Cosa | Dove |
|---|---|
| Preferenze | `localStorage` chiave `opp.settings.v2` |
| Libreria progetti | `localStorage` chiave `opp.library.v2` |
| Autosalvataggio | IndexedDB `opp.db`, store `autosave`, chiave `current` |
| Handle del file | IndexedDB, chiave `fsHandle` |
| Documento salvato | file `.opp.json` via `showSaveFilePicker` |

`loadProjectData(data, {keepFileHandle})` invalida l'handle del file quando si apre/importa un progetto diverso.

## 5. Test

`tests/harness.py` apre l'app in Chrome headless e offre helper DOM; le suite sono: testo, salvataggio, comandi, densità, fase 4 (robustezza), PWA. La variabile `OPP_FILE` sceglie il file da testare (default `index.html`). Vedi `tests/README.md`.

## 6. PWA

`manifest.json` descrive l'app installabile; `sw.js` fa precache di app, icone, catalogo effetti e file degli effetti. La cache è versionata (`opp-v1`): **cambia la versione a ogni modifica di `index.html` o `sw.js`**. Il catalogo effetti è network-first, così un nuovo effetto compare senza aggiornare il service worker.

## 7. Effetti

`effects/manifest.json` elenca gli effetti; ogni effetto è un HTML autonomo che carica `effects/sdk.js`. OPP apre l'effetto in una modale con `iframe src="effects/<file>?embed=1"` e riceve il risultato via `postMessage({type:'opp:image', dataUrl, name})`: l'immagine viene inserita nella slide corrente con un `commit('Effetto <label>')`.

**Aggiungere un effetto non richiede modifiche a `index.html`**: vedi `docs/EFFECTS.md`.

## 8. Punti delicati

- `esc()`/`escAttr()` per ogni interpolazione in `innerHTML` che contenga dati importati.
- `onSurfacePointerDown` usa un rilevamento manuale del doppio clic (il `preventDefault` sopprime gli eventi mouse compatibili).
- Il service worker va aggiornato di versione a ogni deploy con modifiche all'app.
- La cronologia ha un tetto di 24 MB di caratteri: non regolare a mano senza motivo.
