# 🚀 Deploy VoiceCore AI 3.0 a Render.com - GRATIS

## ¿Por qué Render?
- ✅ 100% GRATIS para empezar
- ✅ PostgreSQL incluido GRATIS
- ✅ Deploy automático desde GitHub
- ✅ SSL/HTTPS automático
- ✅ Más simple que Railway

## Paso 1: Crear Cuenta en Render (2 minutos)

1. Ve a: **https://render.com**
2. Click en "Get Started"
3. Conecta con tu cuenta de GitHub
4. Autoriza Render a acceder a tus repos

## Paso 2: Crear PostgreSQL Database (1 minuto)

1. En Render Dashboard, click "New +"
2. Selecciona "PostgreSQL"
3. Nombre: `voicecore-db`
4. Plan: **Free** (0 USD/mes)
5. Click "Create Database"
6. **COPIA** la "Internal Database URL" (la necesitarás)

## Paso 3: Crear Web Service (2 minutos)

1. Click "New +" → "Web Service"
2. Conecta tu repositorio: `xpload/voicecore-ai`
3. Configuración:
   - **Name**: `voicecore-ai`
   - **Region**: Oregon (US West)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn voicecore.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: **Free** (0 USD/mes)

## Paso 4: Configurar Variables de Entorno (1 minuto)

En la sección "Environment", agrega:

```
DATABASE_URL=<pega-aqui-la-url-de-postgresql>
SECRET_KEY=render-production-secret-key-123456789
DEBUG=false
PORT=10000
```

## Paso 5: Deploy! (3-5 minutos)

1. Click "Create Web Service"
2. Render automáticamente:
   - Clona tu repo
   - Instala dependencias
   - Arranca la aplicación
3. Espera a que diga "Live" (verde)

## Paso 6: Verificar

Tu app estará en: `https://voicecore-ai.onrender.com`

Prueba:
- https://voicecore-ai.onrender.com/health
- https://voicecore-ai.onrender.com/docs
- https://voicecore-ai.onrender.com/api/v1/events/statistics

## ¿Problemas?

Si ves errores, ve a "Logs" en Render y dime qué dice.

## Ventajas de Render vs Railway

✅ Base de datos PostgreSQL GRATIS incluida
✅ No necesitas tarjeta de crédito
✅ Deploy más rápido
✅ Logs más claros
✅ SSL automático

## Siguiente Paso

Una vez que esté online, puedes:
1. Ejecutar migraciones: `render run alembic upgrade head`
2. Ver logs en tiempo real
3. Escalar si necesitas más recursos
