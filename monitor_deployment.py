#!/usr/bin/env python3
"""
Monitor Railway Deployment Progress
Verifica cuando el nuevo código está desplegado
"""

import requests
import time
import json
from datetime import datetime

def check_deployment():
    """Verificar si el nuevo código está desplegado"""
    url = "https://voicecore-ai-production.up.railway.app"
    
    print("🔍 Monitoreando despliegue de VoiceCore AI 3.0 Enterprise...")
    print("=" * 60)
    
    # Verificar health endpoint
    try:
        response = requests.get(f"{url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Check: OK")
            print(f"   Servicio: {data.get('service', 'N/A')}")
            print(f"   Versión: {data.get('version', 'N/A')}")
            print(f"   Estado: {data.get('status', 'N/A')}")
        else:
            print(f"❌ Health Check: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check: {e}")
        return False
    
    # Verificar Event Sourcing endpoint (nuevo en 3.0)
    try:
        response = requests.get(f"{url}/api/v1/events/statistics", timeout=10)
        if response.status_code == 200:
            print(f"✅ Event Sourcing API: DESPLEGADO")
            data = response.json()
            print(f"   Total eventos: {data.get('total_events', 0)}")
            print(f"   Tipos de eventos: {data.get('event_types', 0)}")
            return True
        else:
            print(f"⏳ Event Sourcing API: Aún no disponible (esperando redespliegue)")
            return False
    except Exception as e:
        print(f"⏳ Event Sourcing API: Aún no disponible")
        return False

def main():
    """Función principal"""
    max_attempts = 30  # 5 minutos (30 intentos x 10 segundos)
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n[{timestamp}] Intento {attempt}/{max_attempts}")
        
        if check_deployment():
            print("\n" + "=" * 60)
            print("🎉 ¡DESPLIEGUE COMPLETADO!")
            print("=" * 60)
            print("\n🔗 Tu aplicación VoiceCore AI 3.0 Enterprise está lista:")
            print(f"   • Página principal: https://voicecore-ai-production.up.railway.app")
            print(f"   • Dashboard: https://voicecore-ai-production.up.railway.app/dashboard")
            print(f"   • API Docs: https://voicecore-ai-production.up.railway.app/docs")
            print(f"   • Event Sourcing: https://voicecore-ai-production.up.railway.app/api/v1/events/statistics")
            print("\n✨ Nuevas funcionalidades disponibles:")
            print("   • Event Sourcing & CQRS")
            print("   • 50+ tipos de eventos inmutables")
            print("   • Replay de eventos")
            print("   • Snapshots para performance")
            print("   • Blockchain audit trail")
            print("   • Kafka event bus ready")
            print("   • Istio service mesh ready")
            print("   • Vault secrets management ready")
            return True
        
        if attempt < max_attempts:
            print(f"\n⏳ Esperando 10 segundos antes del próximo intento...")
            time.sleep(10)
    
    print("\n" + "=" * 60)
    print("⚠️ TIMEOUT: El despliegue está tomando más tiempo del esperado")
    print("=" * 60)
    print("\n🔧 Posibles acciones:")
    print("1. Verifica el dashboard de Railway: https://railway.app/dashboard")
    print("2. Revisa los logs de despliegue en Railway")
    print("3. Espera unos minutos más y ejecuta este script de nuevo")
    print("4. Verifica que no haya errores en el build")
    return False

if __name__ == "__main__":
    main()
