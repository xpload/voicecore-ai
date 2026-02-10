#!/usr/bin/env python3
"""
VoiceCore AI 2.0 - Startup Script
Comprehensive startup script for the entire VoiceCore AI 2.0 platform
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def print_banner():
    """Print VoiceCore AI 2.0 banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║              🚀 VoiceCore AI 2.0 🚀                         ║
    ║                                                              ║
    ║     Next-Generation Enterprise Virtual Receptionist         ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_docker():
    """Check if Docker is installed and running"""
    print("🔍 Checking Docker installation...")
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ Docker found: {result.stdout.strip()}")
        
        # Check if Docker daemon is running
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Docker daemon is running")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker is not installed or not running")
        print("   Please install Docker: https://docs.docker.com/get-docker/")
        return False

def check_docker_compose():
    """Check if Docker Compose is installed"""
    print("🔍 Checking Docker Compose installation...")
    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ Docker Compose found: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker Compose is not installed")
        print("   Please install Docker Compose: https://docs.docker.com/compose/install/")
        return False

def check_env_file():
    """Check if .env file exists"""
    print("🔍 Checking environment configuration...")
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
        return True
    else:
        print("⚠️  .env file not found")
        print("   Creating .env from .env.example...")
        
        example_file = Path(".env.example")
        if example_file.exists():
            with open(example_file, 'r') as src:
                content = src.read()
            with open(env_file, 'w') as dst:
                dst.write(content)
            print("✅ .env file created")
            print("⚠️  Please edit .env with your configuration before continuing")
            return False
        else:
            print("❌ .env.example not found")
            return False

def start_services():
    """Start all VoiceCore AI 2.0 services"""
    print("\n🚀 Starting VoiceCore AI 2.0 services...")
    print("   This may take a few minutes on first run...\n")
    
    try:
        # Start services with docker-compose
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.microservices.yml", "up", "-d"],
            check=True
        )
        print("\n✅ All services started successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting services: {e}")
        return False

def wait_for_services():
    """Wait for services to be healthy"""
    print("\n⏳ Waiting for services to be ready...")
    print("   This may take 30-60 seconds...\n")
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ Services are ready!")
                return True
        except:
            pass
        
        attempt += 1
        time.sleep(2)
        print(f"   Attempt {attempt}/{max_attempts}...", end='\r')
    
    print("\n⚠️  Services are taking longer than expected to start")
    print("   You can check the logs with: docker-compose -f docker-compose.microservices.yml logs -f")
    return False

def show_service_urls():
    """Display service URLs"""
    print("\n" + "="*70)
    print("🌐 VoiceCore AI 2.0 - Service URLs")
    print("="*70)
    print("\n📱 Frontend:")
    print("   http://localhost:3000")
    print("\n🔌 API Gateway:")
    print("   http://localhost:8000")
    print("   http://localhost:8000/docs (API Documentation)")
    print("\n🏢 Microservices:")
    print("   Tenant Service:      http://localhost:8001")
    print("   Call Service:        http://localhost:8002")
    print("   AI Service:          http://localhost:8003")
    print("   CRM Service:         http://localhost:8004")
    print("   Analytics Service:   http://localhost:8005")
    print("   Integration Service: http://localhost:8006")
    print("   Billing Service:     http://localhost:8007")
    print("\n💾 Infrastructure:")
    print("   PostgreSQL:          localhost:5432")
    print("   Redis:               localhost:6379")
    print("\n" + "="*70)

def show_next_steps():
    """Display next steps"""
    print("\n📋 Next Steps:")
    print("   1. Open http://localhost:3000 in your browser")
    print("   2. Explore the API documentation at http://localhost:8000/docs")
    print("   3. Check service health at http://localhost:8000/health")
    print("\n🔧 Useful Commands:")
    print("   View logs:    docker-compose -f docker-compose.microservices.yml logs -f")
    print("   Stop services: docker-compose -f docker-compose.microservices.yml down")
    print("   Restart:      docker-compose -f docker-compose.microservices.yml restart")
    print("\n📚 Documentation:")
    print("   README:       README_V2.md")
    print("   Spec:         .kiro/specs/voicecore-ai-2.0/")
    print()

def main():
    """Main startup function"""
    print_banner()
    
    # Pre-flight checks
    if not check_docker():
        sys.exit(1)
    
    if not check_docker_compose():
        sys.exit(1)
    
    if not check_env_file():
        print("\n⚠️  Please configure your .env file and run this script again")
        sys.exit(1)
    
    # Start services
    if not start_services():
        sys.exit(1)
    
    # Wait for services to be ready
    wait_for_services()
    
    # Show information
    show_service_urls()
    show_next_steps()
    
    print("✨ VoiceCore AI 2.0 is ready! ✨\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Startup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
