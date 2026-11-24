"""Datos sintéticos chicos para los tests: el dataset real no está en el repo."""
import pandas as pd
import pytest


@pytest.fixture
def flujos() -> pd.DataFrame:
    """8 flujos con las columnas que usan las funciones. Las filas 0 y 1 tienen la misma X."""
    return pd.DataFrame({
        "id":         [1, 2, 3, 4, 5, 6, 7, 8],
        "dur":        [0.1, 0.1, 2.0, 0.5, 1.2, 0.0, 3.1, 0.7],
        "proto":      ["tcp", "tcp", "udp", "tcp", "udp", "tcp", "tcp", "udp"],
        "service":    ["http", "http", "dns", "-", "dns", "-", "ftp", "-"],
        "state":      ["FIN", "FIN", "CON", "INT", "CON", "INT", "FIN", "INT"],
        "dpkts":      [4, 4, 2, 0, 2, 0, 10, 0],
        "sttl":       [31, 31, 31, 254, 31, 254, 62, 254],
        "label":      [0, 1, 0, 1, 0, 1, 0, 1],
        "attack_cat": ["Normal", "Exploits", "Normal", "Generic",
                       "Normal", "Reconnaissance", "Normal", "DoS"],
    })
