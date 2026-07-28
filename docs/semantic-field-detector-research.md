# VE-005D - Ricerca mirata sui detector semantici del campo

**Stato:** ricerca tecnica, nessuna implementazione  
**Data di riferimento:** 28 luglio 2026  
**Ambito:** selezione di una direzione tecnica per fornire a VE-005C evidenze semantiche del terreno di gioco  
**Decisione richiesta:** scegliere se integrare, adattare, addestrare o costruire un detector proprietario MatchIQ

> Nota metodologica: licenze, disponibilità dei pesi e stato dei repository possono cambiare. Le conclusioni di questo documento fotografano le fonti primarie consultate alla data indicata. Ogni uso commerciale dovrà essere verificato nuovamente prima dell'adozione.

---

## 1. Executive summary

VE-005C ha dimostrato che una baseline puramente geometrica basata su colore, linee e segmenti non è sufficiente per produrre una calibrazione automatica affidabile nel dominio MatchIQ. Il problema non è soltanto trovare pixel bianchi o prato: il sistema deve capire **quale elemento del campo** è visibile, distinguere elementi geometricamente simili e comunicare l'ambiguità.

La ricerca non identifica oggi un modello pronto che soddisfi contemporaneamente:

- qualità semantica adeguata;
- robustezza su camera fissa, smartphone e campi dilettantistici;
- compatibilità pulita con Python 3.11 e PyTorch moderno;
- costo operativo sostenibile;
- licenza chiara per codice, pesi e dati;
- integrazione isolata con i contratti VE-005C;
- manutenzione ragionevole in un prodotto proprietario.

Le soluzioni accademiche più solide, tra cui PnLCalib e No Bells Just Whistles, sono pubblicate con licenza GPL-2.0 e usano prevalentemente dati SoccerNet o World Cup con vincoli incompatibili o non sufficientemente chiari per l'addestramento commerciale. TVCalib ha codice principale MIT, ma la catena effettiva comprende un submodule di segmentazione e checkpoint per i quali non è stata trovata una licenza separata sufficientemente chiara. SoccerMaster è tecnicamente il candidato più moderno e completo, ma il repository non espone una licenza software chiara e la provenienza/licenza commerciale di tutti i pesi e dati richiede revisione legale.

La raccomandazione è pertanto:

> **Direzione 3 - costruire un detector semantico proprietario MatchIQ, usando un backbone moderno con licenza permissiva verificata e dati autorizzati MatchIQ.**

La forma consigliata è un modello multi-task leggero che produca:

1. regione valida del terreno;
2. elementi lineari semantici;
3. keypoint/intersezioni semantiche;
4. cerchi e archi;
5. orientamento del campo;
6. qualità e ambiguità dell'evidenza.

KpSFR è il miglior riferimento con codice permissivo tra quelli esaminati, ma non è adottabile direttamente senza modernizzazione dello stack e chiarimento su pesi e dati. SoccerMaster è il miglior riferimento tecnico, ma non è legalmente pronto per l'integrazione. SAM 2 è utile esclusivamente per accelerare pseudo-labeling e annotazione, non come detector semantico finale.

Non viene raccomandata l'integrazione immediata di alcun checkpoint pubblico nel runtime MatchIQ.

---

## 2. Problema emerso da VE-005C

VE-005C produce evidenze geometriche isolate e ripetibili:

- `grass_mask`;
- `line_mask`;
- segmenti;
- keypoint immagine;
- cerchi;
- regione valida;
- confidence geometriche;
- motivi di rifiuto.

Questa architettura è corretta come baseline e come strato di validazione, ma non può risolvere da sola l'associazione semantica. Una linea bianca osservata può essere:

- linea laterale;
- linea di fondo;
- linea di metà campo;
- lato dell'area di rigore;
- lato dell'area di porta;
- arco o segmento falsamente linearizzato;
- pubblicità;
- segnaletica esterna;
- artefatto da ombra o compressione.

La sola geometria locale non consente di stabilire in modo affidabile quale corrispondenza usare per una omografia. Nei video MatchIQ il problema è aggravato da:

- campo parzialmente visibile;
- linee scolorite o interrotte;
- prospettiva non broadcast;
- smartphone inclinato;
- zoom e pan;
- ombre nette;
- illuminazione disomogenea;
- reti, recinzioni e panchine;
- campi sintetici con colori non uniformi;
- risoluzione e bitrate variabili.

VE-005C ha già predisposto il punto di integrazione corretto tramite `AdapterResult`: un detector futuro può fornire elementi semantici, flag di ambiguità, confidence separate e artefatti di debug senza sostituire il calibratore geometrico.

Fonti interne:

- [Pitch calibration research](pitch-calibration-research.md)
- [README VE-005C](../research/pitch_calibration/README.md)
- [Audit third-party VE-005C](../research/pitch_calibration/THIRD_PARTY_AUDIT.md)

---

## 3. Requisiti MatchIQ

### 3.1 Requisiti funzionali

Il detector deve poter produrre, quando visibili:

- regione di gioco valida;
- linea laterale e linea di fondo;
- linea di metà campo;
- lati e fronte dell'area di rigore;
- lati e fronte dell'area di porta;
- dischetto del rigore;
- centrocampo;
- cerchio di centrocampo;
- archi dell'area;
- corner e archi d'angolo;
- intersezioni e keypoint semantici;
- orientamento probabile del campo;
- lato di attacco/difesa solo quando inferibile;
- indicazione esplicita di elemento non determinabile.

### 3.2 Requisiti di prodotto

- Flusso automatico come default.
- Nessun obbligo di cliccare quattro punti.
- Fallback manuale possibile in futuro, ma non principale.
- Output deterministico e ispezionabile.
- Nessuna dipendenza da LLM per la geometria.
- Confidence calibrate e separate.
- `UNKNOWN` preferito a una corrispondenza falsa.
- Debug visuale per ogni predizione.
- Compatibilità con camera fissa, smartphone e dilettantismo.

### 3.3 Requisiti tecnici

- Python 3.11.
- PyTorch moderno oppure runtime esportabile.
- Possibile esecuzione GPU; fallback CPU almeno per test e debug.
- Contratto indipendente dal framework.
- Nessun accoppiamento con RF-DETR o ByteTrack.
- Consumo degli output VE-002/VE-003/VE-004 solo come evidenze opzionali.
- Versionamento di modello, tassonomia e checkpoint.
- Riproducibilità e benchmark prima dell'integrazione.

### 3.4 Requisiti legali

Devono essere verificati separatamente:

1. licenza del codice;
2. licenza del checkpoint;
3. licenza del dataset di addestramento;
4. licenze dei submodule;
5. diritto di usare il modello in un prodotto commerciale;
6. diritto di fine-tuning;
7. diritto di distribuire o ospitare i pesi;
8. obblighi di attribuzione o copyleft.

Una licenza permissiva del repository **non rende automaticamente utilizzabili** checkpoint addestrati su dati con restrizioni commerciali.

---

## 4. Metodologia della ricerca

La valutazione usa quattro assi indipendenti:

1. **Capacità semantica:** cosa rileva davvero il modello.
2. **Adozione tecnica:** dipendenze, stack, performance e integrazione.
3. **Adozione legale:** codice, pesi, dati e submodule.
4. **Aderenza al dominio:** robustezza attesa sui video MatchIQ.

Sono state privilegiate fonti primarie:

- paper ufficiali;
- repository degli autori;
- file `LICENSE`;
- README e requirements ufficiali;
- pagine ufficiali dei dataset;
- model card e file dei checkpoint;
- documentazione interna degli spike MatchIQ.

I conteggi di commit e lo stato di manutenzione sono indicatori deboli: descrivono l'attività visibile del repository, non la qualità scientifica. Quando la licenza non è esplicita, lo stato è `UNKNOWN` o `LEGAL_REVIEW_REQUIRED`, mai implicitamente permissivo.

Scala di giudizio:

- `COMPATIBLE`: adozione tecnicamente e legalmente plausibile con evidenze sufficienti.
- `PROBABLY_COMPATIBLE`: compatibilità probabile, ma restano verifiche circoscritte.
- `RESEARCH_ONLY`: utile per benchmark o studio, non per integrazione commerciale.
- `LEGAL_REVIEW_REQUIRED`: merito tecnico presente, diritti insufficientemente chiari.
- `INCOMPATIBLE`: vincolo noto incompatibile con l'adozione prevista.
- `UNKNOWN`: informazioni insufficienti.

---

## 5. Candidati analizzati

### 5.1 KpSFR

**Identità**

- Paper: [Sports Field Registration via Keypoints-Aware Label Condition](https://openaccess.thecvf.com/content/CVPR2022W/CVSports/html/Chu_Sports_Field_Registration_via_Keypoints-Aware_Label_Condition_CVPRW_2022_paper.html).
- Repository: [ericsujw/KpSFR](https://github.com/ericsujw/KpSFR).
- Autori: Yen-Jui Chu, Jheng-Wei Su, Kai-Wen Hsiao, Chi-Yu Lien, Shu-Ho Fan, Min-Chun Hu, Ruen-Rone Lee, Chih-Yuan Yao e Hung-Kuo Chu.
- Stato osservato: repository compatto, circa 6 commit visibili; attività limitata.
- Framework: PyTorch.

**Stack**

- Python dichiarato: `>=3.8`.
- Stack originale: PyTorch 1.9, torchvision 0.9, CUDA 11, OpenCV 4.5.1.48, Shapely 1.7.1.
- Python 3.11: non dichiarato e non dimostrato.
- PyTorch moderno: richiede porting e validazione.
- CPU: possibile in teoria, non target principale.
- GPU: attesa per inferenza/training.

**Output e capacità**

- Predice heatmap/keypoint distribuiti uniformemente sugli elementi del campo.
- Usa dynamic-filter instance segmentation per distinguere keypoint.
- Deriva una omografia dai keypoint.
- Non è una segmentazione semantica completa del terreno.
- Non produce direttamente una tassonomia ricca di linee, regione valida e orientamento.

**Pesi e dati**

- Il README indica pesi preaddestrati per WorldCup e TS-WorldCup.
- Provenienza: server degli autori collegato dal repository.
- Licenza specifica dei pesi: non individuata.
- Dataset: WorldCup e TS-WorldCup; termini commerciali non sufficientemente espliciti nelle fonti trovate.

**Licenze**

- Codice: MIT, come indicato dal repository.
- Pesi: `UNKNOWN`.
- Dataset: `UNKNOWN` / uso di ricerca da verificare.
- Submodule: nessun vincolo principale emerso equivalente a TVCalib, ma va rieseguito audit transitive dependencies.

**Integrazione VE-005C**

- Può alimentare `detected_field_elements` e keypoint semantici.
- Richiede adapter per convertire heatmap e ID in tassonomia MatchIQ.
- Buon riferimento per una testa keypoint proprietaria.
- Non copre da solo regione valida, linee continue e orientation confidence.

**Valutazione**

- Facilità di debug: buona.
- Costo inferenza: medio.
- Fine-tuning: plausibile dopo porting.
- Generalizzazione su dilettantismo: non dimostrata.
- Domain shift atteso: alto.
- Giudizio: `LEGAL_REVIEW_REQUIRED`.
- Ruolo consigliato: riferimento permissivo di architettura, non checkpoint di produzione.

### 5.2 PnLCalib

**Identità**

- Paper: [PnLCalib: Sports Field Camera Calibration via Points and Lines](https://arxiv.org/abs/2404.08401).
- Repository: [mguti97/PnLCalib](https://github.com/mguti97/PnLCalib).
- Stato osservato: circa 70 commit; aggiornamenti recenti e supporto a WorldPose/DDP.
- Framework: PyTorch, HRNet e ottimizzazione geometrica.

**Stack**

- Ambiente derivato da stack di ricerca PyTorch/HRNet.
- Python 3.11: non garantito dal progetto.
- PyTorch moderno: porting plausibile ma non banale.
- CPU: non ideale.
- GPU: raccomandata.

**Output e capacità**

- Modello keypoint e modello linee separati.
- Heatmap per punti e linee.
- Intersezioni linea-linea.
- Raffinamento non lineare PnL.
- Semantica esplicita più ricca di una semplice segmentazione bianca.
- Non è un detector multi-task pensato per qualità editoriale o dominio dilettantistico.

**Pesi e dati**

- Pesi disponibili per single-view, multi-view e fine-tuning su WorldCup14, TS-WorldCup e WorldPose.
- Modelli base addestrati sulla distribuzione SoccerNet.
- Licenza specifica dei pesi: non separata chiaramente dalla licenza del repository.
- Dati SoccerNet: ricerca/non commerciale.
- WorldPose: uso accademico non commerciale e restrizioni di redistribuzione.

**Licenze**

- Codice: GPL-2.0, [LICENSE ufficiale](https://raw.githubusercontent.com/mguti97/PnLCalib/main/LICENSE).
- Pesi: `LEGAL_REVIEW_REQUIRED`.
- Dataset: prevalentemente `RESEARCH_ONLY`.
- Compatibilità con prodotto proprietario: incompatibile per integrazione diretta del codice GPL.

**Integrazione VE-005C**

- Contratti tecnici compatibili concettualmente.
- Adapter possibile per keypoint, linee, confidence e corrispondenze.
- Ottimo benchmark per misurare la qualità di una soluzione MatchIQ.
- Non deve diventare dipendenza del runtime proprietario.

**Valutazione**

- Accuratezza potenziale: alta.
- Complessità: alta.
- Generalizzazione broadcast: buona rispetto ai baseline storici.
- Generalizzazione dilettantismo: da validare.
- Giudizio: `INCOMPATIBLE` per integrazione; `RESEARCH_ONLY` per confronto.

### 5.3 TVCalib

**Identità**

- Paper: [TVCalib: Camera Calibration for Sports Field Registration in Soccer](https://openaccess.thecvf.com/content/WACV2023/papers/Theiner_TVCalib_Camera_Calibration_for_Sports_Field_Registration_in_Soccer_WACV_2023_paper.pdf).
- Repository: [MM4SPA/tvcalib](https://github.com/MM4SPA/tvcalib).
- Stato osservato: circa 13 commit; progetto accademico compatto.
- Framework: PyTorch e ottimizzazione geometrica.

**Stack**

- Python 3.9.
- PyTorch 1.11.
- NumPy 1.19.5.
- Python 3.11/PyTorch moderno: non compatibile senza porting.
- GPU: prevista per la segmentazione.

**Output e capacità**

- Segmentazione semantica degli elementi del campo.
- Ottimizzazione iterativa dei parametri camera.
- Approccio adatto a linee visibili e geometria nota.
- Il detector effettivo risiede nel submodule `sn_segmentation`.

**Pesi e dati**

- Il repository indica il checkpoint `train_59.pt`.
- Provenienza: storage TIB collegato dagli autori.
- Licenza separata del checkpoint: non individuata.
- Dati collegati alla pipeline SoccerNet/segmentazione.

**Licenze**

- Codice principale: MIT.
- Submodule `sn_segmentation`: nessuna licenza individuata nell'audit locale.
- Checkpoint: `UNKNOWN`.
- Dataset: SoccerNet, uso di ricerca/non commerciale.
- Audit interno: [THIRD_PARTY_AUDIT.md](../research/pitch_calibration/THIRD_PARTY_AUDIT.md).

**Integrazione VE-005C**

- L'adapter esistente dimostra che il contratto è tecnicamente sensato.
- La dipendenza effettiva non è attivabile per ragioni legali e di stack.
- La tassonomia può ispirare lo schema MatchIQ.

**Valutazione**

- Accuratezza potenziale: medio-alta su broadcast.
- Dilettantismo: non dimostrato.
- Costo: medio-alto.
- Manutenibilità: bassa senza fork/porting.
- Giudizio: `LEGAL_REVIEW_REQUIRED`; attualmente `RESEARCH_ONLY`.

### 5.4 SoccerNet Calibration baseline

**Identità**

- Repository: [SoccerNet/sn-calibration](https://github.com/SoccerNet/sn-calibration).
- Task ufficiale: [SoccerNet Camera Calibration](https://www.soccer-net.org/tasks/camera-calibration).
- Stato osservato: circa 56 commit; ultimo aggiornamento pubblico del repository intorno al 2024.
- Framework: baseline DeepLabV3 e strumenti di valutazione.

**Stack**

- Stack accademico legato alle release SoccerNet.
- Python 3.11 e PyTorch moderno: non dichiarati come target ufficiale.
- CPU: possibile ma lenta.
- GPU: raccomandata.

**Output e capacità**

- Segmentazione di 26 elementi semantici del terreno.
- Estremità di segmenti e punti semantici.
- È il riferimento tassonomico più diretto per un detector di linee.
- Il task misura completezza e accuratezza della calibrazione, non robustezza commerciale.

**Pesi e dati**

- Pesi baseline disponibili tramite link ufficiale Google Drive nel README.
- Licenza specifica dei pesi: non trovata.
- Dataset ufficiale: oltre 20.000 immagini annotate; dettagli nella sezione dataset.

**Licenze**

- Licenza software del repository: non esposta chiaramente nella root osservata.
- Dataset: la [FAQ SoccerNet](https://www.soccer-net.org/faq) dichiara uso di ricerca e non commerciale.
- Video broadcast soggetti a copyright/NDA.

**Integrazione VE-005C**

- Tassonomia estremamente utile.
- Metriche utili per benchmark MatchIQ.
- Codice/pesi/dati non sono una base commerciale pronta.
- È possibile reimplementare concetti e metriche senza copiare codice o usare dati vietati.

**Valutazione**

- Precisione potenziale: media come baseline.
- Domain shift: alto verso dilettantismo.
- Giudizio: `RESEARCH_ONLY` e `LEGAL_REVIEW_REQUIRED`.

### 5.5 No Bells Just Whistles

**Identità**

- Paper: [No Bells, Just Whistles](https://openaccess.thecvf.com/content/CVPR2024W/CVsports/papers/Gutierrez-Perez_No_Bells_Just_Whistles_Sports_Field_Registration_by_Leveraging_Geometric_CVPRW_2024_paper.pdf).
- Repository: [mguti97/No-Bells-Just-Whistles](https://github.com/mguti97/No-Bells-Just-Whistles).
- Stato osservato: circa 108 commit.
- Framework: PyTorch, due encoder-decoder e geometria DLT.

**Stack**

- Stack di ricerca moderno rispetto ai baseline più vecchi, ma non dichiarato come Python 3.11 production-ready.
- GPU raccomandata.
- CPU non target.

**Output e capacità**

- Heatmap keypoint.
- Heatmap delle estremità delle linee.
- Stima di corrispondenze e omografia tramite DLT.
- Buona separazione tra detection e geometria.
- Semantica inferiore a un modello multi-task completo.

**Pesi e dati**

- Pesi single-view/multi-view.
- Versioni base SoccerNet e fine-tuned WorldCup14/TS-WorldCup.
- Licenza specifica pesi non separata.
- Dati non commerciali o con termini non chiari.

**Licenze**

- Codice: GPL-2.0, [LICENSE ufficiale](https://raw.githubusercontent.com/mguti97/No-Bells-Just-Whistles/main/LICENSE).
- Pesi: `LEGAL_REVIEW_REQUIRED`.
- Dati: `RESEARCH_ONLY`/`UNKNOWN`.
- Integrazione proprietaria diretta: incompatibile.

**Integrazione VE-005C**

- Eccellente riferimento per separare detector di punti, detector di linee e geometria.
- Output facilmente traducibile nei contratti MatchIQ.
- Non adottare codice nel runtime.

**Valutazione**

- Qualità tecnica: alta.
- Debug: buono.
- Manutenibilità commerciale: bassa per licenza.
- Giudizio: `INCOMPATIBLE` per adozione; `RESEARCH_ONLY` come benchmark.

### 5.6 SoccerNet Game State Reconstruction

**Identità**

- Paper: [SoccerNet Game State Reconstruction](https://arxiv.org/abs/2404.11335).
- Repository: [SoccerNet/sn-gamestate](https://github.com/SoccerNet/sn-gamestate).
- Stato osservato: circa 284 commit; progetto attivo e ampio.
- Framework: TrackLab, detector, tracking, re-identification e calibration plugin.

**Stack**

- Ambiente ufficiale osservato: Python 3.9, PyTorch 1.13.1.
- Python 3.11/PyTorch moderno: non garantiti.
- Dipendenze numerose e accoppiamento elevato.
- GPU praticamente necessaria per la pipeline completa.

**Output e capacità**

- Ricostruzione di stato di gioco, non detector semantico isolato.
- Include componenti e plugin di calibrazione.
- Può servire da benchmark end-to-end.
- Introduce molto più del necessario per VE-005C.

**Pesi e dati**

- Modelli preaddestrati e dataset GSR ufficiali.
- Dataset composto da clip annotate SoccerNet.
- Vincoli SoccerNet non commerciali.

**Licenze**

- Codice: GPL-3.0, [LICENSE ufficiale](https://raw.githubusercontent.com/SoccerNet/sn-gamestate/main/LICENSE).
- Pesi: da verificare singolarmente.
- Dataset: ricerca/non commerciale.

**Integrazione VE-005C**

- Eccessivamente monolitico rispetto ai contratti isolati MatchIQ.
- Licenza e dipendenze ne impediscono l'adozione diretta.
- Utile per comprendere interfacce tra tracking, calibrazione e game state.

**Valutazione**

- Qualità tecnica: alta come piattaforma di ricerca.
- Costo/complessità: molto alti.
- Giudizio: `INCOMPATIBLE` per runtime proprietario; `RESEARCH_ONLY`.

### 5.7 Sportlight SoccerNet Calibration 2023

**Identità**

- Paper tecnico: [Automatic Camera Calibration for Soccer Broadcasts](https://arxiv.org/abs/2410.07401).
- Repository: [NikolasEnt/soccernet-calibration-sportlight](https://github.com/NikolasEnt/soccernet-calibration-sportlight).
- Stato osservato: circa 39 commit.
- Framework: HRNet, keypoint e line detection.

**Stack**

- Linux e Docker.
- Python 3.10.
- PyTorch 2.0, CUDA 11.8.
- GPU NVIDIA con memoria elevata indicata dal progetto.
- Python 3.11/PyTorch moderno: non dimostrati.

**Output e capacità**

- Due modelli: keypoint e linee.
- Tassonomia di circa 57 punti.
- Calibrazione euristica successiva.
- Buona copertura semantica, ma stack pesante.

**Pesi e dati**

- Il README non rende immediatamente evidente un pacchetto completo di checkpoint pronto.
- Addestramento/valutazione sul dominio SoccerNet.
- Pesi: `UNKNOWN`.

**Licenze**

- Licenza software esplicita non individuata nella root del repository.
- Dataset SoccerNet non commerciale.
- Stato legale: `UNKNOWN`.

**Integrazione VE-005C**

- Output coerenti con l'adapter MatchIQ.
- Requisiti hardware troppo elevati per una prima integrazione.
- Utile per tassonomia e benchmark.

**Valutazione**

- Precisione potenziale: alta su broadcast.
- Dilettantismo: non dimostrato.
- Manutenibilità: medio-bassa.
- Giudizio: `LEGAL_REVIEW_REQUIRED` / `RESEARCH_ONLY`.

### 5.8 SoccerMaster

**Identità**

- Paper: [SoccerMaster: A Vision Foundation Model for Soccer Understanding](https://openaccess.thecvf.com/content/CVPR2026/papers/Yang_SoccerMaster_A_Vision_Foundation_Model_for_Soccer_Understanding_CVPR_2026_paper.pdf).
- Repository: [haolinyang-hlyang/SoccerMaster](https://github.com/haolinyang-hlyang/SoccerMaster).
- Project page: [SoccerMaster](https://haolinyang-hlyang.github.io/SoccerMaster/).
- Stato osservato: repository recente, circa 9 commit.
- Framework: PyTorch, backbone foundation e task head multipli.

**Stack**

- Python 3.10.16.
- PyTorch 2.4.1, torchvision 0.19.1, CUDA 12.1.
- Componenti come TrackLab, SAM 2 e flash-attn.
- Python 3.11: plausibile ma non dichiarato.
- GPU: necessaria; costi di memoria e deployment elevati.

**Output e capacità**

- Modello foundation specifico per calcio.
- Head per keypoint e line detection.
- Componenti per detection, tracking e comprensione.
- Registrazione basata su PnL.
- È il candidato tecnicamente più vicino a una piattaforma completa moderna.

**Pesi e dati**

- Model hub: [xleprime/SoccerMaster](https://huggingface.co/xleprime/SoccerMaster).
- File visibili comprendono backbone e checkpoint di keypoint/line detector.
- La model card espone metadato `apache-2.0`, ma non documenta in modo sufficiente provenienza, training data e termini specifici di ogni file.
- Dataset SoccerFactory: circa 7.000 sequenze video con annotazioni per frame secondo le fonti ufficiali del progetto.
- Licenza dataset chiara e completa: non individuata.

**Licenze**

- Repository GitHub: nessun file `LICENSE` esplicito individuato.
- Model card: metadato Apache-2.0, insufficiente da solo a coprire codice, tutti i pesi e dati.
- Dataset: `UNKNOWN`.
- Submodule: licenze eterogenee, da auditare separatamente.

**Integrazione VE-005C**

- Può teoricamente fornire keypoint e linee molto ricchi.
- Lo stack è troppo ampio per un adapter minimo.
- L'isolamento in servizio separato sarebbe obbligatorio.
- Il costo operativo è incompatibile con un primo MVP senza benchmark.

**Valutazione**

- Miglior candidato tecnico.
- Miglior compatibilità concettuale con una roadmap completa.
- Peggiore combinazione di incertezza legale e costo.
- Giudizio: `LEGAL_REVIEW_REQUIRED`; non adottabile ora.

### 5.9 Central-view geometry

**Identità**

- Paper: [Can Geometry Save Central Views for Sports Field Registration?](https://openaccess.thecvf.com/content/CVPR2025W/CVSPORTS/papers/Magera_Can_Geometry_Save_Central_Views_for_Sports_Field_Registration_CVPRW_2025_paper.pdf).
- Tipo: metodo geometrico complementare.
- Codice/checkpoint ufficiale: non individuato durante questa ricerca.

**Stack e output**

- Usa corrispondenze legate a cerchio e geometria per risolvere viste centrali difficili.
- Non è un detector semantico.
- Non sostituisce segmentazione, keypoint o line detection.
- Può migliorare il solver quando il detector fornisce cerchi e punti affidabili.

**Licenze e dati**

- Codice: `UNKNOWN`.
- Checkpoint: non applicabile/non individuato.
- Dati: dipendono dalla valutazione del paper.

**Integrazione VE-005C**

- Molto interessante come futuro raffinamento geometrico.
- VE-005C già espone circle candidates e confidence separate.
- Nessuna adozione possibile senza implementazione indipendente e validazione.

**Valutazione**

- Costo inferenza: potenzialmente basso.
- Rischio legale: dipende da eventuale implementazione propria del metodo descritto.
- Giudizio: `RESEARCH_ONLY`.

### 5.10 Sports Field Localization via Deep Structured Models

**Identità**

- Paper: [Sports Field Localization via Deep Structured Models](https://openaccess.thecvf.com/content_cvpr_2017/papers/Homayounfar_Sports_Field_Localization_CVPR_2017_paper.pdf).
- Pagina autore: [Nima Homayounfar](https://nhoma.github.io/).
- Anno: 2017.
- Framework: deep semantic cues più modello strutturato/MRF.

**Stack e output**

- Evidenze semantiche per superficie, linee e cerchi.
- Ottimizzazione strutturata rispetto al modello del campo.
- Architettura storicamente importante, ma non pronta per stack moderno.
- Codice/dati collegati dalla pagina autore, con manutenzione e compatibilità non dimostrate.

**Licenze**

- Codice: `UNKNOWN`.
- Pesi: `UNKNOWN`.
- Dataset: `UNKNOWN`.

**Integrazione VE-005C**

- Conferma il valore di una pipeline ibrida: evidenze apprese più vincoli geometrici.
- Buon riferimento concettuale per Strategy G.
- Non candidato diretto al runtime.

**Valutazione**

- Precisione moderna: inferiore ai candidati recenti.
- Manutenibilità: bassa.
- Giudizio: `RESEARCH_ONLY`.

### 5.11 SAM 2 come strumento ausiliario

SAM 2 non viene contato come detector semantico candidato principale perché non assegna autonomamente la tassonomia calcistica richiesta. È però rilevante per il processo dati.

- Repository: [facebookresearch/sam2](https://github.com/facebookresearch/sam2).
- Codice e checkpoint: Apache-2.0 dichiarato dal progetto.
- Stack: Python >=3.10, PyTorch >=2.5.1, torchvision >=0.20.1.
- Python 3.11/PyTorch moderno: compatibile in linea di principio.
- Funzione utile: propagare maschere e accelerare annotazioni assistite.
- Funzione non adatta: decidere da solo se una linea è area, metà campo o linea laterale.
- Giudizio: `COMPATIBLE` come tool di pseudo-labeling/annotazione, non come detector finale.

---

## 6. Tabella comparativa tecnica

| Candidato | Output principale | Semantica | Py 3.11 | PyTorch moderno | CPU | GPU | Costo | Dominio dilettanti | Integrazione VE-005C |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| KpSFR | keypoint heatmap + omografia | Media | Non provata | Porting | Limitata | Sì | Medio | Non provato | Buona |
| PnLCalib | keypoint + linee + PnL | Alta | Non provata | Porting | Limitata | Sì | Alto | Da validare | Ottima concettualmente |
| TVCalib | segmenti semantici + camera | Alta | No, stack 3.9 | No, stack 1.11 | Limitata | Sì | Medio-alto | Non provato | Adapter già progettato |
| SoccerNet baseline | 26 linee semantiche | Alta | Non provata | Non provata | Lenta | Sì | Medio | Debole attesa | Ottima tassonomia |
| No Bells | punti + estremità linee + DLT | Medio-alta | Non provata | Porting | Limitata | Sì | Alto | Da validare | Ottima concettualmente |
| SoccerNet GSR | pipeline game state | Indiretta | No target | Stack datato | No pratica | Sì | Molto alto | Non provato | Eccessiva |
| Sportlight | 57 keypoint + linee | Alta | Non provata | PyTorch 2.0 | No pratica | Sì, >=24 GB indicati | Molto alto | Non provato | Buona ma pesante |
| SoccerMaster | foundation + head linee/keypoint | Molto alta | Plausibile | Sì, 2.4.1 | No pratica | Sì | Molto alto | Non provato | Potente ma complessa |
| Central-view geometry | solver su cerchi | Non detector | N/D | N/D | Plausibile | Non necessaria | Basso | Da validare | Complementare |
| Deep Structured Models | superficie + linee + cerchi | Alta | No evidenza | Stack storico | Limitata | Sì | Alto | Non provato | Riferimento |

---

## 7. Tabella licenze

| Candidato | Codice | Checkpoint | Dataset | Submodule | Stato commerciale |
|---|---|---|---|---|---|
| KpSFR | MIT | Non specificata | WorldCup/TSWC non chiariti | Da auditare | `LEGAL_REVIEW_REQUIRED` |
| PnLCalib | GPL-2.0 | Non separata | SoccerNet/WorldPose/WorldCup | Da auditare | `INCOMPATIBLE` diretto |
| TVCalib | MIT principale | Non specificata | SoccerNet non commerciale | `sn_segmentation` senza licenza trovata | `LEGAL_REVIEW_REQUIRED` |
| SoccerNet Calibration | Non chiara nella root | Non specificata | Ricerca, non commerciale | Da auditare | `RESEARCH_ONLY` |
| No Bells | GPL-2.0 | Non separata | SoccerNet/WorldCup | Da auditare | `INCOMPATIBLE` diretto |
| SoccerNet GSR | GPL-3.0 | Eterogenea | SoccerNet non commerciale | Numerosi | `INCOMPATIBLE` diretto |
| Sportlight | Non individuata | Non individuata | SoccerNet non commerciale | Da auditare | `UNKNOWN` |
| SoccerMaster | Non individuata nel repo | Model card Apache-2.0, dettagli insufficienti | SoccerFactory non chiarita | Numerosi, eterogenei | `LEGAL_REVIEW_REQUIRED` |
| Central-view geometry | Codice non individuato | N/D | Da verificare | N/D | `RESEARCH_ONLY` |
| Deep Structured Models | Non chiarita | Non chiarita | Non chiarita | Da verificare | `RESEARCH_ONLY` |
| SAM 2 ausiliario | Apache-2.0 | Apache-2.0 dichiarata | SA-V/non necessaria per uso checkpoint da verificare per caso | Ufficiali | `COMPATIBLE` come tool ausiliario |

### Regola operativa

Prima di adottare qualsiasi artefatto:

- archiviare copia della licenza;
- registrare URL, hash e data di download;
- associare il checkpoint alla sua model card;
- associare il training dataset e i relativi termini;
- verificare i submodule;
- produrre una Software Bill of Materials;
- richiedere revisione legale quando una catena è incompleta.

---

## 8. Dataset pubblici

| Dataset | Dimensione dichiarata | Annotazioni | Dominio | Uso commerciale | Uso MatchIQ consigliato |
|---|---:|---|---|---|---|
| SoccerNet Calibration | 20.028 + 2.104 immagini challenge | linee, estremità, calibrazione | broadcast | No, termini di ricerca | benchmark soltanto |
| WorldCup 2014 | variabile secondo distribuzione | keypoint/omografia | broadcast | Non chiarito | ricerca dopo verifica |
| TS-WorldCup | 3.812 immagini, 43 video | keypoint in sequenza | broadcast | Non chiarito | confronto temporale |
| WorldPose | >80 sequenze, circa 2,5M pose 3D | pose e camera | professionistico | No, accademico | ricerca soltanto |
| SoccerNet GSR | 200 clip | game state, tracking, camera | broadcast | No, termini SoccerNet | benchmark end-to-end |
| SoccerFactory | circa 7.000 sequenze | box, ruoli, numeri, camera | calcio professionistico | Non chiarito | nessun uso prima di audit |
| MatchIQ proprietario | da costruire | linee, keypoint, regione, orientamento | dilettantismo | Sì, con diritti documentati | training e benchmark primari |

### 8.1 SoccerNet Calibration

- Fonte: [task ufficiale](https://www.soccer-net.org/tasks/camera-calibration), [data page](https://www.soccer-net.org/data), [FAQ](https://www.soccer-net.org/faq).
- Dimensione dichiarata dal task: 20.028 immagini da 500 partite, più 2.104 immagini challenge.
- Annotazioni: elementi semantici del campo, estremità di linee e parametri/calibrazione associata.
- Dominio: broadcast professionistico.
- Accesso: registrazione/NDA secondo le procedure SoccerNet.
- Licenza/uso: ricerca, non destinato all'uso commerciale.
- Redistribuzione: limitata dai termini e dal copyright dei video.
- Compatibilità MatchIQ commerciale: no per training commerciale diretto.
- Compatibilità dilettantismo: bassa/media; forte domain shift.
- Uso consigliato: benchmark di ricerca, se consentito.

### 8.2 WorldCup 2014

- Fonti: collegamenti e istruzioni nei repository [KpSFR](https://github.com/ericsujw/KpSFR) e [No Bells](https://github.com/mguti97/No-Bells-Just-Whistles).
- Dominio: broadcast FIFA professionistico.
- Annotazioni: keypoint/omografie a seconda della distribuzione usata.
- Dimensione: varia in base alla versione/distribuzione; non assumere un numero unico.
- Accesso e licenza: termini commerciali non chiariti nelle fonti esaminate.
- Redistribuzione: non presumere consentita.
- Compatibilità MatchIQ: `UNKNOWN`; solo ricerca dopo verifica.
- Dilettantismo: domain shift alto.

### 8.3 TS-WorldCup

- Fonte: [KpSFR](https://github.com/ericsujw/KpSFR).
- Dimensione dichiarata: 3.812 immagini time-sequence da 43 video dei Mondiali 2014/2018.
- Annotazioni: keypoint/corrispondenze per registrazione in sequenza.
- Dominio: broadcast professionistico.
- Licenza: non individuata in forma sufficiente per uso commerciale.
- Training commerciale/redistribuzione: non autorizzati per presunzione.
- Compatibilità dilettantismo: bassa/media.
- Uso consigliato: ricerca e confronto temporale, dopo autorizzazione.

### 8.4 WorldPose

- Fonti: [WorldPose](https://worldpose.ait.ethz.ch/) e [WorldPose Dataset](https://eth-ait.github.io/WorldPoseDataset/).
- Dimensione: oltre 80 sequenze e circa 2,5 milioni di pose 3D secondo la pagina ufficiale.
- Annotazioni: pose, camera e contesto multi-camera.
- Dominio: calcio professionistico.
- Licenza: uso accademico non commerciale, restrizioni di redistribuzione.
- Training commerciale: non consentito.
- Compatibilità dilettantismo: limitata.
- Uso consigliato: ricerca accademica, non pipeline commerciale.

### 8.5 SoccerNet Game State Reconstruction

- Fonte: [repository ufficiale](https://github.com/SoccerNet/sn-gamestate).
- Dimensione dichiarata: 200 clip annotate nella release corrente descritta dal progetto.
- Annotazioni: detection, tracking, ruoli, team, camera/game state.
- Dominio: broadcast professionistico.
- Licenza: vincoli SoccerNet non commerciali.
- Compatibilità MatchIQ: ricerca soltanto.
- Valore: benchmark end-to-end, non dataset primario del detector semantico.

### 8.6 SoccerFactory / SoccerMaster

- Fonti: [SoccerMaster repository](https://github.com/haolinyang-hlyang/SoccerMaster) e [project page](https://haolinyang-hlyang.github.io/SoccerMaster/).
- Dimensione dichiarata: circa 7.000 sequenze video.
- Annotazioni: bounding box, ruoli, numeri, camera e task calcistici secondo il progetto.
- Dominio: principalmente professionistico/broadcast.
- Accesso/licenza: licenza completa del dataset non individuata.
- Training commerciale: `UNKNOWN`.
- Redistribuzione: `UNKNOWN`.
- Compatibilità MatchIQ: non adottare prima di revisione legale.

### 8.7 Dataset proprietario MatchIQ

- Fonte: video caricati con consenso e partite autorizzate.
- Dominio: camera fissa, smartphone, campi e categorie dilettantistiche.
- Annotazioni: progettate espressamente per la tassonomia MatchIQ.
- Licenza: controllabile mediante consenso, contratto, retention e revoca.
- Valore: massimo per il prodotto.
- Rischio: costo di annotazione, varietà insufficiente e gestione minori.
- Compatibilità commerciale: sì, solo con catena documentale completa.
- Necessità: indispensabile anche se viene usato un pretraining pubblico.

---

## 9. Compatibilità Python e PyTorch

### 9.1 Compatibilità dimostrata

Nessun candidato principale è stato dimostrato, dalle sole istruzioni ufficiali, come soluzione pronta per:

- Python 3.11;
- versione PyTorch moderna scelta da MatchIQ;
- Windows e Linux;
- GPU e fallback CPU;
- installazione isolata senza conflitti.

### 9.2 Candidati più vicini

- SoccerMaster usa PyTorch 2.4.1, ma dichiara Python 3.10.16 e ha dipendenze pesanti.
- SAM 2 usa stack moderno e supporta Python >=3.10, ma non è un detector semantico.
- Sportlight usa PyTorch 2.0/Python 3.10, con requisiti GPU elevati.
- KpSFR, TVCalib e altri baseline richiedono porting.

### 9.3 Strategia raccomandata

Il nuovo detector MatchIQ deve essere sviluppato e testato direttamente su:

- Python 3.11;
- una versione PyTorch supportata e bloccata nel modulo research;
- CUDA opzionale e documentata;
- ONNX/TensorRT solo dopo una baseline affidabile;
- contratti JSON/NumPy indipendenti dal framework.

La compatibilità va verificata in CI; non deve dipendere da un ambiente accademico congelato.

---

## 10. Capacità semantiche

### 10.1 Segmentazione di linee

Risponde alla domanda: "quali pixel appartengono a un elemento lineare del campo?"

Non basta se tutte le linee condividono una sola classe. Per VE-005C servono classi canoniche o un sistema di corrispondenza che restituisca ambiguità.

### 10.2 Keypoint detection

Risponde alla domanda: "dove si trova una intersezione o un punto canonico?"

È utile quando le linee sono parziali, ma soffre se il keypoint è fuori inquadratura o se la prospettiva rende simili più configurazioni.

### 10.3 Field registration

Risponde alla domanda: "quale trasformazione collega immagine e modello del campo?"

Non è sinonimo di detector. TVCalib, PnLCalib e No Bells combinano evidenze apprese con solver geometrici.

### 10.4 Regione valida

Deve distinguere:

- terreno giocabile;
- bordo campo;
- pista;
- tribuna;
- panchina;
- zone occluse.

Una grass mask basata sul colore è fragile; un modello semantico deve prevedere anche qualità e visibilità.

### 10.5 Orientamento

Serve a ridurre corrispondenze speculari. Deve essere espresso come probabilità o stato ambiguo, non come decisione forzata.

### 10.6 Conclusione semantica

La miglior rappresentazione per MatchIQ non è una singola mask. È un insieme coerente di:

- polilinee semantiche;
- keypoint;
- cerchi/archi;
- regione valida;
- orientamento;
- visibilità;
- qualità;
- ambiguità.

---

## 11. Compatibilità con VE-005C

### 11.1 Contratto proposto

Un futuro adapter deve restituire almeno:

```json
{
  "model_version": "semantic-field-v0",
  "taxonomy_version": "matchiq-pitch-v1",
  "detected_field_elements": [],
  "image_keypoints": [],
  "valid_field_region": null,
  "orientation": {
    "label": "UNKNOWN",
    "confidence": 0.0
  },
  "technical_quality": 0.0,
  "semantic_confidence": 0.0,
  "ambiguity_flags": [],
  "artifacts": {}
}
```

### 11.2 Regole di integrazione

- VE-005C resta proprietario della validazione geometrica.
- Il detector propone evidenze, non una verità finale.
- Le confidence del detector non vengono confuse con projection confidence.
- Il solver può rifiutare evidenze semanticamente forti ma geometricamente incoerenti.
- Tutti gli output sono salvati per benchmark e feedback.
- Nessun candidato deve importare direttamente moduli applicativi MatchIQ.

### 11.3 Informazioni opzionali da VE-002/003/004

Le detection e le track possono:

- aiutare a escludere occlusioni;
- stimare se l'inquadratura contiene abbastanza giocatori;
- migliorare valid field region;
- fornire foot point per il controllo della proiezione.

Non devono essere requisito per rilevare le linee. Il detector campo deve poter funzionare anche prima o senza tracking.

---

## 12. Classifica finale

### 12.1 Classifica tecnica

1. **SoccerMaster** - più moderno e completo, ma pesante e legalmente incerto.
2. **PnLCalib** - forte separazione punti/linee e solver robusto; GPL.
3. **No Bells Just Whistles** - pipeline chiara e competitiva; GPL.
4. **Sportlight** - tassonomia ricca, ma pesante e licenza non chiara.
5. **TVCalib** - semantica utile, stack vecchio e catena licenze incompleta.
6. **KpSFR** - elegante, permissivo nel codice, più limitato semanticamente.
7. **SoccerNet baseline** - tassonomia/benchmark utile, non prodotto.
8. **Central-view geometry** - complemento prezioso, non detector.
9. **Deep Structured Models** - riferimento storico.
10. **SoccerNet GSR** - potente come piattaforma, eccessivo per questo modulo.

### 12.2 Classifica per adottabilità commerciale immediata

1. **Nessun candidato pronto**.
2. KpSFR come base concettuale con reimplementazione/modernizzazione e dati propri.
3. SAM 2 come tool ausiliario di annotazione.
4. Tutti gli altri come benchmark o riferimenti, soggetti ai rispettivi vincoli.

### 12.3 Miglior candidato permissivo

**KpSFR**, limitatamente al codice MIT. Non si estende automaticamente ai checkpoint e ai dataset.

### 12.4 Miglior candidato tecnico non adottabile ora

**SoccerMaster**, per copertura e stack moderno, ma con:

- licenza del repository non chiara;
- catena checkpoint/dataset non sufficientemente documentata;
- dipendenze ampie;
- costo GPU elevato;
- dominio dilettantistico non validato.

---

## 13. Direzione raccomandata

### Decisione: Direzione 3

**Costruire un detector MatchIQ proprietario su backbone moderno e permissivo, addestrato con dati autorizzati MatchIQ.**

Non significa addestrare ogni componente da zero. Significa controllare:

- tassonomia;
- codice della testa semantica;
- dati;
- checkpoint finale;
- metriche;
- compatibilità;
- distribuzione;
- feedback.

### Architettura preferita

Strategia G, con elementi della F:

- backbone moderno con provenienza e licenza verificate;
- testa per valid field region;
- testa per semantic line segmentation;
- testa keypoint/intersections;
- testa circle/arc;
- testa orientation/visibility;
- confidence calibrate;
- solver geometrico VE-005C separato.

### Perché

- È la sola strada che può ottimizzare il dominio dilettantistico.
- Evita il lock-in verso stack accademici obsoleti.
- Mantiene separata la proprietà intellettuale MatchIQ.
- Permette benchmark progressivi.
- Trasforma feedback e correzioni in dataset proprietario.
- Riduce il rischio di distribuire pesi con provenienza incerta.

### Condizione

Il backbone e gli eventuali pesi iniziali devono ricevere un audit separato di codice, model card e training data. "Open source" non è una categoria legale sufficiente.

---

## 14. Fallback raccomandato

Se il detector proprietario non raggiunge una qualità minima:

1. mantenere VE-005C come baseline e filtro geometrico;
2. usare KpSFR reimplementato/modernizzato come baseline keypoint;
3. aggiungere fallback manuale assistito solo nei casi rifiutati;
4. usare i sistemi GPL esclusivamente offline per benchmark interno, senza incorporarne codice o output nel prodotto se non legalmente autorizzato;
5. usare SAM 2 per velocizzare annotazioni, sempre con revisione umana;
6. non forzare calibrazione quando semantic e geometric confidence sono insufficienti.

---

## 15. Candidati esclusi dall'integrazione diretta

| Candidato | Motivo principale |
|---|---|
| PnLCalib | GPL-2.0 e dati/pesi non commerciali o incerti |
| No Bells | GPL-2.0 e dati/pesi non commerciali o incerti |
| SoccerNet GSR | GPL-3.0, dati non commerciali, stack eccessivo |
| SoccerNet baseline | dati non commerciali e licenza software/pesi non chiara |
| TVCalib | submodule e checkpoint non chiariti; stack obsoleto |
| Sportlight | licenza non individuata e requisiti hardware elevati |
| SoccerMaster | licenza repo/dati e provenienza checkpoint non sufficienti |
| Central-view geometry | non è un detector e non ha implementazione ufficiale adottabile individuata |
| Deep Structured Models | stack storico e licenze non chiare |

L'esclusione riguarda l'integrazione diretta nel prodotto, non il valore scientifico.

---

## 16. Build vs fine-tuning vs integrazione

### Strategia A - Integrare direttamente un modello permissivo

- Dati: nessun nuovo dato iniziale, ma serve benchmark MatchIQ.
- Annotazione: bassa all'inizio.
- Complessità: bassa/media.
- Tempo: breve.
- GPU: dipende dal modello.
- Rischio: checkpoint e training data spesso non coperti dalla licenza del codice.
- Precisione potenziale: media.
- Manutenibilità: media.
- Integrazione: buona se l'output è isolato.
- Decisione: non disponibile oggi un candidato pienamente verificato.

### Strategia B - Usare un baseline accademico

- Dati: benchmark pubblico.
- Annotazione: bassa.
- Complessità: media.
- Tempo: breve per ricerca.
- GPU: media/alta.
- Rischio: domain shift e licenze.
- Precisione potenziale: buona su broadcast.
- Manutenibilità: bassa.
- Integrazione: solo ambiente research.
- Decisione: utile come riferimento, non produzione.

### Strategia C - Fine-tuning di modello permissivo

- Dati: migliaia di frame autorizzati.
- Annotazione: media/alta.
- Complessità: media.
- Tempo: medio.
- GPU: media.
- Rischio: licenza del checkpoint base e tassonomia incompatibile.
- Precisione potenziale: alta.
- Manutenibilità: buona se lo stack è moderno.
- Integrazione: buona.
- Decisione: valida solo dopo audit del backbone/checkpoint.

### Strategia D - Addestrare MatchIQ da zero

- Dati: molti frame e varietà elevata.
- Annotazione: molto alta.
- Complessità: alta.
- Tempo: lungo.
- GPU: alta.
- Rischio: convergenza e costi.
- Precisione potenziale: alta nel dominio, ma incerta all'inizio.
- Manutenibilità: massima proprietà, massimo onere.
- Integrazione: ottima.
- Decisione: non consigliata come primo passo assoluto.

### Strategia E - Segmentazione generica + classificatore semantico

- Dati: mask più label di segmento.
- Annotazione: alta.
- Complessità: medio-alta.
- Tempo: medio.
- GPU: media.
- Rischio: errori a cascata e associazione instabile.
- Precisione potenziale: media.
- Manutenibilità: due modelli/pipeline.
- Integrazione: discreta.
- Decisione: fallback sperimentale, non prima scelta.

### Strategia F - Modelli separati keypoint + linee

- Dati: keypoint e polilinee.
- Annotazione: alta.
- Complessità: alta.
- Tempo: medio-lungo.
- GPU: medio-alta.
- Rischio: incoerenza tra output.
- Precisione potenziale: alta.
- Manutenibilità: media.
- Integrazione: molto buona con VE-005C.
- Decisione: valida se il multi-task non converge.

### Strategia G - Multi-task: terreno, linee, keypoint, orientation

- Dati: annotazioni multi-livello.
- Annotazione: molto alta ma riusabile.
- Complessità: alta.
- Tempo: medio-lungo.
- GPU: media/alta.
- Rischio: bilanciamento delle loss.
- Precisione potenziale: più alta nel dominio MatchIQ.
- Manutenibilità: buona con backbone unico.
- Integrazione: ottima.
- Decisione: **strategia consigliata**.

### Strategia H - Foundation model per pseudo-labeling

- Dati: video autorizzati più prompt/seed.
- Annotazione: ridotta, non eliminata.
- Complessità: media.
- Tempo: breve per tool interno.
- GPU: alta durante pseudo-labeling.
- Rischio: label rumorose e bias.
- Precisione potenziale: dipende dalla revisione.
- Manutenibilità: il foundation model non entra nel runtime.
- Integrazione: indiretta.
- Decisione: consigliata come acceleratore dati, non prodotto.

---

## 17. Dataset minimo proprietario

Le quantità seguenti sono stime ingegneristiche e sono **da validare durante la raccolta dati**.

### Fase 0 - Tassonomia e benchmark

- 500-1.000 frame.
- 10-20 partite.
- almeno 5 impianti;
- camera fissa e smartphone;
- luce, ombra, pioggia, sintetico e naturale;
- split per partita, mai per frame adiacenti.

Obiettivo: validare lo schema, lo strumento di annotazione e le metriche.

### MVP detector

- 3.000-8.000 frame accuratamente stratificati.
- 20-50 partite autorizzate.
- campi e dispositivi diversi;
- forte quota di hard negative;
- almeno due revisori su subset critico.

Obiettivo: superare VE-005C nei casi in cui le linee sono visibili ma semanticamente ambigue.

### Robustezza di produzione

- 15.000-40.000 frame.
- 80-200 partite.
- active learning;
- revisione continua di errori;
- copertura di inquadrature rare.

Obiettivo: generalizzare tra società, campi e dispositivi. Anche questi range sono **da validare durante la raccolta dati**.

### Regole di split

- Nessun frame della stessa partita in train e test.
- Preferibilmente nessun impianto condiviso tra train e test principale.
- Test separati per camera fissa, smartphone e broadcast autorizzato.
- Holdout permanente non usato nel tuning.

---

## 18. Schema preliminare di annotazione

### 18.1 Metadati

- `match_id`;
- `venue_id`;
- `camera_type`;
- `device_family`;
- `resolution`;
- `weather`;
- `lighting`;
- `surface_type`;
- `camera_motion`;
- `rights_record_id`;
- `annotation_version`.

### 18.2 Regione

- poligono del terreno visibile;
- poligoni esclusi;
- percentuale campo visibile;
- occlusione;
- qualità immagine.

### 18.3 Elementi lineari

Ogni polilinea:

- classe canonica;
- punti;
- visibilità;
- occlusione;
- confidence annotatore;
- `UNKNOWN_LINE` se non determinabile.

Tassonomia iniziale:

- touchline left/right;
- goal line near/far;
- halfway line;
- penalty area left/right/front;
- goal area left/right/front;
- center circle;
- penalty arc;
- corner arc;
- unknown field marking.

I nomi finali e la gestione della simmetria sono **da validare durante la raccolta dati**.

### 18.4 Keypoint

- ID canonico;
- coordinate;
- visibile/occluso/inferito;
- origine: intersezione, tangente, centro, dischetto;
- confidence annotatore.

### 18.5 Orientamento

- attacco da sinistra a destra;
- attacco da destra a sinistra;
- vista centrale;
- sconosciuto;
- confidence;
- evidenza usata.

### 18.6 Ambiguità e hard negative

- linea pubblicitaria;
- bordo ombra;
- recinzione;
- tetto/panchina;
- bordo area tecnica;
- grafica televisiva;
- segnaletica non regolamentare;
- linea di altro sport;
- prato scolorito.

### 18.7 Revisione

- annotatore;
- revisore;
- stato;
- motivo correzione;
- versione;
- timestamp;
- eventuale consenso alla pubblicazione dell'artefatto.

---

## 19. Costi qualitativi e rischi

### 19.1 Costi

- Tool di annotazione polilinee/keypoint.
- Definizione tassonomia.
- Revisione senior.
- Storage video e frame.
- GPU training.
- Benchmark e regression set.
- Audit legale di backbone/checkpoint.
- Monitoraggio drift.

### 19.2 Rischi tecnici

- Tassonomia troppo dettagliata.
- Annotation inconsistency.
- Domain imbalance.
- Overfitting sul campo del founder.
- Modello che impara grafiche/tribune.
- Confidence non calibrata.
- Simmetrie non risolte.
- Errori propagati al solver.
- GPU cost troppo alto.

### 19.3 Rischi legali

- Video con minori senza consenso adeguato.
- Revoca dei diritti.
- Checkpoint con training data incompatibili.
- Submodule copyleft.
- Pseudo-label derivati da modelli con termini non verificati.
- Redistribuzione involontaria di frame.

### 19.4 Mitigazioni

- Dataset registry.
- Model registry.
- License manifest.
- Split per impianto.
- Hard-negative library.
- Revisione umana.
- Rifiuto esplicito.
- Benchmark permanente.
- Audit prima di ogni nuovo checkpoint.

---

## 20. Roadmap del prossimo sprint

### VE-005E - Semantic Field Dataset & Benchmark Contract

1. Congelare tassonomia MatchIQ v1.
2. Definire formato annotazione.
3. Definire conversione verso `AdapterResult`.
4. Costruire un benchmark autorizzato piccolo.
5. Annotare hard negative.
6. Definire metriche per linee, keypoint, regione e orientation.
7. Verificare inter-annotator agreement.
8. Auditare 2-3 backbone permissivi moderni e i relativi checkpoint.
9. Prototipare offline Strategy G senza collegarla al prodotto.
10. Confrontare con VE-005C e baseline accademiche legalmente eseguibili.

### Gate prima del training

- diritti video documentati;
- schema stabile;
- benchmark congelato;
- licenza backbone e checkpoint verificata;
- ambiente riproducibile;
- metriche definite;
- budget GPU approvato;
- nessuna integrazione runtime.

---

## 21. Domande aperte

1. Quale livello di semantica è necessario per superare VE-005C senza sovra-annotare?
2. È preferibile usare classi simmetriche e risolvere l'orientamento dopo?
3. Quanti impianti servono per una generalizzazione minima? **Da validare durante la raccolta dati.**
4. Quale backbone permissivo offre il miglior rapporto costo/qualità?
5. I checkpoint permissivi candidati sono addestrati su dati compatibili con uso commerciale?
6. Quanto aiuta il contesto temporale rispetto a frame singolo?
7. Conviene una testa separata per cerchi/archi?
8. Come calibrare confidence semantica e geometrica?
9. Quale quota di `UNKNOWN` è accettabile?
10. Quanto migliora il solver usando orientation e valid region?
11. SAM 2 riduce davvero il costo di annotazione senza aumentare il rumore?
12. Quale fallback manuale è sostenibile senza trasformare il flusso principale?

---

## 22. Fonti primarie

### Paper

- [TVCalib - WACV 2023](https://openaccess.thecvf.com/content/WACV2023/papers/Theiner_TVCalib_Camera_Calibration_for_Sports_Field_Registration_in_Soccer_WACV_2023_paper.pdf)
- [PnLCalib](https://arxiv.org/abs/2404.08401)
- [No Bells, Just Whistles - CVPRW 2024](https://openaccess.thecvf.com/content/CVPR2024W/CVsports/papers/Gutierrez-Perez_No_Bells_Just_Whistles_Sports_Field_Registration_by_Leveraging_Geometric_CVPRW_2024_paper.pdf)
- [SoccerNet Game State Reconstruction](https://arxiv.org/abs/2404.11335)
- [Sportlight camera calibration](https://arxiv.org/abs/2410.07401)
- [Can Geometry Save Central Views? - CVPRW 2025](https://openaccess.thecvf.com/content/CVPR2025W/CVSPORTS/papers/Magera_Can_Geometry_Save_Central_Views_for_Sports_Field_Registration_CVPRW_2025_paper.pdf)
- [SoccerMaster - CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/papers/Yang_SoccerMaster_A_Vision_Foundation_Model_for_Soccer_Understanding_CVPR_2026_paper.pdf)
- [Sports Field Localization via Deep Structured Models - CVPR 2017](https://openaccess.thecvf.com/content_cvpr_2017/papers/Homayounfar_Sports_Field_Localization_CVPR_2017_paper.pdf)

### Repository

- [KpSFR](https://github.com/ericsujw/KpSFR)
- [PnLCalib](https://github.com/mguti97/PnLCalib)
- [TVCalib](https://github.com/MM4SPA/tvcalib)
- [SoccerNet Calibration](https://github.com/SoccerNet/sn-calibration)
- [No Bells Just Whistles](https://github.com/mguti97/No-Bells-Just-Whistles)
- [SoccerNet Game State Reconstruction](https://github.com/SoccerNet/sn-gamestate)
- [Sportlight SoccerNet calibration](https://github.com/NikolasEnt/soccernet-calibration-sportlight)
- [SoccerMaster](https://github.com/haolinyang-hlyang/SoccerMaster)
- [SAM 2](https://github.com/facebookresearch/sam2)

### Dataset e model card

- [SoccerNet Camera Calibration](https://www.soccer-net.org/tasks/camera-calibration)
- [SoccerNet Data](https://www.soccer-net.org/data)
- [SoccerNet FAQ e termini](https://www.soccer-net.org/faq)
- [WorldPose](https://worldpose.ait.ethz.ch/)
- [WorldPose Dataset](https://eth-ait.github.io/WorldPoseDataset/)
- [SoccerMaster model hub](https://huggingface.co/xleprime/SoccerMaster)
- [SoccerMaster project page](https://haolinyang-hlyang.github.io/SoccerMaster/)

### Licenze ufficiali

- [PnLCalib GPL-2.0](https://raw.githubusercontent.com/mguti97/PnLCalib/main/LICENSE)
- [No Bells Just Whistles GPL-2.0](https://raw.githubusercontent.com/mguti97/No-Bells-Just-Whistles/main/LICENSE)
- [SoccerNet GSR GPL-3.0](https://raw.githubusercontent.com/SoccerNet/sn-gamestate/main/LICENSE)
- [SAM 2](https://github.com/facebookresearch/sam2)

---

## Decision record

| Voce | Decisione |
|---|---|
| Candidati principali analizzati | 10 |
| Dataset analizzati | 7 |
| Miglior candidato tecnico | SoccerMaster |
| Miglior codice permissivo tra i candidati principali | KpSFR |
| Candidato pronto per produzione | Nessuno |
| Checkpoint pubblici effettivamente disponibili | Sì, per più candidati |
| Checkpoint con catena legale commerciale pienamente verificata | Nessuno tra i candidati principali |
| Compatibilità Python 3.11 pronta | Non dimostrata |
| Compatibilità PyTorch moderno pronta | Parziale; migliore in SoccerMaster/SAM 2 |
| Direzione finale | Detector proprietario MatchIQ multi-task |
| Uso di modelli pubblici | Benchmark, studio e pseudo-labeling autorizzato |
| Prossimo sprint | VE-005E - Dataset & Benchmark Contract |

**Conclusione:** MatchIQ non deve integrare il primo modello che produce una omografia plausibile. Deve costruire una catena verificabile nella quale dati, semantica, confidence, geometria e diritti siano tutti sotto controllo. Il vantaggio competitivo non sarà una singola architettura, ma l'unione di tassonomia proprietaria, video autorizzati dilettantistici, feedback umano e benchmark permanente.
