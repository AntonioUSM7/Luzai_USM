FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema mínimas y limpiar caché
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY . .

EXPOSE 8000

# Ejecutar con recarga en vivo (hot-reload) para desarrollo
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
