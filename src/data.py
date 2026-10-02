"""Carga y verificación de los datos oficiales de UNSW-NB15."""
import hashlib
from pathlib import Path

import pandas as pd

from src.config import EXPECTED_MD5, TASKS, TEST_CSV, TRAIN_CSV


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


SPLITS = {"train": TRAIN_CSV, "test": TEST_CSV}


def load_split(split: str) -> pd.DataFrame:
    """Verifica y carga la partición oficial pedida ("train" o "test")."""
    if split not in SPLITS:
        raise ValueError(f"split debe ser 'train' o 'test', no {split!r}")
    path = SPLITS[split]
    verify_file(path)          # primero se verifica, después se lee
    return pd.read_csv(path)


def get_X_y(df: pd.DataFrame, task: str) -> tuple[pd.DataFrame, pd.Series]:
    """Separa las variables de entrada (X) y el target (y) para la tarea indicada.

    Saca de X el id, el target de la tarea y el target de la otra tarea,
    para que el modelo no vea la respuesta.
    """
    if task not in TASKS:
        raise ValueError(f"task debe ser 'binary' o 'multiclass', no {task!r}")
    target = TASKS[task]["target"]
    drop = TASKS[task]["drop"]

    y = df[target]
    X = df.drop(columns=drop + [target])

    # Guarda: ninguna de las columnas prohibidas puede quedar en X
    forbidden = set(drop) | {target}
    leaked = forbidden & set(X.columns)
    assert not leaked, f"Columnas prohibidas en X: {leaked}"

    return X, y


if __name__ == "__main__":
    train = load_split("train")
    test = load_split("test")
    print(f"train: {train.shape} | test: {test.shape}")

    for task in TASKS:
        X, y = get_X_y(train, task)
        print(f"\n[{task}] X: {X.shape} | y: {y.name}")
        print(y.value_counts().to_string())
