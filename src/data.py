"""Carga y verificación de los datos oficiales de UNSW-NB15."""
import hashlib
from pathlib import Path

import pandas as pd

from src.config import EXPECTED_MD5


def md5_file(path: Path) -> str:
    """Devuelve el hash MD5 (en hexadecimal) del archivo."""
    digest = hashlib.md5()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path) -> None:
    """Verifica que el archivo exista y que su MD5 sea el esperado.

    Si algo no está bien, lanza una excepción y el programa se detiene.
    """
    # 1. ¿Existe el archivo?
    if not path.is_file():
        raise FileNotFoundError(
            f"No se encontró {path}. Ver data/README.md para descargarlo."
        )

    # 2. ¿Qué hash esperamos para este archivo? (la clave es el nombre, no la ruta)
    expected = EXPECTED_MD5[path.name]

    # 3. ¿Qué hash tiene realmente?
    actual = md5_file(path)

    # 4. Si no coinciden, cortar
    if actual != expected:
        raise ValueError(
            f"MD5 incorrecto para {path.name}: se esperaba {expected} y se obtuvo {actual}. "
            "¿Es la copia de Kaggle? Ver data/README.md."
        )


if __name__ == "__main__":
    from src.config import TRAIN_CSV, TEST_CSV
    for path in (TRAIN_CSV, TEST_CSV):
        verify_file(path)
        print(f"{path.name}: OK")
