# AUDITORÍA DE VIABILIDAD — Proyecto NIDS sobre UNSW-NB15 (versión definitiva)

**Versión:** 3 (cierre de fase de auditoría y planificación) · **Fecha:** 2026-09-10 · **Modalidad:** Grupal · **Reemplaza** a las versiones 1 y 2. Todo lo que aquí figura fue verificado sobre los archivos locales o sobre fuentes externas leídas directamente; las afirmaciones de versiones anteriores que resultaron incorrectas se listan y se descartan en el Anexo A.

Etiquetas: **[HECHO]** comprobado sobre archivos locales · **[EXTERNO]** documentación/bibliografía leída · **[INFERENCIA]** · **[DECISIÓN]** decisión de proyecto adoptada · **NO VERIFICADO**.

---

## 1. Resumen ejecutivo

- **Fuente de datos cerrada.** `data/OneDrive_1_9-9-2026.zip` es la descarga oficial de UNSW Canberra (enlace "HERE" de research.unsw.edu.au → SharePoint de UNSW). Su contenido coincide uno a uno con la documentación pública (49 features, 4 CSV crudos, GT, LIST_EVENTS, partición 175.341 / 82.332). Los archivos de Kaggle son copias byte-idénticas con los nombres `training-set`/`testing-set` **intercambiados**; quedan fuera de la metodología.
- **Dataset operativo [HECHO]:** TRAIN oficial 175.341 × 45 (MD5 `e55caabaa6cd4a8f1c06a227bcfababc`), TEST oficial 82.332 × 45 (MD5 `e0beea40262e46168cdb81476dbc27b4`). 42 features (39 numéricas + `proto`, `service`, `state`), `id` (índice, se descarta), `label` (0/1), `attack_cat` (10 valores). Sin NaN, sin ±inf, sin errores de parsing; `label = 0 ⇔ attack_cat = Normal` sin excepciones.
- **Límite estructural de la clasificación multiclase [HECHO]:** existen vectores X idénticos con etiquetas distintas (17,41 % de las filas de train; 10,70 % del test). Para **un único clasificador determinista** función de las 42 features, el Macro-F1 máximo es **≤ 0,8087 sobre TRAIN completo** y **≤ 0,7877 sobre TEST** (cotas superiores demostradas; mejores asignaciones alcanzables encontradas: 0,8029 y 0,7849). La meta original "Macro-F1 > 0,85" es inalcanzable y se elimina. Estas cotas **no** se aplican automáticamente a resultados de K-fold CV (ver §8.4).
- **Leakage:** `attack_cat` y `label` son mutuamente derivables → excluir el target alternativo de X (crítico); `id` se excluye siempre. Las variables TTL (`sttl`, `dttl`, `ct_state_ttl`) son un **sesgo del dataset / atajo**, no leakage: se mantienen en el modelo principal y se documentan.
- **Baseline sin IA:** la regla SYN/ACK propuesta originalmente no es implementable (no hay flags por paquete ni timestamps). Baseline definitivo: `dpkts == 0` (definido y medido solo en train).
- **Alcance final (grupal, < 2 meses, dedicación parcial):** heurística + regresión logística + **XGBoost** como modelo principal, tareas binaria (principal) y multiclase (secundaria) con el mismo pipeline, CV 5-fold en train, una única evaluación en test, pipeline guardado, CLI de inferencia, README reproducible. XGBoost con parámetros fijados de antemano: la búsqueda de hiperparámetros no forma parte del MVP. Fuera del MVP (solo después de terminado y documentado): tuning, Random Forest, SHAP, bootstrap, ablación TTL, evaluación train-disjoint, pytest. Fuera del proyecto: MLP, autoencoder, PyTorch, SMOTE, FastAPI, Pages, Docker, MLflow, frontend.
- **Veredicto:** 🟡 **VIABLE CON AJUSTES MENORES** y **TERMINABLE en menos de dos meses** con dedicación universitaria parcial (estimación: ≈ 35–42 horas de equipo para el MVP, con 3–4 h por persona y semana y 0–2 h en semanas de parciales; núcleo cerrado en la semana 4–5 de 7; semana 7 de buffer real).

---

## 2. Requisitos de la consigna (`IA___TPFinal.pdf`) y su aplicación a la modalidad grupal

| # | Requisito | Fuente | Clasificación para este proyecto |
|---|---|---|---|
| R1 | Categoría tecnológica (ML predictivo + Data Engineering & IA) | §1 | OBLIGATORIO — cumplido por diseño |
| R2 | Solución medible con métricas objetivas | §1, §2.2 | OBLIGATORIO |
| R3 | Repo con `/data` (excluido de VCS), `/notebooks`, `/src`, `/models` | §2.1 | OBLIGATORIO |
| R4 | Ramas de desarrollo; commits como incrementos lógicos | §2.1 | OBLIGATORIO |
| R5 | Project Charter como primer entregable (README o Issue #1) | §2.2 | OBLIGATORIO |
| R6 | Definición del problema + PEAS | §2.2 | OBLIGATORIO |
| R7 | Origen/naturaleza de datos (volumen, variables, sesgos, limpieza) | §2.2 | OBLIGATORIO |
| R8 | Métricas de éxito + baseline sin IA | §2.2 | OBLIGATORIO |
| R9 | Límites del alcance | §2.2 | OBLIGATORIO |
| R10 | MVP = modelo central funcionando end-to-end (datos → inferencia) | §2.2 recuadro | OBLIGATORIO |
| R11 | Entorno aislado (venv/conda/Docker) | §2.3 | OBLIGATORIO (venv) |
| R12 | Dependencias fijadas (version pinning), Python ≥ 3.10 | §2.3 | OBLIGATORIO |
| R13 | Semilla global en todo proceso estocástico | §2.3 | OBLIGATORIO |
| R14 | Modalidad fijada antes de la primera revisión | §3 | OBLIGATORIO (Grupal) |
| R15 | MVP funcional → review → defensa técnica con prototipo | §3.1 | OBLIGATORIO |
| R16 | Escalado a Proyecto Funcional (≥ 2 ejes: API/GUI/DataEng/MLOps) | §3.2 | NO APLICA A GRUPAL (voluntario) |
| R17 | Commits semánticos indicando problema resuelto y **horas invertidas** | §5 | OBLIGATORIO |
| R18 | Código modular; procesamiento de datos desacoplado del entrenamiento | §5 | OBLIGATORIO |
| R19 | README exhaustivo: entorno, scripts, reproducción de resultados | §5 | OBLIGATORIO |
| R20 | Publicación en github.io | §6 | OBLIGATORIO solo para Proyecto Funcional individual; para grupal: OPCIONAL (10 % de rúbrica) |
| R21 | Evitar data leakage | §6 (rúbrica, 45 %) | OBLIGATORIO |
| R22 | Validación estadística rigurosa (métricas, reproducibilidad) | §6 (rúbrica, 20 %) | OBLIGATORIO en su forma básica (CV con media ± std, métricas por clase, matriz de confusión) |
| R23 | Docker | §2.3 / §3.2 | OPCIONAL |
| R24 | pytest, logging estructurado, MLflow | §3.2 | OPCIONAL para grupal |
| R25 | Gestión de issues, trazabilidad de experimentos | §6 (rúbrica, 10 %) | MUY RECOMENDABLE (Issue #1 + `reports/metrics/*.json`) |

Rúbrica: Implementación de IA 45 % · Validación y métricas 20 % · Arquitectura y código 15 % · Visibilidad 10 % · Git & MLOps 10 %. El 65 % del puntaje depende del modelo y su validación: ahí va el esfuerzo.

---

## 3. Fuente oficial y dataset canónico

### 3.1 Evidencia de procedencia

- **[EXTERNO]** research.unsw.edu.au/projects/unsw-nb15-dataset declara: "49 features with the class label"; "two million and 540,044 [records] … stored in the four CSV files … UNSW-NB15_1.csv … UNSW-NB15_4.csv"; "ground truth table … UNSW-NB15_GT.csv and the list of event file … UNSW-NB15_LIST_EVENTS.csv"; "training set is 175,341 records and the testing set is 82,332 records"; enlace de descarga "HERE" → `unsw-my.sharepoint.com`.
- **Declaración del equipo:** `OneDrive_1_9-9-2026.zip` fue descargado personalmente desde ese enlace.
- **[HECHO] Contenido del ZIP** (720.676.772 B, MD5 `33cf561eec6e808b14fbe867875039aa`):

| Entrada | Bytes | CRC-32 | Coincide con documentación |
|---|---|---|---|
| `Training and Testing Sets/UNSW_NB15_training-set.csv` | 32.293.018 | `1989f2e8` | ✔ 175.341 registros |
| `Training and Testing Sets/UNSW_NB15_testing-set.csv` | 15.380.800 | `d731dcf1` | ✔ 82.332 registros |
| `NUSW-NB15_features.csv` | 4.044 | `29e03d12` | ✔ 49 filas (la errata "NUSW" es de la distribución oficial; no renombrar) |
| `NUSW-NB15_GT.csv` | 86.426.111 | `f5c2924f` | ✔ 188.914 líneas, 12 columnas |
| `UNSW-NB15_LIST_EVENTS.csv` | 4.639 | `25c30bd1` | ✔ 208 filas |
| `UNSW-NB15_1..4.csv` | 168.979.718 / 165.221.021 / 154.588.103 / 97.588.754 | `4132173a` / `1356cee8` / `e9aedb30` / `d5fc744c` | ✔ 49 columnas sin encabezado; 700.001 + 700.001 + 700.001 + 440.044 líneas (2.540.047 vs 2.540.044 documentadas; NO VERIFICADO el motivo; sin impacto) |
| `The UNSW-NB15 description.pdf` | 189.112 | `d42d329a` | descripción oficial (1 página) |

El ZIP no incluye pcap/Bro/Argus (no se necesitan).

- **[HECHO] Kaggle** (`archive.zip`, `UNSW_NB15_training-set.csv.zip`, `UNSW_NB15_testing-set.csv.zip`) contiene los mismos archivos con CRC idénticos, pero con los nombres de la partición **cruzados** (su `training-set.csv` es el de 82.332 filas). Los dos CSV sueltos que hoy están en `data/` provienen de Kaggle y heredan ese cruce.

### 3.2 Dataset canónico [DECISIÓN]

**Fuente canónica = `data/OneDrive_1_9-9-2026.zip` (descarga oficial UNSW).**

| Rol | Archivo (dentro del ZIP oficial) | MD5 | Dimensión |
|---|---|---|---|
| TRAIN | `Training and Testing Sets/UNSW_NB15_training-set.csv` | `e55caabaa6cd4a8f1c06a227bcfababc` | 175.341 × 45 |
| TEST | `Training and Testing Sets/UNSW_NB15_testing-set.csv` | `e0beea40262e46168cdb81476dbc27b4` | 82.332 × 45 |
| Diccionario (referencia) | `NUSW-NB15_features.csv` | `9e6f08b95bc19e4c4986d4d5729f3ce9` | 49 × 4 |
| Procedencia (referencia) | `The UNSW-NB15 description.pdf` | `3698f3702d5f4e07364a1b22ec0ab26f` | — |

Crudos 1–4, GT y LIST_EVENTS: solo contexto; **no** forman parte del pipeline. Kaggle: fuera de la metodología. Acción pendiente (al salir de read-only): extraer los dos CSV oficiales a `data/raw/` con sus nombres oficiales, retirar los archivos de Kaggle y verificar MD5 en código antes de cada entrenamiento.

### 3.3 Inventario actual de `data/` y redundancias [HECHO]

| Archivo | Bytes | Estado |
|---|---|---|
| `OneDrive_1_9-9-2026.zip` | 720.676.772 | **Fuente canónica.** Conservar (no versionar) |
| `UNSW_NB15_testing-set.csv` (nombre Kaggle) | 32.293.018 | = TRAIN oficial (MD5 `e55caab…`). Reemplazar por extracción oficial con nombre correcto |
| `UNSW_NB15_training-set.csv` (nombre Kaggle) | 15.380.800 | = TEST oficial (MD5 `e0beea4…`). Ídem |
| `archive.zip` | 156.257.637 | Redundante (subconjunto del oficial, nombres cruzados) |
| `UNSW_NB15_training-set.csv.zip` / `UNSW_NB15_testing-set.csv.zip` | 4.021.633 / 8.466.093 | Redundantes (copias comprimidas exactas) |
| `NUSW-NB15_features.csv`, `UNSW-NB15_LIST_EVENTS.csv` | 4.044 / 4.639 | Idénticos a los del ZIP oficial; metadata de referencia |

---

## 4. Auditoría de TRAIN y TEST oficiales [HECHO]

| Aspecto | TRAIN (175.341) | TEST (82.332) |
|---|---|---|
| Encoding / delimitador / parsing | UTF-8 con BOM / `,` / 0 errores | Ídem |
| Columnas | 45, mismo nombre, orden y dtype en ambos | ✔ |
| NaN / strings vacíos / ±inf | 0 / 0 / 0 | 0 / 0 / 0 |
| Duplicados (ignorando `id`) | 67.601 (38,55 %) | 26.387 (32,05 %) |
| `id` | único, consecutivo 1..N (índice de fila) | ídem (se solapa numéricamente con train: sin significado) |
| Columnas constantes | ninguna | ninguna; casi constantes: `is_ftp_login`, `ct_ftp_cmd` (99,2 % ceros) |
| `proto` | 133 valores (`icmp`, `rtp` solo en train) | 131 |
| `service` | 13 valores; `'-'` = 53,71 % | 13; `'-'` = 57,27 % |
| `state` | 9 valores | 7; **`ACC`, `CLO` solo en test** → `handle_unknown='ignore'` obligatorio |
| Proporción de ataques | **68,06 %** | **55,06 %** (cambio de prior) |
| Filas con algún valor numérico fuera del rango de train | — | 72 (0,09 %) |

Redundancias entre features: `is_ftp_login == ct_ftp_cmd` (100 % en train, 99,99 % en test); `tcprtt == synack + ackdat` (100 %); |corr| > 0,98 entre `sbytes~sloss`, `dbytes~dloss`, `swin~dwin`. Discrepancia con el diccionario: `is_ftp_login` documentada como binaria pero toma valores {0, 1, 2, 4}. Sin flags TCP por paquete, sin conteos SYN, sin timestamps, sin IPs ni puertos.

Distribución de `attack_cat`:

| Clase | TRAIN n (%) | TEST n (%) |
|---|---|---|
| Normal | 56.000 (31,94) | 37.000 (44,94) |
| Generic | 40.000 (22,81) | 18.871 (22,92) |
| Exploits | 33.393 (19,04) | 11.132 (13,52) |
| Fuzzers | 18.184 (10,37) | 6.062 (7,36) |
| DoS | 12.264 (6,99) | 4.089 (4,97) |
| Reconnaissance | 10.491 (5,98) | 3.496 (4,25) |
| Analysis | 2.000 (1,14) | 677 (0,82) |
| Backdoor | 1.746 (1,00) | 583 (0,71) |
| Shellcode | 1.133 (0,65) | 378 (0,46) |
| Worms | 130 (0,07) | 44 (0,05) |

---

## 5. Targets [HECHO]

`label` ∈ {0, 1}. `attack_cat` ∈ {Analysis, **Backdoor** (singular), DoS, Exploits, Fuzzers, Generic, Normal, Reconnaissance, Shellcode, Worms}; 0 NaN. `label = 0 ⇔ attack_cat = Normal` con **0 inconsistencias** en ambos conjuntos. Tarea binaria: `y = label`. Tarea multiclase: `y = attack_cat` (10 clases).

---

## 6. Contaminación train/test y ruido de etiquetas [HECHO]

- 4.247 filas del test (5,16 %) son copias exactas (X + `label` + `attack_cat`) de filas de train; 8.541 (10,37 %) tienen una X exactamente presente en train. Subconjunto del test **disjunto** de train a nivel de X: 73.791 filas (89,63 %).
- Dentro de train: 101.040 X únicas; 1.772 X con más de una `attack_cat` (30.528 filas, 17,41 %); 229 X con ambos `label` (940 filas, 0,54 %). Dentro de test: 53.946 X únicas; 575 X conflictivas (8.809 filas, 10,70 %); 6 X con ambos `label`.
- Combinación conflictiva dominante: Analysis / Backdoor / DoS / Exploits / Fuzzers (/ Reconnaissance). **[EXTERNO]** Zoghi & Serpen (arXiv 2101.05067; Wiley 2024) documentan el mismo fenómeno ("class overlap": esas clases comparten registros idénticos).

[DECISIÓN] El test oficial se evalúa **íntegro** como evaluación principal; no se modifica ni se usa para entrenar. Un análisis complementario sobre el subconjunto train-disjoint es opcional (muy recomendable si hay tiempo).

---

## 7. Data leakage (metodológico) vs sesgo del dataset

### 7.1 Leakage metodológico — riesgos y guardas

| Riesgo | Nivel | Guarda |
|---|---|---|
| `attack_cat` en X (binario) / `label` en X (multiclase) | **CRÍTICO** | Eliminar el target alternativo en `src/data.py`; test unitario opcional |
| `id` como feature | **ALTO** | Eliminar siempre; nunca ordenar por `id` antes de dividir |
| Ajustar preprocessing, umbral, hiperparámetros, features o metas con TEST | **ALTO** | Toda decisión con CV en train; test una sola vez, al final |
| `fit` de encoder/escalador fuera del fold de entrenamiento | MEDIO | `Pipeline` + `ColumnTransformer` ajustados dentro de cada fold |
| Duplicados train↔test (5,16 %) | MEDIO | Reportar; opcional análisis train-disjoint |
| Duplicados dentro de train en CV por fila | BAJO–MEDIO | Documentar como limitación (CV algo optimista) |

### 7.2 TTL: sesgo del dataset / shortcut learning (NO es leakage)

- **[HECHO]** `sttl = 31` → 0 % ataque (39.455 filas de train); `sttl = 254` → 90,2 % (114.743); `ct_state_ttl` (derivada de TTL) separa igual. La regla `sttl >= 254` sola alcanza F1 0,884 en train. En test el atajo se debilita: 41 % de los normales tienen `sttl >= 254` (20 % en train).
- **[EXTERNO]** Sarhan et al. (arXiv 2011.09144) eliminan `sttl`, `dttl`, `ct_state_ttl` "due to their extreme correlation with the labels" y las describen como posibles "'hidden label' features". D'hooge et al. (DIMVA 2022) documentan shortcut learning por metadatos (puerto destino) en UNSW-NB15.
- **Clasificación:** TTL es observable en inferencia y no deriva del etiquetado → **sesgo del testbed / atajo**, no leakage.
- **[DECISIÓN]** Mantener las tres variables en el modelo principal (comparabilidad con el benchmark) y documentarlo como limitación. Ablación sin TTL: fuera del MVP; extra opcional (≈ 2–4 horas) solo si el MVP está terminado y documentado.

---

## 8. Límites estructurales de Macro-F1 (formulación correcta)

### 8.1 Formulación

Sea $X_g$ cada vector único de las 42 features y $n_{g,c}$ el número de filas del grupo $g$ con clase $c$. Un clasificador determinista $f(X)$ asigna una única predicción $\hat y_g$ a todo el grupo. Con $TP_c=\sum_{g:\hat y_g=c} n_{g,c}$ y $P_c=\sum_{g:\hat y_g=c} n_g$: $F1_c = 2TP_c/(N_c+P_c)$ y Macro-F1 $=\frac{1}{10}\sum_c F1_c$.

- **Accuracy máxima:** se alcanza asignando a cada grupo su clase mayoritaria.
- **Máximo F1 individual de la clase $c$:** elegir el subconjunto de grupos a predecir como $c$; el óptimo es un conjunto umbral sobre la pureza $n_{g,c}/n_g$ (Dinkelbach), calculado exactamente evaluando todos los prefijos por pureza.
- **Cota superior de Macro-F1 conjunto:** $UB = \frac{1}{10}\sum_c \max F1_c$ (cada $F1_c$ de cualquier asignación conjunta es ≤ su máximo individual). Una asignación concreta (ascenso coordinado sobre los grupos conflictivos, 28 inicializaciones) da una cota inferior alcanzable.

### 8.2 Resultados [HECHO]

| Conjunto | Accuracy máx. (mayoría) | Macro-F1 de esa asignación | **Cota superior probada de Macro-F1** | Mejor Macro-F1 alcanzable encontrado |
|---|---|---|---|---|
| TRAIN (175.341) | 0,9075 | 0,7982 | **0,8087** | 0,8029 |
| TEST (82.332) | 0,9360 | 0,7654 | **0,7877** | 0,7849 |

Máximo F1 individual por clase (TEST / TRAIN): Analysis 0,262 / 0,478 · Backdoor 0,271 / 0,433 · DoS 0,679 / 0,566 · Exploits 0,845 / 0,818 · Fuzzers 0,885 / 0,947 · Reconnaissance 0,948 / 0,902 · Generic 0,999 / 0,996 · Normal 1,000 / 0,997 · Shellcode 0,999 / 0,997 · Worms 0,989 / 0,952. Binario: accuracy máxima 0,9982 (train) / 0,9999 (test); sin techo práctico.

### 8.3 Qué demuestra y qué no

- **Demuestra:** para cualquier clasificador determinista basado en las 42 features (sin `id` ni otra información), Macro-F1 ≤ 0,8087 evaluado sobre TRAIN completo y ≤ 0,7877 evaluado sobre TEST. La meta "Macro-F1 > 0,85" **es inalcanzable** y se elimina del Charter. El modelo final (un único ajuste sobre train, evaluado en test) está sujeto a la cota de 0,7877.
- **No demuestra** que 0,8087 acote automáticamente los resultados de K-fold CV: en CV existen $K$ modelos distintos $f_1,\dots,f_K$; dos filas con X idéntica y etiquetas distintas que caigan en folds distintos pueden recibir predicciones distintas, de modo que las predicciones out-of-fold no constituyen una única función $f(X)$. El mecanismo (X idénticas con etiquetas contradictorias) sigue limitando en la práctica el Macro-F1 de CV, pero la cota exacta no es transferible. Se reporta la cota de train como **contexto estructural**, no como límite de CV.
- **Uso permitido:** la cota de TRAIN (0,8087) justifica, sin mirar el test, retirar la meta de 0,85 y fundamentar un criterio relativo. La cota de TEST (0,7877) es un análisis estructural del benchmark; **no** se usa para decisiones de modelado ni para fijar metas, y se informa en el análisis final de resultados.

---

## 9. Baselines [DECISIÓN]

- **Sin IA (binario):** regla única `pred_ataque = (dpkts == 0)` ("el destino no responde", típico de escaneos y sondas de DoS). Definida y medida **solo en train**: recall 0,650 · precisión 0,921 · FPR 0,119 · F1 0,762 · accuracy 0,724. La regla original "paquetes SYN sin ACK en ventana" no es implementable (no hay flags por paquete ni timestamps).
- **Sin IA (multiclase):** clasificador de clase mayoritaria (`DummyClassifier(strategy='most_frequent')`).
- **ML sencillo (ambas tareas):** regresión logística con `class_weight='balanced'`, one-hot + escalado estándar.

---

## 10. Criterios de éxito finales [DECISIÓN]

### 10.1 Tarea binaria (principal)

**Criterio principal:** el modelo principal debe alcanzar en el test oficial (una única evaluación) **recall de ataque ≥ 0,90** en el umbral seleccionado exclusivamente con las predicciones out-of-fold de la CV sobre train (regla pre-registrada: umbral que maximiza F1 en OOF sujeto a recall OOF ≥ 0,90), **manteniendo una tasa de falsos positivos igual o inferior a la del baseline heurístico** sobre ese mismo test, y superando en F1 de ataque a la heurística y a la regresión logística.

**Métricas reportadas (no son criterios de aprobación):** precisión, F1, FPR, PR-AUC, ROC-AUC, matriz de confusión, resultados también al umbral por defecto 0,5, y media ± desviación estándar de las métricas en CV.

### 10.2 Tarea multiclase (secundaria)

**Métrica principal:** Macro-F1, complementada con precisión, recall y F1 por clase, F1 ponderado, balanced accuracy y matriz de confusión normalizada.

**Criterio principal:** el modelo principal debe superar en Macro-F1 a los dos baselines (clase mayoritaria y regresión logística) en validación cruzada estratificada de 5 particiones sobre el conjunto de entrenamiento (media ± std; la diferencia con la regresión logística debe ser mayor que la desviación estándar del modelo principal), y mantener esa superioridad en la evaluación definitiva, realizada **una única vez** sobre el test oficial.

**Contexto para la interpretación (no meta):** la cota estructural de 0,8087 sobre train para un único clasificador; la cota de 0,7877 sobre test se informa junto con los resultados finales.

Bootstrap, intervalos de confianza y pruebas estadísticas: **opcionales**.

---

## 11. Uso metodológico del test

- Durante esta auditoría se inspeccionó el test para verificar integridad y viabilidad (esquema, nulos, duplicados, distribución de clases, consistencia de etiquetas, solapamiento con train y cota estructural). Es control de calidad de datos, no evaluación de modelos.
- **Compromiso:** ninguna decisión de modelado (features, preprocessing, hiperparámetros, umbral, balanceo, selección de modelo) ni ninguna meta numérica se basa en estadísticas del test. Las metas se definen antes de entrenar y se justifican con train. El test se evalúa una sola vez con los modelos congelados. Este compromiso y la inspección realizada se declaran en el README.

---

## 12. Alcance final (modalidad grupal)

### 12.1 MVP MÍNIMO SEGURO (obligatorio para dar por cumplida la consigna)

1. Verificación (MD5) y carga de los dos CSV oficiales.
2. EDA mínimo (shape, tipos, nulos, distribuciones de `label` y `attack_cat`, desbalance, estadísticas básicas, categóricas, duplicados, consistencia de targets, TTL).
3. Pipeline reproducible (`ColumnTransformer` + `Pipeline`, semilla global, guardas anti-leakage).
4. Baseline heurístico (binario) y clase mayoritaria (multiclase).
5. Regresión logística (ambas tareas).
6. **XGBoost** como modelo principal (ambas tareas), con parámetros razonables fijados de antemano; la búsqueda de hiperparámetros no forma parte del MVP.
7. CV 5-fold estratificada sobre train con media ± std; selección del umbral binario en OOF.
8. Evaluación final única sobre el test oficial completo.
9. Métricas guardadas (`reports/metrics/*.json`) y matrices de confusión.
10. Pipelines guardados (`models/*.joblib`).
11. CLI de inferencia (`python -m src.inference --input archivo.csv --task binary|multiclass`).
12. README reproducible; Charter en README/Issue #1; commits con horas.

### 12.2 Extras fuera del MVP (solo si el MVP está terminado y documentado; en este orden)

Unas pocas configuraciones de XGBoost por CV (≤ 5) → evaluación sobre el subconjunto del test disjunto de train (≈ 1–2 h) → ablación sin `sttl`/`dttl`/`ct_state_ttl` (≈ 2–4 h) → 2–4 tests pytest (≈ 2–3 h) → Random Forest por defecto → SHAP pequeño → bootstrap de IC → GitHub Pages / FastAPI (no previstos). Ninguno es necesario para dar por terminado el TP.

### 12.3 Presupuesto y dedicación

3–4 h por persona y semana (0–2 h en semanas de parciales); ≈ 35–42 h de equipo para el MVP; semana 7 como buffer real. Detalle en `PLAN_IMPLEMENTACION.md`.

### 12.4 Fuera del proyecto

MLP, autoencoder, PyTorch/TensorFlow, SMOTE/SMOTENC, PCA, feature selection, MLflow, Docker, frontend, base de datos, autenticación, captura en vivo, IPS, procesamiento de crudos/pcap.

---

## 13. Modelos [DECISIÓN]

| Modelo | Rol | Decisión |
|---|---|---|
| Heurística `dpkts == 0` / clase mayoritaria | Baseline sin IA | MVP |
| Regresión logística | Baseline ML | MVP |
| **XGBoost** | Modelo principal | MVP |
| Random Forest | Segunda familia de ensamble | Opcional (no necesario: XGBoost ya provee la comparación lineal vs. no lineal; costo ≈ 1–2 h si sobra tiempo) |
| MLP / Autoencoder / PyTorch | — | Fuera |

Ambas tareas se mantienen porque comparten dataset, pipeline, preprocesamiento, CV, métricas y CLI: la segunda tarea cuesta ≈ 20–30 % adicional. Binaria = principal; multiclase = secundaria (si hay atraso, se ejecuta con parámetros por defecto, sin búsqueda).

---

## 14. Preprocessing y balanceo mínimos [DECISIÓN]

```
drop: id, target alternativo
ColumnTransformer:
  categóricas [proto, service, state] → OneHotEncoder(handle_unknown='ignore', min_frequency=50)
  numéricas (39)                      → StandardScaler solo para regresión logística; passthrough para XGBoost
Pipeline(preprocesador, modelo)  — fit exclusivamente dentro del fold de entrenamiento
```
Balanceo: `class_weight='balanced'` (LR) y `sample_weight` balanceado (XGBoost). Sin SMOTE, sin PCA, sin feature selection. `log1p` solo como contingencia documentada si la regresión logística no converge.

---

## 15. Recursos y entorno [HECHO]

20 CPUs lógicas, 127,8 GB RAM, 149 GB libres; Python 3.13.12, git 2.52, venv disponible. Dataset < 100 MB en memoria; LR/XGBoost en segundos–minutos. Faltan en el entorno global: scikit-learn, xgboost, joblib, pytest (se instalan en el venv del proyecto; si alguna wheel no existe para 3.13, crear el venv con 3.12). Sin cuellos de botella.

---

## 16. Blockers y riesgos

| Nivel | Hallazgo / riesgo | Mitigación |
|---|---|---|
| CRÍTICO | Ninguno | — |
| ALTO | CSV con nombres de Kaggle en `data/` → entrenar sobre el test por error | Extraer del ZIP oficial + verificación MD5 en código |
| ALTO | Charter con meta imposible (0,85) y baseline no implementable | Charter corregido (`PROJECT_CHARTER_CORREGIDO.md`) |
| ALTO | Leakage `attack_cat`↔`label`, `id` | Guardas en `src/data.py` |
| MEDIO | Tiempo (otras materias, parciales) | Alcance mínimo, orden de recorte, núcleo cerrado en semana 4–5 |
| MEDIO | Evaluar el test más de una vez por iteraciones tardías | Congelar modelos antes de `evaluate`; documentar cualquier re-ejecución |
| MEDIO | Cambio de prior train→test desplaza recall/FPR del umbral fijado en train | Reportar ambos umbrales (OOF y 0,5) y la curva Recall–FPR |
| BAJO | Wheels de Python 3.13; convergencia de LR | venv 3.12; `log1p` como contingencia |

---

## 17. Veredicto

- **Viabilidad:** 🟡 **VIABLE CON AJUSTES MENORES**. Datos completos, íntegros y de fuente oficial; problemas restantes son de documento (Charter) y de convención de archivos (nombres de Kaggle).
- **Terminabilidad en menos de dos meses:** **SÍ**, con dedicación universitaria parcial. Estimación del MVP: ≈ 35–42 horas de equipo con 3–4 h por persona y semana (0–2 h en semanas de parciales); núcleo cerrado al final de la semana 4–5; semana 6 para README, reproducibilidad y defensa; semana 7 como buffer real que el MVP no necesita. Ver `PLAN_IMPLEMENTACION.md`.

---

## Anexo A — Afirmaciones de versiones anteriores descartadas o corregidas

| Afirmación anterior | Estado | Corrección |
|---|---|---|
| "Recall máximo teórico de Analysis = 0,086 y de Backdoor = 0,111" | **Incorrecta** | Eran los recalls de la asignación por mayoría (óptima para accuracy), no máximos. El máximo F1 individual en test es 0,262 (Analysis) y 0,271 (Backdoor) |
| "Macro-F1 ≤ ≈ 0,81" derivado de esos recalls con precisión 1 | **Método inválido** | Cota correcta: ≤ 0,7877 (test), ≤ 0,8087 (train); ver §8 |
| "Macro-F1 ≥ 0,70" como meta | **Retirada** | Derivada del test y con factor arbitrario; reemplazada por criterio relativo (§10.2) |
| "FPR ≤ 0,10" | **Retirada** | Número redondo sin anclaje; reemplazada por "FPR ≤ FPR del baseline heurístico" (§10.1) |
| TTL presentada dentro de la tabla de "riesgos de data leakage" | **Reclasificada** | Sesgo del dataset / shortcut learning (§7.2) |
| SHAP, pytest, bootstrap, test deduplicado, ablación TTL como MUST HAVE | **Reclasificados** | Opcionales / muy recomendables (§12) |
| "La cota 0,8087 acota también cualquier validación cruzada interna" | **Incorrecta** | Solo acota un único clasificador evaluado sobre train completo (§8.3) |
| "La literatura reporta F1 Backdoor ≈ 31,8 % y DoS ≈ 41 % en el split oficial (Zoghi 2024)" | **Mal atribuida** | Son detection rate / F1 de la versión NetFlow NF-UNSW-NB15 en Sarhan et al., Tabla 9 |
| Random Forest, MLP y autoencoder como parte del plan de modelos | **Recortados** | RF opcional; MLP/AE fuera |

## Anexo B — Fuentes externas

UNSW Research, *The UNSW-NB15 Dataset* (research.unsw.edu.au/projects/unsw-nb15-dataset) · Moustafa & Slay 2015, MilCIS · Sarhan, Layeghy, Moustafa, Portmann 2020, *NetFlow Datasets for ML-based NIDS* (arXiv 2011.09144) · Zoghi & Serpen 2021/2024, *UNSW-NB15: Analysis through Visualization* (arXiv 2101.05067; Wiley SPY) y *Building an IDS on UNSW-NB15: data overlap and imbalance* (Wiley CPE, doi 10.1002/cpe.8242) · D'hooge et al. 2022, *Establishing the Contaminating Effect of Metadata Feature Inclusion…* (DIMVA, LNCS) · ALzaher & AlJarullah 2025, IJACSA 16(8) (NF-UNSW-NB15-v2; no comparable).
