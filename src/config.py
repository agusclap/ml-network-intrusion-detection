"""Configuración central del proyecto: todos los valores fijos en un solo lugar."""
from pathlib import Path

# --- Semilla -----------------------------------------------------------------
# Se usa en todo lo que tenga azar (división en folds, modelos) para que
# los resultados sean reproducibles.
SEED = 42

# --- Rutas -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent   # config.py está en src/, subimos dos niveles
DATA_RAW = ROOT / "data" / "raw"
TRAIN_CSV = DATA_RAW / "UNSW_NB15_training-set.csv"
TEST_CSV = DATA_RAW / "UNSW_NB15_testing-set.csv"
MODELS_DIR = ROOT / "models"
METRICS_DIR = ROOT / "reports" / "metrics"
FIGURES_DIR = ROOT / "reports" / "figures"

# --- Integridad de los datos -------------------------------------------------
# Hash MD5 de los CSV oficiales (ver data/README.md). Si un archivo no coincide,
# no es el que esperamos (por ejemplo, la copia de Kaggle con nombres cruzados).
EXPECTED_MD5 = {
    "UNSW_NB15_training-set.csv": "e55caabaa6cd4a8f1c06a227bcfababc",
    "UNSW_NB15_testing-set.csv": "e0beea40262e46168cdb81476dbc27b4",
}

# --- Columnas ----------------------------------------------------------------
ID_COL = "id"                       # índice de fila: nunca se usa como variable
BINARY_TARGET = "label"             # 0 = normal, 1 = ataque
MULTICLASS_TARGET = "attack_cat"    # Normal + 9 categorías de ataque
CATEGORICAL_COLS = ["proto", "service", "state"]
# Las columnas numéricas no se listan a mano: son todas las que quedan
# después de sacar el id, los dos targets y las categóricas (se calculan en data.py).

# Para cada tarea: qué columna es el target y cuál hay que sacar de la entrada
# para que el modelo no vea la respuesta (guarda anti-leakage).
TASKS = {
    "binary": {"target": BINARY_TARGET, "drop": [ID_COL, MULTICLASS_TARGET]},
    "multiclass": {"target": MULTICLASS_TARGET, "drop": [ID_COL, BINARY_TARGET]},
}

# --- Hiperparámetros fijos (sin búsqueda) ------------------------------------
LR_PARAMS = {
    "class_weight": "balanced",
    "max_iter": 2000,
    "C": 1.0,
    "random_state": SEED,
}

# El sample_weight de XGBoost no va acá: se calcula en cada fold en train.py.
XGB_PARAMS = {
    "tree_method": "hist",
    "n_estimators": 400,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": SEED,
    "n_jobs": -1,
}
