# Datos — UNSW-NB15

Los archivos de datos **no se versionan** en este repositorio (requisito de la consigna y ~700 MB).
Este documento explica de dónde salen, cómo obtenerlos y cómo verificar que son exactamente los mismos
que usamos, para que cualquier persona pueda reproducir los resultados.

## Fuente oficial

- **Dataset:** UNSW-NB15 — Australian Centre for Cyber Security (ACCS), UNSW Canberra.
- **Página oficial:** https://research.unsw.edu.au/projects/unsw-nb15-dataset
- **Descarga:** enlace "HERE" de la sección *"The UNSW-NB15 source files"* de esa página, que lleva al
  SharePoint/OneDrive de UNSW. Desde ahí se descarga la carpeta de CSV como un ZIP
  (el navegador lo nombra `OneDrive_1_<fecha>.zip`).
- **Fecha de nuestra descarga:** 9 de septiembre de 2026.
- **Cita requerida por los autores:** Moustafa, N. & Slay, J. (2015). *UNSW-NB15: a comprehensive data set
  for network intrusion detection systems (UNSW-NB15 network data set)*. Military Communications and
  Information Systems Conference (MilCIS). https://doi.org/10.1109/MilCIS.2015.7348942

> ⚠️ **No usar la copia de Kaggle.** Contiene los mismos datos byte a byte, pero con los nombres
> `training-set` y `testing-set` **intercambiados** (su `UNSW_NB15_training-set.csv` es el de 82.332 filas).
> Usarla con los nombres tal cual haría entrenar sobre el test oficial. Por eso el código verifica cada
> archivo por su MD5 y no confía en el nombre.

## Cómo reconstruir esta carpeta

1. Descargar el ZIP desde el enlace oficial indicado arriba.
2. De la carpeta `Training and Testing Sets/` del ZIP, copiar a `data/raw/`:
   - `UNSW_NB15_training-set.csv`
   - `UNSW_NB15_testing-set.csv`
3. (Opcional, solo referencia) copiar el resto del ZIP a `data/raw/referencia/`.
4. Verificar la integridad (debe coincidir con la tabla siguiente):
   ```bash
   md5sum data/raw/*.csv                 # Linux / Git Bash
   Get-FileHash data/raw/*.csv -Algorithm MD5   # PowerShell
   ```
   El pipeline también lo verifica automáticamente con `python -m src.data`.

## Estructura esperada

```
data/
├── README.md                          ← este archivo (único versionado)
└── raw/                               ← datos originales, sin modificar
    ├── UNSW_NB15_training-set.csv     ← TRAIN oficial (usado por el pipeline)
    ├── UNSW_NB15_testing-set.csv      ← TEST oficial (usado solo en la evaluación final)
    └── referencia/                    ← contexto; NO usado por el pipeline
        ├── NUSW-NB15_features.csv     (diccionario de las 49 variables del dataset crudo)
        ├── The UNSW-NB15 description.pdf
        ├── UNSW-NB15_1.csv … UNSW-NB15_4.csv   (dataset crudo, 2.540.044 registros, sin encabezado)
        ├── NUSW-NB15_GT.csv           (ground truth de los eventos de ataque)
        └── UNSW-NB15_LIST_EVENTS.csv  (resumen de eventos por categoría)
```

Los nombres con `NUSW` son los de la distribución oficial (errata de origen): no renombrarlos.
Los archivos de `data/raw/` **nunca se modifican**; cualquier dato derivado iría a `data/processed/`.

## Verificación de integridad (MD5)

| Archivo | Filas × columnas | Bytes | MD5 |
|---|---|---|---|
| `raw/UNSW_NB15_training-set.csv` | 175.341 × 45 | 32.293.018 | `e55caabaa6cd4a8f1c06a227bcfababc` |
| `raw/UNSW_NB15_testing-set.csv` | 82.332 × 45 | 15.380.800 | `e0beea40262e46168cdb81476dbc27b4` |
| `raw/referencia/NUSW-NB15_features.csv` | 49 × 4 | 4.044 | `9e6f08b95bc19e4c4986d4d5729f3ce9` |
| `raw/referencia/UNSW-NB15_LIST_EVENTS.csv` | 208 × 3 | 4.639 | `fb6a2eb2efb7e0a0e7abe2435db1d3f9` |
| `raw/referencia/NUSW-NB15_GT.csv` | 188.913 × 12 | 86.426.111 | `efa04c34ec50b7ed10e6673f7ac67b59` |
| `raw/referencia/UNSW-NB15_1.csv` | 700.001 líneas × 49 | 168.979.718 | `560dcc5981b3f6ab98027a16b053c9c1` |
| `raw/referencia/UNSW-NB15_2.csv` | 700.001 líneas × 49 | 165.221.021 | `59215357fbed7c76efc6a404a8607688` |
| `raw/referencia/UNSW-NB15_3.csv` | 700.001 líneas × 49 | 154.588.103 | `75e8567341edb760a23f803b920b69d4` |
| `raw/referencia/UNSW-NB15_4.csv` | 440.044 líneas × 49 | 97.588.754 | `f55875cab7f037fdad40b5b737e7db5e` |
| `raw/referencia/The UNSW-NB15 description.pdf` | — | 189.112 | `3698f3702d5f4e07364a1b22ec0ab26f` |

Solo los dos primeros son obligatorios para ejecutar el proyecto.

## Contenido de los archivos usados

Ambos CSV (UTF-8 con BOM, separador `,`, sin valores nulos ni infinitos) tienen las mismas **45 columnas**:

- `id` — índice de fila (1..N). **Se descarta**: no es una característica del tráfico.
- **42 variables predictoras**: 39 numéricas y 3 categóricas (`proto`, `service`, `state`).
- `label` — 0 = normal, 1 = ataque. Target de la tarea **binaria**.
- `attack_cat` — 10 valores: `Normal`, `Generic`, `Exploits`, `Fuzzers`, `DoS`, `Reconnaissance`,
  `Analysis`, `Backdoor`, `Shellcode`, `Worms`. Target de la tarea **multiclase**.
  `label = 0` si y solo si `attack_cat = Normal` (sin excepciones).

Para evitar fuga de información, en cada tarea se elimina de las variables de entrada el **otro** target
(`attack_cat` en la binaria, `label` en la multiclase), además de `id`.

| | TRAIN | TEST |
|---|---|---|
| Registros | 175.341 | 82.332 |
| Ataques (`label = 1`) | 119.341 (68,06 %) | 45.332 (55,06 %) |
| Normales (`label = 0`) | 56.000 (31,94 %) | 37.000 (44,94 %) |

Particularidades documentadas en `AUDITORIA_VIABILIDAD.md`: solapamiento de etiquetas entre categorías de
ataque, cambio de proporción de clases entre train y test, 5,16 % de filas del test idénticas a filas de
train y variables TTL (`sttl`, `dttl`, `ct_state_ttl`) muy asociadas a la etiqueta por el testbed.

## Uso del test

El test oficial se usa **una única vez**, al final, con los modelos ya congelados. Toda selección de modelo,
umbral o preprocesamiento se hace con validación cruzada sobre el train. Durante la auditoría inicial se
inspeccionó el test solo para verificar su integridad (nulos, duplicados, distribución de clases).
