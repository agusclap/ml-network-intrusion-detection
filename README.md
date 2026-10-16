# Detección de intrusiones en redes con Machine Learning

Trabajo final de Inteligencia Artificial - Ingeniería en Informática - Universidad de la Defensa Nacional (CRUC IUA), 2026.

Docente: Ing. Hernando Alexis González. Modalidad grupal.

## Integrantes

- Maximo Agustin Rodeyro
- Lautaro Niccolini

## De qué se trata

Estamos armando un sistema de detección de intrusiones (NIDS) basado en Machine Learning. A partir de los datos de un flujo de red, el modelo decide si ese flujo es tráfico normal o un ataque. Como segunda tarea, también intenta predecir qué tipo de ataque es.

Trabajamos con el dataset [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset), usando la división en train y test que publicaron sus autores.

## Estado actual

Ya tenemos el primer modelo funcionando de punta a punta en la tarea binaria, validado con cross-validation sobre el train. Todavía no evaluamos sobre el test: lo vamos a hacer una sola vez, cuando los modelos estén terminados.

- [x] Carga de los datos oficiales con verificación de integridad (MD5)
- [x] Análisis exploratorio ([notebooks/01_eda_minimo.ipynb](notebooks/01_eda_minimo.ipynb))
- [x] Preprocesamiento: one-hot de las categóricas y estandarización de las numéricas para la regresión logística
- [x] Baselines: regla sin IA (`dpkts == 0`) y clase mayoritaria
- [x] Cross-validation de 5 folds con la regla, la regresión logística y XGBoost en la tarea binaria
- [ ] Complemento del análisis exploratorio: outliers, entropía y duplicados
- [ ] Tarea multiclase
- [ ] Evaluación final sobre el test
- [ ] Script de predicción por consola

## Propuesta del proyecto

La propuesta completa (problema, PEAS, datos, métricas de éxito, baselines y alcance) está en [PROJECT_CHARTER_CORREGIDO.md](PROJECT_CHARTER_CORREGIDO.md) y también en el Issue #1 del repositorio.

En resumen:

- **Tarea principal:** clasificación binaria (normal o ataque).
- **Tarea secundaria:** clasificación multiclase (Normal o una de las 9 categorías de ataque).
- **Baselines:** una regla sin IA (`dpkts == 0`, es decir, el destino no respondió) y una regresión logística.
- **Modelo principal:** XGBoost.
- **Validación:** cross-validation de 5 folds sobre el train. El test se usa una sola vez, al final.
- **Objetivo en la tarea binaria:** detectar al menos el 90 % de los ataques sin tener más falsos positivos que la regla sin IA.
- **Objetivo en la tarea multiclase:** superar a los baselines en Macro-F1.

## Datos

| Archivo | Registros | Para qué lo usamos |
|---|---|---|
| `UNSW_NB15_training-set.csv` | 175.341 | Entrenamiento y cross-validation |
| `UNSW_NB15_testing-set.csv` | 82.332 | Evaluación final |

Los datos no están en el repositorio porque son pesados. En [data/README.md](data/README.md) explicamos cómo descargarlos y cómo comprobar que son los archivos correctos.

Ojo con la copia del dataset que hay en Kaggle: tiene los nombres de train y test intercambiados.

## Estructura del repositorio

```
data/              datos (no se suben, ver data/README.md)
notebooks/         análisis exploratorio
src/
  config.py        semilla, rutas, hashes de los datos, columnas e hiperparámetros
  data.py          verificación y carga de los datos; separación en X e y sin el target de la otra tarea
  features.py      preprocesamiento (one-hot y escalado)
  baselines.py     regla sin IA y clase mayoritaria
  metrics.py       métricas y elección del umbral
  train.py         cross-validation, umbral y entrenamiento del modelo final
models/            modelos entrenados (no se suben, se generan con train.py)
reports/metrics/   métricas de la cross-validation en JSON
```

## Instalación y uso

Probado con Python 3.13.

```bash
# Crear el entorno e instalar dependencias
python -m venv .venv
.venv\Scripts\activate          # en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# Descargar los datos según data/README.md y verificarlos
python -m src.data

# Cross-validation y entrenamiento final (tarea binaria)
python -m src.train --model heuristic
python -m src.train --model lr
python -m src.train --model xgb
```

Cada corrida de `train.py` imprime las métricas de cada fold y su promedio, guarda el modelo entrenado con todo el train en `models/` y las métricas en `reports/metrics/`.

Usamos la semilla 42 y versiones fijas de las librerías, así que los resultados se tienen que poder reproducir exactamente.

Todavía falta: la tarea multiclase, la evaluación sobre el test (`src/evaluate.py`) y el script de predicción (`src/inference.py`).

## Resultados

### Tarea binaria: cross-validation de 5 folds sobre el train

Media ± desviación estándar de los 5 folds, con el umbral por defecto (0,5):

| Modelo | F1 | Recall | Precisión | Tasa de falsos positivos | ROC-AUC |
|---|---|---|---|---|---|
| Regla sin IA (`dpkts == 0`) | 0,762 ± 0,002 | 0,650 ± 0,002 | 0,921 ± 0,002 | 0,119 ± 0,003 | 0,766 |
| Regresión logística | 0,951 ± 0,001 | 0,952 ± 0,002 | 0,949 ± 0,001 | 0,108 ± 0,001 | 0,984 |
| XGBoost | **0,967 ± 0,001** | **0,957 ± 0,001** | **0,978 ± 0,001** | **0,046 ± 0,003** | **0,994** |

Con el umbral elegido usando las predicciones out-of-fold (el de mejor F1 entre los que dan recall de 0,90 o más):

| Modelo | Umbral | Recall | Tasa de falsos positivos | F1 |
|---|---|---|---|---|
| Regresión logística | 0,368 | 0,982 | 0,161 | 0,954 |
| XGBoost | 0,347 | 0,978 | 0,076 | 0,971 |

Qué vemos hasta ahora:

- Los dos modelos de ML superan ampliamente a la regla sin IA, que solo detecta el 65 % de los ataques.
- XGBoost detecta casi la misma proporción de ataques que la regresión logística, pero con menos de la mitad de falsos positivos. La regresión logística separa las clases con una frontera lineal; los árboles de XGBoost pueden combinar condiciones sobre varias variables, y en este problema eso marca la diferencia.
- Con su umbral, XGBoost cumple el criterio de la tarea binaria (recall de al menos 0,90 con menos falsos positivos que la regla sin IA). La regresión logística, para llegar a ese recall, tiene más falsos positivos que la regla.
- La desviación estándar entre folds es muy chica en todos los casos: los modelos son estables.

Estos números son de cross-validation. El resultado definitivo va a salir de la evaluación sobre el test, que todavía no hicimos.

## Cosas a tener en cuenta del dataset

- Para que el modelo no "vea la respuesta", en cada tarea sacamos de la entrada la columna `id` y la etiqueta que no corresponde (`attack_cat` en la tarea binaria y `label` en la multiclase).
- Hay registros con exactamente los mismos valores pero distinta categoría de ataque, sobre todo entre Analysis, Backdoor, DoS y Exploits. Por eso ningún modelo puede separar esas clases del todo.
- Las variables de TTL (`sttl`, `dttl`, `ct_state_ttl`) separan casi solas el tráfico normal de los ataques, por cómo se generó el tráfico en el laboratorio. Las dejamos en el modelo y lo tomamos como una limitación del dataset.
- En el train el 68 % de los registros son ataques y en el test el 55 %. Además, alrededor del 5 % de las filas del test también están en el train.
- El 38 % de las filas del train está repetido. No lo eliminamos porque son flujos reales que se repiten, no errores de carga; por eso la cross-validation puede dar resultados algo optimistas.
- Los valores extremos de las variables numéricas tampoco se eliminan: en tráfico de red son legítimos y muchas veces son la señal del ataque.

La justificación de cada decisión y su relación con el teórico de la materia está en la sección 3 y en la tabla "Relación con los contenidos de la materia" del [Charter](PROJECT_CHARTER_CORREGIDO.md). El análisis completo de los datos está en [AUDITORIA_VIABILIDAD.md](AUDITORIA_VIABILIDAD.md).

## Cronograma

| Semana | Fechas | Qué hacemos | Estado |
|---|---|---|---|
| 1 | 28/9 – 4/10 | Repositorio, entorno, carga de datos y análisis exploratorio | Hecho |
| 2 | 5/10 – 11/10 | Preprocesamiento, regla sin IA y regresión logística binaria | Hecho |
| 3 | 12/10 – 18/10 | XGBoost binario y complemento del análisis exploratorio | En curso |
| 4 | 19/10 – 25/10 | Revisión con la cátedra y tarea multiclase | |
| 5 | 26/10 – 1/11 | Evaluación final en el test y script de predicción | |
| 6 | 2/11 – 8/11 | Revisión de reproducibilidad, documentación y defensa | |
| 7 | 9/11 – 15/11 | Margen para imprevistos | |

La evaluación sobre el test la dejamos para después de la revisión con la cátedra, para poder incorporar sus correcciones sin haber mirado todavía el test. El detalle está en [PLAN_IMPLEMENTACION.md](PLAN_IMPLEMENTACION.md).

## Forma de trabajo

- La rama `main` tiene siempre una versión estable y cada tarea se hace en su propia rama.
- En los commits ponemos qué se hizo y cuántas horas llevó, por ejemplo: `feat(data): carga y verificación de los CSV [1.5h]`.

## Referencias

- Moustafa, N. y Slay, J. (2015). UNSW-NB15: a comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set). Military Communications and Information Systems Conference (MilCIS). https://doi.org/10.1109/MilCIS.2015.7348942
- UNSW Canberra. The UNSW-NB15 Dataset. https://research.unsw.edu.au/projects/unsw-nb15-dataset
