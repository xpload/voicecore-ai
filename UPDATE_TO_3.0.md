# 🚀 Actualizar a VoiceCore AI 3.0 Enterprise

## Tu aplicación actual está en:
**https://voicecore-ai-production.up.railway.app/**

## Vamos a actualizarla con Event Sourcing y todas las nuevas funcionalidades

---

## OPCIÓN 1: Actualización Automática con Git (Recomendado)

### Paso 1: Verificar Git
```bash
git status
```

### Paso 2: Agregar todos los archivos nuevos
```bash
git add .
```

### Paso 3: Commit con los cambios
```bash
git commit -m "Update to VoiceCore AI 3.0 Enterprise - Event Sourcing + CQRS"
```

### Paso 4: Push a GitHub
```bash
git push origin main
```

**Railway detectará los cambios automáticamente y redesplegará en 2-5 minutos**

---

## OPCIÓN 2: Actualización Manual desde Railway Dashboard

1. Ve a: **https://railway.app/dashboard**
2. Selecciona tu proyecto: **voicecore-ai-production**
3. Click en **"Settings"**
4. Click en **"Redeploy"**
5. Espera 2-5 minutos

---

## OPCIÓN 3: Script Automático

```bash
python update_railway.py
```

Este script hace todo automáticamente:
- ✅ Git add
- ✅ Git commit
- ✅ Git push
- ✅ Railway redeploy automático

---

## ¿Qué hay de nuevo en 3.0?

### ✨ Event Sourcing & CQRS
- 50+ tipos de eventos inmutables
- Replay de eventos para debugging
- Snapshots para performance
- Blockchain audit trail

### 🎯 Nuevas APIs
- `/api/v1/events` - Event Sourcing
- `/api/v1/events/statistics` - Estadísticas
- `/api/v1/events/replay` - Replay de eventos
- `/api/v1/events/snapshots` - Snapshots

### 📊 Mejoras
- 9 migraciones de base de datos
- Multi-tenant con RLS
- Kafka event bus ready
- Istio service mesh ready

---

## Verificar después de actualizar

### 1. Health Check
```bash
curl https://voicecore-ai-production.up.railway.app/health
```

### 2. Event Sourcing
```bash
curl https://voicecore-ai-production.up.railway.app/api/v1/events/statistics
```

### 3. Dashboard
Abre: https://voicecore-ai-production.up.railway.app/dashboard

---

## Troubleshooting

### Error: "Git not configured"
```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
```

### Error: "No remote origin"
```bash
git remote add origin https://github.com/TU_USUARIO/voicecore-ai.git
```

### Error: "Push rejected"
```bash
git pull origin main --rebase
git push origin main
```

---

## ¿Necesitas ayuda?

Ejecuta este comando para encontrar tu URL actual:
```bash
python find_railway_url.py
```

O actualiza directamente:
```bash
python update_railway.py
```
