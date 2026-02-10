# 🚀 Despliegue Manual SUPER SIMPLE (Sin CLI)

## Paso 1: Crear cuenta en Railway (2 minutos)

1. Ve a: **https://railway.app/**
2. Click en **"Start a New Project"**
3. Inicia sesión con GitHub (recomendado) o email

## Paso 2: Crear proyecto desde GitHub (3 minutos)

### Opción A: Si tu código está en GitHub

1. En Railway, click **"Deploy from GitHub repo"**
2. Conecta tu cuenta de GitHub
3. Selecciona el repositorio `voicecore-ai`
4. Click **"Deploy Now"**

### Opción B: Si NO está en GitHub (usa esta)

1. En Railway, click **"Empty Project"**
2. Click **"+ New"** → **"GitHub Repo"**
3. Sigue las instrucciones para conectar GitHub
4. O usa **"Deploy from CLI"** (pero necesitas CLI)

### Opción C: La MÁS SIMPLE - Subir código directamente

**No puedes subir código directamente en Railway**, PERO puedes:

1. Crear un repo en GitHub primero
2. Subir tu código
3. Conectar Railway a ese repo

## Paso 3: Agregar PostgreSQL (1 minuto)

1. En tu proyecto de Railway
2. Click **"+ New"**
3. Selecciona **"Database"**
4. Elige **"PostgreSQL"**
5. Espera 1-2 minutos a que se provisione

## Paso 4: Configurar Variables de Entorno (2 minutos)

1. Click en tu servicio (el que tiene tu código)
2. Ve a la pestaña **"Variables"**
3. Agrega estas variables:

```
SECRET_KEY=tu-clave-secreta-minimo-32-caracteres-aqui
JWT_SECRET_KEY=tu-jwt-secret-key-minimo-32-caracteres
```

**Opcional (para funcionalidad completa):**
```
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_PHONE_NUMBER=+1234567890
OPENAI_API_KEY=sk-proj-xxxxx
```

**Nota:** `DATABASE_URL` se configura automáticamente

## Paso 5: Desplegar (Automático)

Railway desplegará automáticamente cuando:
- Conectes el repo de GitHub
- Hagas push a la rama main

## Paso 6: Ejecutar Migraciones

1. En Railway, ve a tu servicio
2. Click en **"Settings"**
3. Busca **"Deploy Command"** o **"Build Command"**
4. O usa la terminal web de Railway

**Comando para ejecutar:**
```bash
alembic upgrade head && python scripts/init_project.py
```

## Paso 7: Obtener URL

1. En tu servicio de Railway
2. Ve a **"Settings"**
3. Busca **"Domains"**
4. Click **"Generate Domain"**
5. Copia la URL: `https://tu-app.railway.app`

## Paso 8: Probar

```bash
curl https://tu-app.railway.app/health
```

Deberías ver:
```json
{"status":"healthy","database":"connected"}
```

---

## ⚠️ PROBLEMA: No tienes GitHub?

### Solución: Crear repo en GitHub AHORA

1. Ve a: **https://github.com/new**
2. Nombre: `voicecore-ai`
3. Privado o Público (tu eliges)
4. Click **"Create repository"**

5. En tu terminal (en la carpeta del proyecto):

```bash
git init
git add .
git commit -m "Initial commit - VoiceCore AI 3.0"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/voicecore-ai.git
git push -u origin main
```

6. Ahora conecta Railway a este repo

---

## 🎯 ALTERNATIVA MÁS RÁPIDA: Render.com

Si Railway es complicado, usa **Render.com** (más simple):

1. Ve a: **https://render.com/**
2. Crea cuenta
3. Click **"New +"** → **"Web Service"**
4. Conecta GitHub repo
5. Configuración:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn voicecore.main:app --host 0.0.0.0 --port $PORT`
6. Agrega PostgreSQL desde el dashboard
7. Configura variables de entorno
8. Deploy!

---

## 💡 OPCIÓN MÁS SIMPLE DE TODAS: Heroku

1. Ve a: **https://heroku.com/**
2. Crea cuenta (gratis)
3. Instala Heroku CLI: **https://devcenter.heroku.com/articles/heroku-cli**
4. En terminal:

```bash
heroku login
heroku create voicecore-ai
heroku addons:create heroku-postgresql:mini
git push heroku main
heroku run alembic upgrade head
heroku run python scripts/init_project.py
heroku open
```

---

## 🆘 Si TODO falla: Prueba LOCAL primero

```bash
# 1. Instala dependencias
pip install -r requirements.txt

# 2. Ejecuta migraciones
alembic upgrade head

# 3. Inicializa datos
python scripts/init_project.py

# 4. Inicia servidor
uvicorn voicecore.main:app --reload

# 5. Abre navegador
# http://localhost:8000/docs
```

Esto te permite probar TODO localmente antes de desplegar.

---

## ✅ Resumen de Opciones

| Plataforma | Dificultad | Tiempo | Costo |
|------------|-----------|--------|-------|
| Railway | Media | 10 min | $10/mes |
| Render | Fácil | 15 min | $7/mes |
| Heroku | Fácil | 10 min | $5/mes |
| Local | Muy Fácil | 5 min | Gratis |

**Recomendación:** Empieza con **LOCAL** para probar, luego despliega a **Render** (más simple que Railway).
