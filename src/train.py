"""Entrenamiento con cross-validation estratificada sobre el train oficial."""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier
import argparse
import json
import pandas as pd
from sklearn.preprocessing import LabelEncoder

import joblib

from src.config import METRICS_DIR, MODELS_DIR
from src.metrics import select_binary_threshold
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


def fit_model(clf, model: str, X, y):
    """Entrena el modelo. XGBoost recibe pesos por clase calculados con el mismo y que se usa para entrenar."""
    if model == "xgb":
        weights = compute_sample_weight("balanced", y)
        clf.fit(X, y, model__sample_weight=weights)
    else:
        clf.fit(X, y)
    return clf


def load_xy(task: str):
    """Carga el train. En multiclase, codifica attack_cat como enteros 0..9 con LabelEncoder."""
    X, y = get_X_y(load_split("train"), task)
    encoder = None
    if task == "multiclass":
        encoder = LabelEncoder().fit(y)
        y = pd.Series(encoder.transform(y), index=y.index, name=y.name)
    return X, y, encoder


def cross_validate(task: str, model: str):
    """Corre la CV de 5 folds. Devuelve las métricas de cada fold y los scores out-of-fold."""
    X, y, encoder = load_xy(task)

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)

    fold_metrics = []
    oof_scores = np.zeros(len(y))     # probabilidad de ataque para cada fila (binaria)

    for k, (train_idx, val_idx) in enumerate(skf.split(X, y), start=1):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        clf = fit_model(build_model(task, model), model, X_tr, y_tr)


        y_pred = clf.predict(X_val)
        y_score = clf.predict_proba(X_val)[:, 1] if task == "binary" else None
        if task == "binary":
            oof_scores[val_idx] = y_score
            m = compute_metrics(task, y_val, y_pred, y_score=y_score)
            print(f"fold {k}: f1={m['f1']:.3f}  recall={m['recall']:.3f}  fpr={m['fpr']:.3f}")
        else:
            # las métricas se calculan con los nombres reales, para que el F1 por clase sea legible
            m = compute_metrics(task,
                                encoder.inverse_transform(y_val),
                                encoder.inverse_transform(y_pred),
                                labels=encoder.classes_)
            print(f"fold {k}: macro_f1={m['macro_f1']:.3f}  weighted_f1={m['weighted_f1']:.3f}")
        fold_metrics.append(m)
    return fold_metrics, oof_scores, y, encoder



SUMMARY_KEYS = {
    "binary": ["f1", "recall", "precision", "fpr", "roc_auc", "pr_auc"],
    "multiclass": ["macro_f1", "weighted_f1", "balanced_accuracy"],
}


def run(task: str, model: str) -> None:
    print(f"\n=== {task} / {model} ===")
    fold_metrics, oof_scores, y, encoder = cross_validate(task, model)

    # 1. Media ± desviación estándar de cada métrica en los 5 folds
    summary = {}
    for key in SUMMARY_KEYS[task]:
        values = [m[key] for m in fold_metrics if m[key] is not None]
        summary[key] = {"mean": float(np.mean(values)), "std": float(np.std(values))}
        print(f"  {key:10s} {summary[key]['mean']:.4f} ± {summary[key]['std']:.4f}")

    # 2. Umbral elegido SOLO con las predicciones out-of-fold del train
    threshold = None
    oof_at_threshold = None
    if task == "binary" and model != "heuristic":
        threshold = select_binary_threshold(y, oof_scores, min_recall=0.90)
        oof_pred = (oof_scores >= threshold).astype(int)
        oof_at_threshold = compute_metrics("binary", y, oof_pred, y_score=oof_scores)
        print(f"  umbral OOF = {threshold:.4f} -> recall {oof_at_threshold['recall']:.4f}, "
              f"fpr {oof_at_threshold['fpr']:.4f}, f1 {oof_at_threshold['f1']:.4f}")

    # 3. Modelo final: se entrena con TODO el train
    X_full, y_full, encoder = load_xy(task)
    final = fit_model(build_model(task, model), model, X_full, y_full)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": final, "threshold": threshold, "label_encoder": encoder},
            MODELS_DIR / f"{task}_{model}.joblib")


    # 4. Métricas de CV a JSON
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    result = {"task": task, "model": model, "n_folds": N_FOLDS, "seed": SEED,
            "cv_summary": summary, "threshold": threshold,
            "oof_at_threshold": oof_at_threshold, "folds": fold_metrics}
    with open(METRICS_DIR / f"{task}_{model}_cv.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cross-validation y entrenamiento final")
    parser.add_argument("--task", choices=["binary", "multiclass"], default="binary")
    parser.add_argument("--model", choices=["heuristic", "lr", "xgb"], required=True)
    args = parser.parse_args()
    run(args.task, args.model)

