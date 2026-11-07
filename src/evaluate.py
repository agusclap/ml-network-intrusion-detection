"""Evaluación final de los modelos congelados. El test se usa una sola vez."""
import argparse
import json

from src.config import FIGURES_DIR, METRICS_DIR
from src.data import get_X_y, load_split
from src.inference import load_bundle
from src.metrics import compute_metrics
from src.plots import save_confusion_matrix, save_roc_curve


def evaluate(task: str, model: str, split: str = "test") -> None:
    print(f"\n=== {task} / {model} / {split} ===")
    out_path = METRICS_DIR / f"{task}_{model}_{split}.json"
    if out_path.exists():
        raise FileExistsError(f"{out_path} ya existe: el {split} ya se evaluó con este modelo.")

    bundle = load_bundle(task, model)
    pipeline = bundle["pipeline"]
    threshold = bundle["threshold"]       
    encoder = bundle["label_encoder"]        

    X, y = get_X_y(load_split(split), task)           

    if task == "binary":
        y_score = pipeline.predict_proba(X)[:, 1]     
        y_pred = pipeline.predict(X) if threshold is None else (y_score >= threshold).astype(int)   
        metrics = compute_metrics(task, y, y_pred, y_score=y_score)
        print(f"  recall {metrics['recall']:.4f}  fpr {metrics['fpr']:.4f}  f1 {metrics['f1']:.4f}")
    else:
        y_pred = encoder.inverse_transform(pipeline.predict(X))      
        metrics = compute_metrics(task, y, y_pred, labels=encoder.classes_)
        print(f"  macro_f1 {metrics['macro_f1']:.4f}  weighted_f1 {metrics['weighted_f1']:.4f}")

    if model != "heuristic":
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        if task == "binary":
            save_confusion_matrix(y, y_pred, FIGURES_DIR / f"{task}_{model}_{split}_cm.png",
                                  f"Matriz de confusión {split} — {model} (umbral {threshold:.3f})",
                                  labels=["Normal", "Ataque"])
            save_roc_curve(y, y_score, FIGURES_DIR / f"{task}_{model}_{split}_roc.png",
                           f"Curva ROC {split} — {model}")
        else:
            save_confusion_matrix(y, y_pred, FIGURES_DIR / f"{task}_{model}_{split}_cm.png",
                                  f"Matriz de confusión {split} — {model}",
                                  labels=[str(c) for c in encoder.classes_])

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    result = {"task": task, "model": model, "split": split, "threshold": threshold, "metrics": metrics}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["binary", "multiclass"], required=True)
    parser.add_argument("--model", choices=["heuristic", "lr", "xgb"], required=True)
    parser.add_argument("--split", choices=["train", "test"], default="test")
    args = parser.parse_args()
    evaluate(args.task, args.model, args.split)
