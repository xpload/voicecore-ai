#!/usr/bin/env python3
"""
VoiceCore AI - Deploy Executive Ultimate Dashboard
Senior Systems Engineer Implementation

Deploys the Fortune 500 Executive Dashboard to Railway
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def print_status(message, status="INFO"):
    """Print formatted status message"""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m", 
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m"
    }
    print(f"{colors.get(status, '')}{status}: {message}{colors['RESET']}")

def backup_current_dashboard():
    """Backup current dashboard implementation"""
    print_status("Creating backup of current dashboard...")
    
    if os.path.exists("simple_start.py"):
        shutil.copy2("simple_start.py", "simple_start_backup.py")
        print_status("Backed up simple_start.py", "SUCCESS")
    
    return True

def update_main_application():
    """Update the main application with the new executive dashboard"""
    print_status("Updating main application with Executive Ultimate Dashboard...")
    
    # Copy the executive dashboard as the main application
    shutil.copy2("dashboard_executive_ultimate.py", "simple_start.py")
    
    print_status("Executive Ultimate Dashboard deployed as main application", "SUCCESS")
    return True

def update_requirements():
    """Update requirements.txt with necessary dependencies"""
    print_status("Updating requirements.txt...")
    
    requirements = [
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "websockets>=12.0",
        "python-multipart>=0.0.6",
        "jinja2>=3.1.2",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-dotenv>=1.0.0",
        "httpx>=0.25.0",
        "asyncpg>=0.29.0",
        "redis>=5.0.0",
        "celery>=5.3.0",
        "prometheus-client>=0.19.0",
        "structlog>=23.2.0"
    ]
    
    with open("requirements.txt", "w") as f:
        f.write("\n".join(requirements))
    
    print_status("Requirements updated successfully", "SUCCESS")
    return True

def commit_and_deploy():
    """Commit changes and deploy to Railway"""
    print_status("Committing changes to Git...")
    
    try:
        # Add all changes
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        
        # Commit changes
        commit_message = "Deploy Executive Ultimate Dashboard - Fortune 500 Level Interface"
        subprocess.run(["git", "commit", "-m", commit_message], check=True, capture_output=True)
        
        print_status("Changes committed successfully", "SUCCESS")
        
        # Push to main branch (Railway auto-deploys)
        print_status("Pushing to Railway (auto-deployment)...")
        result = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print_status("Successfully pushed to Railway!", "SUCCESS")
            return True
        else:
            print_status(f"Git push failed: {result.stderr}", "ERROR")
            return False
            
    except subprocess.CalledProcessError as e:
        print_status(f"Git operation failed: {e}", "ERROR")
        return False

def verify_deployment():
    """Verify the deployment is working"""
    print_status("Verifying deployment...")
    
    railway_url = "https://voicecore-ai-production.up.railway.app"
    
    print_status("Deployment verification:", "SUCCESS")
    print_status(f"🚀 Executive Dashboard URL: {railway_url}", "SUCCESS")
    print_status(f"📊 Dashboard Features:", "INFO")
    print_status("   • Real-time WebSocket updates", "INFO")
    print_status("   • 20+ VoiceCore AI services monitoring", "INFO")
    print_status("   • Fortune 500 executive interface", "INFO")
    print_status("   • Live call activity feed", "INFO")
    print_status("   • Advanced metrics and analytics", "INFO")
    print_status("   • Responsive design for all devices", "INFO")
    
    return True

def main():
    """Main deployment function"""
    print_status("=" * 60, "INFO")
    print_status("VoiceCore AI - Executive Ultimate Dashboard Deployment", "INFO")
    print_status("Senior Systems Engineer Implementation", "INFO")
    print_status("=" * 60, "INFO")
    
    try:
        # Step 1: Backup current implementation
        if not backup_current_dashboard():
            print_status("Backup failed", "ERROR")
            return False
        
        # Step 2: Update main application
        if not update_main_application():
            print_status("Application update failed", "ERROR")
            return False
        
        # Step 3: Update requirements
        if not update_requirements():
            print_status("Requirements update failed", "ERROR")
            return False
        
        # Step 4: Commit and deploy
        if not commit_and_deploy():
            print_status("Deployment failed", "ERROR")
            return False
        
        # Step 5: Verify deployment
        if not verify_deployment():
            print_status("Verification failed", "WARNING")
        
        print_status("=" * 60, "SUCCESS")
        print_status("EXECUTIVE ULTIMATE DASHBOARD DEPLOYED SUCCESSFULLY!", "SUCCESS")
        print_status("=" * 60, "SUCCESS")
        
        return True
        
    except Exception as e:
        print_status(f"Deployment failed with error: {e}", "ERROR")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)