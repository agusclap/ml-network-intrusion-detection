# Propuesta de Proyecto Final (Project Charter) — versión corregida

**Universidad de la Defensa Nacional – CRUC IUA · Facultad de Ingeniería · Ingeniería en Informática · Inteligencia Artificial**

| | |
|---|---|
| **Título** | Sistema de Detección de Intrusiones en Redes (NIDS) mediante Machine Learning sobre UNSW-NB15 |
| **Docente** | Ing. Hernando Alexis González |
| **Modalidad** | Grupal |
| **Integrantes** | [Nombre completo alumno 1] – [Nombre completo alumno 2] |
| **Categorías tecnológicas** | Machine Learning Predictivo + Data Engineering & IA |
| **Fecha** | [Completar] |
| **Repositorio / Issue #1** | [Completar al crear el repo] |

---

## 1. Resumen

Proponemos construir un clasificador de tráfico de red que, a partir de las características de un flujo (duración, protocolo, servicio, estado de la conexión, bytes y paquetes por sentido, TTL, tiempos de establecimiento TCP y contadores de conexiones recientes), determine si el flujo es **normal o un ataque** (tarea principal) y, como segunda tarea, a qué **categoría de ataque** pertenece (Analysis, Backdoor, DoS, Exploits, Fuzzers, Generic, Reconnaissance, Shellcode, Worms, además de Normal). Usamos la partición oficial del dataset UNSW-NB15, comparamos un baseline sin IA y una regresión logística contra un modelo de gradient boosting (XGBoost) con parámetros fijados de antemano, validamos con cross-validation sobre el conjunto de entrenamiento y evaluamos una única vez sobre el test oficial. El entregable es un pipeline reproducible con una herramienta de línea de comandos que recibe un CSV de flujos y devuelve la predicción.

## 2. Definición del problema

### 2.1 Descripción funcional

Los sistemas de detección de intrusiones basados en firmas dependen de reglas escritas a mano y no detectan variantes no catalogadas. Queremos entrenar un modelo que aprenda el comportamiento de los flujos etiquetados como ataque y funcione como capa complementaria de detección basada en comportamiento. El sistema recibe un registro de flujo con 42 variables y devuelve una etiqueta (normal/ataque o categoría) con su probabilidad.

### 2.2 Modelado del entorno (PEAS)

| Componente | Descripción |
|---|---|
| **Performance** | Binario: recall de ataque y tasa de falsos positivos en el punto de operación elegido, F1, PR-AUC. Multiclase: Macro-F1 y F1 por clase. |
| **Environment** | Registros de flujo de red de la partición oficial UNSW-NB15; parcialmente observable (solo metadatos del flujo, sin contenido); estático (archivos CSV); las clases de ataque presentan solapamiento real entre sí. |
| **Actuators** | Emisión de una etiqueta (binaria o de categoría) y su probabilidad por cada flujo de entrada. |
| **Sensors** | Las 42 variables del flujo provistas por el dataset: `proto`, `service`, `state`, duración, bytes/paquetes por sentido, tasas, TTL (`sttl`, `dttl`), pérdidas, jitter, ventanas y números de secuencia TCP, tiempos de handshake (`synack`, `ackdat`, `tcprtt`), tamaños medios, profundidad HTTP y contadores de conexiones recientes (`ct_*`). |

## 3. Origen y naturaleza de los datos

- **Fuente oficial:** UNSW-NB15, Australian Centre for Cyber Security, UNSW Canberra (Moustafa & Slay, 2015). Descargado desde el enlace oficial de research.unsw.edu.au/projects/unsw-nb15-dataset (SharePoint de UNSW). Usamos exclusivamente la partición provista por los autores en `Training and Testing Sets/`:
  - `UNSW_NB15_training-set.csv`: **175.341 registros** (MD5 `e55caabaa6cd4a8f1c06a227bcfababc`).
  - `UNSW_NB15_testing-set.csv`: **82.332 registros** (MD5 `e0beea40262e46168cdb81476dbc27b4`).
  - Verificamos la integridad por MD5 en el código antes de cada entrenamiento. La copia disponible en Kaggle contiene los mismos datos con los nombres de ambos archivos intercambiados; por eso no la usamos y cargamos cada archivo por su hash y no por su nombre.
- **Estructura:** 45 columnas por registro = **42 variables predictoras** (39 numéricas y 3 categóricas: `proto`, `service`, `state`) + `id` (índice de fila, se descarta) + dos etiquetas: `label` (0 = normal, 1 = ataque) y `attack_cat` (10 valores: 9 categorías de ataque + `Normal`; `label = 0` si y solo si `attack_cat = Normal`, verificado sin excepciones). El dataset crudo original tiene 49 variables (incluye IPs, puertos y timestamps) que los autores excluyeron de la partición; no las usamos.
- **Calidad:** sin valores nulos ni infinitos; sin errores de formato. Existen categorías de `state` que solo aparecen en el test (`ACC`, `CLO`), por lo que la codificación one-hot debe tolerar categorías desconocidas.
- **Desbalance:** en entrenamiento 68 % de los registros son ataques (55 % en test). Entre categorías el desbalance es fuerte: `Generic` 40.000 y `Exploits` 33.393 frente a `Worms` 130 y `Shellcode` 1.133. Lo tratamos con ponderación de clases (`class_weight` / `sample_weight`) y métricas robustas (F1 por clase, Macro-F1, PR-AUC); no usamos sobremuestreo sintético.
- **Particularidades detectadas en el análisis previo de los datos, que condicionan la metodología:**
  1. **Solapamiento de etiquetas:** un 17,4 % de las filas de entrenamiento comparten exactamente las 42 variables con filas de otra categoría (sobre todo entre Analysis, Backdoor, DoS, Exploits, Fuzzers y Reconnaissance). Para un único clasificador determinista esto impone un techo estructural de Macro-F1 de ≈ 0,81 sobre el conjunto de entrenamiento; por eso no fijamos una meta absoluta de Macro-F1 y usamos un criterio relativo a los baselines.
  2. **Cambio de distribución entre entrenamiento y test:** la proporción de ataques pasa de 68 % a 55 % y un 5 % de las filas del test son copias exactas de filas de entrenamiento. El test se evalúa íntegro (benchmark oficial) y estas características se discuten como limitación.
  3. **Variables de TTL (`sttl`, `dttl`, `ct_state_ttl`):** separan casi por sí solas ataque de normal por cómo se generó el tráfico sintético del testbed (una regla sobre `sttl` alcanza F1 ≈ 0,88 en entrenamiento). No es fuga de información —el TTL se observa en producción— sino un sesgo del dataset. Las mantenemos en el modelo principal y lo documentamos como limitación.
  4. **Redundancias menores:** `ct_ftp_cmd` es idéntica a `is_ftp_login`; `tcprtt = synack + ackdat`. No afectan a los modelos de árboles.

## 4. Métricas de éxito y baselines

### 4.1 Baselines

- **Sin IA (binario):** regla `dpkts == 0` (el destino no responde: comportamiento típico de escaneos y sondas de DoS). Definida y medida únicamente sobre entrenamiento: recall 0,65, precisión 0,92, tasa de falsos positivos 0,12, F1 0,76.
- **Sin IA (multiclase):** predecir siempre la clase mayoritaria.
- **ML sencillo (ambas tareas):** regresión logística con ponderación de clases sobre las mismas variables.

### 4.2 Criterio de éxito — tarea binaria (principal)

El modelo principal debe alcanzar sobre el test oficial, en una única evaluación, **recall de ataque ≥ 0,90 manteniendo una tasa de falsos positivos igual o inferior a la del baseline heurístico**, y superar en F1 de ataque tanto a la heurística como a la regresión logística. El umbral de decisión se elige **solo con las predicciones out-of-fold de la validación cruzada sobre entrenamiento** (regla fijada de antemano: el umbral que maximiza F1 sujeto a recall ≥ 0,90 en OOF).

Métricas reportadas (no son criterios de aprobación): precisión, F1, tasa de falsos positivos, PR-AUC, ROC-AUC, matriz de confusión, resultados al umbral 0,5, y media ± desviación estándar en validación cruzada.

### 4.3 Criterio de éxito — tarea multiclase (secundaria)

La métrica principal es **Macro-F1**, complementada con precisión, recall y F1 por clase, F1 ponderado, balanced accuracy y matriz de confusión. El modelo principal deberá **superar a los dos baselines en Macro-F1 mediante validación cruzada estratificada de 5 particiones sobre el conjunto de entrenamiento** (media ± desviación estándar; la mejora sobre la regresión logística debe ser mayor que la desviación estándar del modelo principal) y mantener esa superioridad en la evaluación definitiva, realizada una única vez sobre el test oficial. Reportamos el techo estructural de Macro-F1 del dataset como contexto para interpretar los resultados, no como meta.

### 4.4 Cómo validamos

- Cross-validation estratificada de 5 particiones sobre el conjunto de entrenamiento, con semilla fija, para comparar modelos y fijar el umbral binario.
- **Sin búsqueda de hiperparámetros en el MVP:** la regresión logística y XGBoost usan parámetros razonables fijados de antemano y documentados en el código. Solo si el proyecto está terminado y documentado podríamos probar unas pocas configuraciones, siempre por validación cruzada.
- Reajuste de cada modelo sobre todo el entrenamiento y **una única evaluación** sobre el test oficial. Después de esa evaluación no se modifican modelos ni umbrales.
- Semilla global (42) en la división, los modelos y cualquier muestreo; versiones de librerías fijadas.
- Transparencia: durante la auditoría inicial de los datos inspeccionamos el test para verificar su integridad (nulos, duplicados, distribución de clases, solapamiento con entrenamiento). Ninguna decisión de modelado ni meta se basó en esa inspección.

## 5. Alcance del MVP

### 5.1 MVP (lo que entregamos)

Un pipeline reproducible, ejecutable desde consola, que:
1. verifica por MD5 y carga los dos CSV oficiales (`python -m src.data`);
2. entrena y valida por CV los baselines, la regresión logística y XGBoost para cada tarea, guardando métricas y el pipeline entrenado (`python -m src.train --task binary|multiclass --model heuristic|lr|xgb`);
3. evalúa una única vez sobre el test oficial y guarda métricas y matrices de confusión (`python -m src.evaluate --task ... --model ...`);
4. predice sobre un CSV nuevo con el mismo preprocesamiento, validando el esquema de entrada (`python -m src.inference --input archivo.csv --task binary`);
5. documenta en el README cómo recrear el entorno y reproducir cada número del informe.

Incluye un notebook de EDA acotado (forma, tipos, nulos, distribución de etiquetas, desbalance, categóricas, duplicados, consistencia `label`/`attack_cat`, variables TTL).

El proyecto se considera terminado cuando lo anterior funciona y está documentado. Nada de lo que sigue es necesario para darlo por terminado.

### 5.2 Posibles extensiones, fuera del MVP

Solo si el MVP está terminado y documentado, en este orden: unas pocas configuraciones adicionales de XGBoost; evaluación complementaria sobre el subconjunto del test disjunto de entrenamiento; ablación sin variables TTL; 2–4 tests automáticos; Random Forest; SHAP acotado.

## 6. Límites del alcance (fuera del proyecto)

- Inspección de paquetes o contenido; procesamiento de los archivos crudos, ground truth o pcap; re-derivación de la partición.
- Captura de tráfico en vivo, integración con hardware de red, inferencia en tiempo real, sistema de prevención (bloqueo).
- Robustez ante ataques adversariales.
- Búsqueda de hiperparámetros como requisito; redes neuronales (MLP, autoencoder), PyTorch/TensorFlow, sobremuestreo sintético (SMOTE), PCA, selección de features.
- API web, interfaz gráfica, base de datos, autenticación, MLflow, Docker, GitHub Pages.

## 7. Arquitectura técnica mínima

- **Preprocesamiento:** eliminar `id` y el target alternativo; `ColumnTransformer` con `OneHotEncoder(handle_unknown='ignore')` para `proto`, `service`, `state`; escalado estándar de las numéricas solo para la regresión logística; sin transformación para XGBoost. Todo dentro de un `Pipeline` de scikit-learn ajustado únicamente con datos de entrenamiento (o del fold de entrenamiento).
- **Modelos:** heurística `dpkts == 0` / clase mayoritaria (sin IA); regresión logística (`class_weight='balanced'`); **XGBoost** (`tree_method='hist'`, `sample_weight` balanceado, semilla fija, parámetros fijados de antemano) como modelo principal.
- **Artefactos:** un `.joblib` por tarea y modelo; métricas en JSON por corrida; figuras de matrices de confusión.
- **Stack:** Python ≥ 3.10 en entorno virtual (`venv`), `requirements.txt` con versiones exactas; pandas, NumPy, scikit-learn, XGBoost, joblib, matplotlib, Jupyter.

## 8. Metodología de trabajo

- Repositorio Git con rama `main` estable y ramas `feature/*` por incremento; commits semánticos que indican el problema resuelto y las horas invertidas (ej. `feat(train): CV 5-fold para XGBoost binario [3h]`).
- Este Charter se publica como Issue #1 y como sección del README; los cambios de alcance se registran en issues.
- `data/` excluido del control de versiones salvo `data/README.md` con la procedencia y los MD5.
- Semilla global y versiones fijadas; cualquier persona debe poder recrear el entorno y obtener los mismos números.
- Dedicación prevista: 3–4 horas por integrante y semana (menos en semanas de parciales); presupuesto total estimado de 35–45 horas de equipo.

## 9. Cronograma (7 semanas)

| Semana | Objetivo | Entregable verificable |
|---|---|---|
| 1 | Repo, entorno, datos oficiales verificados, carga, EDA mínimo, Charter en Issue #1 | `requirements.txt`; `python -m src.data` verde; notebook de EDA |
| 2 | Pipeline, guardas anti-leakage, métricas, baseline heurístico y regresión logística binaria end-to-end | primer resultado end-to-end (LR binaria con CV y umbral OOF) |
| 3 | XGBoost binario; regresión logística y XGBoost multiclase reutilizando la infraestructura | tabla comparativa de CV; **congelamiento de modelos** |
| 4 | Cierre de CV, congelamiento y evaluación final única en test (ambas tareas) | `reports/metrics/*.json`, matrices, `models/*.joblib` |
| 5 | CLI de inferencia, README con resultados, correcciones | `python -m src.inference` funcionando desde un venv limpio |
| 6 | Reproducibilidad (reproducción desde cero por el otro integrante), documentación final, ensayo de defensa | README final |
| 7 | **Buffer** para parciales, imprevistos y correcciones de la cátedra | — |

Cada hito tiene una semana de tolerancia; si una semana de parcial no permite trabajar, el cronograma lo absorbe con la holgura de las semanas 3–5 y la semana 7.

## 10. Riesgos y simplificación

Si el núcleo se atrasa, simplificamos la forma sin tocar la sustancia: EDA solo con tablas; multiclase con reporte mínimo (macro-F1, F1 por clase, matriz), nunca eliminada; README mínimo pero completo. No se recortan: reproducibilidad, guardas anti-leakage, baselines, regresión logística, XGBoost, validación cruzada, evaluación única en test, pipeline guardado, inferencia por CLI, README y los requisitos explícitos de la consigna.

## 11. Justificación de la elección

Elegimos esta propuesta frente a otras alternativas (mantenimiento predictivo, fraude, análisis de conducción, agentes/LLM) porque combina de forma natural dos categorías de la cátedra, usa un dataset público, oficial y bien documentado, permite un baseline sin IA honesto y métricas de validación claras, y su alcance es compatible con la modalidad grupal y con el tiempo disponible. El análisis previo del dataset (solapamiento de etiquetas, sesgo del TTL, cambio de distribución) nos da además material sólido para discutir limitaciones en la defensa.
