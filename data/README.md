# Datos: UNSW-NB15

Los archivos de datos no se suben al repositorio: la consigna pide dejar `data/` fuera del control de versiones y además pesan unos 700 MB. Acá explicamos de dónde los sacamos, cómo descargarlos y cómo comprobar que son exactamente los mismos que usamos nosotros.

## De dónde salen

El dataset es UNSW-NB15, del Australian Centre for Cyber Security de UNSW Canberra.

1. Entrar a la página oficial: https://research.unsw.edu.au/projects/unsw-nb15-dataset
2. En la parte de "The UNSW-NB15 source files" hay un enlace "HERE" que lleva a un SharePoint de UNSW.
3. Desde ahí se descarga la carpeta con los CSV (el navegador la baja como un ZIP llamado `OneDrive_1_<fecha>.zip`).

Nosotros lo descargamos el 9 de septiembre de 2026.

No usen la copia que está en Kaggle. Tiene los mismos datos, pero los archivos de train y test tienen los nombres intercambiados, así que usándola tal cual se termina entrenando con el test.

## Dónde ubicar los archivos

Del ZIP solo necesitamos los dos archivos que están en la carpeta `Training and Testing Sets/`. Van en `data/raw/`:

```
data/
├── README.md
└── raw/
    ├── UNSW_NB15_training-set.csv
    ├── UNSW_NB15_testing-set.csv
    └── referencia/        (opcional)
```

En `referencia/` dejamos el resto de lo que trae el ZIP (el dataset completo sin dividir, la tabla de ataques, el diccionario de variables `NUSW-NB15_features.csv` y un PDF con la descripción). No lo usamos en el proyecto, pero sirve para consultar. Algunos archivos empiezan con "NUSW" en vez de "UNSW": así vienen en la descarga oficial, no hay que cambiarles el nombre.

Los archivos de `data/raw/` no se modifican nunca.

## Cómo comprobar que son los archivos correctos

Comparamos el hash MD5 de cada archivo con el que obtuvimos nosotros:

| Archivo | Registros | MD5 |
|---|---|---|
| `UNSW_NB15_training-set.csv` | 175.341 | `e55caabaa6cd4a8f1c06a227bcfababc` |
| `UNSW_NB15_testing-set.csv` | 82.332 | `e0beea40262e46168cdb81476dbc27b4` |

Para calcularlo:

```bash
md5sum data/raw/*.csv                          # Git Bash o Linux
Get-FileHash data/raw/*.csv -Algorithm MD5     # PowerShell
```

El script `python -m src.data` también hace esta verificación antes de cargar los datos.

## Qué tienen los archivos

Los dos CSV tienen las mismas 45 columnas:

- `id`: número de fila. No lo usamos como variable.
- 42 variables del flujo de red: 39 numéricas y 3 categóricas (`proto`, `service` y `state`).
- `label`: 0 si el tráfico es normal y 1 si es un ataque. Es la etiqueta de la tarea binaria.
- `attack_cat`: la categoría del ataque (Generic, Exploits, Fuzzers, DoS, Reconnaissance, Analysis, Backdoor, Shellcode, Worms) o "Normal". Es la etiqueta de la tarea multiclase.

En cada tarea sacamos de la entrada la etiqueta que no corresponde, porque si no el modelo tendría la respuesta en los datos.

| | Train | Test |
|---|---|---|
| Registros | 175.341 | 82.332 |
| Ataques | 119.341 (68 %) | 45.332 (55 %) |
| Normales | 56.000 (32 %) | 37.000 (45 %) |

El test lo usamos una sola vez, al final, para evaluar los modelos ya terminados. Todo lo demás (comparar modelos, elegir el umbral, etc.) lo hacemos con cross-validation sobre el train.
