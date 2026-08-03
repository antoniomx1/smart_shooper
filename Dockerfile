# Usar imagen ligera de Python 3.11 en Debian Bookworm
FROM python:3.11-slim-bookworm

# Evitar que Python escriba archivos .pyc y forzar stdout sin buffer para logs de GCP
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Instalar Chromium Headless, WebDriver y dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    curl \
    gnupg \
    && rm -rf /var/lib/apt-get/lists/*

# Configurar variables de entorno para que Selenium sepa dónde está Chromium
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Comando por defecto para ejecutar la aplicación
CMD ["python", "main.py"]