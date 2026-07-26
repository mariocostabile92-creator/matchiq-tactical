# L’ambiente MatchIQ è ora riproducibile da zero su Windows con Python 3.11.9.
Runtime, test e Vision separati con versioni bloccate.
.env.example completo e senza credenziali.
Setup automatico Windows creato.
Verifica ambiente non distruttiva creata.
README e audit tecnico completati.
Database e segreti temporanei eliminati.
Verifiche
check_environment.py: 0 errori, 5 warning opzionali.
Backend Uvicorn: avviato correttamente.
/api/health: status: healthy.
Prima suite: 450/450 test superati.
Seconda suite: 450/450 test superati.
pip check: nessun conflitto.
Dipendenze Vision: risoluzione simulata riuscita.
Nessun test saltato.
Setup Windows
cd C:\Users\Mario\Desktop\matchiq-tactical\matchiq-tactical\backend
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1 -Dev
Per installare anche RF-DETR/Torch:
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1 -Vision
La documentazione completa è in [README.md](/C:/Users/Mario/Desktop/matchiq-tactical/matchiq-tactical/backend/README.md) e [environment-reproducibility-audit.md](/C:/Users/Mario/Desktop/matchiq-tactical/matchiq-tactical/backend/docs/environment-reproducibility-audit.md).
Nessuna logica funzionale, API, database, AI, frontend o PWA è stata modificata. Nessun commit e nessun push eseguito. social-assets/ è rimasta intatta.