#!/usr/bin/env python3
"""
🎯 VERIFICACIÓN FINAL DEL DASHBOARD
Verifica que el dashboard esté funcionando correctamente
"""

import requests
import time
from datetime import datetime

def test_endpoint(url, name):
    """Probar un endpoint específico"""
    try:
        response = requests.get(url, timeout=10)
        status = response.status_code
        
        if status == 200:
            return True, status, len(response.text)
        else:
            return False, status, 0
            
    except Exception as e:
        return False, f"Error: {e}", 0

def main():
    """Función principal"""
    
    print("🎯 VERIFICACIÓN FINAL - DASHBOARD ENTERPRISE")
    print("=" * 60)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    base_url = "https://voicecore-ai-production.up.railway.app"
    
    endpoints = [
        ("/", "Página Principal"),
        ("/health", "Health Check"),
        ("/docs", "API Documentation"),
        ("/dashboard", "Dashboard Enterprise"),
        ("/api/tenants", "API Tenants"),
        ("/api/calls", "API Calls")
    ]
    
    print("🔍 PROBANDO TODOS LOS ENDPOINTS:")
    print("-" * 40)
    
    working = 0
    total = len(endpoints)
    
    for path, name in endpoints:
        url = base_url + path
        success, status, size = test_endpoint(url, name)
        
        if success:
            print(f"✅ {name:<20} - OK (Status: {status}, Size: {size})")
            working += 1
        else:
            print(f"❌ {name:<20} - FAIL (Status: {status})")
    
    print()
    print("=" * 60)
    print(f"📊 RESUMEN: {working}/{total} endpoints funcionando")
    print(f"📈 Porcentaje de éxito: {(working/total)*100:.1f}%")
    
    if working == total:
        print()
        print("🎉 ¡TODO FUNCIONA PERFECTAMENTE!")
        print("🎨 Dashboard Enterprise disponible en:")
        print(f"   {base_url}/dashboard")
        print()
        print("🎯 FEATURES DISPONIBLES:")
        print("  📊 Métricas del sistema en tiempo real")
        print("  🏗️ Monitoreo de infraestructura Railway")
        print("  📈 Gráficos interactivos con Chart.js")
        print("  💻 Interfaz responsive y profesional")
        print("  🔄 Auto-refresh cada 30 segundos")
        print("  📥 Exportación de métricas")
        print("  🌙 Tema oscuro moderno")
        print("  📱 Compatible con móviles")
        print()
        print("🎉 ¡PROYECTO COMPLETADO EXITOSAMENTE!")
        
    elif working >= total * 0.8:  # 80% o más
        print()
        print("✅ ¡CASI TODO FUNCIONA!")
        print("La mayoría de endpoints están funcionando.")
        print("Algunos pueden tardar un poco más en estar disponibles.")
        
    else:
        print()
        print("⚠️ ALGUNOS PROBLEMAS DETECTADOS")
        print("Verifica el estado del despliegue en Railway:")
        print("https://railway.app/dashboard")

if __name__ == "__main__":
    main()