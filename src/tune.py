"""Búsqueda de hiperparámetros de XGBoost con la misma CV agrupada de train.py (issue #28). No toca el test."""
import itertools
import json

import numpy as np

from src.config import METRICS_DIR, SEED, XGB_GRID, XGB_PARAMS
from src.train import N_FOLDS, cross_validate

MODEL = "xgb_sinttl"


def configurations() -> list[dict]:
    """Todas las combinaciones de la grilla, cada una como {hiperparámetro: valor}."""
    names = list(XGB_GRID)
    return [dict(zip(names, values)) for values in itertools.product(*XGB_GRID.values())]


def run() -> None:
    configs = configurations()
    results = []
    for i, combo in enumerate(configs, start=1):
        print(f"\n[{i}/{len(configs)}] {combo}")
        params = {**XGB_PARAMS, **combo}      # parte de los fijos y pisa los tres de la grilla
        fold_metrics, *_ = cross_validate("binary", MODEL, params=params)
        f1 = [m["f1"] for m in fold_metrics]
        fpr = [m["fpr"] for m in fold_metrics]
        results.append({**combo,
                        "f1_mean": float(np.mean(f1)), "f1_std": float(np.std(f1)),
                        "fpr_mean": float(np.mean(fpr)), "fpr_std": float(np.std(fpr))})

    # Ordenar de mayor a menor F1
    results.sort(key=lambda r: r["f1_mean"], reverse=True)

    print("\nmax_depth  learning_rate  min_child_weight      F1 (media ± desvío)    FPR")
    for r in results:
        print(f"{r['max_depth']:>9}  {r['learning_rate']:>13}  {r['min_child_weight']:>16}"
              f"      {r['f1_mean']:.4f} ± {r['f1_std']:.4f}     {r['fpr_mean']:.4f}")

    # Regla fijada en la issue #28 antes de correr
    mejor = results[0]
    actual = next(r for r in results if all(r[k] == XGB_PARAMS[k] for k in XGB_GRID))
    diferencia = mejor["f1_mean"] - actual["f1_mean"]
    if diferencia < max(mejor["f1_std"], actual["f1_std"]):
        elegida, motivo = actual, "empate: la mejora es menor que el desvío entre folds"
    else:
        elegida, motivo = mejor, "la mejora supera el desvío entre folds"
    print(f"\nMejor: {mejor}\nActual: {actual}\nElegida ({motivo}): "
          f"{ {k: elegida[k] for k in XGB_GRID} }")

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    out = {"model": MODEL, "n_folds": N_FOLDS, "seed": SEED, "grid": XGB_GRID,
           "metric": "f1_mean", "results": results,
           "chosen": {k: elegida[k] for k in XGB_GRID}, "reason": motivo}
    with open(METRICS_DIR / f"binary_{MODEL}_tuning.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    run()