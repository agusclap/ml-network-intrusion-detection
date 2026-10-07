"""Preprocesamiento: one-hot de categóricas y escalado de numéricas según el modelo."""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import CATEGORICAL_COLS


def build_preprocessor(model: str) -> ColumnTransformer:
    """Construye el preprocesador (sin ajustar) para el modelo indicado: "lr" o "xgb"."""
    if model == "lr":
        numeric_step = StandardScaler()
    elif model == "xgb":
        numeric_step = "passthrough"
    else:
        raise ValueError(f"model debe ser 'lr' o 'xgb', no {model!r}")

    categorical_step = OneHotEncoder(
        handle_unknown="ignore",   # una categoría que no vio en fit no rompe: queda todo en 0
        min_frequency=50,          # categorías con menos de 50 filas se agrupan en una sola columna
        sparse_output=False,
    )

    return ColumnTransformer([
        ("cat", categorical_step, CATEGORICAL_COLS),
        ("num", numeric_step, make_column_selector(dtype_include="number")),
    ])


if __name__ == "__main__":
    from src.data import get_X_y, load_split

    X, y = get_X_y(load_split("train"), "binary")
    for model in ("lr", "xgb"):
        prep = build_preprocessor(model)
        Xt = prep.fit_transform(X)
        print(f"[{model}] {X.shape} -> {Xt.shape}")

    # Una fila con un 'state' que nunca vio no tiene que romper
    fila_rara = X.head(1).copy()
    fila_rara["state"] = "XYZ"
    print("categoría desconocida OK:", prep.transform(fila_rara).shape)
