# VE-001 Baseline Runner

Runner isolato per misurare la pipeline Video AI corrente senza modificarne
sampling, prompt, tassonomia o algoritmo.

## Esecuzione

Dalla root `backend`, con l'ambiente development ufficiale e una chiave OpenAI
gia configurata:

```powershell
.\.venv\Scripts\python.exe -m research.baseline_runner `
  --video "C:\video\partita.mp4" `
  --output "reports\vision-baseline\partita" `
  --focus "Analisi tattica generale" `
  --desired-count 6
```

Il comando genera:

- `<video>_baseline.json`
- `<video>_baseline.html`
- `frames/` con i JPEG osservati dal selettore

Gli output finiscono sotto `reports/`, gia esclusa da Git.

## Perimetro

Il runner replica:

1. timestamp equidistanti della UI corrente;
2. JPEG a larghezza massima 720 px;
3. score pixel locale con gli stessi pesi del browser;
4. prompt e chiamata OpenAI del selettore corrente;
5. validazione della tassonomia corrente.

Non usa RF-DETR, tracking, calibrazione del campo o analisi di sequenza. Le
confidence riportate mantengono origine e significato attuali e non vengono
ricalibrate.
