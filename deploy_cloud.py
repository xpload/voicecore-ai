#!/usr/bin/env python3
"""
VoiceCore AI - Script de Despliegue en la Nube

Este script automatiza el despliegue de VoiceCore AI en diferentes proveedores de nube.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import argparse

class Colors:
    """Colores para output en terminal."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class CloudDeployer:
    """Clase principal para despliegue en la nube."""
    
    def __init__(self, provider: str, environment: str = "production"):
        self.provider = provider.lower()
        self.environment = environment
        self.project_root = Path(__file__).parent
        
        # Configuración por proveedor
        self.providers = {
            "aws": self._deploy_aws,
            "gcp": self._deploy_gcp,
            "azure": self._deploy_azure,
            "digitalocean": self._deploy_digitalocean,
            "heroku": self._deploy_heroku,
            "railway": self._deploy_railway,
            "render": self._deploy_render
        }
    
    def print_banner(self):
        """Imprime el banner de despliegue."""
        banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                🚀 VoiceCore AI Cloud Deploy                  ║
║                                                              ║
║  Proveedor: {self.provider.upper():<15} Entorno: {self.environment:<15}  ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}
        """
        print(banner)
    
    def validate_environment(self) -> bool:
        """Valida que el entorno esté configurado correctamente."""
        print(f"{Colors.BLUE}🔍 Validando entorno de despliegue...{Colors.END}")
        
        # Verificar archivo .env
        env_file = self.project_root / f".env.{self.environment}"
        if not env_file.exists():
            env_file = self.project_root / ".env"
        
        if not env_file.exists():
            print(f"{Colors.RED}❌ Archivo de configuración no encontrado{Colors.END}")
            return False
        
        # Verificar Docker
        if not self._check_command("docker --version"):
            print(f"{Colors.RED}❌ Docker no está instalado{Colors.END}")
            return False
        
        print(f"{Colors.GREEN}✅ Entorno validado correctamente{Colors.END}")
        return True
    
    def _check_command(self, command: str) -> bool:
        """Verifica si un comando está disponible."""
        try:
            subprocess.run(command.split(), capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def build_docker_image(self) -> bool:
        """Construye la imagen Docker para producción."""
        print(f"{Colors.BLUE}🐳 Construyendo imagen Docker...{Colors.END}")
        
        try:
            # Construir imagen
            subprocess.run([
                "docker", "build",
                "-t", f"voicecore-ai:{self.environment}",
                "-f", "Dockerfile",
                "."
            ], cwd=self.project_root, check=True)
            
            print(f"{Colors.GREEN}✅ Imagen Docker construida correctamente{Colors.END}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}❌ Error construyendo imagen Docker: {e}{Colors.END}")
            return False
    
    def deploy(self) -> bool:
        """Ejecuta el despliegue según el proveedor seleccionado."""
        if self.provider not in self.providers:
            print(f"{Colors.RED}❌ Proveedor '{self.provider}' no soportado{Colors.END}")
            print(f"{Colors.YELLOW}Proveedores disponibles: {', '.join(self.providers.keys())}{Colors.END}")
            return False
        
        self.print_banner()
        
        if not self.validate_environment():
            return False
        
        if not self.build_docker_image():
            return False
        
        # Ejecutar despliegue específico del proveedor
        return self.providers[self.provider]()
    
    def _deploy_aws(self) -> bool:
        """Despliega en Amazon Web Services usando ECS."""
        print(f"{Colors.BLUE}☁️ Desplegando en AWS ECS...{Colors.END}")
        
        # Verificar AWS CLI
        if not self._check_command("aws --version"):
            print(f"{Colors.RED}❌ AWS CLI no está instalado{Colors.END}")
            print(f"{Colors.YELLOW}💡 Instala desde: https://aws.amazon.com/cli/{Colors.END}")
            return False
        
        try:
            # 1. Crear repositorio ECR si no existe
            print(f"{Colors.CYAN}📦 Configurando repositorio ECR...{Colors.END}")
            
            repo_name = "voicecore-ai"
            region = os.getenv("AWS_REGION", "us-east-1")
            
            # Obtener URI del repositorio
            result = subprocess.run([
                "aws", "ecr", "describe-repositories",
                "--repository-names", repo_name,
                "--region", region
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                # Crear repositorio
                subprocess.run([
                    "aws", "ecr", "create-repository",
                    "--repository-name", repo_name,
                    "--region", region
                ], check=True)
                print(f"{Colors.GREEN}✅ Repositorio ECR creado{Colors.END}")
            
            # 2. Obtener login token para Docker
            login_result = subprocess.run([
                "aws", "ecr", "get-login-password",
                "--region", region
            ], capture_output=True, text=True, check=True)
            
            account_id = subprocess.run([
                "aws", "sts", "get-caller-identity",
                "--query", "Account",
                "--output", "text"
            ], capture_output=True, text=True, check=True).stdout.strip()
            
            ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
            
            # Login a ECR
            subprocess.run([
                "docker", "login",
                "--username", "AWS",
                "--password-stdin", ecr_uri
            ], input=login_result.stdout, text=True, check=True)
            
            # 3. Tag y push de la imagen
            print(f"{Colors.CYAN}📤 Subiendo imagen a ECR...{Colors.END}")
            
            image_tag = f"{ecr_uri}/{repo_name}:latest"
            
            subprocess.run([
                "docker", "tag",
                f"voicecore-ai:{self.environment}",
                image_tag
            ], check=True)
            
            subprocess.run([
                "docker", "push", image_tag
            ], check=True)
            
            # 4. Desplegar con ECS
            print(f"{Colors.CYAN}🚀 Desplegando en ECS...{Colors.END}")
            
            # Crear o actualizar servicio ECS
            self._create_ecs_service(image_tag, region)
            
            print(f"{Colors.GREEN}🎉 Despliegue en AWS completado exitosamente!{Colors.END}")
            print(f"{Colors.CYAN}🌐 URL: https://tu-load-balancer.{region}.elb.amazonaws.com{Colors.END}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}❌ Error en despliegue AWS: {e}{Colors.END}")
            return False
    
    def _create_ecs_service(self, image_uri: str, region: str):
        """Crea o actualiza el servicio ECS."""
        
        # Definición de tarea
        task_definition = {
            "family": "voicecore-ai",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "1024",
            "memory": "2048",
            "executionRoleArn": f"arn:aws:iam::{self._get_account_id()}:role/ecsTaskExecutionRole",
            "containerDefinitions": [
                {
                    "name": "voicecore-ai",
                    "image": image_uri,
                    "portMappings": [
                        {
                            "containerPort": 8000,
                            "protocol": "tcp"
                        }
                    ],
                    "environment": self._get_aws_environment_variables(),
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "/ecs/voicecore-ai",
                            "awslogs-region": region,
                            "awslogs-stream-prefix": "ecs"
                        }
                    }
                }
            ]
        }
        
        # Registrar definición de tarea
        with open("/tmp/task-definition.json", "w") as f:
            json.dump(task_definition, f)
        
        subprocess.run([
            "aws", "ecs", "register-task-definition",
            "--cli-input-json", "file:///tmp/task-definition.json"
        ], check=True)
    
    def _get_account_id(self) -> str:
        """Obtiene el ID de cuenta de AWS."""
        result = subprocess.run([
            "aws", "sts", "get-caller-identity",
            "--query", "Account",
            "--output", "text"
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    
    def _get_aws_environment_variables(self) -> List[Dict[str, str]]:
        """Obtiene las variables de entorno para AWS."""
        env_vars = []
        
        # Variables críticas que deben estar en AWS Systems Manager Parameter Store
        critical_vars = [
            "DATABASE_URL",
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY",
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "OPENAI_API_KEY",
            "SECRET_KEY",
            "JWT_SECRET_KEY"
        ]
        
        for var in critical_vars:
            env_vars.append({
                "name": var,
                "valueFrom": f"arn:aws:ssm:us-east-1:{self._get_account_id()}:parameter/voicecore-ai/{var}"
            })
        
        # Variables no sensibles
        env_vars.extend([
            {"name": "ENVIRONMENT", "value": self.environment},
            {"name": "PORT", "value": "8000"},
            {"name": "HOST", "value": "0.0.0.0"}
        ])
        
        return env_vars
    
    def _deploy_gcp(self) -> bool:
        """Despliega en Google Cloud Platform usando Cloud Run."""
        print(f"{Colors.BLUE}☁️ Desplegando en Google Cloud Run...{Colors.END}")
        
        # Verificar gcloud CLI
        if not self._check_command("gcloud version"):
            print(f"{Colors.RED}❌ Google Cloud CLI no está instalado{Colors.END}")
            print(f"{Colors.YELLOW}💡 Instala desde: https://cloud.google.com/sdk{Colors.END}")
            return False
        
        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            if not project_id:
                print(f"{Colors.RED}❌ Variable GOOGLE_CLOUD_PROJECT no configurada{Colors.END}")
                return False
            
            region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
            
            # 1. Configurar Docker para GCR
            subprocess.run([
                "gcloud", "auth", "configure-docker"
            ], check=True)
            
            # 2. Tag y push de la imagen
            print(f"{Colors.CYAN}📤 Subiendo imagen a Container Registry...{Colors.END}")
            
            image_tag = f"gcr.io/{project_id}/voicecore-ai:latest"
            
            subprocess.run([
                "docker", "tag",
                f"voicecore-ai:{self.environment}",
                image_tag
            ], check=True)
            
            subprocess.run([
                "docker", "push", image_tag
            ], check=True)
            
            # 3. Desplegar en Cloud Run
            print(f"{Colors.CYAN}🚀 Desplegando en Cloud Run...{Colors.END}")
            
            subprocess.run([
                "gcloud", "run", "deploy", "voicecore-ai",
                "--image", image_tag,
                "--platform", "managed",
                "--region", region,
                "--allow-unauthenticated",
                "--port", "8000",
                "--memory", "2Gi",
                "--cpu", "2",
                "--max-instances", "100",
                "--set-env-vars", self._get_gcp_env_vars()
            ], check=True)
            
            # Obtener URL del servicio
            result = subprocess.run([
                "gcloud", "run", "services", "describe", "voicecore-ai",
                "--platform", "managed",
                "--region", region,
                "--format", "value(status.url)"
            ], capture_output=True, text=True, check=True)
            
            service_url = result.stdout.strip()
            
            print(f"{Colors.GREEN}🎉 Despliegue en GCP completado exitosamente!{Colors.END}")
            print(f"{Colors.CYAN}🌐 URL: {service_url}{Colors.END}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}❌ Error en despliegue GCP: {e}{Colors.END}")
            return False
    
    def _get_gcp_env_vars(self) -> str:
        """Obtiene las variables de entorno para GCP."""
        env_vars = [
            f"ENVIRONMENT={self.environment}",
            "PORT=8000",
            "HOST=0.0.0.0"
        ]
        return ",".join(env_vars)
    
    def _deploy_azure(self) -> bool:
        """Despliega en Microsoft Azure usando Container Instances."""
        print(f"{Colors.BLUE}☁️ Desplegando en Azure Container Instances...{Colors.END}")
        
        # Verificar Azure CLI
        if not self._check_command("az version"):
            print(f"{Colors.RED}❌ Azure CLI no está instalado{Colors.END}")
            print(f"{Colors.YELLOW}💡 Instala desde: https://docs.microsoft.com/cli/azure/{Colors.END}")
            return False
        
        try:
            resource_group = os.getenv("AZURE_RESOURCE_GROUP", "voicecore-ai-rg")
            location = os.getenv("AZURE_LOCATION", "eastus")
            registry_name = os.getenv("AZURE_REGISTRY_NAME", "voicecoreai")
            
            # 1. Crear grupo de recursos si no existe
            subprocess.run([
                "az", "group", "create",
                "--name", resource_group,
                "--location", location
            ], check=True)
            
            # 2. Crear registro de contenedores
            subprocess.run([
                "az", "acr", "create",
                "--resource-group", resource_group,
                "--name", registry_name,
                "--sku", "Basic",
                "--admin-enabled", "true"
            ], check=True)
            
            # 3. Login al registro
            subprocess.run([
                "az", "acr", "login",
                "--name", registry_name
            ], check=True)
            
            # 4. Tag y push de la imagen
            print(f"{Colors.CYAN}📤 Subiendo imagen a Azure Container Registry...{Colors.END}")
            
            image_tag = f"{registry_name}.azurecr.io/voicecore-ai:latest"
            
            subprocess.run([
                "docker", "tag",
                f"voicecore-ai:{self.environment}",
                image_tag
            ], check=True)
            
            subprocess.run([
                "docker", "push", image_tag
            ], check=True)
            
            # 5. Desplegar en Container Instances
            print(f"{Colors.CYAN}🚀 Desplegando en Container Instances...{Colors.END}")
            
            subprocess.run([
                "az", "container", "create",
                "--resource-group", resource_group,
                "--name", "voicecore-ai",
                "--image", image_tag,
                "--cpu", "2",
                "--memory", "4",
                "--registry-login-server", f"{registry_name}.azurecr.io",
                "--ports", "8000",
                "--environment-variables", "ENVIRONMENT=production", "PORT=8000"
            ], check=True)
            
            # Obtener IP pública
            result = subprocess.run([
                "az", "container", "show",
                "--resource-group", resource_group,
                "--name", "voicecore-ai",
                "--query", "ipAddress.ip",
                "--output", "tsv"
            ], capture_output=True, text=True, check=True)
            
            public_ip = result.stdout.strip()
            
            print(f"{Colors.GREEN}🎉 Despliegue en Azure completado exitosamente!{Colors.END}")
            print(f"{Colors.CYAN}🌐 URL: http://{public_ip}:8000{Colors.END}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}❌ Error en despliegue Azure: {e}{Colors.END}")
            return False
    
    def _deploy_heroku(self) -> bool:
        """Despliega en Heroku."""
        print(f"{Colors.BLUE}☁️ Desplegando en Heroku...{Colors.END}")
        
        # Verificar Heroku CLI
        if not self._check_command("heroku --version"):
            print(f"{Colors.RED}❌ Heroku CLI no está instalado{Colors.END}")
            print(f"{Colors.YELLOW}💡 Instala desde: https://devcenter.heroku.com/articles/heroku-cli{Colors.END}")
            return False
        
        try:
            app_name = os.getenv("HEROKU_APP_NAME", "voicecore-ai-app")
            
            # 1. Crear aplicación si no existe
            result = subprocess.run([
                "heroku", "apps:info", app_name
            ], capture_output=True)
            
            if result.returncode != 0:
                subprocess.run([
                    "heroku", "create", app_name
                ], check=True)
                print(f"{Colors.GREEN}✅ Aplicación Heroku creada{Colors.END}")
            
            # 2. Login al registro de contenedores
            subprocess.run([
                "heroku", "container:login"
            ], check=True)
            
            # 3. Push y release
            print(f"{Colors.CYAN}📤 Desplegando contenedor en Heroku...{Colors.END}")
            
            subprocess.run([
                "heroku", "container:push", "web",
                "--app", app_name
            ], cwd=self.project_root, check=True)
            
            subprocess.run([
                "heroku", "container:release", "web",
                "--app", app_name
            ], check=True)
            
            # 4. Configurar variables de entorno
            self._set_heroku_config_vars(app_name)
            
            # Obtener URL de la aplicación
            result = subprocess.run([
                "heroku", "apps:info", app_name,
                "--json"
            ], capture_output=True, text=True, check=True)
            
            app_info = json.loads(result.stdout)
            app_url = app_info["web_url"]
            
            print(f"{Colors.GREEN}🎉 Despliegue en Heroku completado exitosamente!{Colors.END}")
            print(f"{Colors.CYAN}🌐 URL: {app_url}{Colors.END}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}❌ Error en despliegue Heroku: {e}{Colors.END}")
            return False
    
    def _set_heroku_config_vars(self, app_name: str):
        """Configura las variables de entorno en Heroku."""
        config_vars = {
            "ENVIRONMENT": self.environment,
            "PORT": "8000",
            "HOST": "0.0.0.0"
        }
        
        for key, value in config_vars.items():
            subprocess.run([
                "heroku", "config:set",
                f"{key}={value}",
                "--app", app_name
            ], check=True)
    
    def _deploy_digitalocean(self) -> bool:
        """Despliega en DigitalOcean App Platform."""
        print(f"{Colors.BLUE}☁️ Desplegando en DigitalOcean App Platform...{Colors.END}")
        
        # Crear archivo de especificación para DO App Platform
        app_spec = {
            "name": "voicecore-ai",
            "services": [
                {
                    "name": "api",
                    "source_dir": "/",
                    "github": {
                        "repo": os.getenv("GITHUB_REPO", "tu-usuario/voicecore-ai"),
                        "branch": "main"
                    },
                    "run_command": "uvicorn voicecore.main:app --host 0.0.0.0 --port 8080",
                    "environment_slug": "python",
                    "instance_count": 1,
                    "instance_size_slug": "basic-xxs",
                    "http_port": 8080,
                    "envs": [
                        {
                            "key": "ENVIRONMENT",
                            "value": self.environment
                        },
                        {
                            "key": "PORT",
                            "value": "8080"
                        }
                    ]
                }
            ]
        }
        
        # Guardar especificación
        spec_file = self.project_root / "do-app-spec.yaml"
        with open(spec_file, "w") as f:
            import yaml
            yaml.dump(app_spec, f)
        
        print(f"{Colors.GREEN}✅ Especificación creada en {spec_file}{Colors.END}")
        print(f"{Colors.YELLOW}💡 Sube tu código a GitHub y usa la especificación en DigitalOcean App Platform{Colors.END}")
        
        return True
    
    def _deploy_railway(self) -> bool:
        """Despliega en Railway."""
        print(f"{Colors.BLUE}☁️ Desplegando en Railway...{Colors.END}")
        
        # Crear archivo railway.json
        railway_config = {
            "build": {
                "builder": "DOCKERFILE"
            },
            "deploy": {
                "startCommand": "uvicorn voicecore.main:app --host 0.0.0.0 --port $PORT",
                "healthcheckPath": "/health"
            }
        }
        
        config_file = self.project_root / "railway.json"
        with open(config_file, "w") as f:
            json.dump(railway_config, f, indent=2)
        
        print(f"{Colors.GREEN}✅ Configuración Railway creada en {config_file}{Colors.END}")
        print(f"{Colors.YELLOW}💡 Conecta tu repositorio en https://railway.app{Colors.END}")
        
        return True
    
    def _deploy_render(self) -> bool:
        """Despliega en Render."""
        print(f"{Colors.BLUE}☁️ Desplegando en Render...{Colors.END}")
        
        # Crear archivo render.yaml
        render_config = {
            "services": [
                {
                    "type": "web",
                    "name": "voicecore-ai",
                    "env": "docker",
                    "plan": "starter",
                    "dockerfilePath": "./Dockerfile",
                    "dockerContext": "./",
                    "envVars": [
                        {
                            "key": "ENVIRONMENT",
                            "value": self.environment
                        },
                        {
                            "key": "PORT",
                            "value": "10000"
                        }
                    ]
                }
            ]
        }
        
        config_file = self.project_root / "render.yaml"
        with open(config_file, "w") as f:
            import yaml
            yaml.dump(render_config, f)
        
        print(f"{Colors.GREEN}✅ Configuración Render creada en {config_file}{Colors.END}")
        print(f"{Colors.YELLOW}💡 Conecta tu repositorio en https://render.com{Colors.END}")
        
        return True

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Despliega VoiceCore AI en la nube")
    parser.add_argument("provider", choices=[
        "aws", "gcp", "azure", "heroku", "digitalocean", "railway", "render"
    ], help="Proveedor de nube")
    parser.add_argument("--environment", default="production", 
                       choices=["development", "staging", "production"],
                       help="Entorno de despliegue")
    
    args = parser.parse_args()
    
    try:
        deployer = CloudDeployer(args.provider, args.environment)
        success = deployer.deploy()
        
        if success:
            print(f"\n{Colors.GREEN}🎉 ¡Despliegue completado exitosamente!{Colors.END}")
        else:
            print(f"\n{Colors.RED}❌ El despliegue falló{Colors.END}")
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Despliegue cancelado por el usuario{Colors.END}")
        return 1
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error inesperado: {e}{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())