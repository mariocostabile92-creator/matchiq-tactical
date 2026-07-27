# VE-002 Player Detection Layer

Modulo di ricerca isolato che rileva candidati `person` su immagini statiche.
Non modifica Video AI, backend, API o pipeline attiva.

## Backend disponibili

Il backend raccomandato per la ricerca VE-002 e `rfdetr`. `opencv_hog` resta
disponibile come fallback tecnico e baseline comparativa.

Configurazione RF-DETR validata:

- modello: RF-DETR Small COCO;
- libreria: `rfdetr==1.8.3`;
- pesi ufficiali: `checkpoint_best_regular.pth`;
- fonte: `https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth`;
- percorso locale predefinito:
  `research/vision_spike/checkpoints/rfdetr-small-coco/checkpoint_best_regular.pth`;
- SHA-256:
  `d81979a9213a2109345158ce9232668df4c1ae52e9b8db3f2ec0a8cbad959b33`;
- variabile alternativa: `MATCHIQ_RFDETR_WEIGHTS`;
- nessun download automatico durante inferenza o test.

## Immagine singola

```powershell
.\.venv\Scripts\python.exe -m research.player_detection `
  --backend rfdetr `
  --image "C:\path\frame.jpg" `
  --output "reports\player-detection\rfdetr-single" `
  --threshold 0.30 `
  --device cpu
```

## Directory immagini

```powershell
.\.venv\Scripts\python.exe -m research.player_detection `
  --backend rfdetr `
  --input-dir "C:\path\frames" `
  --output "reports\player-detection\rfdetr-batch" `
  --threshold 0.30 `
  --device cpu
```

## Frame VE-001

```powershell
.\.venv\Scripts\python.exe -m research.player_detection `
  --backend rfdetr `
  --ve001-frames "reports\vision-baseline\partita\frames" `
  --output "reports\player-detection\rfdetr-ve001" `
  --threshold 0.30 `
  --device cpu
```

## Confronto HOG vs RF-DETR

```powershell
.\.venv\Scripts\python.exe -m research.player_detection.compare `
  --input-dir "C:\path\frames" `
  --output "reports\player-detection\comparison" `
  --threshold 0.30 `
  --device cpu
```

Ogni run produce:

- `json/*.json`, un record per immagine valida;
- `debug/*_annotated.jpg`, senza sovrascrivere l'originale;
- `player_detection_manifest.json`;
- `player_detection_report.html`.

## Limiti

RF-DETR COCO e OpenCV HOG sono detector generici di persone, non modelli
addestrati sul calcio. Le detection sono quindi `player_candidate`, non identita
certe. VE-002 non identifica squadre, ruoli, giocatori, pallone o arbitri e non
include tracking, calibrazione del campo o interpretazione tattica.
