import pandas as pd
import pytest

from src.inference import validate_input

ESPERADAS = ["dur", "proto", "sttl"]


def test_falta_una_columna_da_error():
    df = pd.DataFrame({"dur": [0.1], "proto": ["tcp"]})  # falta sttl
    with pytest.raises(ValueError, match="sttl"):
        validate_input(df, ESPERADAS)


def test_ignora_sobrantes_y_respeta_el_orden(capsys):
    df = pd.DataFrame({"sttl": [254], "id": [7], "extra": [1], "proto": ["udp"], "dur": [0.0]})
    salida = validate_input(df, ESPERADAS)
    assert list(salida.columns) == ESPERADAS                                # las columnas de salida son ESPERADAS, en ese orden
    assert "extra" in capsys.readouterr().out  # avisa que ignora "extra"
