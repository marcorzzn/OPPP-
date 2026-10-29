# Effetti modulari: aggiungerne uno in 10 minuti

## Cos'è un effetto

Un effetto è una **pagina HTML indipendente** dentro `effects/`. Puoi aprirla da sola (doppio clic) e funziona come un piccolo strumento a sé. Quando la apri da OverPowerPoint, l'app la mostra in una finestra (iframe) e può ricevere il risultato: un'immagine PNG che finisce direttamente nella slide.

L'isolamento è la forza del sistema: **per aggiungere o cambiare un effetto non tocchi `index.html`**. Se un effetto è brutto o lento, lo sistemi nel suo file.

## 1. Copia il template

```bash
cp effects/_template.html effects/mio-effetto.html
```

Apri `effects/mio-effetto.html` in un editor e guarda lo `<script>` in fondo: c'è un commento `// === QUI la tua trasformazione ===`. Scrivi lì il codice che disegna il risultato sul canvas.

Esempio minimo (filtro seppia):

```js
img.onload = () => {
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  ctx.filter = "sepia(0.7) contrast(1.1)";
  ctx.drawImage(img, 0, 0);
};
```

## 2. Regole del contratto

1. Il file si chiama `effects/<id>.html` (id = slug, es. `mio-effetto`).
2. Deve funzionare **anche da solo**: titolo, controlli, canvas, pulsante di download.
3. Se l'URL contiene `?embed=1`, il file aggiunge la classe `embed` al body (`OPPFrame.apply()` lo fa per te): via titolo e descrizione, restano controlli e canvas.
4. Il pulsante **Invia a OPP** deve esistere solo in embed e chiamare `OPPFrame.sendImage(canvas, 'nome.png')`.
5. Espone `window.getEffectCanvas = () => canvas` con il canvas principale.
6. Carica `./sdk.js` prima del tuo script.

## 3. Aggiungi la voce al catalogo

Apri `effects/manifest.json` e aggiungi:

```json
{
  "id": "mio-effetto",
  "file": "mio-effetto.html",
  "label": "Mio effetto",
  "icon": "✨",
  "description": "Cosa fa, in una riga.",
  "tags": ["foto"],
  "version": "1.0.0"
}
```

## 4. Provalo

1. **Da solo**: doppio clic sul file. Deve caricare un'immagine e mostrare il canvas.
2. **Dentro OPP**: apri `index.html` → scheda **Effetti** → **Ricarica catalogo** → apri la card del tuo effetto.
3. Carica un'immagine, premi **Invia a OPP**: l'immagine deve comparire nella slide e la modale chiudersi.

## 5. Pubblicalo

```bash
git add effects/
git commit -m "Nuovo effetto: mio-effetto"
git push
```

GitHub Pages aggiorna in 1–2 minuti. Chi ha già l'app aperta può premere **Ricarica catalogo** (il catalogo è network-first, quindi arriva la versione nuova senza aspettare il service worker).

## 6. Come migliorare o cambiare un effetto

- **Modifica** direttamente il suo HTML: non serve toccare OPP.
- **Rinomina** l'id e il file, aggiorna `manifest.json`.
- **Rimuovi** la voce dal manifest e cancella il file.
- Se un effetto non compare: controlla che `manifest.json` sia JSON valido (una virgola di troppo rompe tutto) e che il percorso `file` esista.

## 7. Errori comuni

| Sintomo | Causa probabile |
|---|---|
| La card non compare | voce mancante nel manifest o `file` sbagliato |
| In embed il pulsante "Invia a OPP" non c'è | `OPPFrame.isEmbed()` falso: manca `?embed=1` o manca `sdk.js` |
| OPP non riceve l'immagine | `postMessage` non inviato, oppure canvas vuoto (`drawImage` prima del caricamento) |
| Funziona in locale ma non online | dimenticato `git push`, oppure cache vecchia: incrementa `CACHE` in `sw.js` |

## 8. Idee per nuovi effetti

- Collage a griglia, poster con testo, QR code, ritaglio circolare, duotone, glitch, cornice Polaroid, testo su percorso, palette da un'immagine (estrai i 5 colori dominanti).
