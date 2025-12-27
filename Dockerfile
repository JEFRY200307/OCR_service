# Usamos Python 3.11 Slim para mantenerlo ligero
FROM python:3.11-slim

# 1. Instalar dependencias del sistema (gl1 para OpenCV, gomp para Paddle)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libgomp1 \
    libglib2.0-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Instalar librerías de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Pre-descargar el modelo OCR (Truco para que no falle el primer request)
# Esto descarga el modelo en español al construir la imagen
RUN python3 -c "from paddleocr import PaddleOCR; PaddleOCR(lang='es', use_textline_orientation=True)"

# 4. Copiar todo el código fuente
COPY . .

# 5. Crear usuario no root para mayor seguridad
RUN useradd -m appuser
USER appuser

# 6. Exponer puerto
EXPOSE 8000

# 7. Ejecutar la API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]