# RECOVER — Specifica Tecnica

**Versione:** 0.1  
**Data:** 2026-04-20  
**Linguaggio:** Python 3.11+  
**Ambiente:** sempre in virtualenv (`venv`)  
**Interfaccia:** TUI (Textual o curses)  
**Config:** TOML  

---

## 1. Obiettivo

Utility interattiva TUI per il recupero di file da dispositivi di archiviazione esterni (principalmente SD card), con supporto a filesystem corrotti e file cancellati. Output organizzato, rinominato con metadata EXIF, deduplicato e documentato in report HTML.

---

## 2. Stack tecnologico

### Tool esterni (dipendenze di sistema)
| Tool | Versione minima | Uso |
|---|---|---|
| `ddrescue` | 1.27 | Imaging disco con gestione settori danneggiati |
| `testdisk` | 7.1 | Recupero file da FAT/exFAT con filesystem parzialmente integro |
| `photorec` | 7.1 | File carving raw (bundled con testdisk) |
| `exiftool` | 12.0 | Lettura metadata EXIF per rinominazione |
| `fsck` | — | Verifica integrità filesystem (VERIFY) |
| `file` | — | Verifica magic bytes post-carving |

### Librerie Python
| Libreria | Uso |
|---|---|
| `textual` | Framework TUI |
| `tomllib` (builtin 3.11+) | Parsing config.toml |
| `tomli-w` | Scrittura config.toml |
| `rich` | Tabelle, progress bar, logging a schermo |
| `subprocess` | Wrapping tool esterni |
| `hashlib` | Deduplicazione (SHA-256) |
| `pathlib` | Gestione path |
| `shutil` | Copia/move file |
| `jinja2` | Generazione report HTML |
| `python-magic` | Verifica tipo file (fallback a `file` CLI) |
| `Pillow` | Thumbnail per report HTML |

---

## 3. Struttura del progetto

```
recover/
├── main.py                  # Entry point
├── config.toml              # Configurazione utente
├── config.toml.default      # Template con valori di default
├── recover/
│   ├── __init__.py
│   ├── tui/
│   │   ├── app.py           # App Textual principale
│   │   ├── screens/
│   │   │   ├── main_menu.py
│   │   │   ├── detect.py
│   │   │   ├── confirm.py
│   │   │   ├── imaging.py
│   │   │   ├── analyze.py
│   │   │   ├── carve.py
│   │   │   ├── organize.py
│   │   │   └── report.py
│   │   └── widgets/
│   │       ├── device_list.py
│   │       ├── progress_panel.py
│   │       └── log_panel.py
│   ├── core/
│   │   ├── detect.py        # Rilevamento dispositivi
│   │   ├── imaging.py       # Wrapper ddrescue
│   │   ├── verify.py        # Wrapper fsck + checksum
│   │   ├── analyze.py       # Wrapper testdisk
│   │   ├── carve.py         # Wrapper photorec
│   │   ├── organize.py      # Rinomina, dedup, sorting
│   │   └── report.py        # Generazione HTML
│   ├── utils/
│   │   ├── deps.py          # Verifica dipendenze all'avvio
│   │   ├── exif.py          # Lettura EXIF via exiftool
│   │   ├── hash.py          # SHA-256 per deduplicazione
│   │   ├── logger.py        # Logger su file + TUI
│   │   └── fs.py            # Utility filesystem/mount
│   └── templates/
│       └── report.html.j2   # Template Jinja2 per report
├── tests/
│   └── ...
└── requirements.txt
```

---

## 4. Configurazione — config.toml

```toml
[general]
output_dir = "~/RECOVER"          # Directory base di recupero
log_level = "INFO"                # DEBUG | INFO | WARNING
lang = "it"                       # it | en (per futura i18n)

[recovery]
deduplication = true              # SHA-256, disattivabile
rename_with_exif = true           # Rinomina con metadata EXIF
fallback_name = "recovered"       # Prefisso se EXIF assente
create_thumbnail = true           # Miniature nel report HTML
thumbnail_size = [256, 256]

[imaging]
ddrescue_extra_args = ""          # Args aggiuntivi ddrescue
image_dir = "~/RECOVER/dsks"  # Dove salvare le immagini disco

[carving]
photorec_extra_args = ""
target_formats = [                # Formati prioritari
  "jpg", "jpeg", "png", "raw", "cr2", "cr3", "nef", "arw",
  "heic", "heif", "tiff",
  "mp4", "mov", "avi", "mkv", "mts", "m2ts"
]
include_all_formats = false       # Se true recupera tutti i tipi

[filesystems]
supported = ["fat", "exfat"]      # fat, exfat | ntfs, ext4 (futuro)

[output]
subdir_images = "images"
subdir_videos = "videos"
subdir_others = "others"
subdir_duplicates = "duplicates"  # File duplicati (non cancellati)
```

---

## 5. Workflow dettagliato

### Fase 0 — INIT
- Verifica dipendenze (`deps.py`): controlla che ddrescue, photorec, testdisk, exiftool, fsck, file siano nel PATH
- Se mancano: lista le dipendenze assenti con comando di installazione suggerito (apt/brew/pacman)
- Carica `config.toml` (crea da default se assente)
- Inizializza logger su file (`~/RECOVER/logs/YYYYMMDD_HHMMSS.log`)

### Fase 1 — DETECT
- Lista dispositivi a blocchi: parsing `/proc/partitions` + `lsblk -J`
- Per ogni dispositivo espone: nome, size, filesystem rilevato, label, punto di mount, stato (montato/smontato)
- Filtra: mostra solo rimovibili (esclude disco di sistema)
- Opzione: inserire path manuale a immagine `.img` esistente

### Fase 2 — CONFIRM
- Mostra scheda dettagliata del dispositivo selezionato
- Warning esplicito se il dispositivo è montato (suggerisce umount)
- Richiede conferma esplicita prima di procedere (no operazioni distruttive sul dispositivo)
- Scelta modalità:
  - **A) Recupero file cancellati** (filesystem ancora leggibile)
  - **B) Recupero da filesystem corrotto** (carving raw)
  - **C) Solo imaging** (crea immagine e ferma)

### Fase 3 — IMAGE
- Esegue `ddrescue` per creare immagine `.img` del dispositivo
- Progress bar con: settori letti, errori, velocità, ETA
- Salva log ddrescue (`device_YYYYMMDD.log`) per eventuale resume
- Output: `~/RECOVER/_images/{device_label}_{date}.img`
- **Tutte le fasi successive lavorano sull'immagine, mai sul dispositivo originale**

### Fase 4 — VERIFY
- `fsck -n` sull'immagine (read-only, non modifica)
- Calcola SHA-256 dell'immagine e lo salva in `.sha256`
- Riporta: stato filesystem, errori trovati, settori non leggibili da ddrescue
- Decide il percorso:
  - Filesystem leggibile → **ANALYZE (testdisk)**
  - Filesystem corrotto/illeggibile → **CARVE (photorec)**
  - Utente può forzare il percorso manualmente

### Fase 5A — ANALYZE (testdisk)
- Modalità A: filesystem integro
- Lancia `testdisk` in modalità batch per elencare file cancellati
- Lista file trovati con: nome originale, dimensione, stato (buono/corrotto)
- Utente può selezionare tutto o sottoinsieme
- Copia i file selezionati nella directory di output

### Fase 5B — CARVE (photorec)
- Modalità B: filesystem corrotto
- Lancia `photorec` con formati configurati da `config.toml`
- Progress: file trovati per tipo, dimensione totale
- Output raw in directory temporanea, poi passa a ORGANIZE

### Fase 6 — ORGANIZE
Per ogni file recuperato:

1. **Verifica tipo** con `python-magic` (controlla magic bytes, non solo estensione)
2. **Lettura EXIF** tramite `exiftool`
3. **Rinominazione:**
   ```
   {YYYY}-{MM}-{DD}_{HH}-{MM}-{SS}_{Make}_{Model}.{ext}
   es: 2023-08-15_14-32-07_Canon_EOS_R5.jpg
   
   Se EXIF parziale:
   2023-08-15_14-32-07_unknown.jpg
   
   Se EXIF assente:
   recovered_00142_no_meta.jpg
   
   Se collisione nome (stesso timestamp):
   2023-08-15_14-32-07_Canon_EOS_R5_001.jpg
   ```
4. **Deduplicazione** (se attiva):
   - Calcola SHA-256
   - Se hash già visto → sposta in `duplicates/` invece di cancellare
5. **Sorting in sottocartelle:**
   ```
   {output_dir}/{device_label}_{date}/
   ├── images/
   ├── videos/
   ├── others/
   └── duplicates/
   ```

### Fase 7 — REPORT
Genera `report.html` nella directory di output con:

- **Header:** dispositivo, data recupero, modalità usata
- **Sommario:** totale file recuperati per tipo, dimensione totale, duplicati trovati, file senza metadata
- **Tabella file:** nome, tipo, dimensione, data originale (da EXIF), stato EXIF, thumbnail (se immagine)
- **Log sezione:** warning, errori, settori non leggibili
- **Footer:** SHA-256 immagine disco, versioni tool usati

---

## 6. Output directory — struttura finale

```
~/RECOVER/
├── _images/                          # Immagini disco (ddrescue)
│   ├── SanDisk_32GB_2026-04-20.img
│   └── SanDisk_32GB_2026-04-20.sha256
├── logs/
│   └── 2026-04-20_143200.log
└── SanDisk_32GB_2026-04-20/          # Recupero specifico
    ├── images/
    │   ├── 2023-08-15_14-32-07_Canon_EOS_R5.jpg
    │   └── recovered_00142_no_meta.jpg
    ├── videos/
    │   └── 2023-08-15_15-10-22_unknown.mp4
    ├── others/
    ├── duplicates/
    └── report.html
```

---

## 7. TUI — schermate principali

```
┌─────────────────────────────────────────────┐
│  RECOVER v0.1          [Q]quit  [?]help      │
├─────────────────────────────────────────────┤
│  > Nuovo recupero                            │
│    Riprendi sessione esistente               │
│    Configurazione                            │
│    Verifica dipendenze                       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  DISPOSITIVI RILEVATI                        │
├────────────┬───────┬────────┬───────────────┤
│ Dispositivo│ Size  │   FS   │ Stato         │
├────────────┼───────┼────────┼───────────────┤
│ /dev/sdb1  │ 32GB  │ FAT32  │ montato       │
│ /dev/sdc   │ 64GB  │ exFAT  │ non montato   │
└────────────┴───────┴────────┴───────────────┘
  [Invio] Seleziona   [M] Path manuale   [R] Ricarica
```

---

## 8. Filesystem supportati

| Filesystem | Versione 0.1 | Futuro |
|---|---|---|
| FAT32 | ✅ | — |
| exFAT | ✅ | — |
| NTFS | 🔲 | v0.2 |
| ext4 | 🔲 | v0.3 |

L'architettura prevede un adapter per filesystem: aggiungere NTFS/ext4 richiede solo un nuovo modulo in `core/` senza modificare il flusso principale.

---

## 9. Gestione errori e sicurezza

- **Mai scrivere sul dispositivo originale** — ogni operazione avviene sull'immagine
- Dispositivo montato: warning + suggerimento `umount`, non procede automaticamente
- ddrescue fallisce: log errore, offre retry o skip imaging (se immagine parziale usabile)
- photorec output vuoto: notifica, suggerisce di allargare `target_formats`
- Permessi insufficienti: richiede `sudo` solo per ddrescue/fsck, spiega perché
- Interruzione (Ctrl+C): salva stato sessione per resume futuro

---

## 10. Fasi di sviluppo

| Fase | Contenuto | Priorità |
|---|---|---|
| **v0.1** | INIT, DETECT, CONFIRM, IMAGE, VERIFY | Core |
| **v0.2** | CARVE (photorec), ORGANIZE base, REPORT minimale | Recovery |
| **v0.3** | ANALYZE (testdisk), EXIF rename, dedup, report completo | Polish |
| **v0.4** | NTFS support, resume sessione, i18n | Espansione |

---

## 11. Dipendenze — installazione

```bash
# Sistema (Debian/Ubuntu)
sudo apt install gddrescue testdisk exiftool libmagic1

# Setup venv (obbligatorio)
python3.11 -m venv .venv
source .venv/bin/activate

# Python
pip install textual rich tomli-w jinja2 python-magic Pillow
```

Il progetto usa **sempre** un virtualenv dedicato. Non installare dipendenze Python a livello di sistema. Il file `requirements.txt` è il riferimento per le dipendenze pinned.

---

## 12. Limiti tecnici e comportamento atteso

### Immagine disco parziale (settori danneggiati)

ddrescue riempie i settori illeggibili con zeri (`0x00`) e li traccia nel **mapfile** (`.map`). L'immagine rimane utilizzabile:

- photorec e testdisk lavorano normalmente, saltando i blocchi zeroed
- I file i cui dati cadono interamente su settori leggibili vengono recuperati integri
- I file che attraversano un settore corrotto vengono recuperati **parziali** (troncati o con buco interno)
- ddrescue può essere eseguito più volte sullo stesso dispositivo con strategie progressive (`--retry-passes`, lettura inversa) per ridurre i buchi

La utility NON corregge i dati — recupera il massimo fisicamente leggibile. I file parziali vengono flaggati nel report con stato `PARZIALE`.

### File sovrascritti — cosa è recuperabile

| Scenario | Recuperabile via software | Note |
|---|---|---|
| File cancellato, blocchi non sovrascritti | ✅ Sì | photorec trova la signature |
| File cancellato, blocchi parzialmente sovrascritti | ⚠️ Parzialmente | frammento recuperato, file corrotto |
| Blocchi fisicamente sovrascritti | ❌ No | dato perso irrecuperabilmente |
| Wear leveling NAND (SD card) | ❌ No via software | richiederebbe chip-off forensics hardware |

I file recuperati con dimensione anomala o magic bytes incoerenti vengono flaggati con stato `CORROTTO` nel report. La utility non tenta ricostruzioni — raccoglie e classifica.
