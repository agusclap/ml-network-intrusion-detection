"""Entrenamiento con cross-validation estratificada sobre el train oficial."""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from src.baselines import make_baseline
from src.config import LR_PARAMS, SEED, XGB_PARAMS
from src.data import get_X_y, load_split
from src.features import build_preprocessor
from src.metrics import compute_metrics

N_FOLDS = 5


def build_model(task: str, model: str):
    """Devuelve el modelo sin entrenar: la regla sin IA, o un Pipeline (preprocesador + modelo)."""
    if model == "heuristic":
        return make_baseline(task)            # recibe X crudo: no lleva preprocesador
    if model == "lr":
        estimator = LogisticRegression(**LR_PARAMS)
    elif model == "xgb":
        estimator = XGBClassifier(**XGB_PARAMS)
    else:
        raise ValueError(f"model debe ser 'heuristic', 'lr' o 'xgb', no {model!r}")
    return Pipeline([
        ("prep", build_preprocessor(model)),
        ("model", estimator),
    ])


def cross_validate(task: str, model: str):
    """Corre la CV de 5 folds. Devuelve las métricas de cada fold y los scores out-of-fold."""
    X, y = get_X_y(load_split("train"), task)
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)

    fold_metrics = []
    oof_scores = np.zeros(len(y))     # probabilidad de ataque para cada fila (binaria)

    for k, (train_idx, val_idx) in enumerate(skf.split(X, y), start=1):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        clf = build_model(task, model)       # modelo nuevo en cada fold
        if model == "xgb":
            # pesos por clase calculados SOLO con el fold de entrenamiento
            weights = compute_sample_weight("balanced", y_tr)
            clf.fit(X_tr, y_tr, model__sample_weight=weights)
        else:
            clf.fit(X_tr, y_tr)

        y_pred = clf.predict(X_val)
        y_score = clf.predict_proba(X_val)[:, 1] if task == "binary" else None
        if task == "binary":
            oof_scores[val_idx] = y_score

        m = compute_metrics(task, y_val, y_pred, y_score=y_score)
        fold_metrics.append(m)
        print(f"fold {k}: f1={m['f1']:.3f}  recall={m['recall']:.3f}  fpr={m['fpr']:.3f}")

    return fold_metrics, oof_scores


if __name__ == "__main__":
    for model in ("heuristic", "lr", "xgb"):
        print(f"\n=== binary / {model} ===")
        cross_validate("binary", model)
