# Project Charter: Detección de intrusiones en redes con Machine Learning

Inteligencia Artificial - Ingeniería en Informática - UNDEF CRUC IUA

- **Docente:** Ing. Hernando Alexis González
- **Modalidad:** Grupal
- **Integrantes:** Maximo Agustin Rodeyro y Lautaro Niccolini
- **Categorías:** Machine Learning Predictivo y Data Engineering & IA
- **Fecha:** 29/9/2026 (actualizado el 8/11/2026 con los resultados, ver sección 10)

## 1. Resumen

La idea del proyecto es armar un sistema de detección de intrusiones (NIDS) basado en Machine Learning. El sistema recibe los datos de un flujo de red (protocolo, servicio, duración, bytes y paquetes enviados en cada sentido, TTL, etc.) y decide si ese flujo es tráfico normal o un ataque. Como segunda tarea, también intentamos predecir de qué tipo de ataque se trata.

Para esto usamos el dataset UNSW-NB15 con la división en train y test que publicaron sus autores. Vamos a comparar una regla simple sin IA y una regresión logística contra XGBoost, validar con cross-validation sobre el train y evaluar el modelo final una sola vez sobre el test. Al final queremos tener un pipeline reproducible y un script de consola que reciba un CSV con flujos y devuelva las predicciones.

## 2. Definición del problema

Los IDS tradicionales funcionan con firmas, es decir, reglas escritas a mano para ataques ya conocidos, y les cuesta detectar variantes nuevas. Nuestra propuesta es entrenar un modelo que aprenda cómo se comporta el tráfico malicioso a partir de ejemplos etiquetados, para que funcione como una capa más de detección.

Planteamos dos tareas sobre los mismos datos:

- **Binaria (tarea principal):** normal o ataque.
- **Multiclase (tarea secundaria):** Normal o una de las 9 categorías de ataque del dataset (Analysis, Backdoor, DoS, Exploits, Fuzzers, Generic, Reconnaissance, Shellcode y Worms).

### PEAS

| | |
|---|---|
| Performance | Tarea binaria: recall de ataques y tasa de falsos positivos, además de F1 y PR-AUC. Tarea multiclase: Macro-F1 y F1 por clase. |
| Environment | Registros de flujos de red del dataset UNSW-NB15 (ver propiedades abajo). |
| Actuators | Para cada flujo, el sistema devuelve una etiqueta (normal/ataque o categoría de ataque) junto con su probabilidad. |
| Sensors | Las 42 variables que trae cada registro: protocolo, servicio, estado de la conexión, duración, bytes y paquetes por sentido, TTL, pérdidas, jitter, tiempos del handshake TCP, tamaño medio de los paquetes y contadores de conexiones recientes. |

Propiedades del entorno:

| Propiedad | Nuestro caso | Por qué |
|---|---|---|
| Observabilidad | Parcialmente observable | Solo tenemos los metadatos de cada flujo, no el contenido de los paquetes ni el resto del tráfico de la red. |
| Determinismo | Estocástico | Encontramos flujos con exactamente los mismos valores en las 42 variables y distinta etiqueta: la misma entrada puede corresponder a salidas distintas. |
| Secuencialidad | Episódico | Cada flujo se clasifica por separado y una decisión no cambia las siguientes. |
| Dinamismo | Estático | Trabajamos sobre archivos fijos; el entorno no cambia mientras el sistema decide. |
| Continuidad | Discreto | La acción es elegir una etiqueta de un conjunto finito. |
| Agentes | Agente individual | Un solo sistema clasifica el tráfico. |

En cuanto al tipo de agente, la regla sin IA que usamos como baseline (`dpkts == 0`) funciona como un agente reactivo simple: una regla si-entonces sobre la percepción actual. Los modelos de Machine Learning, en cambio, aprenden esas reglas a partir de los datos etiquetados.

## 3. Datos

Usamos UNSW-NB15, un dataset armado por el Australian Centre for Cyber Security de UNSW Canberra (Moustafa y Slay, 2015). Lo descargamos desde la página oficial (research.unsw.edu.au/projects/unsw-nb15-dataset). Trabajamos solamente con la partición en train y test que publicaron los autores:

- `UNSW_NB15_training-set.csv`: 175.341 registros.
- `UNSW_NB15_testing-set.csv`: 82.332 registros.

Cada registro tiene 45 columnas. De esas, 42 son las variables que usamos como entrada (39 numéricas y 3 categóricas: `proto`, `service` y `state`). Las otras tres son `id`, que es un índice de fila y se descarta, y las dos etiquetas: `label` (0 = normal, 1 = ataque) y `attack_cat` (la categoría del ataque, o "Normal").

También existe una copia del dataset en Kaggle, pero ahí los archivos de train y test tienen los nombres cambiados. Por eso usamos la versión oficial y verificamos los archivos con su hash MD5 antes de entrenar. Los hashes y los pasos para descargar los datos están en `data/README.md`.

Cuando revisamos los datos encontramos varias cosas a tener en cuenta:

- **No hay valores faltantes.** Algunos valores de `state` aparecen solo en el test, así que el encoding de las variables categóricas tiene que soportar categorías que no vio en el entrenamiento.
- **Desbalance.** En el train el 68 % de los registros son ataques, y en el test el 55 %. Entre las categorías de ataque la diferencia es mucho más grande: Generic tiene 40.000 registros y Worms solo 130. Para manejarlo usamos pesos por clase en los modelos y métricas que no se engañan con el desbalance (F1 por clase, Macro-F1, PR-AUC). No vamos a generar datos sintéticos.
- **Registros iguales con distinta etiqueta.** Cerca del 17 % de las filas del train tiene exactamente los mismos valores en las 42 variables que otra fila con otra categoría de ataque. Pasa sobre todo entre Analysis, Backdoor, DoS y Exploits. Esto hace que ningún modelo pueda separar perfectamente esas clases: calculamos que el Macro-F1 máximo posible en el train ronda 0,81. Por eso no ponemos un valor fijo de Macro-F1 como objetivo.
- **Variables de TTL.** `sttl`, `dttl` y `ct_state_ttl` separan casi solas el tráfico normal de los ataques, por cómo se generó el tráfico en el laboratorio. No se trata de data leakage porque el TTL es un dato que también está disponible en una red real, pero sí es un sesgo del dataset. Las dejamos en el modelo y lo mencionamos como limitación. En el test se vio el costo de esta decisión: es la causa de la mayoría de los falsos positivos (sección 10).
- **Duplicados dentro del train.** El 38 % de las filas del train está repetida (mismos valores en todas las columnas salvo `id`). No las eliminamos: no son errores de carga sino flujos de red reales que se repiten (por ejemplo, muchas conexiones cortas idénticas durante un escaneo), y sacarlas cambiaría la proporción real de cada tipo de tráfico en el benchmark. Para que esto no infle la validación, la cross-validation agrupa las filas idénticas y manda todas sus repeticiones al mismo fold (ver "Validación").
- **Duplicados entre train y test.** Alrededor del 5 % de las filas del test también aparecen en el train. Evaluamos sobre el test completo porque es el benchmark oficial, y lo mencionamos como limitación.
- **Outliers.** Varias variables numéricas tienen valores muy extremos (por ejemplo, en el train `sbytes` llega a casi 13 MB cuando la mediana es de 430 bytes). Los analizamos en el EDA, pero no los eliminamos ni los recortamos: en tráfico de red son valores legítimos (una descarga grande, un flujo largo) y muchas veces son justamente la señal de un ataque. XGBoost no se ve afectado por ellos, y para la regresión logística se estandarizan.
- **Split oficial no estratificado.** La proporción de ataques es distinta en el train (68 %) y en el test (55 %), así que la partición oficial no está estratificada. No la cambiamos porque es el benchmark con el que se comparan otros trabajos, pero sí estratificamos los folds de la cross-validation para que cada fold tenga la misma proporción de clases que el train (cada fold queda con 68 % de ataques).

## 4. Baselines y métricas de éxito

### Baselines

- **Sin IA, tarea binaria:** marcar como ataque todo flujo en el que el destino no respondió ningún paquete (`dpkts == 0`), algo típico de escaneos y algunos DoS. La definimos y medimos solo con el train: recall 0,65, precisión 0,92, tasa de falsos positivos 0,12 y F1 0,76.
- **Sin IA, tarea multiclase:** predecir siempre la clase más frecuente.
- **Modelo simple de ML, en las dos tareas:** regresión logística con pesos por clase.

### Criterio de éxito de la tarea binaria

Sobre el test, el modelo tiene que llegar a un **recall de ataques de al menos 0,90 con una tasa de falsos positivos que no supere la de la regla sin IA**. Además tiene que tener mejor F1 que los dos baselines.

El umbral de decisión se elige únicamente con el train, usando las predicciones de la cross-validation: tomamos el umbral con mejor F1 entre los que dan un recall de 0,90 o más.

También vamos a reportar precisión, F1, ROC-AUC, PR-AUC y la matriz de confusión, pero no las usamos como criterio para aprobar o rechazar el modelo.

Priorizamos el recall (sensibilidad) porque en este problema el error más grave es el falso negativo (error de tipo II): un ataque que pasa sin ser detectado. Una falsa alarma (falso positivo, error de tipo I) tiene un costo, pero mucho menor, y por eso la controlamos con la tasa de falsos positivos, que es 1 − especificidad. Es el mismo razonamiento que en la detección de enfermedades, donde se prefiere detectar todos los casos aunque haya algunas falsas alarmas. En otros problemas el criterio se invierte: en un filtro de spam, por ejemplo, lo grave es el falso positivo, porque se pierde un correo legítimo. No usamos la exactitud (accuracy) como métrica principal porque con clases desbalanceadas puede ser alta aunque el modelo no detecte nada útil.

### Criterio de éxito de la tarea multiclase

La métrica principal es el Macro-F1, acompañado del F1 de cada clase y la matriz de confusión. El modelo tiene que **superar en Macro-F1 a los dos baselines en la cross-validation sobre el train**, con una diferencia mayor que la desviación estándar entre folds, y mantener esa ventaja cuando lo evaluamos en el test.

### Validación

- Cross-validation de 5 folds sobre el train, que usamos para comparar modelos y elegir el umbral. Usamos `StratifiedGroupKFold`: las filas que tienen exactamente los mismos valores en las 42 variables forman un grupo, y cada grupo cae entero en un solo fold. Así ninguna fila repetida queda a la vez en entrenamiento y en validación, y el modelo no puede "acertar" una fila de validación por haberla memorizado al entrenar. Además, cada fold mantiene la misma proporción de clases que el train. Lo cambiamos por recomendación de la cátedra: con un `StratifiedKFold` común, las repeticiones de una misma fila caían en folds distintos y las métricas de validación salían infladas.
- No hacemos búsqueda de hiperparámetros. Tanto la regresión logística como XGBoost usan valores razonables que fijamos antes de empezar. Si al final nos sobra tiempo, podemos probar algunas configuraciones más, siempre con cross-validation.
- Después se entrena cada modelo con todo el train y se evalúa **una sola vez** en el test. Una vez hecho eso, no se cambia nada del modelo.
- Usamos una semilla fija (42) y versiones fijas de las librerías para que los resultados se puedan reproducir.
- Antes de empezar revisamos el test solamente para verificar que los datos estuvieran bien (nulos, duplicados, distribución de clases). No tomamos ninguna decisión de modelado a partir de eso.

## 5. Alcance

Lo que vamos a entregar:

1. Un script que verifica y carga los datos.
2. Un notebook con un análisis exploratorio corto.
3. El entrenamiento y la cross-validation de los baselines, la regresión logística y XGBoost para las dos tareas.
4. La evaluación final sobre el test, con las métricas y las matrices de confusión guardadas.
5. Los modelos entrenados guardados en archivos.
6. Un script de consola que recibe un CSV y devuelve las predicciones usando el mismo preprocesamiento del entrenamiento.
7. Un README con los pasos para instalar todo y reproducir los resultados.

Si terminamos esto con tiempo de sobra, las posibles mejoras son: probar algunas configuraciones más de XGBoost, entrenar sin las variables de TTL para ver cuánto dependen los modelos de ellas, sumar algunos tests automáticos y analizar qué variables pesan más en las predicciones.

### Fuera del alcance

- Analizar el contenido de los paquetes, o usar los archivos crudos del dataset y las capturas pcap.
- Capturar tráfico en vivo, detectar en tiempo real o bloquear ataques (el sistema solo detecta).
- Robustez frente a ataques pensados para engañar al modelo.
- Redes neuronales, generación de datos sintéticos (SMOTE) y búsqueda exhaustiva de hiperparámetros.
- API web, interfaz gráfica, base de datos, usuarios o Docker.

## 6. Arquitectura y herramientas

- **Preprocesamiento:** se descartan `id` y la etiqueta que no corresponde a la tarea, para que el modelo no vea la respuesta. Las 3 variables categóricas pasan por one-hot encoding. Las numéricas se estandarizan solo para la regresión logística, porque es un modelo lineal y le afecta la escala; XGBoost trabaja con árboles y no lo necesita. Las columnas del one-hot no se escalan porque ya valen 0 o 1. Todo esto va dentro de un `Pipeline` de scikit-learn que se ajusta solamente con datos de entrenamiento (en la cross-validation, solo con los folds de entrenamiento) y después se aplica a los datos de validación y de test.
- **Codificación de `proto`:** tiene 133 valores distintos, una cardinalidad alta para one-hot. Igual elegimos one-hot porque agrupamos en una sola columna las categorías con menos de 50 filas, lo que deja 188 variables en total frente a 175.341 observaciones de entrenamiento, una relación más que suficiente. Las alternativas para alta cardinalidad tienen problemas que preferimos evitar: el hashing tiene colisiones y el target encoding tiene riesgo de sobreajuste.
- **Por qué no eliminamos una columna del one-hot:** en regresión lineal se recomienda eliminar una columna por variable para evitar la trampa de las variables dummies, porque las columnas de una misma variable quedan perfectamente correlacionadas. Eso es un problema cuando el modelo no está regularizado: el sistema de ecuaciones no tiene una solución única. Nuestra regresión logística sí está regularizada (penalización L2, la misma idea que la regresión de Ridge), así que la solución es única aunque haya columnas redundantes, y a los árboles de XGBoost no les afecta. Además, una categoría que no apareció en el entrenamiento (como `ACC` en el test) queda con todas sus columnas en 0; si elimináramos una columna, la categoría eliminada también quedaría en 0 y el modelo no podría distinguirlas.
- **Por qué no hacemos selección de variables:** usamos las 42 variables sin aplicar métodos como forward, backward o stepwise. Con 175.341 observaciones de entrenamiento y 188 columnas después del one-hot, la cantidad de parámetros es mucho menor que la cantidad de datos. Además, la regularización L2 de la regresión logística controla la varianza, y XGBoost elige por sí solo qué variables usar en cada división de los árboles.
- **Etiqueta multiclase:** `attack_cat` es texto, y XGBoost necesita las clases como números (0 a 9), así que la codificamos con label encoding. El encoder se ajusta con el train y se guarda junto con el modelo para poder traducir las predicciones de vuelta a nombres de categoría.
- **Desbalance:** en lugar de remuestrear, usamos pesos por clase (`class_weight` en la regresión logística y `sample_weight` en XGBoost), calculados solo con los datos de entrenamiento de cada fold. El test nunca se balancea.
- **Modelos:** regla `dpkts == 0` y clase mayoritaria como baselines sin IA, regresión logística como baseline de ML y XGBoost como modelo principal.
- **Herramientas:** Python en un entorno virtual, con pandas, NumPy, scikit-learn, XGBoost, joblib, matplotlib y Jupyter. Las versiones quedan fijadas en `requirements.txt`.

### Relación con los contenidos de la materia

| Decisión del proyecto | Tema del teórico |
|---|---|
| PEAS, propiedades del entorno y tipo de agente | Agentes |
| Desbalance detectado con gráficos de barras y proporciones de clase | Procesamiento y limpieza de datos |
| Tratamiento de duplicados y outliers (analizados y justificados) | Procesamiento y limpieza de datos |
| Codificación según la cardinalidad (one-hot) y label encoding del target | Procesamiento y limpieza de datos |
| Split antes de transformar; calcular las transformaciones con train y aplicarlas al resto | Procesamiento y nuevas features |
| Estandarización para el modelo lineal; las variables del one-hot no se escalan | Procesamiento y nuevas features |
| Pesos por clase para mitigar el desbalance; el test nunca se balancea | Procesamiento y nuevas features |
| Hiperparámetros fijados antes de entrenar, K-fold sobre train y test reservado para la evaluación final | Aprendizaje automático |
| K-fold agrupado (`StratifiedGroupKFold`) para que las filas repetidas no estén en entrenamiento y validación a la vez | Aprendizaje automático y Procesamiento y nuevas features (no contaminar la evaluación) |
| Priorizar el recall porque no todos los errores tienen la misma gravedad | Aprendizaje automático |
| Estandarización (y no normalización) por ser menos sensible a los outliers; media y desvío calculados solo con train | Regresión |
| One-hot para variables nominales y por qué no eliminamos una columna (trampa de las dummies) | Regresión |
| Regresión logística con regularización L2 (equivalente a Ridge) como baseline de ML | Regresión |
| Por qué no aplicamos selección de variables (forward, backward, stepwise) | Regresión |
| Regresión logística binaria y multiclase (sigmoide, ajuste por máxima verosimilitud con gradiente descendente) | Clasificación |
| Matriz de confusión, errores de tipo I y II, y por qué el falso negativo es el error más grave en un NIDS | Clasificación |
| Métricas: recall (sensibilidad), precisión, F1, tasa de falsos positivos (1 − especificidad), exactitud balanceada y ROC-AUC; no usar accuracy con clases desbalanceadas | Clasificación |
| Umbral de decisión distinto de 0,5, elegido con las predicciones de la cross-validation | Clasificación |

## 7. Forma de trabajo

- Trabajamos en un repositorio de GitHub. La rama `main` siempre tiene una versión estable, y cada tarea se desarrolla en su propia rama.
- En los mensajes de commit indicamos qué se resolvió y cuántas horas llevó, por ejemplo `feat(data): carga y verificación de los CSV [1.5h]`.
- Los datos no se suben al repositorio: en `data/README.md` explicamos cómo descargarlos y verificarlos.
- Calculamos dedicarle entre 3 y 4 horas por persona por semana, menos en semanas de parciales. En total estimamos entre 35 y 45 horas entre los dos.

## 8. Cronograma

| Semana | Qué hacemos |
|---|---|
| 1 | Repositorio, entorno, carga y verificación de los datos, análisis exploratorio |
| 2 | Preprocesamiento, regla sin IA y regresión logística de punta a punta en la tarea binaria |
| 3 | XGBoost binario, y regresión logística y XGBoost multiclase |
| 4 | Cierre de la cross-validation y evaluación final en el test |
| 5 | Script de predicción y README con los resultados |
| 6 | Verificar que todo se pueda reproducir desde cero, documentación final y preparación de la defensa |
| 7 | Margen para parciales, imprevistos y correcciones |

Si alguna semana no podemos avanzar por parciales, usamos la semana 7 y la holgura de las semanas 3 a 5 para recuperar. Si nos atrasamos, simplificamos la presentación (por ejemplo, un análisis exploratorio con menos gráficos), pero no sacamos los baselines, la validación, la evaluación en el test, el script de predicción ni el README.

**Estado al 8/11/2026:** las semanas 1 a 6 están terminadas. Queda la semana 7 para la documentación final y la preparación de la defensa. La entrega es el viernes 13/11.

## 9. Por qué elegimos este proyecto

También consideramos mantenimiento predictivo, detección de fraude, análisis de conducción y un sistema con agentes basado en LLMs. Nos quedamos con este porque combina dos de las categorías que propone la consigna del trabajo integrador, el dataset es público y conocido, se puede armar un baseline sin IA con sentido y el alcance es razonable para dos personas en el tiempo que tenemos. Además, los problemas que encontramos en el dataset (clases que se superponen, el sesgo del TTL, las diferencias entre train y test) nos dan bastante para analizar y discutir en la defensa.

## 10. Resultados

Todo lo de la sección 5 está entregado. El código, las métricas en JSON y las figuras están en el repositorio, y el detalle está en el README.

### Cross-validation sobre el train

5 folds con `StratifiedGroupKFold`, media ± desviación estándar entre folds.

**Binaria**, con el umbral elegido con las predicciones out-of-fold:

| Modelo | Umbral | Recall | Tasa de falsos positivos | F1 |
|---|---|---|---|---|
| Regla `dpkts == 0` | - | 0,650 | 0,119 | 0,762 |
| Regresión logística | 0,367 | 0,982 | 0,162 | 0,954 |
| XGBoost | 0,358 | 0,974 | 0,080 | 0,968 |

**Multiclase:**

| Modelo | Macro-F1 |
|---|---|
| Clase mayoritaria | 0,048 ± 0,000 |
| Regresión logística | 0,412 ± 0,005 |
| XGBoost | 0,620 ± 0,008 |

En la cross-validation, XGBoost cumplía los dos criterios.

### Evaluación final sobre el test

Cada modelo se evaluó una sola vez, con el modelo entrenado en todo el train y el umbral elegido en la cross-validation. Después no se cambió nada.

**Binaria:**

| Modelo | Recall | Tasa de falsos positivos | Precisión | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Regla `dpkts == 0` | 0,658 | 0,167 | 0,828 | 0,733 | 0,745 |
| Regresión logística | 0,964 | 0,372 | 0,761 | 0,850 | 0,956 |
| **XGBoost** | **0,983** | 0,251 | **0,828** | **0,898** | **0,984** |

Matriz de confusión de XGBoost: 27.717 verdaderos negativos, 9.283 falsos positivos, 788 falsos negativos y 44.544 verdaderos positivos.

**Multiclase:**

| Modelo | Macro-F1 | Weighted-F1 | Exactitud balanceada |
|---|---|---|---|
| Clase mayoritaria | 0,062 | 0,279 | 0,100 |
| Regresión logística | 0,352 | 0,685 | 0,548 |
| **XGBoost** | **0,524** | **0,741** | **0,644** |

### Criterios de éxito

| Criterio (sección 4) | Resultado en el test | ¿Se cumple? |
|---|---|---|
| Binaria: recall de al menos 0,90 | 0,983 | Sí |
| Binaria: tasa de falsos positivos no mayor que la de la regla sin IA (0,167) | 0,251 | **No** |
| Binaria: mejor F1 que los dos baselines | 0,898 contra 0,733 y 0,850 | Sí |
| Multiclase: ventaja en Macro-F1 sobre los dos baselines | 0,524 contra 0,062 y 0,352 | Sí |

### Por qué no se cumple el criterio de falsos positivos

La tasa de falsos positivos de XGBoost sube de 0,080 en la cross-validation a 0,251 en el test, y casi todo se explica por una variable, `sttl`:

| `sttl` | Normales en train | Ataques en train | Normales en test |
|---|---|---|---|
| 31 | 70,5 % | 0 % | 45,1 % |
| 254 | 20,1 % | 86,7 % | 40,7 % |

- En el train, `sttl = 254` es casi siempre un ataque, y el modelo lo aprendió como señal. Es el sesgo del TTL que marcamos en la sección 3.
- En el test, el tráfico normal con `sttl = 254` se duplica. De los 9.283 falsos positivos, 8.099 (87 %) tienen ese valor. Los normales con `sttl = 31` no generan ninguna falsa alarma.
- La regla sin IA también empeora (de 0,119 a 0,167): el tráfico normal del test es distinto al del train, no es solo un problema de nuestro modelo.
- El ROC-AUC sigue en 0,984: el modelo ordena bien los flujos. Lo que falla es el umbral elegido en el train, porque cambió la distribución.

No cambiamos el umbral después de ver el test, porque eso sería ajustar el modelo al test y el resultado dejaría de ser una evaluación independiente. El análisis está en `notebooks/02_analisis_test.ipynb`. Para usar el modelo en otra red habría que volver a elegir el umbral con tráfico de esa red, o entrenar sin las variables de TTL.

### Reproducibilidad

En la misma máquina, volver a correr todo da exactamente los mismos números. En otra máquina (Linux con 8 núcleos, contra Windows con 20 núcleos) los datos y los folds salen idénticos, pero los modelos cambian en el tercer decimal por diferencias de redondeo del procesador. Eso mueve un poco el umbral de XGBoost (0,346 en vez de 0,358) sin cambiar las conclusiones.

## 11. Cambios respecto a la primera versión

- **Validación agrupada (2/11):** por recomendación de la cátedra, la cross-validation pasó de `StratifiedKFold` a `StratifiedGroupKFold`, para que las filas repetidas no queden en entrenamiento y validación a la vez (secciones 3 y 4).
- **Métricas y umbral (2/11):** agregamos la justificación del recall y del umbral con los contenidos de clasificación (secciones 4 y 6).
- **Resultados (8/11):** agregamos la sección 10 con la cross-validation, el test y el análisis de los falsos positivos.
