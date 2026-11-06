"""Generación de figuras para evaluar las predicciones out-of-fold."""

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import ConfusionMatrixDisplay, RocCurveDisplay, confusion_matrix


def save_confusion_matrix(
    y_true: Any,
    y_pred: Any,
    path: str | Path,
    title: str,
    labels: list[str] | None = None,
) -> None:
    """Guarda una matriz de confusión como PNG."""
    if labels is None:
        matrix_labels = None
        display_labels = None
    else:
        observed = set(np.asarray(y_true).tolist()) | set(np.asarray(y_pred).tolist())
        if observed.issubset(set(labels)):
            matrix_labels = labels
            display_labels = labels
        else:
            # Permite pasar nombres visibles cuando los datos conservan IDs enteros.
            matrix_labels = np.arange(len(labels))
            display_labels = labels
    matrix = confusion_matrix(y_true, y_pred, labels=matrix_labels)
    display = ConfusionMatrixDisplay(
        confusion_matrix=matrix,
        display_labels=display_labels if labels is not None else matrix_labels,
    )
    figsize = (14, 10) if labels is not None and len(labels) > 5 else (9, 7)
    fig, ax = plt.subplots(figsize=figsize)
    display.plot(ax=ax, cmap="Blues", colorbar=False, values_format="d")
    ax.set_title(title)
    if labels is not None and len(labels) > 5:
        ax.tick_params(axis="x", labelrotation=45, labelsize=9)
        ax.tick_params(axis="y", labelsize=9)
        for tick in ax.get_xticklabels():
            tick.set_horizontalalignment("right")
    fig.tight_layout()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_roc_curve(y_true: Any, y_score: Any, path: str | Path, title: str) -> None:
    """Guarda la curva ROC con su AUC y la diagonal de azar."""
    fig, ax = plt.subplots(figsize=(8, 7))
    RocCurveDisplay.from_predictions(y_true, y_score, ax=ax, name="OOF")
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Azar")
    ax.set(xlim=(0, 1), ylim=(0, 1.02), xlabel="Tasa de falsos positivos",
           ylabel="Tasa de verdaderos positivos", title=title)
    ax.grid(alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)
