FROM python:3.13-slim
WORKDIR /app

# XGBoost usa OpenMP y la imagen slim no trae esa librería
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Primero solo las dependencias: si cambiás el código, Docker no las reinstala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Después el código, los modelos y el ejemplo
COPY src/ src/
COPY models/ models/
COPY examples/ examples/
COPY streamlit_app.py .

EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]