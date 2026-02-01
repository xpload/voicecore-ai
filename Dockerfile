# Dockerfile para VoiceCore AI - Railway Optimizado
FROM python:3.11-slim

# Configurar directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias primero (para cache de Docker)
COPY requirements_minimal.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_minimal.txt

# Copiar código de la aplicación
COPY . .

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Railway asigna el puerto dinámicamente
EXPOSE $PORT

# Comando para iniciar la aplicación con puerto dinámico
CMD python simple_start.py