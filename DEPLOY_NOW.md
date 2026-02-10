# 🚀 Deploy VoiceCore AI to Production NOW

## Quick Start (10 minutes)

### Option 1: Automated Script (Recommended)

```bash
python deploy_railway.py
```

The script will guide you through:
1. ✅ Check Railway CLI
2. ✅ Login to Railway
3. ✅ Create project
4. ✅ Add PostgreSQL
5. ✅ Set environment variables
6. ✅ Deploy application
7. ✅ Run migrations
8. ✅ Initialize data

### Option 2: Manual Steps

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Add PostgreSQL (do this in Railway Dashboard)
# Go to: https://railway.app/dashboard
# Click "+ New" > "Database" > "PostgreSQL"

# 5. Set environment variables (in Railway Dashboard)
# Required:
# - SECRET_KEY=your-secret-key-min-32-chars
# - JWT_SECRET_KEY=your-jwt-secret-key

# 6. Deploy
railway up

# 7. Run migrations
railway run alembic upgrade head

# 8. Initialize project
railway run python scripts/init_project.py

# 9. Get your URL
railway domain
```

## Environment Variables

### Required (Minimum to run)
```
SECRET_KEY=your-secret-key-minimum-32-characters-long
JWT_SECRET_KEY=your-jwt-secret-key-minimum-32-chars
```

### Optional (For full functionality)
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
```

**Note:** `DATABASE_URL` is automatically set by Railway when you add PostgreSQL.

## After Deployment

### 1. View Logs
```bash
railway logs --follow
```

### 2. Test API
```bash
# Get your URL
railway domain

# Test health endpoint
curl https://your-app.railway.app/health

# Expected response:
# {"status":"healthy","database":"connected"}
```

### 3. Configure Twilio (if using)
1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Select your number
3. Configure webhooks:
   - **Voice**: `https://your-app.railway.app/api/v1/webhooks/twilio/voice`
   - **SMS**: `https://your-app.railway.app/api/v1/webhooks/twilio/sms`

### 4. Make Test Call
Call your Twilio number and verify:
- ✅ Call is answered
- ✅ AI responds
- ✅ Conversation works
- ✅ Events are logged

### 5. Verify Event Sourcing
```bash
# Check events in database
railway run python -c "
from voicecore.database import init_database, get_db_session
from sqlalchemy import text
import asyncio

async def check_events():
    await init_database()
    async with get_db_session() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM event_store'))
        count = result.scalar()
        print(f'Total events: {count}')

asyncio.run(check_events())
"
```

## Useful Commands

```bash
# View status
railway status

# View variables
railway variables

# Restart service
railway restart

# Connect to PostgreSQL
railway connect postgres

# Open dashboard
railway open

# View recent logs
railway logs

# Follow logs in real-time
railway logs --follow
```

## Troubleshooting

### Error: "No project found"
```bash
railway link
# Select your project from the list
```

### Error: "Database connection failed"
```bash
# Check PostgreSQL is running
railway status

# View DATABASE_URL
railway variables | grep DATABASE_URL
```

### Error: "Port already in use"
Railway automatically assigns the port. Make sure your code uses:
```python
port = int(os.getenv("PORT", 8000))
```

### Error: "Migration failed"
```bash
# Check current migration
railway run alembic current

# Try upgrading again
railway run alembic upgrade head

# If still fails, check logs
railway logs
```

## Monitoring

### Real-time Logs
```bash
railway logs --follow
```

### Resource Usage
```bash
railway status
```

### Database Queries
```bash
railway connect postgres
# Then run SQL queries
```

## Cost Estimate

- **PostgreSQL**: ~$5/month
- **Web Service**: ~$5/month
- **Total**: ~$10/month

**Free Credits**: Railway provides $5 free credit to start.

## What's Deployed

✅ **Backend API** (FastAPI)
- All REST endpoints
- WebSocket support
- Event Sourcing
- CQRS architecture

✅ **PostgreSQL Database**
- Multi-tenant with RLS
- Event store
- All migrations applied

✅ **Services**
- Call routing
- AI conversation
- Analytics
- CRM integration
- Event bus (Kafka ready)

## Next Steps After Deployment

1. **Test with real calls** - Make actual phone calls
2. **Monitor metrics** - Watch logs and performance
3. **Verify Event Sourcing** - Check events are being stored
4. **Test multi-tenant** - Create multiple tenants
5. **Load testing** - Test with concurrent calls
6. **Configure monitoring** - Set up alerts
7. **Backup strategy** - Configure automated backups

## Production Checklist

- [ ] Railway CLI installed
- [ ] Logged in to Railway
- [ ] Project created
- [ ] PostgreSQL added
- [ ] Environment variables set
- [ ] Application deployed
- [ ] Migrations run
- [ ] Initial data created
- [ ] Health check passes
- [ ] Twilio webhooks configured (if using)
- [ ] Test call successful
- [ ] Logs accessible
- [ ] Monitoring configured

## Support

- **Railway Dashboard**: https://railway.app/dashboard
- **Railway Docs**: https://docs.railway.app
- **API Documentation**: https://your-app.railway.app/docs
- **Logs**: `railway logs --follow`

---

**Ready to deploy?** Run: `python deploy_railway.py`
