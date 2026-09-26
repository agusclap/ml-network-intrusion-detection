# PLAN DE IMPLEMENTACIÓN — NIDS sobre UNSW-NB15 (modalidad grupal, presupuesto reducido)

Principio rector: **primero poco y bien; después, solo si sobra tiempo, agregar.** Correcto > complejo · Terminado > ambicioso · Reproducible > lleno de features · Un modelo bien validado > cinco a medias.

**Disponibilidad real asumida:** dos integrantes; 3–4 h por persona y semana en semanas normales (6–8 h de equipo); 0–2 h por persona en semanas con parciales (0–4 h de equipo). **Presupuesto objetivo total: 35–45 h de equipo.** Horizonte: 7 semanas; el MVP debe estar cerrado al final de la semana 6 **sin necesitar la semana 7**, que es buffer real.

---

## 1. Núcleo del proyecto (camino crítico, en orden)

```
datos oficiales (MD5) → EDA mínimo → preprocessing → guardas anti-leakage → baseline heurístico
→ Logistic Regression → XGBoost (parámetros razonables, sin tuning) → CV 5-fold en train
→ congelamiento → evaluación final única en test → guardar pipeline → CLI → README
```

Decisiones definitivas: binaria = tarea principal; multiclase = secundaria (se mantiene porque reutiliza todo el pipeline y solo cambia el target y las métricas); tres modelos y nada más (heurística, LR, XGBoost); XGBoost con parámetros fijados de antemano; **el tuning no forma parte del MVP** y nunca debe ser necesario para terminar.

## 2. Arquitectura mínima

```
src/config.py     semilla (42), rutas, MD5 de los CSV oficiales, listas de columnas, definición de tareas,
                  hiperparámetros fijos de LR y XGBoost
src/data.py       carga + verificación MD5 + X/y por tarea; guardas: elimina id y el target alternativo
src/features.py   build_preprocessor(model): ColumnTransformer
                    proto/service/state → OneHotEncoder(handle_unknown='ignore', min_frequency=50)
                    numéricas (39)      → StandardScaler (LR) | passthrough (XGBoost)
src/baselines.py  heurística binaria dpkts == 0; clase mayoritaria (multiclase)
src/metrics.py    métricas binarias (recall, FPR, precisión, F1, PR-AUC, ROC-AUC, matriz) y multiclase
                  (macro-F1, F1 por clase, weighted-F1, balanced accuracy, matriz)
src/train.py      CV manual StratifiedKFold(5, shuffle, seed) por (task, model) → media ± std;
                  binario: predicciones OOF → umbral (max F1 s.a. recall ≥ 0,90);
                  refit en train completo → models/<task>_<model>.joblib; reports/metrics/<task>_<model>_cv.json
src/evaluate.py   UNA evaluación sobre el test oficial → reports/metrics/<task>_<model>_test.json + matriz (png)
src/inference.py  CLI: valida esquema, aplica el pipeline guardado, escribe predicciones (+ probabilidades);
                  si el CSV trae targets, imprime métricas
```

- CV manual (≈ 30 líneas) en lugar de `cross_validate`/`RandomizedSearchCV`: XGBoost necesita `sample_weight` por fold y así se evita el ruteo de metadatos de scikit-learn. Es explícito y fácil de defender.
- Un único `Pipeline(preprocesador, modelo)` persistido con `joblib`: la inferencia usa exactamente el mismo preprocesamiento.
- `src/` plano: separación de responsabilidades suficiente para la consigna (datos ≠ features ≠ entrenamiento ≠ evaluación ≠ inferencia).

## 3. Estructura de carpetas

```
ProyectoIA2026/
├── data/                      # gitignored salvo data/README.md
│   ├── raw/                   # UNSW_NB15_training-set.csv, UNSW_NB15_testing-set.csv (del ZIP oficial)
│   │   └── referencia/        # resto del ZIP oficial (crudos, GT, diccionario); fuera del pipeline
│   ├── README.md              # procedencia, URL oficial, fecha de descarga, MD5, nota sobre Kaggle
│   └── (el ZIP oficial no se conserva: se re-descarga desde la URL de data/README.md)
├── notebooks/01_eda_minimo.ipynb
├── src/  (config, data, features, baselines, metrics, train, evaluate, inference, __init__)
├── models/                    # *.joblib (gitignored; se regeneran con train.py)
├── reports/metrics/           # *.json versionados
├── reports/figures/           # matrices de confusión
├── requirements.txt           # versiones exactas (pip freeze tras instalar en el venv)
├── README.md                  # Charter + reproducción + resultados
└── .gitignore
```

## 4. Fases y horas (equipo)

| Fase | Contenido | Horas | Riesgo |
|---|---|---|---|
| F0 Setup | repo, ramas, `.gitignore`, venv, instalar y fijar dependencias, `config.py`, extraer CSV oficiales a `data/raw/`, `data/README.md` con MD5 | 3,0 | BAJO |
| F1 Charter | volcar el Charter a README/Issue #1 (el DOCX se actualiza copiando el texto) | 1,5 | BAJO |
| F2 Datos + EDA | `data.py` (carga, MD5, X/y, guardas) 1,5 h + notebook de EDA mínimo 2,5 h | 4,0 | BAJO |
| F3 Pipeline + métricas + baselines | `features.py`, `metrics.py`, `baselines.py` | 4,0 | BAJO |
| F4 LR binaria end-to-end | `train.py` con CV manual + LR binaria + umbral OOF | 3,0 | BAJO |
| F5 XGBoost + multiclase | XGBoost binario (parámetros fijos, `sample_weight`) 2,5 h + LR y XGBoost multiclase reutilizando `train.py` 2,5 h | 5,0 | MEDIO |
| F6 Congelamiento + test | `evaluate.py`; una evaluación por tarea/modelo; JSON + matrices | 3,5 | MEDIO (disciplina) |
| F7 CLI | `inference.py` con validación de esquema y categorías desconocidas | 3,0 | BAJO |
| F8 README + reproducibilidad | instrucciones, tablas de resultados, limitaciones; reproducción de los 4 comandos desde un venv limpio por el otro integrante | 5,0 | BAJO |
| F9 Defensa | guion de decisiones + demo del CLI | 3,0 | BAJO |
| **Total MVP** | | **35 h** (rango realista **35–42 h**) | |

Ningún extra está incluido en estas horas.

## 5. Cronograma (7 semanas)

| Semana | Fases | Hito verificable al cierre | Horas equipo |
|---|---|---|---|
| **1** | F0, F1, F2 | Repo + venv + `requirements.txt`; `python -m src.data` verifica MD5 y carga; EDA mínimo; Charter en Issue #1 | 7–8,5 |
| **2** | F3, F4 | **Primer modelo end-to-end**: heurística + LR binaria con CV y umbral OOF | 7 |
| **3** | F5 | XGBoost binario; LR y XGBoost multiclase; tabla comparativa de CV | 5 |
| **4** | F6 | **Congelamiento de modelos** y **evaluación única en test** (ambas tareas); métricas y matrices guardadas; `.joblib` | 3,5 |
| **5** | F7, inicio F8 | CLI funcionando; README con resultados y correcciones | 5 |
| **6** | F8, F9 | Reproducción desde venv limpio por el otro integrante; README final; ensayo de defensa | 6 |
| **7** | — | **BUFFER real**: parciales, imprevistos, correcciones de la cátedra | 0–6 |

Suma planificada semanas 1–6: 33,5–35 h, con las semanas 3, 4 y 5 por debajo del máximo semanal.

**Regla de absorción de semanas de parcial:** cada hito tiene una semana de tolerancia. Si una semana rinde 0–4 h, el hito se corre una semana y se compensa con la holgura de las semanas 3–5 y con la semana 7. Límites duros: primer modelo end-to-end a más tardar en la semana 3; test evaluado a más tardar en la semana 5; README reproducible a más tardar en la semana 7. En una semana de parcial solo se hacen tareas de ≤ 1 h (issues, README) o nada.

Congelamiento: al cerrar la semana 3 (o cuando termine F5) no se modifican features, preprocesamiento, modelos ni umbral. Cualquier re-evaluación del test posterior a la primera se documenta explícitamente.

## 6. Dependencias e hiperparámetros fijos

Obligatorias (versiones exactas tras instalar): `pandas`, `numpy`, `scikit-learn`, `xgboost`, `joblib`, `matplotlib`, `jupyter`/`ipykernel`. **No** instalar: PyTorch, TensorFlow, imbalanced-learn, shap, MLflow, FastAPI, pytest (salvo extras posteriores al Definition of Done). Si alguna wheel falta para Python 3.13, crear el venv con 3.12.

Parámetros fijados de antemano (sin búsqueda):
- `LogisticRegression(class_weight='balanced', max_iter=2000, C=1.0, random_state=42)`.
- `XGBClassifier(tree_method='hist', n_estimators=400, max_depth=6, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1)` con `sample_weight = compute_sample_weight('balanced', y_fold)`; multiclase con `objective='multi:softprob'`.
- Contingencia documentada si LR no converge: subir `max_iter` y, solo si persiste, `log1p` sobre las numéricas de cola pesada.

## 7. EDA mínimo obligatorio

Una notebook: shape de train y test; dtypes; nulos (esperado 0); distribución de `label` y `attack_cat` (tablas y un gráfico de barras); desbalance por clase; `describe()` de numéricas; cardinalidad y top valores de `proto`, `service`, `state` (categorías presentes solo en test); duplicados ignorando `id`; verificación `label = 0 ⇔ attack_cat = Normal`; cruce `sttl` × `label` (sesgo TTL); columnas a excluir (`id`, target alternativo). Nada más.

## 8. Definition of Done (sin extras)

Cuando todos los ítems estén marcados, **el TP está terminado**. Ninguno de los extras del §10 es necesario.

- [ ] Los dos CSV oficiales están en `data/raw/` con nombre oficial y `python -m src.data` verifica sus MD5.
- [ ] `data/README.md` documenta procedencia (URL oficial, fecha, MD5) y la nota sobre Kaggle.
- [ ] Charter corregido publicado como Issue #1 y en el README; DOCX actualizado con el mismo texto.
- [ ] Repo con `data/ notebooks/ src/ models/ reports/`, `.gitignore`, rama `main` + ramas de feature, commits con horas.
- [ ] Venv + `requirements.txt` con versiones exactas; Python ≥ 3.10; semilla global en `config.py`.
- [ ] Notebook de EDA mínimo ejecutada de punta a punta.
- [ ] `src/data.py` elimina `id` y el target alternativo en ambas tareas.
- [ ] Pipeline `ColumnTransformer` + `Pipeline` ajustado solo con datos de entrenamiento/fold.
- [ ] Baseline heurístico (`dpkts == 0`) y clase mayoritaria evaluados.
- [ ] LR y XGBoost (parámetros fijos) entrenados y validados por CV 5-fold (media ± std) en ambas tareas.
- [ ] Umbral binario elegido con predicciones OOF según la regla pre-registrada.
- [ ] Modelos congelados; test oficial evaluado **una sola vez** por tarea; métricas en `reports/metrics/*.json`; matrices en `reports/figures/`.
- [ ] Criterios de éxito del Charter verificados y reportados (cumplidos o no, con explicación).
- [ ] Pipelines guardados en `models/*.joblib`, regenerables con `train.py`.
- [ ] `python -m src.inference --input archivo.csv --task binary|multiclass` funciona desde un venv limpio y rechaza esquemas inválidos.
- [ ] README permite recrear el entorno, ejecutar cada script y reproducir cada número; incluye limitaciones (solapamiento de etiquetas, sesgo TTL, cambio de prior, duplicados) y la declaración sobre el uso del test.
- [ ] El otro integrante reprodujo los resultados desde cero con los 4 comandos.
- [ ] Podemos explicar en la defensa: por qué XGBoost, por qué esos baselines, cómo evitamos leakage, por qué no hay meta absoluta de Macro-F1, qué es el sesgo TTL, qué limita el dataset.

## 9. Si el núcleo se atrasa (orden de simplificación)

No hay extras que recortar en el camino crítico; lo que se simplifica es la forma, nunca la sustancia:
1. EDA solo con tablas (sin gráficos).
2. Multiclase con LR y XGBoost por defecto y reporte mínimo (macro-F1, F1 por clase, matriz), sin análisis adicional. Nunca se elimina: figura en el Charter.
3. README mínimo pero completo (instrucciones de reproducción + tablas de resultados + limitaciones en viñetas).
4. Defensa preparada con el propio README como guion.

**Nunca se recorta:** reproducibilidad (seed, versiones), guardas anti-leakage, baselines, LR, XGBoost, CV, evaluación única en test, pipeline guardado, CLI, README, estructura de repo, commits con horas, Charter.

## 10. Extras — solo después del Definition of Done, en este orden

1. Unas pocas configuraciones de XGBoost (≤ 5, por CV; 1–2 h).
2. Evaluación sobre el subconjunto del test disjunto de train (1–2 h).
3. Ablación sin `sttl`/`dttl`/`ct_state_ttl` (2–4 h).
4. 2–4 tests pytest (2–3 h).
5. Random Forest por defecto (1–2 h).
6. SHAP pequeño (4–6 h).
7. Bootstrap de IC (2 h).
8. GitHub Pages / FastAPI / Docker / MLflow (no previstos).

Fuera del proyecto en cualquier caso: MLP, autoencoder, PyTorch/TensorFlow, SMOTE/SMOTENC, PCA, feature selection, frontend, base de datos, autenticación, captura en vivo, IPS, crudos/pcap.

## 11. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Semanas de parcial con 0–4 h de equipo | ALTA | ALTO | Semanas 3–5 livianas + semana 7 buffer; regla de absorción; límites duros |
| Entrenar sobre el test por los nombres cruzados de Kaggle | MEDIA | ALTO | Extracción del ZIP oficial + MD5 en `data.py` |
| Evaluar el test más de una vez | MEDIA | MEDIO | Congelamiento al cerrar F5; re-evaluaciones documentadas |
| `sample_weight` con Pipeline/CV | MEDIA | BAJO | CV manual |
| LR no converge | MEDIA | BAJO | `max_iter` ↑; `log1p` como contingencia |
| Cambio de prior train→test desplaza el punto de operación | ALTA | BAJO | Reportar umbral OOF y 0,5; discutirlo |
| Sobre-ingeniería espontánea | MEDIA | MEDIO | Definition of Done sin extras; §10 solo después |

## 12. Convenciones

- Commits: `tipo(ámbito): qué resuelve [Nh]` (ej. `feat(data): carga con verificación MD5 [1.5h]`).
- Ramas: `main` estable + `feature/<tema>`; merge revisado por el otro integrante.
- Artefactos: `models/binary_xgb.joblib`, `reports/metrics/binary_xgb_cv.json`, `reports/metrics/binary_xgb_test.json`.
- Semilla: `SEED = 42` en `src/config.py`; toda función que muestree recibe `random_state=SEED`.
