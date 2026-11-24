import pytest

from src.data import get_X_y

PROHIBIDAS = {"id", "label", "attack_cat"}


@pytest.mark.parametrize("task", ["binary", "multiclass"])
def test_get_X_y_no_filtra_etiquetas(flujos, task):
    X, y = get_X_y(flujos, task)
    assert not (PROHIBIDAS & set(X.columns))



def test_get_X_y_binaria_usa_label(flujos):
    X, y = get_X_y(flujos, "binary")
    assert y.equals(flujos["label"])



def test_get_X_y_multiclase_usa_attack_cat(flujos):
    X, y = get_X_y(flujos, "multiclass")
    assert y.equals(flujos["attack_cat"])



def test_get_X_y_tarea_invalida(flujos):
    with pytest.raises(ValueError):
        get_X_y(flujos, "regresion")
