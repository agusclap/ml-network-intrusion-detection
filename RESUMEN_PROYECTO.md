# Resumen del proyecto: detección de intrusiones con Machine Learning

Documento de estudio para entender el proyecto completo: qué buscamos, cómo está armado, qué resultados tenemos, qué significan y cómo se calculan. Estado al 2/11/2026.

---

## 1. Qué queremos lograr

Un **sistema de detección de intrusiones (NIDS)** que, mirando los datos de un flujo de red, decida si es tráfico normal o un ataque. Un *flujo* es una conexión entre dos equipos resumida en números: cuánto duró, cuántos bytes y paquetes mandó cada lado, qué protocolo usó, etc.

Tenemos dos tareas sobre los mismos datos:

- **Binaria (principal):** ¿normal o ataque?
- **Multiclase (secundaria):** ¿Normal o qué tipo de ataque? (9 categorías: Analysis, Backdoor, DoS, Exploits, Fuzzers, Generic, Reconnaissance, Shellcode, Worms).

**Por qué con Machine Learning:** los IDS tradicionales usan reglas escritas a mano para ataques conocidos. Un modelo aprende el comportamiento del tráfico malicioso a partir de ejemplos, y puede detectar patrones que nadie escribió como regla.

**Criterios de éxito** (definidos en el Charter antes de entrenar):
- Binaria: detectar al menos el 90 % de los ataques (recall ≥ 0,90) **sin tener más falsos positivos que la regla sin IA**, y tener mejor F1 que los baselines.
- Multiclase: superar a los baselines en Macro-F1, con una diferencia mayor que la variación entre folds. No ponemos un número fijo porque el dataset tiene un techo (sección 10).

---

## 2. Los datos

Dataset **UNSW-NB15** (UNSW Canberra, 2015), descargado de la página oficial. Usamos la división que publicaron los autores:

| Archivo | Registros | Uso |
|---|---|---|
| `UNSW_NB15_training-set.csv` | 175.341 | entrenar y validar (cross-validation) |
| `UNSW_NB15_testing-set.csv` | 82.332 | evaluación final, **una sola vez** |

Cada registro tiene 45 columnas:
- **42 variables de entrada:** 39 numéricas (duración, bytes, paquetes, TTL, tiempos del handshake TCP, contadores de conexiones recientes…) y 3 categóricas (`proto`, `service`, `state`).
- **`id`:** número de fila. Se descarta.
- **`label`:** 0 = normal, 1 = ataque (target de la binaria).
- **`attack_cat`:** la categoría (target de la multiclase). `label = 0` exactamente cuando `attack_cat = "Normal"`.

Distribución en el train: 68 % ataques, 32 % normales. Entre categorías, el desbalance es fuerte: Generic tiene 40.000 filas y Worms 130.

---

## 3. Cómo está estructurado

### El flujo completo

```
CSV oficial ──► verificar MD5 ──► separar X / y ──► preprocesar ──► modelo ──► predicción
                (data.py)         (data.py)         (features.py)   (train.py)
                                  sin id ni el                       regla / LR / XGBoost
                                  target de la
                                  otra tarea
```

### Los archivos

| Archivo | Qué hace |
|---|---|
| `src/config.py` | Todos los valores fijos: semilla (42), rutas, hashes MD5, nombres de columnas, qué columnas sacar en cada tarea, hiperparámetros. |
| `src/data.py` | Verifica que los CSV sean los oficiales (MD5) y separa entradas (`X`) y respuesta (`y`), sacando las columnas prohibidas. |
| `src/features.py` | Arma el preprocesamiento: one-hot de las categóricas y estandarización de las numéricas (solo para la regresión logística). |
| `src/baselines.py` | Los modelos sin IA: la regla `dpkts == 0` y "siempre la clase más frecuente". |
| `src/metrics.py` | Calcula las métricas y elige el umbral de decisión. |
| `src/train.py` | Hace la cross-validation, elige el umbral, entrena el modelo final y guarda todo. |
| `notebooks/01_eda_minimo.ipynb` | Análisis exploratorio de los datos. |
| `reports/metrics/*.json` | Resultados de cada modelo (se suben al repo). |
| `models/*.joblib` | Modelos entrenados (no se suben: se regeneran con `train.py`). |

Uso:
```bash
python -m src.data                                   # verifica y carga
python -m src.train --model xgb                      # binaria
python -m src.train --task multiclass --model xgb    # multiclase
```

---

## 4. Preprocesamiento: cómo se preparan los datos

**One-hot encoding** para las 3 categóricas. Cada valor se convierte en una columna de 0 y 1. Por ejemplo, `proto = "tcp"` pasa a `proto_tcp = 1, proto_udp = 0, ...`. Las categorías con menos de 50 filas se agrupan en una sola columna. Resultado: de 42 variables pasamos a **188 columnas**. Una categoría que el modelo nunca vio (como `state = ACC`, que solo aparece en el test) queda con todo en 0 y no rompe nada.

**Estandarización** de las 39 numéricas, solo para la regresión logística:

```
z = (x − media) / desvío
```

Así todas las variables quedan con media 0 y desvío 1. Hace falta porque la regresión logística suma `peso × valor`, y una variable como `sbytes` (millones) aplastaría a otra como `sttl` (0 a 255). XGBoost no lo necesita, porque los árboles solo preguntan "¿el valor es mayor que tal umbral?", y escalar no cambia esa respuesta.

**Regla de oro (deck 06):** la media y el desvío se calculan **solo con los datos de entrenamiento** y después se aplican a los de validación y test. Si se calcularan con todos los datos, el modelo recibiría "pistas" de los datos con los que lo evaluamos. Por eso el preprocesamiento va dentro de un `Pipeline` que se ajusta de nuevo en cada fold.

**Guardas anti-leakage:** en la binaria se saca `attack_cat` de la entrada, y en la multiclase se saca `label`, porque cada una revela la respuesta de la otra (si el modelo ve `attack_cat = "Normal"`, ya sabe que `label = 0`). `id` se saca siempre. `get_X_y` lo hace y además lo verifica con un `assert`.

**Pesos por clase** (para el desbalance, en lugar de generar datos sintéticos). Cada fila pesa:

```
peso de la clase c = total de filas / (cantidad de clases × filas de la clase c)
```

En la binaria: normal = 175.341 / (2 × 56.000) ≈ 1,57 y ataque = 175.341 / (2 × 119.341) ≈ 0,73. En la multiclase, Worms pesa 175.341 / (10 × 130) ≈ 135. Así, equivocarse en una clase chica "cuesta" lo mismo en total que equivocarse en una grande. Los pesos se calculan solo con el fold de entrenamiento.

**Label encoding** del target multiclase: XGBoost necesita las clases como números, así que `attack_cat` se convierte en 0 a 9 (orden alfabético: Analysis = 0, …, Worms = 9). El encoder se guarda con el modelo para traducir las predicciones de vuelta a nombres.

---

## 5. Los modelos

| Modelo | Tipo | Cómo decide |
|---|---|---|
| **Regla `dpkts == 0`** | Baseline sin IA (binaria) | Si el destino no respondió ningún paquete, es ataque. Es un **agente reactivo simple** (deck 07): una regla si-entonces. |
| **Clase mayoritaria** | Baseline sin IA (multiclase) | Siempre predice "Normal". Es el piso mínimo. |
| **Regresión logística** | Baseline de ML | Hace una suma ponderada de las variables y la pasa por una función que la convierte en probabilidad (entre 0 y 1). Separa las clases con una **frontera lineal**. Tiene regularización L2 (la misma idea que Ridge, deck 10). |
| **XGBoost** | Modelo principal | Entrena 400 árboles de decisión **en secuencia**: cada árbol nuevo se enfoca en corregir los errores de los anteriores (*boosting*). Puede combinar condiciones sobre varias variables, como "`state` es INT **y** `dpkts` es 0 **y** `sttl` es 254". |

Los hiperparámetros están fijados de antemano en `config.py` (sin búsqueda). Por ejemplo, XGBoost usa 400 árboles de profundidad 6 y tasa de aprendizaje 0,1.

---

## 6. Cómo se entrena y se valida

### Cross-validation de 5 folds (deck 09)

```
train (175.341 filas) dividido en 5 partes ("folds")

vuelta 1:  [VAL ][TRAIN][TRAIN][TRAIN][TRAIN]  → métricas 1
vuelta 2:  [TRAIN][VAL ][TRAIN][TRAIN][TRAIN]  → métricas 2
   ...
vuelta 5:  [TRAIN][TRAIN][TRAIN][TRAIN][VAL ]  → métricas 5

resultado = media ± desviación estándar de las 5
```

En cada vuelta se entrena un modelo nuevo con 4 partes y se evalúa con la quinta, que no vio. Los folds son **estratificados**: cada uno tiene la misma proporción de clases que el train completo (68 % de ataques).

**Folds agrupados (`StratifiedGroupKFold`).** El 38 % del train son filas repetidas. Si los folds se armaran al azar, las repeticiones de una misma fila podrían caer en entrenamiento y en validación a la vez, y el modelo "acertaría" en validación filas que ya memorizó al entrenar: las métricas saldrían infladas. Por eso, siguiendo la recomendación de la cátedra, las filas con exactamente los mismos valores en las 42 variables forman un **grupo**, y cada grupo cae entero en un solo fold. La **desviación estándar** dice qué tan estable es el modelo: si es chica, el resultado no depende de qué datos le tocaron.

### Predicciones out-of-fold (OOF)

Cada fila del train se predice exactamente una vez, en la vuelta en que fue validación, o sea **con un modelo que no la vio**. Juntando las 5 vueltas tenemos una predicción "honesta" para las 175.341 filas, sin tocar el test.

### El umbral de decisión (solo binaria)

El modelo no dice "ataque" o "normal": da una **probabilidad** de ataque. El umbral es a partir de qué probabilidad decimos "ataque". Por defecto es 0,5.

- **Umbral más bajo** → marca más flujos como ataque → detecta más ataques (más recall), pero también más falsas alarmas (más FPR).
- **Umbral más alto** → lo contrario.

Elegimos el umbral **con las predicciones OOF**: probamos todos los umbrales posibles y nos quedamos con el de mejor F1 entre los que detectan al menos el 90 % de los ataques. Se guarda junto con el modelo y **nunca se recalcula con el test**.

### Modelo final y test

Los 5 modelos de la CV solo sirven para **medir**. El modelo que se guarda se entrena con el 100 % del train. El **test todavía no se tocó**: se va a evaluar una sola vez, cuando los modelos estén congelados. Si usáramos el test para elegir algo, terminaríamos optimizando para ese conjunto (deck 09).

---

## 7. Las métricas: qué son y cómo se calculan

### La matriz de confusión (binaria)

Todo sale de contar los cuatro casos posibles. Ejemplo real: XGBoost, predicciones OOF con su umbral (0,358), sobre las 175.341 filas del train:

|  | Predijo normal | Predijo ataque |
|---|---|---|
| **Era normal** (56.000) | **TN** = 51.501 (bien) | **FP** = 4.499 (falsa alarma) |
| **Era ataque** (119.341) | **FN** = 3.072 (ataque no detectado) | **TP** = 116.269 (bien) |

### Las fórmulas, con esos números

| Métrica | Pregunta que responde | Fórmula | Valor |
|---|---|---|---|
| **Recall** | De todos los ataques, ¿cuántos detectó? | TP / (TP + FN) = 116.269 / 119.341 | **0,974** |
| **Precisión** | De lo que marcó como ataque, ¿cuánto era ataque? | TP / (TP + FP) = 116.269 / 120.768 | **0,963** |
| **FPR** (tasa de falsos positivos) | De todo el tráfico normal, ¿cuánto marcó como ataque por error? | FP / (FP + TN) = 4.499 / 56.000 | **0,080** |
| **F1** | Equilibrio entre precisión y recall | 2 × P × R / (P + R) | **0,968** |
| **Accuracy** | ¿Cuántas acertó en total? | (TP + TN) / total | 0,957 |

**Por qué no usamos accuracy como métrica principal:** con clases desbalanceadas engaña. Un modelo que dijera siempre "ataque" tendría 68 % de accuracy sin detectar nada útil.

**Por qué priorizamos el recall:** en un NIDS, un ataque no detectado (FN) es más grave que una falsa alarma (FP). Es el ejemplo del spam del deck 09: no todos los errores pesan lo mismo. Pero miramos también la FPR, porque un detector que da alarma por todo es inútil.

**ROC-AUC y PR-AUC:** miden qué tan bien el modelo ordena los flujos (ataques con probabilidad alta, normales con probabilidad baja), **sin depender del umbral**. Van de 0,5 (azar) a 1 (perfecto) en el caso de ROC-AUC.

### Métricas de la multiclase

Se calcula precisión, recall y F1 **para cada clase** por separado (cada clase contra todas las demás), y después se resumen:

- **Macro-F1:** promedio simple del F1 de las 10 clases. Todas pesan igual: Worms (130 filas) cuenta lo mismo que Generic (40.000). Por eso es la métrica principal: castiga ignorar las clases chicas.
- **Weighted-F1:** promedio ponderado por la cantidad de filas de cada clase. Lo dominan las clases grandes.
- **Balanced accuracy:** promedio del recall de cada clase.

---

## 8. Resultados: tarea binaria

Cross-validation agrupada de 5 folds sobre el train (media ± desviación estándar), umbral 0,5:

| Modelo | F1 | Recall | Precisión | FPR | ROC-AUC |
|---|---|---|---|---|---|
| Regla `dpkts == 0` | 0,762 ± 0,003 | 0,650 | 0,921 | 0,119 | 0,766 |
| Regresión logística | 0,950 ± 0,001 | 0,952 | 0,949 | 0,109 | 0,984 |
| **XGBoost** | **0,965 ± 0,001** | **0,955** | **0,976** | **0,050** | **0,993** |

Con el umbral elegido en OOF:

| Modelo | Umbral | Recall | FPR | F1 |
|---|---|---|---|---|
| Regresión logística | 0,367 | 0,982 | 0,162 | 0,954 |
| XGBoost | 0,358 | 0,974 | 0,080 | 0,968 |

**Qué significan:**
- **La regla sin IA** detecta solo el 65 % de los ataques: deja pasar uno de cada tres.
- **La regresión logística** detecta el 95 %, pero con su umbral llega a 16 % de falsos positivos, más que la regla. Al ser lineal, para detectar más tiene que aceptar muchas más falsas alarmas.
- **XGBoost** detecta el 97,4 % de los ataques con 8,0 % de falsos positivos. **Cumple el criterio del Charter.** La diferencia con la logística es la ventaja de un modelo no lineal: combina condiciones que una frontera recta no puede representar.
- Las desviaciones estándar son muy chicas (≈ 0,001): los modelos son **estables** (baja varianza, deck 09).
- Con la validación agrupada, XGBoost bajó un poco respecto de la versión anterior (F1 de 0,967 a 0,965, FPR de 4,6 % a 5,0 %): esa diferencia era lo que inflaba la memorización de filas repetidas. Es chica, así que el modelo no dependía mucho de memorizar.

---

## 9. Resultados: tarea multiclase

| Modelo | Macro-F1 | Weighted-F1 | Balanced accuracy |
|---|---|---|---|
| Clase mayoritaria | 0,048 ± 0,000 | 0,155 | 0,100 |
| Regresión logística | 0,412 ± 0,005 | 0,716 | 0,585 |
| **XGBoost** | **0,620 ± 0,008** | **0,803** | **0,700** |

**Cumple el criterio:** XGBoost supera a los dos baselines y la diferencia con la logística (≈ 0,21) es unas 25 veces la desviación estándar.

F1 por clase (promedio de los 5 folds):

| Clase | Filas por fold | Regresión logística | XGBoost |
|---|---|---|---|
| Generic | 8.000 | 0,986 | 0,990 |
| Normal | 11.200 | 0,884 | 0,912 |
| Reconnaissance | 2.098 | 0,352 | 0,827 |
| Fuzzers | 3.636 | 0,608 | 0,750 |
| Shellcode | 227 | 0,180 | 0,702 |
| Worms | 26 | 0,035 | 0,680 |
| Exploits | 6.679 | 0,527 | 0,652 |
| DoS | 2.453 | 0,297 | 0,379 |
| Analysis | 400 | 0,163 | 0,184 |
| Backdoor | 350 | 0,084 | 0,121 |

**Qué significan:**
- XGBoost reconoce bien incluso clases muy chicas como Worms y Shellcode, gracias a los pesos por clase.
- **Analysis, Backdoor y DoS quedan muy bajas en los dos modelos.** No es una falla del modelo: en el dataset, muchas de esas filas tienen **exactamente los mismos valores** que filas de otras categorías (sobre todo Exploits). Si dos flujos son idénticos en las 42 variables, ningún modelo puede saber cuál es cuál.
- Con la validación agrupada, Analysis, DoS y Backdoor **mejoraron** (de 0,12 a 0,18, de 0,32 a 0,38 y de 0,07 a 0,12). Lo más probable es que antes el modelo memorizara la etiqueta más frecuente de cada fila repetida (casi siempre Exploits) y fallara en validación con las repeticiones que tenían la etiqueta de una clase chica.
- El recall de Normal baja a 0,85 en la multiclase: al darle mucho peso a las clases chicas, el modelo "se arriesga" más con las grandes. Es el costo esperable de balancear.

---

## 10. Limitaciones del dataset (lo que hay que poder explicar)

| Limitación | Qué es | Qué hicimos |
|---|---|---|
| **Registros iguales con distinta etiqueta** | 17 % de las filas del train tienen las mismas 42 variables que otra fila de otra categoría | Calculamos que, para un único modelo, el Macro-F1 máximo posible en el train ronda 0,81. Por eso el criterio multiclase es relativo y no un número fijo. |
| **Variables de TTL** | `sttl`, `dttl`, `ct_state_ttl` separan casi solas normal de ataque, por cómo se generó el tráfico en el laboratorio | No es data leakage (el TTL existe en una red real), es un sesgo del dataset. Las dejamos y lo documentamos. |
| **Duplicados** | 38 % de las filas del train están repetidas | No las eliminamos: son flujos reales repetidos, no errores. Para que no inflen la validación, la CV agrupa las repeticiones en el mismo fold (recomendación de la cátedra). |
| **Outliers** | Entre 9 % y 16 % de valores atípicos por IQR en las variables de tamaño y duración | Son legítimos (cola larga del tráfico). No se tocan. |
| **Split no estratificado** | 68 % de ataques en train y 55 % en test | Es el benchmark oficial, no lo cambiamos. Estratificamos los folds de la CV. |

---

## 11. Qué falta

| Tarea | Cuándo |
|---|---|
| Figuras de la cross-validation (matriz de confusión y curva ROC) | semana 6 |
| Congelar modelos y **evaluar en el test una sola vez** (`evaluate.py`) | semana 6 |
| README final, reproducción desde cero, preparación de la defensa | semana 7 |

El feedback del profe ya está aplicado y el script de predicción por consola (`inference.py`) ya está hecho.

---

## 12. Feedback de la cátedra

Le consultamos por mail tres decisiones: los duplicados, el criterio multiclase y la regla del umbral. Nos respondió que el proyecto va bien encaminado, con un punto a corregir: con el 38 % de filas duplicadas y un `StratifiedKFold` común, las mismas filas caían a la vez en entrenamiento y validación, y en XGBoost eso infla las métricas por memorización. Recomendó agrupar las filas idénticas con `StratifiedGroupKFold` o eliminar los duplicados.

Elegimos agrupar, porque mantiene la distribución real del dataset, que era el motivo para no eliminar los duplicados. Los resultados de las secciones 8 y 9 ya están calculados con la validación agrupada.

Preguntas que no hicimos y conviene tener preparadas para la defensa (las respuestas están en el Charter):
- **One-hot sobre `proto` (133 valores):** con la agrupación de categorías raras quedan 188 columnas para 175.341 filas. Hashing tiene colisiones y target encoding tiene riesgo de sobreajuste.
- **Variables de TTL:** son un sesgo del dataset, no data leakage. La comparación sin ellas es un extra opcional.
- **Alcance:** la consigna acepta un script de consola como MVP.
