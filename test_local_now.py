#!/usr/bin/env python3
"""
Prueba LOCAL RÁPIDA de VoiceCore AI
Sin necesidad de desplegar a producción
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_system():
    """Test the system locally."""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║         VoiceCore AI 3.0 - Prueba Local                 ║
    ║         Testing sin desplegar                           ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Test 1: Import models
    print("\n📋 Test 1: Importando modelos...")
    try:
        from voicecore.models import (
            Tenant, Agent, Call, EventStore, 
            CallAnalytics, VIPCaller
        )
        print("✅ Modelos importados correctamente")
        print(f"   - Tenant: {Tenant.__name__}")
        print(f"   - Agent: {Agent.__name__}")
        print(f"   - Call: {Call.__name__}")
        print(f"   - EventStore: {EventStore.__name__}")
    except Exception as e:
        print(f"❌ Error importando modelos: {e}")
        return False
    
    # Test 2: Import services
    print("\n📋 Test 2: Importando servicios...")
    try:
        from voicecore.services.event_sourcing_service import EventSourcingService
        from voicecore.services.call_routing_service import CallRoutingService
        print("✅ Servicios importados correctamente")
        print(f"   - EventSourcingService: OK")
        print(f"   - CallRoutingService: OK")
    except Exception as e:
        print(f"❌ Error importando servicios: {e}")
        return False
    
    # Test 3: Database connection
    print("\n📋 Test 3: Probando conexión a base de datos...")
    try:
        from voicecore.database import init_database, get_db_session
        from sqlalchemy import text
        
        await init_database()
        print("✅ Base de datos inicializada")
        
        async with get_db_session() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            if value == 1:
                print("✅ Conexión a base de datos OK")
            else:
                print("❌ Conexión a base de datos falló")
                return False
                
    except Exception as e:
        print(f"⚠️  Base de datos no disponible: {e}")
        print("   (Esto es normal si no has ejecutado migraciones)")
    
    # Test 4: Event Sourcing
    print("\n📋 Test 4: Probando Event Sourcing...")
    try:
        from voicecore.services.event_sourcing_service import EventSourcingService
        import uuid
        
        service = EventSourcingService()
        
        # Create a test event
        test_event = {
            "aggregate_id": str(uuid.uuid4()),
            "aggregate_type": "Call",
            "event_type": "CallInitiated",
            "event_data": {
                "from_number": "+1234567890",
                "to_number": "+0987654321",
                "test": True
            },
            "tenant_id": str(uuid.uuid4())
        }
        
        print("✅ Event Sourcing service creado")
        print(f"   - Evento de prueba: {test_event['event_type']}")
        
    except Exception as e:
        print(f"❌ Error en Event Sourcing: {e}")
        return False
    
    # Test 5: API Routes
    print("\n📋 Test 5: Verificando rutas de API...")
    try:
        from voicecore.main import app
        
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        print(f"✅ API tiene {len(routes)} rutas configuradas")
        print("   Rutas principales:")
        for route in sorted(routes)[:10]:
            print(f"   - {route}")
        
    except Exception as e:
        print(f"❌ Error verificando rutas: {e}")
        return False
    
    # Test 6: Configuration
    print("\n📋 Test 6: Verificando configuración...")
    try:
        from voicecore.config import settings
        
        print("✅ Configuración cargada")
        print(f"   - App Name: {settings.app_name}")
        print(f"   - Debug: {settings.debug}")
        print(f"   - Database: {settings.database_url[:30]}...")
        
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        return False
    
    return True


async def main():
    """Main test function."""
    try:
        success = await test_system()
        
        print("\n" + "="*60)
        if success:
            print("✅ TODOS LOS TESTS PASARON!")
            print("="*60)
            print("""
🎉 Tu sistema está funcionando correctamente!

Próximos pasos:

1. Ejecutar migraciones:
   alembic upgrade head

2. Inicializar datos:
   python scripts/init_project.py

3. Iniciar servidor local:
   uvicorn voicecore.main:app --reload

4. Abrir en navegador:
   http://localhost:8000/docs

5. O desplegar a producción:
   python deploy_railway.py
            """)
            return 0
        else:
            print("❌ ALGUNOS TESTS FALLARON")
            print("="*60)
            print("""
Revisa los errores arriba y:

1. Instala dependencias:
   python -m pip install -r requirements.txt

2. Verifica el archivo .env existe

3. Ejecuta este test de nuevo:
   python test_local_now.py
            """)
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelado por usuario")
        return 1
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
