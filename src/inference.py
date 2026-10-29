"""Predicción sobre un CSV de flujos usando un modelo ya entrenado con train.py."""
import argparse

import joblib
import pandas as pd

from src.config import ID_COL, MODELS_DIR


def load_bundle(task: str, model: str) -> dict:
    """Carga el modelo guardado por train.py (pipeline + umbral + encoder)."""
    path = MODELS_DIR / f"{task}_{model}.joblib"
    if not path.is_file():
        raise FileNotFoundError(
            f"No existe {path}. Entrená el modelo primero: "
            f"python -m src.train --task {task} --model {model}"
        )
    return joblib.load(path)


def validate_input(df: pd.DataFrame, expected: list[str]) -> pd.DataFrame:
    """Verifica que estén todas las columnas que vio el modelo y las devuelve en el mismo orden."""
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el CSV de entrada: {missing}")
    extra = [c for c in df.columns if c not in expected and c != ID_COL]
    if extra:
        print(f"Aviso: se ignoran columnas que el modelo no usa: {extra}")
    return df[expected]


def predict(df: pd.DataFrame, task: str, model: str) -> pd.DataFrame:
    """Devuelve un DataFrame con la predicción (y su probabilidad) para cada flujo."""
    bundle = load_bundle(task, model)
    pipeline = bundle["pipeline"]
    expected = list(pipeline.feature_names_in_)   # las columnas con las que se entrenó
    X = validate_input(df, expected)

    out = pd.DataFrame(index=df.index)
    if ID_COL in df.columns:
        out[ID_COL] = df[ID_COL]

    if task == "binary":
        proba = pipeline.predict_proba(X)[:, 1]
        threshold = bundle["threshold"]
        if threshold is None:                      # la regla sin IA no tiene umbral
            pred = pipeline.predict(X)
        else:
            pred = (proba >= threshold).astype(int)
        out["prob_ataque"] = proba.round(4)
        out["prediccion"] = pred
        out["etiqueta"] = pd.Series(pred, index=df.index).map({0: "normal", 1: "ataque"})
    else:
        proba = pipeline.predict_proba(X)          # una columna por clase
        pred_idx = proba.argmax(axis=1)            # la clase con mayor probabilidad
        out["categoria"] = bundle["label_encoder"].inverse_transform(pred_idx)
        out["prob_categoria"] = proba.max(axis=1).round(4)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predicción de flujos de red con un modelo entrenado")
    parser.add_argument("--input", required=True, help="CSV con los flujos a clasificar")
    parser.add_argument("--task", choices=["binary", "multiclass"], default="binary")
    parser.add_argument("--model", choices=["heuristic", "lr", "xgb"], default="xgb")
    parser.add_argument("--output", default="predicciones.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    result = predict(df, args.task, args.model)
    result.to_csv(args.output, index=False)

    print(f"{len(result)} flujos clasificados -> {args.output}")
    column = "etiqueta" if args.task == "binary" else "categoria"
    print(result[column].value_counts().to_string())
