#!/usr/bin/env python3
"""
👀 MONITOREAR DESPLIEGUE DEL DASHBOARD
Verifica cada minuto si el dashboard ya está disponible
"""

import requests
import time
from datetime import datetime

def check_dashboard():
    """Verificar si el dashboard está disponible"""
    url = "https://voicecore-ai-production.up.railway.app/dashboard"
    
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200, response.status_code
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """Función principal"""
    
    print("👀 MONITOREO DEL DESPLIEGUE - DASHBOARD ENTERPRISE")
    print("=" * 60)
    print(f"🕐 Iniciado: {datetime.now().strftime('%H:%M:%S')}")
    print("🎯 URL: https://voicecore-ai-production.up.railway.app/dashboard")
    print()
    print("⏱️ Verificando cada 30 segundos...")
    print("🛑 Presiona Ctrl+C para detener")
    print()
    
    attempt = 1
    max_attempts = 20  # 10 minutos máximo
    
    while attempt <= max_attempts:
        print(f"🔍 Intento {attempt}/{max_attempts} - {datetime.now().strftime('%H:%M:%S')}")
        
        is_available, status = check_dashboard()
        
        if is_available:
            print("🎉 ¡DASHBOARD DISPONIBLE!")
            print("=" * 40)
            print("✅ El dashboard enterprise está funcionando")
            print("🎨 URL: https://voicecore-ai-production.up.railway.app/dashboard")
            print()
            print("🎯 FEATURES DISPONIBLES:")
            print("  📊 Métricas del sistema en tiempo real")
            print("  🏗️ Monitoreo de infraestructura Railway")
            print("  📈 Gráficos interactivos")
            print("  💻 Interfaz responsive")
            print("  🔄 Auto-refresh cada 30 segundos")
            print("  📥 Exportación de métricas")
            print()
            print("🎉 ¡DESPLIEGUE COMPLETADO EXITOSAMENTE!")
            break
            
        else:
            print(f"   ⏳ Aún no disponible (Status: {status})")
            print("   🔄 Railway sigue desplegando...")
            
        if attempt < max_attempts:
            print("   ⏱️ Esperando 30 segundos...")
            print()
            time.sleep(30)
        
        attempt += 1
    
    else:
        print("⚠️ TIEMPO DE ESPERA AGOTADO")
        print("=" * 30)
        print("El dashboard puede tardar un poco más.")
        print("Verifica manualmente en:")
        print("https://voicecore-ai-production.up.railway.app/dashboard")
        print()
        print("También puedes verificar el progreso en:")
        print("https://railway.app/dashboard")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoreo detenido por el usuario")
        print("Puedes verificar manualmente:")
        print("https://voicecore-ai-production.up.railway.app/dashboard")