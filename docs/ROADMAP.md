# Roadmap (non vincolante)

Idee per le fasi future, in ordine sparso. Nessuna è promessa: servono a non perdere le idee buone.

## Effetti

- Collage a griglia con margini configurabili.
- Duotone / poster con testo.
- QR code e codici a barre.
- Ritaglio circolare e cornici.
- Glitch / pixel sort.
- Estrai palette (5 colori dominanti) e applicala alla slide.

## App

- Template di presentazione pronti (oltre ai layout esistenti).
- Migliore accessibilità: navigazione da tastiera nelle card, contrasto, etichette ARIA.
- Internazionalizzazione (IT/EN) per l'interfaccia.
- Anteprima live della slide nell'export.
- Compressione automatica delle immagini importate molto grandi.
- Pannello "Strumento pennello" in modalità compatta mobile (ora gli slider sono nascosti).

## Test e manutenzione

- Formattazione: se serve ridurre le 15.797 righe, `prettier --print-width 200`.
- Profilo di allocazione reale (oltre al test `performance.memory`).
- Test su Firefox/Safari per le parti non-Chromium (PWA esclusa).
- Screenshot di regressione visiva per la ribbon.

## Deploy

- GitHub Actions per eseguire i test a ogni push (invece che in locale).
- Versione `opp-vN` automatica nel service worker (oggi è manuale).
