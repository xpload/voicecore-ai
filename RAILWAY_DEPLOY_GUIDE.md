# 🚀 VoiceCore AI - Despliegue Rápido en Railway

## Paso 1: Instalar Railway CLI (2 minutos)

```bash
# Opción A: Con npm (recomendado)
npm install -g @railway/cli

# Opción B: Con PowerShell (Windows)
iwr https://railway.app/install.ps1 | iex
```

## Paso 2: Login y Setup (3 minutos)

```bash
# 1. Login a Railway
railway login

# 2. Crear nuevo proyecto
railway init

# 3. Agregar PostgreSQL
railway add

# Selecciona: PostgreSQL
```

## Paso 3: Configurar Variables de Entorno (5 minutos)

Railway detectará automáticamente el `DATABASE_URL` de PostgreSQL.

Necesitas agregar estas variables manualmente:

```bash
# Opción A: Desde CLI
railway variables set TWILIO_ACCOUNT_SID=ACxxxxx
railway variables set TWILIO_AUTH_TOKEN=xxxxx
railway variables set TWILIO_PHONE_NUMBER=+1234567890
railway variables set OPENAI_API_KEY=sk-proj-xxxxx
railway variables set SECRET_KEY=tu-clave-secreta-minimo-32-caracteres
railway variables set JWT_SECRET_KEY=tu-jwt-secret-key

# Opción B: Desde Dashboard Web
# Ve a: https://railway.app/dashboard
# Selecciona tu proyecto > Variables
```

## Paso 4: Crear Procfile (1 minuto)

Railway necesita saber cómo iniciar tu app:

```bash
# Ya está creado en el proyecto como Procfile
```

## Paso 5: Deploy (5 minutos)

```bash
# Deploy a Railway
railway up

# Ver logs en tiempo real
railway logs
```

## Paso 6: Ejecutar Migraciones (2 minutos)

```bash
# Conectar a la base de datos y ejecutar migraciones
railway run alembic upgrade head

# Crear tenant inicial
railway run python scripts/init_project.py
```

## Paso 7: Obtener URL de Producción (1 minuto)

```bash
# Ver la URL de tu aplicación
railway domain

# O desde el dashboard:
# https://railway.app/dashboard > Tu Proyecto > Settings > Domains
```

## Paso 8: Configurar Twilio Webhooks (3 minutos)

1. Ve a: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Selecciona tu número
3. En "A CALL COMES IN":
   - Webhook: `https://tu-app.railway.app/api/v1/webhooks/twilio/voice`
   - HTTP POST

## Paso 9: Probar con Llamada Real (5 minutos)

```bash
# Ver logs en tiempo real
railway logs --follow

# Llama a tu número de Twilio desde tu teléfono
# Deberías ver los logs en tiempo real
```

## 🎯 Comandos Útiles

```bash
# Ver status del proyecto
railway status

# Ver variables de entorno
railway variables

# Abrir dashboard web
railway open

# Ver logs
railway logs

# Conectar a PostgreSQL
railway connect postgres

# Ejecutar comando en producción
railway run <comando>

# Reiniciar servicio
railway restart
```

## 🔧 Troubleshooting

### Error: "No project found"
```bash
railway link
# Selecciona tu proyecto
```

### Error: "Database connection failed"
```bash
# Verificar que PostgreSQL está corriendo
railway status

# Ver variables de entorno
railway variables
```

### Error: "Port already in use"
```bash
# Railway asigna el puerto automáticamente
# Asegúrate de usar: PORT=${PORT:-8000}
```

## 📊 Monitoreo

```bash
# Ver métricas en tiempo real
railway logs --follow

# Ver uso de recursos
railway status

# Dashboard web con gráficas
railway open
```

## 💰 Costos

- **PostgreSQL**: ~$5/mes
- **Servicio Web**: ~$5/mes
- **Total**: ~$10/mes

**Créditos gratis**: Railway da $5 de crédito gratis para empezar.

## 🎉 ¡Listo!

Tu VoiceCore AI está ahora en producción con:
- ✅ PostgreSQL real
- ✅ HTTPS automático
- ✅ Logs en tiempo real
- ✅ Escalamiento automático
- ✅ Backups automáticos
- ✅ Monitoreo incluido

**Próximos pasos:**
1. Hacer tu primera llamada real
2. Verificar Event Sourcing con datos reales
3. Monitorear métricas
4. Ajustar según feedback real
