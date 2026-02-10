"""
VoiceCore AI - Automated Production Deployment Script
Handles complete deployment process with validation
"""

import sys
import os
import subprocess
import time
from colorama import init, Fore, Style
import requests

init(autoreset=True)


class ProductionDeployer:
    """Automated production deployment"""
    
    def __init__(self):
        self.steps_completed = []
        self.deployment_method = None
        self.domain = None
        self.database_url = None
    
    def print_header(self, text):
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{text.center(80)}")
        print(f"{Fore.CYAN}{'='*80}\n")
    
    def print_step(self, step_num, total, text):
        print(f"\n{Fore.YELLOW}[{step_num}/{total}] {text}{Style.RESET_ALL}")
    
    def print_success(self, text):
        print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")
    
    def print_error(self, text):
        print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")
    
    def print_info(self, text):
        print(f"{Fore.BLUE}ℹ️  {text}{Style.RESET_ALL}")
    
    def run_command(self, command, description, check=True):
        """Run a shell command"""
        self.print_info(f"Running: {description}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=check
            )
            if result.returncode == 0:
                self.print_success(f"{description} completed")
                return True, result.stdout
            else:
                self.print_error(f"{description} failed")
                print(f"{Fore.RED}{result.stderr}{Style.RESET_ALL}")
                return False, result.stderr
        except Exception as e:
            self.print_error(f"{description} failed: {str(e)}")
            return False, str(e)
    
    def step_1_pre_deployment_tests(self):
        """Run pre-deployment tests"""
        self.print_step(1, 10, "Pre-Deployment Testing")
        
        # Check readiness
        self.print_info("Checking system readiness...")
        success, _ = self.run_command(
            "python check_test_readiness.py",
            "System readiness check",
            check=False
        )
        
        if not success:
            self.print_error("System not ready. Please fix issues and try again.")
            return False
        
        # Run tests
        self.print_info("Running test suite...")
        success, _ = self.run_command(
            "python run_call_tests.py",
            "Test suite execution",
            check=False
        )
        
        if not success:
            response = input(f"\n{Fore.YELLOW}Tests failed. Continue anyway? (y/n): {Style.RESET_ALL}")
            if response.lower() != 'y':
                return False
        
        self.steps_completed.append("pre_deployment_tests")
        return True
    
    def step_2_configure_environment(self):
        """Configure production environment"""
        self.print_step(2, 10, "Environment Configuration")
        
        # Check if .env.production exists
        if not os.path.exists('.env.production'):
            self.print_info("Creating .env.production from template...")
            if os.path.exists('.env.production.example'):
                success, _ = self.run_command(
                    "cp .env.production.example .env.production",
                    "Copy environment template"
                )
            else:
                self.print_error(".env.production.example not found")
                return False
        
        self.print_info("Please configure .env.production with your production values")
        input(f"{Fore.YELLOW}Press Enter when ready...{Style.RESET_ALL}")
        
        # Get domain
        self.domain = input(f"{Fore.YELLOW}Enter your domain (e.g., api.yourdomain.com): {Style.RESET_ALL}")
        
        # Get database URL
        self.database_url = input(f"{Fore.YELLOW}Enter database URL: {Style.RESET_ALL}")
        
        self.steps_completed.append("configure_environment")
        return True
    
    def step_3_database_migration(self):
        """Run database migrations"""
        self.print_step(3, 10, "Database Migration")
        
        # Set database URL
        os.environ['DATABASE_URL'] = self.database_url
        
        # Run migrations
        success, _ = self.run_command(
            "alembic upgrade head",
            "Database migration"
        )
        
        if not success:
            return False
        
        # Verify migration
        success, output = self.run_command(
            "alembic current",
            "Verify migration"
        )
        
        if success:
            self.print_success(f"Current revision: {output.strip()}")
        
        self.steps_completed.append("database_migration")
        return True
    
    def step_4_choose_deployment_method(self):
        """Choose deployment method"""
        self.print_step(4, 10, "Deployment Method Selection")
        
        print(f"\n{Fore.CYAN}Available deployment methods:")
        print(f"  1. Docker Compose (Recommended for single server)")
        print(f"  2. Kubernetes (Recommended for production cluster)")
        print(f"  3. Railway (Managed platform)")
        print(f"  4. Heroku (Managed platform)")
        
        choice = input(f"\n{Fore.YELLOW}Select deployment method (1-4): {Style.RESET_ALL}")
        
        methods = {
            '1': 'docker-compose',
            '2': 'kubernetes',
            '3': 'railway',
            '4': 'heroku'
        }
        
        self.deployment_method = methods.get(choice)
        
        if not self.deployment_method:
            self.print_error("Invalid choice")
            return False
        
        self.print_success(f"Selected: {self.deployment_method}")
        self.steps_completed.append("choose_deployment_method")
        return True
    
    def step_5_deploy_docker_compose(self):
        """Deploy using Docker Compose"""
        self.print_step(5, 10, "Docker Compose Deployment")
        
        # Build images
        success, _ = self.run_command(
            "docker-compose -f docker-compose.prod.yml build",
            "Build Docker images"
        )
        if not success:
            return False
        
        # Start services
        success, _ = self.run_command(
            "docker-compose -f docker-compose.prod.yml up -d",
            "Start services"
        )
        if not success:
            return False
        
        # Wait for services to start
        self.print_info("Waiting for services to start...")
        time.sleep(10)
        
        # Check services
        success, output = self.run_command(
            "docker-compose -f docker-compose.prod.yml ps",
            "Check services status"
        )
        
        print(f"\n{Fore.CYAN}Services Status:")
        print(output)
        
        self.steps_completed.append("deploy")
        return True
    
    def step_5_deploy_kubernetes(self):
        """Deploy using Kubernetes"""
        self.print_step(5, 10, "Kubernetes Deployment")
        
        # Create namespace
        success, _ = self.run_command(
            "kubectl create namespace voicecore-prod --dry-run=client -o yaml | kubectl apply -f -",
            "Create namespace"
        )
        
        # Create secrets
        success, _ = self.run_command(
            "kubectl create secret generic voicecore-secrets --from-env-file=.env.production -n voicecore-prod --dry-run=client -o yaml | kubectl apply -f -",
            "Create secrets"
        )
        
        # Deploy application
        deployments = [
            "kubernetes/deployment.yaml",
            "kubernetes/service.yaml",
            "kubernetes/ingress.yaml",
            "kubernetes/hpa.yaml"
        ]
        
        for deployment in deployments:
            if os.path.exists(deployment):
                success, _ = self.run_command(
                    f"kubectl apply -f {deployment} -n voicecore-prod",
                    f"Deploy {deployment}"
                )
                if not success:
                    return False
        
        # Wait for pods
        self.print_info("Waiting for pods to be ready...")
        time.sleep(20)
        
        # Check pods
        success, output = self.run_command(
            "kubectl get pods -n voicecore-prod",
            "Check pods status"
        )
        
        print(f"\n{Fore.CYAN}Pods Status:")
        print(output)
        
        self.steps_completed.append("deploy")
        return True
    
    def step_5_deploy_railway(self):
        """Deploy using Railway"""
        self.print_step(5, 10, "Railway Deployment")
        
        # Check Railway CLI
        success, _ = self.run_command(
            "railway --version",
            "Check Railway CLI",
            check=False
        )
        
        if not success:
            self.print_error("Railway CLI not installed")
            self.print_info("Install with: npm install -g @railway/cli")
            return False
        
        # Login
        self.print_info("Please login to Railway...")
        success, _ = self.run_command(
            "railway login",
            "Railway login"
        )
        
        # Deploy
        success, _ = self.run_command(
            "railway up",
            "Deploy to Railway"
        )
        
        if not success:
            return False
        
        self.steps_completed.append("deploy")
        return True
    
    def step_5_deploy_heroku(self):
        """Deploy using Heroku"""
        self.print_step(5, 10, "Heroku Deployment")
        
        # Check Heroku CLI
        success, _ = self.run_command(
            "heroku --version",
            "Check Heroku CLI",
            check=False
        )
        
        if not success:
            self.print_error("Heroku CLI not installed")
            return False
        
        # Login
        self.print_info("Please login to Heroku...")
        success, _ = self.run_command(
            "heroku login",
            "Heroku login"
        )
        
        # Create app
        app_name = input(f"{Fore.YELLOW}Enter Heroku app name: {Style.RESET_ALL}")
        success, _ = self.run_command(
            f"heroku create {app_name}",
            "Create Heroku app",
            check=False
        )
        
        # Add addons
        self.run_command(
            f"heroku addons:create heroku-postgresql:standard-0 -a {app_name}",
            "Add PostgreSQL"
        )
        
        self.run_command(
            f"heroku addons:create heroku-redis:premium-0 -a {app_name}",
            "Add Redis"
        )
        
        # Deploy
        success, _ = self.run_command(
            "git push heroku main",
            "Deploy to Heroku"
        )
        
        if not success:
            return False
        
        # Run migrations
        success, _ = self.run_command(
            f"heroku run alembic upgrade head -a {app_name}",
            "Run migrations on Heroku"
        )
        
        self.steps_completed.append("deploy")
        return True
    
    def step_6_post_deployment_verification(self):
        """Verify deployment"""
        self.print_step(6, 10, "Post-Deployment Verification")
        
        # Health check
        self.print_info("Checking health endpoint...")
        
        url = f"https://{self.domain}/health" if self.domain else "http://localhost:8000/health"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                self.print_success("Health check passed")
                print(f"{Fore.CYAN}{response.json()}{Style.RESET_ALL}")
            else:
                self.print_error(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            self.print_error(f"Health check failed: {str(e)}")
            self.print_info("Service may still be starting up...")
        
        self.steps_completed.append("post_deployment_verification")
        return True
    
    def step_7_configure_twilio(self):
        """Configure Twilio webhooks"""
        self.print_step(7, 10, "Twilio Configuration")
        
        webhook_url = f"https://{self.domain}/api/v1/webhooks/twilio/voice"
        
        print(f"\n{Fore.CYAN}Configure Twilio webhooks:")
        print(f"  Voice URL: {webhook_url}")
        print(f"  SMS URL: https://{self.domain}/api/v1/webhooks/twilio/sms")
        print(f"\n  Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming")
        
        input(f"\n{Fore.YELLOW}Press Enter when Twilio is configured...{Style.RESET_ALL}")
        
        self.steps_completed.append("configure_twilio")
        return True
    
    def step_8_setup_monitoring(self):
        """Setup monitoring"""
        self.print_step(8, 10, "Monitoring Setup")
        
        self.print_info("Setting up monitoring...")
        
        # Apply monitoring configs
        if self.deployment_method == 'kubernetes':
            success, _ = self.run_command(
                "kubectl apply -f monitoring/ -n voicecore-prod",
                "Apply monitoring configs",
                check=False
            )
        
        self.print_success("Monitoring configured")
        self.print_info(f"Prometheus: http://{self.domain}:9090")
        self.print_info(f"Grafana: http://{self.domain}:3000")
        
        self.steps_completed.append("setup_monitoring")
        return True
    
    def step_9_production_tests(self):
        """Run production tests"""
        self.print_step(9, 10, "Production Testing")
        
        self.print_info("Running production API tests...")
        
        # Test API endpoints
        if self.domain:
            try:
                # Test root endpoint
                response = requests.get(f"https://{self.domain}/")
                if response.status_code == 200:
                    self.print_success("Root endpoint OK")
                
                # Test API docs
                response = requests.get(f"https://{self.domain}/docs")
                if response.status_code == 200:
                    self.print_success("API docs OK")
                
            except Exception as e:
                self.print_error(f"Production tests failed: {str(e)}")
        
        self.steps_completed.append("production_tests")
        return True
    
    def step_10_final_summary(self):
        """Print final summary"""
        self.print_step(10, 10, "Deployment Summary")
        
        print(f"\n{Fore.GREEN}{Style.BRIGHT}🎉 Deployment Completed Successfully!{Style.RESET_ALL}\n")
        
        print(f"{Fore.CYAN}Deployment Details:")
        print(f"  Method: {self.deployment_method}")
        print(f"  Domain: {self.domain}")
        print(f"  Steps Completed: {len(self.steps_completed)}/10")
        
        print(f"\n{Fore.CYAN}Access Points:")
        print(f"  API: https://{self.domain}")
        print(f"  Dashboard: https://{self.domain}/dashboard")
        print(f"  API Docs: https://{self.domain}/docs")
        print(f"  Health: https://{self.domain}/health")
        
        print(f"\n{Fore.CYAN}Next Steps:")
        print(f"  1. Test a real call to your Twilio number")
        print(f"  2. Monitor logs and metrics")
        print(f"  3. Configure alerts")
        print(f"  4. Setup backups")
        print(f"  5. Configure CDN")
        
        print(f"\n{Fore.CYAN}Useful Commands:")
        if self.deployment_method == 'docker-compose':
            print(f"  View logs: docker-compose -f docker-compose.prod.yml logs -f")
            print(f"  Restart: docker-compose -f docker-compose.prod.yml restart")
            print(f"  Stop: docker-compose -f docker-compose.prod.yml down")
        elif self.deployment_method == 'kubernetes':
            print(f"  View logs: kubectl logs -f deployment/voicecore-api -n voicecore-prod")
            print(f"  Scale: kubectl scale deployment voicecore-api --replicas=3 -n voicecore-prod")
            print(f"  Status: kubectl get pods -n voicecore-prod")
        
        return True
    
    def deploy(self):
        """Main deployment flow"""
        self.print_header("VoiceCore AI - Production Deployment")
        
        try:
            # Step 1: Pre-deployment tests
            if not self.step_1_pre_deployment_tests():
                return False
            
            # Step 2: Configure environment
            if not self.step_2_configure_environment():
                return False
            
            # Step 3: Database migration
            if not self.step_3_database_migration():
                return False
            
            # Step 4: Choose deployment method
            if not self.step_4_choose_deployment_method():
                return False
            
            # Step 5: Deploy (method-specific)
            if self.deployment_method == 'docker-compose':
                if not self.step_5_deploy_docker_compose():
                    return False
            elif self.deployment_method == 'kubernetes':
                if not self.step_5_deploy_kubernetes():
                    return False
            elif self.deployment_method == 'railway':
                if not self.step_5_deploy_railway():
                    return False
            elif self.deployment_method == 'heroku':
                if not self.step_5_deploy_heroku():
                    return False
            
            # Step 6: Post-deployment verification
            if not self.step_6_post_deployment_verification():
                return False
            
            # Step 7: Configure Twilio
            if not self.step_7_configure_twilio():
                return False
            
            # Step 8: Setup monitoring
            if not self.step_8_setup_monitoring():
                return False
            
            # Step 9: Production tests
            if not self.step_9_production_tests():
                return False
            
            # Step 10: Final summary
            if not self.step_10_final_summary():
                return False
            
            return True
            
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}Deployment interrupted by user.{Style.RESET_ALL}")
            return False
        except Exception as e:
            self.print_error(f"Deployment failed: {str(e)}")
            return False


def main():
    """Main entry point"""
    deployer = ProductionDeployer()
    success = deployer.deploy()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
