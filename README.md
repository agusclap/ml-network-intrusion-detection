# Detección de intrusiones en redes con Machine Learning

Trabajo final de Inteligencia Artificial - Ingeniería en Informática - Universidad de la Defensa Nacional (CRUC IUA), 2026.

Docente: Ing. Hernando Alexis González. Modalidad grupal.

## Integrantes

- Maximo Agustin Rodeyro
- Lautaro Niccolini

## De qué se trata

Estamos armando un sistema de detección de intrusiones (NIDS) basado en Machine Learning. A partir de los datos de un flujo de red, el modelo decide si ese flujo es tráfico normal o un ataque. Como segunda tarea, también intenta predecir qué tipo de ataque es.

Trabajamos con el dataset [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset), usando la división en train y test que publicaron sus autores.

**Estado actual:** terminamos la planificación y estamos empezando el desarrollo. Las secciones de instalación, uso y resultados las vamos completando a medida que avanzamos.

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
data/            datos (no se suben, ver data/README.md)
notebooks/       análisis exploratorio
src/             código: carga de datos, preprocesamiento, entrenamiento, evaluación y predicción
models/          modelos entrenados (no se suben, se generan al entrenar)
reports/         métricas y gráficos de los resultados
```

Las carpetas `notebooks/`, `src/`, `models/` y `reports/` las vamos creando durante el desarrollo.

## Instalación y uso

Todavía en construcción. La idea es que quede así:

```bash
# Crear el entorno e instalar dependencias
python -m venv .venv
.venv\Scripts\activate          # en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# Verificar y cargar los datos
python -m src.data

# Entrenar y validar
python -m src.train --task binary --model xgb

# Evaluar en el test
python -m src.evaluate --task binary --model xgb

# Predecir sobre un CSV nuevo
python -m src.inference --input archivo.csv --task binary
```

Usamos la semilla 42 y versiones fijas de las librerías para que los resultados se puedan reproducir.

## Resultados

Pendiente.

## Cosas a tener en cuenta del dataset

- Para que el modelo no "vea la respuesta", en cada tarea sacamos de la entrada la columna `id` y la etiqueta que no corresponde (`attack_cat` en la tarea binaria y `label` en la multiclase).
- Hay registros con exactamente los mismos valores pero distinta categoría de ataque, sobre todo entre Analysis, Backdoor, DoS y Exploits. Por eso ningún modelo puede separar esas clases del todo.
- Las variables de TTL (`sttl`, `dttl`, `ct_state_ttl`) separan casi solas el tráfico normal de los ataques, por cómo se generó el tráfico en el laboratorio. Las dejamos en el modelo y lo tomamos como una limitación del dataset.
- En el train el 68 % de los registros son ataques y en el test el 55 %. Además, alrededor del 5 % de las filas del test también están en el train.

El análisis completo de los datos está en [AUDITORIA_VIABILIDAD.md](AUDITORIA_VIABILIDAD.md).

## Cronograma

| Semana | Qué hacemos |
|---|---|
| 1 | Repositorio, entorno, carga de datos y análisis exploratorio |
| 2 | Preprocesamiento, regla sin IA y regresión logística binaria |
| 3 | XGBoost binario y modelos multiclase |
| 4 | Evaluación final en el test |
| 5 | Script de predicción y resultados en el README |
| 6 | Revisión de reproducibilidad, documentación y defensa |
| 7 | Margen para imprevistos |

El detalle está en [PLAN_IMPLEMENTACION.md](PLAN_IMPLEMENTACION.md).

## Forma de trabajo

- La rama `main` tiene siempre una versión estable y cada tarea se hace en su propia rama.
- En los commits ponemos qué se hizo y cuántas horas llevó, por ejemplo: `feat(data): carga y verificación de los CSV [1.5h]`.

## Referencias

- Moustafa, N. y Slay, J. (2015). UNSW-NB15: a comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set). Military Communications and Information Systems Conference (MilCIS). https://doi.org/10.1109/MilCIS.2015.7348942
- UNSW Canberra. The UNSW-NB15 Dataset. https://research.unsw.edu.au/projects/unsw-nb15-dataset
