#!/usr/bin/env python3
"""
Script para arrancar VoiceCore AI 3.0 localmente
"""

import uvicorn
import sys
import os

# Asegurarse de que estamos usando el .env correcto
os.environ.setdefault("ENV_FILE", ".env")

if __name__ == "__main__":
    print("🚀 Arrancando VoiceCore AI 3.0 Enterprise - Local Development")
    print("=" * 60)
    print("📍 URL: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("💚 Health: http://localhost:8000/health")
    print("📊 Event Sourcing: http://localhost:8000/api/v1/events/statistics")
    print("=" * 60)
    print()
    
    try:
        uvicorn.run(
            "voicecore.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 VoiceCore AI detenido")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error al arrancar: {e}")
        sys.exit(1)
