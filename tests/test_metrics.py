import numpy as np
import pytest

from src.metrics import compute_metrics, select_binary_threshold


def test_umbral_cumple_recall_minimo():
    rng = np.random.default_rng(42)
    y_true = rng.integers(0, 2, 200)                                  # 200 etiquetas al azar
    y_score = np.clip(y_true * 0.6 + rng.normal(0.2, 0.25, 200), 0, 1)  # scores con ruido
    umbral = select_binary_threshold(y_true, y_score)
    pred = (y_score >= umbral).astype(int)
    recall = ((pred == 1) & (y_true == 1)).sum() / (y_true == 1).sum()
    assert recall >= 0.90


def test_umbral_ejemplo_conocido():
    # 8 ataques y 2 normales. Con umbral 0,6 o más se pierde el ataque de score 0,2
    # (recall 7/8 = 0,875 < 0,90): la regla obliga a bajar hasta 0,2.
    y_true  = [0,   0,   1,   1,   1,    1,   1,    1,   1,    1]
    y_score = [0.1, 0.6, 0.2, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99]
    assert select_binary_threshold(y_true, y_score) == 0.2


def test_umbral_necesita_las_dos_clases():
    with pytest.raises(ValueError):
        select_binary_threshold([1, 1, 1], [0.2, 0.5, 0.9])


def test_tasa_de_falsos_positivos():
    # 4 normales (uno marcado como ataque) y 2 ataques detectados
    m = compute_metrics("binary", [0, 0, 0, 0, 1, 1], [1, 0, 0, 0, 1, 1])
    assert m["fpr"] == 0.25
    assert m["recall"] == 1.0
