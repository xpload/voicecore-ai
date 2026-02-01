#!/usr/bin/env python3
"""
🔍 DETECTOR AUTOMÁTICO DE RAILWAY URL
Busca tu aplicación VoiceCore AI en todas las URLs posibles
"""

import requests
import json
import time
from datetime import datetime
import concurrent.futures
import threading

class RailwayURLDetector:
    def __init__(self):
        self.found_urls = []
        self.lock = threading.Lock()
        
    def generate_possible_urls(self):
        """Generar todas las URLs posibles de Railway"""
        base_patterns = [
            "voicecore-ai",
            "voicecore-ai-production", 
            "voicecore-ai-main",
            "voicecore-ai-web",
            "voicecore-ai-app",
            "voicecore",
            "voicecore-production",
            "voicecore-main"
        ]
        
        # Generar variaciones con números y sufijos comunes
        urls = []
        for pattern in base_patterns:
            # URLs básicas
            urls.append(f"https://{pattern}.railway.app")
            
            # Con sufijos numéricos
            for i in range(1000, 9999, 111):
                urls.append(f"https://{pattern}-{i}.railway.app")
                urls.append(f"https://{pattern}-production-{i}.railway.app")
            
            # Con sufijos de Railway comunes
            suffixes = ["web", "api", "server", "backend", "frontend"]
            for suffix in suffixes:
                urls.append(f"https://{pattern}-{suffix}.railway.app")
                for i in range(1000, 5000, 200):
                    urls.append(f"https://{pattern}-{suffix}-{i}.railway.app")
        
        return urls[:100]  # Limitar a 100 URLs para no sobrecargar
    
    def check_url(self, url):
        """Verificar si una URL es válida y contiene VoiceCore AI"""
        try:
            print(f"🔍 Probando: {url}")
            
            # Verificar endpoint de salud
            response = requests.get(f"{url}/health", timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "VoiceCore AI" in str(data) or "voicecore" in str(data).lower():
                        with self.lock:
                            self.found_urls.append({
                                "url": url,
                                "status": "✅ ENCONTRADA",
                                "health_data": data,
                                "response_time": response.elapsed.total_seconds()
                            })
                        print(f"🎉 ¡ENCONTRADA! {url}")
                        return True
                except:
                    pass
            
            # Verificar página principal
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                content = response.text.lower()
                if "voicecore" in content or "recepcionista virtual" in content:
                    with self.lock:
                        self.found_urls.append({
                            "url": url,
                            "status": "✅ ENCONTRADA (página principal)",
                            "response_time": response.elapsed.total_seconds()
                        })
                    print(f"🎉 ¡ENCONTRADA! {url}")
                    return True
                    
        except requests.exceptions.RequestException:
            pass
        except Exception as e:
            pass
        
        return False
    
    def search_parallel(self):
        """Buscar URLs en paralelo para mayor velocidad"""
        urls = self.generate_possible_urls()
        
        print(f"🚀 Iniciando búsqueda en {len(urls)} URLs posibles...")
        print("=" * 60)
        
        # Usar ThreadPoolExecutor para búsqueda paralela
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.check_url, url) for url in urls]
            
            # Esperar a que terminen todas las búsquedas
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    pass
        
        return self.found_urls
    
    def display_results(self):
        """Mostrar resultados de la búsqueda"""
        print("\n" + "=" * 60)
        print("🎯 RESULTADOS DE LA BÚSQUEDA")
        print("=" * 60)
        
        if self.found_urls:
            print(f"🎉 ¡ENCONTRÉ {len(self.found_urls)} APLICACIÓN(ES)!")
            print()
            
            for i, result in enumerate(self.found_urls, 1):
                print(f"📍 APLICACIÓN {i}:")
                print(f"   🔗 URL: {result['url']}")
                print(f"   ✅ Estado: {result['status']}")
                print(f"   ⚡ Tiempo de respuesta: {result['response_time']:.2f}s")
                
                if 'health_data' in result:
                    health = result['health_data']
                    print(f"   📊 Servicio: {health.get('service', 'N/A')}")
                    print(f"   🏷️ Versión: {health.get('version', 'N/A')}")
                
                print(f"   🎯 Dashboard: {result['url']}/dashboard")
                print(f"   📚 Docs: {result['url']}/docs")
                print()
            
            # Mostrar la URL principal
            main_url = self.found_urls[0]['url']
            print("🚀 TU APLICACIÓN VOICECORE AI ESTÁ EN:")
            print(f"   {main_url}")
            print()
            print("🎯 ENLACES DIRECTOS:")
            print(f"   • Página principal: {main_url}")
            print(f"   • Dashboard monitoreo: {main_url}/dashboard")
            print(f"   • Documentación API: {main_url}/docs")
            print(f"   • Estado del sistema: {main_url}/health")
            
        else:
            print("❌ No se encontró ninguna aplicación VoiceCore AI")
            print()
            print("🔧 POSIBLES SOLUCIONES:")
            print("1. Verifica que hayas subido el código a GitHub")
            print("2. Revisa que Railway esté conectado a tu repositorio")
            print("3. Espera unos minutos más para el despliegue")
            print("4. Revisa el dashboard de Railway para errores")

def main():
    """Función principal"""
    print("🔍 VoiceCore AI - DETECTOR AUTOMÁTICO DE RAILWAY")
    print("=" * 60)
    print("Buscando tu aplicación en todas las URLs posibles...")
    print()
    
    detector = RailwayURLDetector()
    
    # Realizar búsqueda
    start_time = time.time()
    results = detector.search_parallel()
    end_time = time.time()
    
    # Mostrar resultados
    detector.display_results()
    
    print(f"\n⏱️ Búsqueda completada en {end_time - start_time:.1f} segundos")
    
    if results:
        print("\n🎉 ¡LISTO! Ya tienes la URL de tu aplicación VoiceCore AI")
    else:
        print("\n🔄 Si no encontré nada, espera unos minutos y ejecuta de nuevo")

if __name__ == "__main__":
    main()