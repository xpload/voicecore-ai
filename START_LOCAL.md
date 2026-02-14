# 🚀 Arrancar VoiceCore AI 3.0 Localmente

## Paso 1: Instalar Dependencias (2 minutos)

```bash
pip install -r requirements.txt
```

## Paso 2: Configurar Variables de Entorno (1 minuto)

Copia el archivo de ejemplo:
```bash
copy .env.example .env
```

Edita `.env` con valores mínimos para arrancar:
```env
# Mínimo para arrancar
SECRET_KEY=mi-super-secreto-local-123456789
DATABASE_URL=sqlite:///./voicecore_local.db
DEBUG=true
HOST=0.0.0.0
PORT=8000
```

## Paso 3: Crear Base de Datos (30 segundos)

```bash
alembic upgrade head
```

## Paso 4: Arrancar la Aplicación (10 segundos)

```bash
python -m uvicorn voicecore.main:app --reload --host 0.0.0.0 --port 8000
```

## Paso 5: Verificar que Funciona

Abre tu navegador en:
- http://localhost:8000 - Página principal
- http://localhost:8000/health - Health check
- http://localhost:8000/docs - Documentación API
- http://localhost:8000/api/v1/events/statistics - Event Sourcing

## ¿Problemas?

Si ves errores, dime cuál es y lo arreglamos en segundos.
