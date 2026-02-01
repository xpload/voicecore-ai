#!/usr/bin/env python3
"""
🧪 TESTER DE APLICACIÓN LIVE - VoiceCore AI
Verifica que todos los endpoints estén funcionando
"""

import requests
import json
from datetime import datetime

def test_endpoint(url, endpoint, description):
    """Probar un endpoint específico"""
    full_url = f"{url}{endpoint}"
    try:
        print(f"🔍 Probando: {description}")
        print(f"   URL: {full_url}")
        
        response = requests.get(full_url, timeout=10)
        
        if response.status_code == 200:
            print(f"   ✅ FUNCIONA - Status: {response.status_code}")
            
            # Intentar parsear JSON si es posible
            try:
                data = response.json()
                if isinstance(data, dict):
                    if 'status' in data:
                        print(f"   📊 Estado: {data['status']}")
                    if 'service' in data:
                        print(f"   🏷️ Servicio: {data['service']}")
                    if 'version' in data:
                        print(f"   🔢 Versión: {data['version']}")
            except:
                # Es HTML, mostrar longitud
                print(f"   📄 Contenido HTML: {len(response.text)} caracteres")
                
        else:
            print(f"   ❌ ERROR - Status: {response.status_code}")
            
        print()
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ ERROR DE CONEXIÓN: {e}")
        print()
        return False

def main():
    """Función principal de testing"""
    
    base_url = "https://voicecore-ai-production.up.railway.app"
    
    print("🧪 TESTING VOICECORE AI - APLICACIÓN LIVE")
    print("=" * 60)
    print(f"🎯 URL Base: {base_url}")
    print(f"🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # Lista de endpoints para probar
    endpoints = [
        ("/", "Página Principal"),
        ("/health", "Estado del Sistema"),
        ("/docs", "Documentación API"),
        ("/dashboard", "Dashboard de Monitoreo"),
        ("/system/status", "API de Estado del Sistema"),
        ("/system/railway/url", "URL de Railway"),
        ("/api/tenants", "API de Tenants"),
        ("/api/calls", "API de Llamadas")
    ]
    
    results = []
    
    # Probar cada endpoint
    for endpoint, description in endpoints:
        success = test_endpoint(base_url, endpoint, description)
        results.append((endpoint, description, success))
    
    # Resumen de resultados
    print("=" * 60)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 60)
    
    working = sum(1 for _, _, success in results if success)
    total = len(results)
    
    print(f"✅ Funcionando: {working}/{total} endpoints")
    print(f"📈 Porcentaje de éxito: {(working/total)*100:.1f}%")
    print()
    
    print("📋 DETALLE:")
    for endpoint, description, success in results:
        status = "✅ OK" if success else "❌ FALLO"
        print(f"   {status} {endpoint} - {description}")
    
    print()
    
    if working >= total * 0.8:  # 80% o más funcionando
        print("🎉 ¡APLICACIÓN FUNCIONANDO CORRECTAMENTE!")
        print()
        print("🔗 ENLACES DIRECTOS:")
        print(f"   • Página Principal: {base_url}")
        print(f"   • Dashboard Monitoreo: {base_url}/dashboard")
        print(f"   • Documentación API: {base_url}/docs")
        print(f"   • Estado del Sistema: {base_url}/health")
        print()
        print("🚀 ¡Tu recepcionista virtual con IA está ONLINE!")
        
    else:
        print("⚠️ ALGUNOS ENDPOINTS NO FUNCIONAN")
        print("   Esto puede ser normal si no has actualizado con el dashboard")
        print("   La aplicación básica debería funcionar correctamente")
    
    print()
    print("🎯 PRÓXIMOS PASOS:")
    print("1. Visita la página principal para ver la interfaz")
    print("2. Prueba el dashboard de monitoreo")
    print("3. Revisa la documentación de la API")
    print("4. Configura Twilio y OpenAI para funcionalidad completa")

if __name__ == "__main__":
    main()