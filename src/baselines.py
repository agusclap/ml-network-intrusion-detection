"""Baselines sin aprendizaje para las tareas del proyecto UNSW-NB15."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.validation import check_is_fitted


def _row_count(X: Any) -> int:
    """Devuelve la cantidad de filas o informa una entrada inválida."""
    if X is None:
        raise ValueError("X no puede ser None.")
    try:
        return len(X)
    except TypeError as exc:
        raise ValueError("X debe ser una tabla o matriz con filas.") from exc


def _destination_packets(X: Any) -> np.ndarray:
    """Obtiene dpkts y valida la entrada de la heurística binaria."""
    if not isinstance(X, pd.DataFrame):
        raise TypeError("La heurística requiere X como pandas.DataFrame con la columna 'dpkts'.")
    if "dpkts" not in X.columns:
        raise ValueError("Falta la columna requerida 'dpkts' para la heurística binaria.")
    if X["dpkts"].isna().any():
        raise ValueError("La columna 'dpkts' contiene valores nulos.")
    try:
        return pd.to_numeric(X["dpkts"], errors="raise").to_numpy()
    except (TypeError, ValueError) as exc:
        raise ValueError("La columna 'dpkts' debe contener valores numéricos.") from exc


class DpktsZeroClassifier(ClassifierMixin, BaseEstimator):
    """Predice ataque (1) cuando el destino no recibió paquetes (`dpkts == 0`).

    Es el baseline heurístico binario definido en el Charter. Se implementa
    como estimador de scikit-learn para poder ajustarlo dentro de cada fold.
    """

    def fit(self, X: pd.DataFrame, y: Any) -> DpktsZeroClassifier:
        packets = _destination_packets(X)
        target = np.asarray(y)
        if target.ndim != 1:
            raise ValueError("y debe ser un vector unidimensional.")
        if len(target) != len(packets):
            raise ValueError("X e y deben tener la misma cantidad de filas.")
        if target.size == 0:
            raise ValueError("No se puede ajustar la heurística con un conjunto vacío.")
        if not np.isin(target, [0, 1]).all():
            raise ValueError("DpktsZeroClassifier solo admite etiquetas binarias 0 y 1.")

        self.classes_ = np.array([0, 1], dtype=int)
        self.n_features_in_ = X.shape[1]
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Devuelve 1 para `dpkts == 0` y 0 en los demás casos."""
        check_is_fitted(self, attributes=["classes_"])
        packets = _destination_packets(X)
        return (packets == 0).astype(int)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Devuelve probabilidades deterministas compatibles con sklearn."""
        predictions = self.predict(X)
        return np.column_stack((1 - predictions, predictions)).astype(float)


class MajorityClassClassifier(ClassifierMixin, BaseEstimator):
    """Predice en todas las filas la clase más frecuente observada en `fit`."""

    def fit(self, X: Any, y: Any) -> MajorityClassClassifier:
        rows = _row_count(X)
        target = np.asarray(y)
        if target.ndim != 1:
            raise ValueError("y debe ser un vector unidimensional.")
        if len(target) != rows:
            raise ValueError("X e y deben tener la misma cantidad de filas.")
        if target.size == 0:
            raise ValueError("No se puede ajustar el baseline con un conjunto vacío.")

        self.classes_, counts = np.unique(target, return_counts=True)
        # np.unique ordena las clases; ante un empate se elige la primera,
        # de forma determinista e independiente del orden de las filas.
        majority_index = int(np.flatnonzero(counts == counts.max())[0])
        self.majority_class_ = self.classes_[majority_index]
        self.majority_index_ = majority_index
        if hasattr(X, "shape") and len(X.shape) > 1:
            self.n_features_in_ = X.shape[1]
            if isinstance(X, pd.DataFrame):
                self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        return self

    def predict(self, X: Any) -> np.ndarray:
        """Devuelve la clase mayoritaria para cada fila de `X`."""
        check_is_fitted(self, attributes=["majority_class_"])
        return np.full(_row_count(X), self.majority_class_, dtype=self.classes_.dtype)

    def predict_proba(self, X: Any) -> np.ndarray:
        """Devuelve probabilidad 1 para la clase mayoritaria y 0 para el resto."""
        check_is_fitted(self, attributes=["majority_index_"])
        probabilities = np.zeros((_row_count(X), len(self.classes_)), dtype=float)
        probabilities[:, self.majority_index_] = 1.0
        return probabilities


def make_baseline(task: str) -> ClassifierMixin:
    """Crea el baseline sin IA que corresponde a la tarea.

    `binary` usa la regla `dpkts == 0`; `multiclass` usa la clase mayoritaria,
    que se aprende exclusivamente a partir del `y` recibido en `fit`.
    """
    if task == "binary":
        return DpktsZeroClassifier()
    if task == "multiclass":
        return MajorityClassClassifier()
    raise ValueError("task debe ser 'binary' o 'multiclass'.")
