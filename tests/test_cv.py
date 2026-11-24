import pandas as pd

from src.data import get_X_y
from src.train import make_folds, make_groups


def test_filas_identicas_mismo_grupo(flujos):
    X, _ = get_X_y(flujos, "binary")
    groups = make_groups(X)
    assert groups[0] == groups[1]  # las filas 0 y 1 tienen la misma X
    assert groups.nunique() == 7   # 8 filas, de las cuales 2 son idénticas


def test_folds_no_mezclan_grupos(flujos):
    muchos = pd.concat([flujos] * 5, ignore_index=True)  # cada flujo repetido 5 veces
    X, y = get_X_y(muchos, "binary")
    groups = make_groups(X)
    for train_idx, val_idx in make_folds(X, y, groups):
        grupos_train = set(groups.iloc[train_idx])
        grupos_val = set(groups.iloc[val_idx])
        assert not (grupos_train & grupos_val)  # ningún grupo en entrenamiento y validación a la vez


def test_cada_fila_se_valida_una_sola_vez(flujos):
    muchos = pd.concat([flujos] * 5, ignore_index=True)
    X, y = get_X_y(muchos, "binary")
    folds = make_folds(X, y, make_groups(X))
    validadas = sorted(i for _, val_idx in folds for i in val_idx)
    assert validadas == list(range(len(muchos)))
