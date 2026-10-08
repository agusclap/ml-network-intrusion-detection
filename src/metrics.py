"""Métricas y selección de umbral para las dos tareas del proyecto."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_auc_score,
)


def _as_vector(values: Any, name: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1:
        raise ValueError(f"{name} debe ser un vector unidimensional.")
    if array.size == 0:
        raise ValueError(f"{name} no puede estar vacío.")
    return array


def _check_same_length(y_true: np.ndarray, y_pred: np.ndarray) -> None:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true e y_pred deben tener la misma cantidad de elementos.")


def _python_scalar(value: Any) -> Any:
    """Convierte escalares numpy a tipos nativos serializables como JSON."""
    return value.item() if isinstance(value, np.generic) else value


def _binary_score_vector(y_score: Any, n_samples: int) -> np.ndarray:
    scores = np.asarray(y_score, dtype=float)
    if scores.ndim != 1 or len(scores) != n_samples:
        raise ValueError("y_score debe ser un vector con un score para la clase positiva por fila.")
    if not np.isfinite(scores).all():
        raise ValueError("y_score contiene valores no finitos.")
    return scores


def binary_metrics(
    y_true: Any,
    y_pred: Any,
    y_score: Any | None = None,
) -> dict[str, Any]:
    """Calcula métricas binarias, tomando `1` como la clase ataque.

    `y_score`, si se informa, debe contener el score/probabilidad de ataque
    para cada fila. `pr_auc` se calcula como average precision de sklearn.
    Las métricas de ranking quedan en `None` si falta una de las dos clases.
    La matriz usa siempre el orden `[[TN, FP], [FN, TP]]`.
    """
    truth = _as_vector(y_true, "y_true")
    prediction = _as_vector(y_pred, "y_pred")
    _check_same_length(truth, prediction)
    if not np.isin(truth, [0, 1]).all():
        raise ValueError("y_true debe contener solamente las clases 0 y 1.")
    if not np.isin(prediction, [0, 1]).all():
        raise ValueError("y_pred debe contener solamente las clases 0 y 1.")

    matrix = confusion_matrix(truth, prediction, labels=[0, 1])
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    recall = float(tp / (tp + fn)) if tp + fn else 0.0
    fpr = float(fp / (fp + tn)) if fp + tn else None
    precision, _, f1, _ = precision_recall_fscore_support(
        truth, prediction, labels=[1], average="binary", zero_division=0
    )

    pr_auc: float | None = None
    roc_auc: float | None = None
    if y_score is not None and np.unique(truth).size == 2:
        scores = _binary_score_vector(y_score, len(truth))
        pr_auc = float(average_precision_score(truth, scores, pos_label=1))
        roc_auc = float(roc_auc_score(truth, scores))

    return {
        "accuracy": float(accuracy_score(truth, prediction)),
        "recall": recall,
        "fpr": fpr,
        "precision": float(precision),
        "f1": float(f1),
        "pr_auc": pr_auc,
        "roc_auc": roc_auc,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "confusion_matrix": matrix.astype(int).tolist(),
        "confusion_matrix_labels": [0, 1],
    }


def multiclass_metrics(
    y_true: Any,
    y_pred: Any,
    labels: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Calcula métricas multiclase y el detalle por clase.

    Si `labels` se proporciona, fija el orden de las clases de la matriz y
    del informe, incluso si alguna clase no aparece en este fold.
    """
    truth = _as_vector(y_true, "y_true")
    prediction = _as_vector(y_pred, "y_pred")
    _check_same_length(truth, prediction)

    if labels is None:
        class_labels = np.unique(np.concatenate((truth, prediction))).tolist()
    else:
        class_labels = [_python_scalar(label) for label in labels]
        if not class_labels:
            raise ValueError("labels no puede estar vacío.")
        if len(set(class_labels)) != len(class_labels):
            raise ValueError("labels no puede contener clases duplicadas.")
        allowed = set(class_labels)
        observed = set(truth.tolist()) | set(prediction.tolist())
        if not observed.issubset(allowed):
            raise ValueError("labels debe incluir todas las clases de y_true e y_pred.")

    precision, recall, f1, support = precision_recall_fscore_support(
        truth,
        prediction,
        labels=class_labels,
        zero_division=0,
    )
    matrix = confusion_matrix(truth, prediction, labels=class_labels)
    per_class = {
        str(label): {
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(f1[index]),
            "support": int(support[index]),
        }
        for index, label in enumerate(class_labels)
    }

    return {
        "accuracy": float(accuracy_score(truth, prediction)),
        "macro_precision": float(np.mean(precision)),
        "macro_recall": float(np.mean(recall)),
        "macro_f1": float(f1_score(
            truth, prediction, labels=class_labels, average="macro", zero_division=0
        )),
        "weighted_precision": float(np.average(precision, weights=support)) if support.sum() else 0.0,
        "weighted_recall": float(np.average(recall, weights=support)) if support.sum() else 0.0,
        "weighted_f1": float(f1_score(
            truth, prediction, labels=class_labels, average="weighted", zero_division=0
        )),
        "balanced_accuracy": float(balanced_accuracy_score(truth, prediction)),
        "per_class": per_class,
        "confusion_matrix": matrix.astype(int).tolist(),
        "confusion_matrix_labels": [_python_scalar(label) for label in class_labels],
    }


def compute_metrics(
    task: str,
    y_true: Any,
    y_pred: Any,
    y_score: Any | None = None,
    labels: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Despacha a las métricas de la tarea indicada (`binary` o `multiclass`)."""
    if task == "binary":
        if labels is not None:
            raise ValueError("labels solo se usa para la tarea multiclase.")
        return binary_metrics(y_true, y_pred, y_score=y_score)
    if task == "multiclass":
        if y_score is not None:
            raise ValueError("y_score solo se usa para métricas binarias en este proyecto.")
        return multiclass_metrics(y_true, y_pred, labels=labels)
    raise ValueError("task debe ser 'binary' o 'multiclass'.")


def select_binary_threshold(
    y_true: Any,
    y_score: Any,
    min_recall: float = 0.90,
) -> float:
    """Elige el umbral con mejor F1 que cumple el recall mínimo.

    Ante un empate de F1, devuelve el umbral más alto, que mantiene el mismo
    F1 y genera la menor cantidad de predicciones positivas. Debe aplicarse a
    predicciones out-of-fold de train, nunca a scores del test.
    """
    truth = _as_vector(y_true, "y_true")
    if not np.isin(truth, [0, 1]).all():
        raise ValueError("y_true debe contener solamente las clases 0 y 1.")
    if np.unique(truth).size != 2:
        raise ValueError("Se necesitan ejemplos positivos y negativos para elegir el umbral.")
    if not 0.0 <= min_recall <= 1.0:
        raise ValueError("min_recall debe estar entre 0 y 1.")
    scores = _binary_score_vector(y_score, len(truth))

    precision, recall, thresholds = precision_recall_curve(truth, scores, pos_label=1)
    if thresholds.size == 0:
        raise ValueError("No hay umbrales candidatos para estos scores.")
    precision = precision[:-1]
    recall = recall[:-1]
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(precision),
        where=(precision + recall) != 0,
    )
    eligible = np.flatnonzero(recall >= min_recall)
    if eligible.size == 0:
        raise ValueError(
            f"Ningún umbral alcanza recall >= {min_recall:.2f} en estas predicciones."
        )

    best_f1 = float(f1[eligible].max())
    tied = eligible[np.isclose(f1[eligible], best_f1, rtol=0.0, atol=1e-12)]
    return float(thresholds[tied[-1]])
