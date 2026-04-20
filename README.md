# RECOVER

Utility interattiva TUI per il recupero di file da dispositivi di archiviazione esterni, principalmente SD card.

---

## Cosa fa

- Rileva automaticamente i dispositivi rimovibili collegati
- Crea un'immagine disco sicura con **ddrescue** (lavora sempre sulla copia, mai sul dispositivo originale)
- Recupera file cancellati da filesystem intatto con **testdisk**
- Recupera file da filesystem corrotto o SD danneggiata con **photorec** (file carving raw)
- Organizza i file recuperati rinominandoli con i metadata EXIF (`2023-08-15_14-32-07_Canon_EOS_R5.jpg`)
- Deduplica i file via SHA-256
- Genera un report HTML con anteprima, statistiche e log della sessione

**Formati target:** JPEG, PNG, RAW (CR2, CR3, NEF, ARW), HEIC, TIFF, MP4, MOV, AVI, MKV e altri.  
**Filesystem supportati:** FAT32, exFAT (NTFS ed ext4 in roadmap).

---

## Ambiente di sviluppo e test

Sviluppato e testato su **Ubuntu 25.10**.

---

## Requisiti

### Sistema

```bash
sudo apt install gddrescue testdisk libimage-exiftool-perl libmagic1
```

### Python

Python 3.11+ con virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Avvio

```bash
source .venv/bin/activate
python main.py
```

---

## Utilizzo

All'avvio si presenta un menu interattivo navigabile da tastiera:

```
  Nuovo recupero
  Riprendi sessione esistente
  Configurazione
  Verifica dipendenze
```

### Flusso tipico

1. **Nuovo recupero** — rileva i dispositivi rimovibili collegati
2. Seleziona la SD card o inserisci il path di un'immagine `.img` esistente
3. Scegli la modalità:
   - **A** — file cancellati (filesystem ancora leggibile)
   - **B** — filesystem corrotto o SD danneggiata (carving raw)
   - **C** — solo imaging (crea `.img` e ferma)
4. L'utility crea l'immagine disco, analizza e recupera i file
5. I file vengono organizzati in sottocartelle, rinominati e deduplicati
6. Viene generato un `report.html` nella directory di output

### Directory di output

```
~/RECOVER/
├── dsks/                             # Immagini disco (.img + .sha256)
├── logs/                             # Log di sessione
└── SanDisk_32GB_2026-04-20/          # Una cartella per ogni recupero
    ├── images/
    ├── videos/
    ├── others/
    ├── duplicates/
    └── report.html
```

### Configurazione

Modifica `config.toml` per personalizzare:
- Directory di output
- Formati file da recuperare
- Attivare/disattivare deduplicazione e rinominazione EXIF
- Argomenti aggiuntivi per ddrescue e photorec

---

## Limiti

- I blocchi fisicamente sovrascritti su NAND flash non sono recuperabili via software
- I file i cui dati cadono su settori danneggiati vengono recuperati parzialmente e segnalati nel report
- Il wear leveling delle SD card può rendere inaccessibili dati "vecchi" senza strumenti hardware dedicati (chip-off forensics)

---

## Dipendenze Python

| Libreria | Uso |
|---|---|
| `textual` | Interfaccia TUI |
| `rich` | Output formattato |
| `jinja2` | Template report HTML |
| `python-magic` | Verifica tipo file (magic bytes) |
| `Pillow` | Thumbnail nel report |
| `tomli-w` | Scrittura config.toml |

---

Realizzato con [Claude Code](https://claude.ai/code) in Visual Studio Code.
