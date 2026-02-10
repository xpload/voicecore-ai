#!/usr/bin/env python3
"""
VoiceCore AI - Railway Deployment Script
Quick deployment to Railway with PostgreSQL
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd: str, description: str, check=True):
    """Run a shell command with nice output."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}\n")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    if check and result.returncode != 0:
        print(f"\n❌ Failed: {description}")
        sys.exit(1)
    
    print(f"✅ Success: {description}")
    return result


def check_railway_cli():
    """Check if Railway CLI is installed."""
    result = subprocess.run("railway --version", shell=True, capture_output=True)
    return result.returncode == 0


def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║         VoiceCore AI - Railway Deployment               ║
    ║         Production-Ready in 10 Minutes                  ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Check Railway CLI
    print("\n📋 Step 1: Checking Railway CLI...")
    if not check_railway_cli():
        print("""
        ❌ Railway CLI not found!
        
        Install it with:
        npm install -g @railway/cli
        
        Or on Windows with PowerShell:
        iwr https://railway.app/install.ps1 | iex
        """)
        sys.exit(1)
    print("✅ Railway CLI is installed")
    
    # Step 2: Check if logged in
    print("\n📋 Step 2: Checking Railway login...")
    result = subprocess.run("railway whoami", shell=True, capture_output=True)
    if result.returncode != 0:
        print("\n🔐 Please login to Railway...")
        run_command("railway login", "Login to Railway")
    else:
        print("✅ Already logged in to Railway")
    
    # Step 3: Check if project exists
    print("\n📋 Step 3: Checking Railway project...")
    result = subprocess.run("railway status", shell=True, capture_output=True)
    if result.returncode != 0:
        print("\n🆕 Creating new Railway project...")
        run_command("railway init", "Initialize Railway project")
    else:
        print("✅ Railway project exists")
    
    # Step 4: Add PostgreSQL
    print("\n📋 Step 4: Setting up PostgreSQL...")
    print("""
    ⚠️  MANUAL STEP REQUIRED:
    
    1. Go to: https://railway.app/dashboard
    2. Select your project
    3. Click "+ New" button
    4. Select "Database" > "PostgreSQL"
    5. Wait for it to provision (1-2 minutes)
    6. Press Enter when done...
    """)
    input("Press Enter after adding PostgreSQL...")
    
    # Step 5: Set environment variables
    print("\n📋 Step 5: Setting environment variables...")
    print("""
    ⚠️  MANUAL STEP REQUIRED:
    
    Set these variables in Railway Dashboard:
    
    1. Go to: https://railway.app/dashboard
    2. Select your project > Variables tab
    3. Add these variables:
    
    Required:
    - SECRET_KEY=your-secret-key-min-32-chars
    - JWT_SECRET_KEY=your-jwt-secret-key
    
    Optional (for full functionality):
    - TWILIO_ACCOUNT_SID=ACxxxxx
    - TWILIO_AUTH_TOKEN=xxxxx
    - TWILIO_PHONE_NUMBER=+1234567890
    - OPENAI_API_KEY=sk-proj-xxxxx
    
    Note: DATABASE_URL is automatically set by Railway
    
    Press Enter when done...
    """)
    input("Press Enter after setting variables...")
    
    # Step 6: Deploy
    print("\n📋 Step 6: Deploying to Railway...")
    run_command("railway up", "Deploy application")
    
    # Step 7: Run migrations
    print("\n📋 Step 7: Running database migrations...")
    run_command("railway run alembic upgrade head", "Run migrations")
    
    # Step 8: Initialize project
    print("\n📋 Step 8: Initializing project data...")
    run_command("railway run python scripts/init_project.py", "Initialize project")
    
    # Step 9: Get URL
    print("\n📋 Step 9: Getting production URL...")
    result = run_command("railway domain", "Get production URL", check=False)
    
    print("""
    
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║              🎉 DEPLOYMENT SUCCESSFUL! 🎉                ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    
    📊 Next Steps:
    
    1. View logs:
       railway logs --follow
    
    2. Check status:
       railway status
    
    3. Open dashboard:
       railway open
    
    4. Get your URL:
       railway domain
    
    5. Test your API:
       curl https://your-app.railway.app/health
    
    6. Configure Twilio webhooks (if using Twilio):
       - Voice: https://your-app.railway.app/api/v1/webhooks/twilio/voice
       - SMS: https://your-app.railway.app/api/v1/webhooks/twilio/sms
    
    7. Make a test call to your Twilio number!
    
    📚 Documentation:
    - Railway Dashboard: https://railway.app/dashboard
    - API Docs: https://your-app.railway.app/docs
    - Monitoring: railway logs --follow
    
    🆘 Troubleshooting:
    - View logs: railway logs
    - Restart: railway restart
    - Connect to DB: railway connect postgres
    - Check variables: railway variables
    
    """)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Deployment failed: {e}")
        sys.exit(1)
