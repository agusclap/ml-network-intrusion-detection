# NIDS con Machine Learning sobre UNSW-NB15

Trabajo Práctico Final de **Inteligencia Artificial** — Ingeniería en Informática, Universidad de la Defensa Nacional (CRUC IUA), 2026.
Docente: Ing. Hernando Alexis González · Modalidad: **grupal**.

Clasificador de tráfico de red que, a partir de las características de un flujo, decide si es **normal o un ataque** (tarea principal) y, como segunda tarea, a qué **categoría de ataque** pertenece. Se entrena y evalúa sobre la partición oficial del dataset [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset).

> **Estado:** fase de planificación cerrada. Todavía no hay código ni resultados; las secciones de instalación, uso y resultados se completan a medida que avanza el desarrollo (ver [cronograma](#cronograma)).

## Integrantes

- Maximo Agustin Rodeyro
- Lautaro Niccolini

## Project Charter

La propuesta formal del proyecto (problema, PEAS, datos, métricas de éxito, baselines, alcance y límites) está en **[PROJECT_CHARTER_CORREGIDO.md](PROJECT_CHARTER_CORREGIDO.md)** y se publica también como Issue #1 del repositorio.

Resumen:

| | |
|---|---|
| **Problema** | Detectar flujos de red maliciosos a partir de 42 variables del flujo (sin contenido de paquetes) |
| **Tarea principal** | Binaria: `label` (0 = normal, 1 = ataque) |
| **Tarea secundaria** | Multiclase: `attack_cat` (Normal + 9 categorías de ataque) |
| **Baselines** | Regla sin IA `dpkts == 0` (binaria) / clase mayoritaria (multiclase); regresión logística |
| **Modelo principal** | XGBoost con parámetros fijados de antemano |
| **Validación** | Cross-validation estratificada de 5 particiones sobre train; **una única** evaluación final sobre el test oficial |
| **Éxito binario** | Recall de ataque ≥ 0,90 con tasa de falsos positivos ≤ la del baseline heurístico; umbral elegido solo con predicciones out-of-fold de train |
| **Éxito multiclase** | Superar a ambos baselines en Macro-F1 en CV sobre train y mantenerlo en el test (sin meta absoluta: el dataset tiene un techo estructural de ≈ 0,81) |
| **Entregable** | Pipeline reproducible + herramienta de línea de comandos para predecir sobre un CSV de flujos |

## Datos

Se usa exclusivamente la partición oficial de UNSW-NB15 descargada desde el sitio de UNSW Canberra:

| Archivo | Registros | Uso |
|---|---|---|
| `UNSW_NB15_training-set.csv` | 175.341 | entrenamiento y validación cruzada |
| `UNSW_NB15_testing-set.csv` | 82.332 | evaluación final (una sola vez) |

Los datos **no se versionan**. Cómo descargarlos, dónde ubicarlos y cómo verificar su integridad (MD5): **[data/README.md](data/README.md)**.

> ⚠️ No usar la copia de Kaggle: tiene los nombres de train y test intercambiados.

## Estructura del repositorio

```
├── data/                 # datos (no versionados) — ver data/README.md
│   └── raw/              # CSV oficiales sin modificar
├── notebooks/            # EDA mínimo
├── src/                  # código: datos, features, baselines, métricas, train, evaluate, inference
├── models/               # pipelines entrenados (.joblib, no versionados; se regeneran)
├── reports/
│   ├── metrics/          # métricas de CV y test en JSON (versionadas)
│   └── figures/          # matrices de confusión
├── AUDITORIA_VIABILIDAD.md
├── PLAN_IMPLEMENTACION.md
├── PROJECT_CHARTER_CORREGIDO.md
├── requirements.txt
└── README.md
```

Las carpetas `notebooks/`, `src/`, `models/`, `reports/` y el archivo `requirements.txt` se crean durante el desarrollo.

## Instalación y uso

> 🚧 En construcción. Flujo previsto:

```bash
# 1. Entorno (Python >= 3.10)
python -m venv .venv
.venv\Scripts\activate          # Windows  |  source .venv/bin/activate  (Linux/Mac)
pip install -r requirements.txt

# 2. Datos: descargar y ubicar según data/README.md, luego verificar
python -m src.data

# 3. Entrenar y validar (CV sobre train)
python -m src.train --task binary --model xgb

# 4. Evaluación final sobre el test oficial
python -m src.evaluate --task binary --model xgb

# 5. Predecir sobre un CSV nuevo
python -m src.inference --input archivo.csv --task binary
```

Todos los procesos aleatorios usan la semilla global `42` y las dependencias tienen versiones fijadas, de modo que los resultados sean reproducibles.

## Resultados

> 🚧 Pendiente. Aquí se publicarán las métricas de validación cruzada (media ± desviación estándar) y de la evaluación final sobre el test para los baselines, la regresión logística y XGBoost en ambas tareas.

## Decisiones metodológicas y limitaciones conocidas

- **Anti-leakage:** en cada tarea se eliminan de las variables de entrada `id` y el *otro* target (`attack_cat` en la binaria, `label` en la multiclase). Todo el preprocesamiento se ajusta solo con datos de entrenamiento.
- **Uso del test:** se evalúa una única vez con los modelos congelados. Durante la auditoría inicial se inspeccionó solo para verificar su integridad; ninguna decisión de modelado ni meta se basó en él.
- **Solapamiento de etiquetas:** el 17,4 % de las filas de train comparten exactamente las 42 variables con filas de otra categoría (sobre todo Analysis, Backdoor, DoS y Exploits), lo que limita la clasificación multiclase.
- **Sesgo del dataset (TTL):** `sttl`, `dttl` y `ct_state_ttl` separan casi por sí solas ataque de normal por cómo se generó el tráfico sintético. No es fuga de información; se mantienen y se documentan como limitación.
- **Cambio de distribución:** 68 % de ataques en train vs 55 % en test; el 5 % de las filas del test son copias exactas de filas de train.

El análisis completo está en **[AUDITORIA_VIABILIDAD.md](AUDITORIA_VIABILIDAD.md)**.

## Cronograma

| Semana | Objetivo |
|---|---|
| 1 | Repositorio, entorno, datos verificados, EDA mínimo |
| 2 | Pipeline, baseline heurístico y regresión logística binaria end-to-end |
| 3 | XGBoost binario; regresión logística y XGBoost multiclase |
| 4 | Congelamiento de modelos y evaluación final en test |
| 5 | CLI de inferencia y README con resultados |
| 6 | Reproducibilidad, documentación final y defensa |
| 7 | Margen para imprevistos y correcciones |

Detalle, estimación de horas y Definition of Done: **[PLAN_IMPLEMENTACION.md](PLAN_IMPLEMENTACION.md)**.

## Convenciones de trabajo

- Rama `main` estable; cada tarea en una rama `feature/<tema>`.
- Mensajes de commit con el problema resuelto y las horas invertidas, por ejemplo: `feat(data): carga con verificación MD5 [1.5h]`.

## Referencias

- Moustafa, N. & Slay, J. (2015). *UNSW-NB15: a comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set)*. Military Communications and Information Systems Conference (MilCIS). https://doi.org/10.1109/MilCIS.2015.7348942
- UNSW Canberra. *The UNSW-NB15 Dataset*. https://research.unsw.edu.au/projects/unsw-nb15-dataset
