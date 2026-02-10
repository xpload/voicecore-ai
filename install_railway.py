#!/usr/bin/env python3
"""
Install Railway CLI for Windows
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path


def download_railway_cli():
    """Download Railway CLI for Windows."""
    print("🚀 Descargando Railway CLI para Windows...")
    
    # Railway CLI download URL for Windows
    url = "https://github.com/railwayapp/cli/releases/latest/download/railway_windows_amd64.zip"
    
    # Download to temp directory
    zip_path = "railway_cli.zip"
    
    try:
        print(f"📥 Descargando desde: {url}")
        urllib.request.urlretrieve(url, zip_path)
        print("✅ Descarga completada")
        
        # Extract
        print("📦 Extrayendo archivos...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("railway_cli")
        
        # Move to a location in PATH
        exe_path = Path("railway_cli/railway.exe")
        if exe_path.exists():
            # Try to move to user's local bin
            local_bin = Path.home() / "AppData" / "Local" / "Microsoft" / "WindowsApps"
            if not local_bin.exists():
                local_bin = Path.home() / ".local" / "bin"
                local_bin.mkdir(parents=True, exist_ok=True)
            
            dest = local_bin / "railway.exe"
            shutil.copy(str(exe_path), str(dest))
            
            print(f"✅ Railway CLI instalado en: {dest}")
            print("\n⚠️  IMPORTANTE:")
            print(f"   Agrega esta ruta a tu PATH: {local_bin}")
            print("\n   O ejecuta Railway desde aquí:")
            print(f"   {dest} --version")
            
            # Cleanup
            os.remove(zip_path)
            shutil.rmtree("railway_cli")
            
            return True
        else:
            print("❌ No se encontró railway.exe en el archivo descargado")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║         Railway CLI Installer for Windows               ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    if download_railway_cli():
        print("""
        
✅ Instalación completada!

Próximos pasos:
1. Cierra y abre una nueva terminal
2. Verifica la instalación: railway --version
3. Si no funciona, ejecuta desde la ruta completa
4. Luego ejecuta: python deploy_railway.py

        """)
    else:
        print("""
        
❌ Instalación falló

Alternativa manual:
1. Ve a: https://railway.app/
2. Crea una cuenta
3. Usa el dashboard web para desplegar

O instala Node.js primero:
1. Descarga: https://nodejs.org/
2. Instala Node.js
3. Ejecuta: npm install -g @railway/cli

        """)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Instalación cancelada")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
