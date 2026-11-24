"""Demo interactiva: clasifica un CSV de flujos de red con el modelo XGBoost entrenado."""
from pathlib import Path

import pandas as pd
import streamlit as st

from src.inference import predict

EJEMPLO = Path(__file__).parent / "examples" / "flujos_test_demo.csv"

st.set_page_config(page_title="Detección de intrusiones con ML", page_icon="🛡️", layout="wide")
st.title("Detección de intrusiones en redes con Machine Learning")
st.write(
    "Subí un CSV con flujos de red (las 42 variables de UNSW-NB15) y el modelo XGBoost los clasifica. "
    "Si el CSV trae las etiquetas reales (`label` o `attack_cat`), se muestra cuántos acertó."
)

tarea = st.radio(
    "Tarea", ["binary", "multiclass"], horizontal=True,
    format_func=lambda t: "Binaria: normal o ataque" if t == "binary" else "Multiclase: tipo de ataque",
)
archivo = st.file_uploader("CSV de flujos", type="csv")
usar_ejemplo = st.toggle("Usar 17 flujos de ejemplo del test (8 normales y uno de cada ataque)")

# --- Datos de entrada -------------------------------------------------------
if archivo is not None:
    df = pd.read_csv(archivo)
elif usar_ejemplo:
    df = pd.read_csv(EJEMPLO)
else:
    st.info("Subí un CSV o activá el ejemplo para empezar.")
    st.stop()                     # todavía no hay datos: corta acá

# --- Predicción -------------------------------------------------------------
try:
    resultado = predict(df, tarea, "xgb")
except ValueError as e:           # validate_input avisa si falta alguna columna
    st.error(f"El CSV no tiene el formato esperado: {e}")
    st.stop()

columna = "etiqueta" if tarea == "binary" else "categoria"
if "sttl" in df.columns:
    resultado["sttl"] = df["sttl"].values   # para ver la relación de las falsas alarmas con el TTL

# --- Comparación con las etiquetas reales, si vienen en el CSV --------------
real = "label" if tarea == "binary" else "attack_cat"
if real in df.columns:
    verdad = df["label"].map({0: "normal", 1: "ataque"}) if tarea == "binary" else df["attack_cat"]
    resultado.insert(1, "real", verdad.values)

# --- Resultados -------------------------------------------------------------
st.subheader("Resultado")
c1, c2, c3 = st.columns(3)
c1.metric("Flujos clasificados", len(resultado))
if tarea == "binary":
    c2.metric("Marcados como ataque", int((resultado["etiqueta"] == "ataque").sum()))
if "real" in resultado.columns:
    aciertos = (resultado["real"] == resultado[columna]).mean()
    c3.metric("Aciertos", f"{aciertos:.0%}")

st.bar_chart(resultado[columna].value_counts())
st.dataframe(resultado, width="stretch", hide_index=True)
st.download_button("Descargar predicciones", resultado.to_csv(index=False), "predicciones.csv", "text/csv")