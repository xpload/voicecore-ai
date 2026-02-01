#!/bin/bash

# VoiceCore AI - Production Deployment Script
# Automated deployment with health checks and rollback capability

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
BACKUP_DIR="backups"
LOG_FILE="deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker is not running"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if environment file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Environment file $ENV_FILE not found"
        exit 1
    fi
    
    # Check if compose file exists
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Compose file $COMPOSE_FILE not found"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Create backup
create_backup() {
    log "Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    BACKUP_NAME="voicecore-backup-$(date +%Y%m%d-%H%M%S)"
    
    # Backup database (if using local PostgreSQL)
    if docker-compose -f "$COMPOSE_FILE" ps postgres | grep -q "Up"; then
        log "Backing up PostgreSQL database..."
        docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U voicecore voicecore > "$BACKUP_DIR/$BACKUP_NAME-db.sql"
    fi
    
    # Backup Redis data
    if docker-compose -f "$COMPOSE_FILE" ps redis | grep -q "Up"; then
        log "Backing up Redis data..."
        docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli BGSAVE
        docker cp "$(docker-compose -f "$COMPOSE_FILE" ps -q redis):/data/dump.rdb" "$BACKUP_DIR/$BACKUP_NAME-redis.rdb"
    fi
    
    # Backup configuration files
    log "Backing up configuration files..."
    tar -czf "$BACKUP_DIR/$BACKUP_NAME-config.tar.gz" \
        "$ENV_FILE" \
        "$COMPOSE_FILE" \
        nginx/ \
        monitoring/ \
        2>/dev/null || true
    
    success "Backup created: $BACKUP_NAME"
    echo "$BACKUP_NAME" > "$BACKUP_DIR/latest-backup.txt"
}

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    
    log "Performing health check..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s http://localhost:8000/health > /dev/null; then
            success "Health check passed"
            return 0
        fi
        
        log "Health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    error "Health check failed after $max_attempts attempts"
    return 1
}

# Rollback function
rollback() {
    error "Deployment failed, initiating rollback..."
    
    if [[ -f "$BACKUP_DIR/latest-backup.txt" ]]; then
        BACKUP_NAME=$(cat "$BACKUP_DIR/latest-backup.txt")
        log "Rolling back to backup: $BACKUP_NAME"
        
        # Stop current services
        docker-compose -f "$COMPOSE_FILE" down
        
        # Restore configuration
        if [[ -f "$BACKUP_DIR/$BACKUP_NAME-config.tar.gz" ]]; then
            tar -xzf "$BACKUP_DIR/$BACKUP_NAME-config.tar.gz"
        fi
        
        # Restore database
        if [[ -f "$BACKUP_DIR/$BACKUP_NAME-db.sql" ]]; then
            docker-compose -f "$COMPOSE_FILE" up -d postgres
            sleep 10
            docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U voicecore -d voicecore < "$BACKUP_DIR/$BACKUP_NAME-db.sql"
        fi
        
        # Restore Redis
        if [[ -f "$BACKUP_DIR/$BACKUP_NAME-redis.rdb" ]]; then
            docker cp "$BACKUP_DIR/$BACKUP_NAME-redis.rdb" "$(docker-compose -f "$COMPOSE_FILE" ps -q redis):/data/dump.rdb"
            docker-compose -f "$COMPOSE_FILE" restart redis
        fi
        
        # Start services
        docker-compose -f "$COMPOSE_FILE" up -d
        
        if health_check; then
            success "Rollback completed successfully"
        else
            error "Rollback failed"
            exit 1
        fi
    else
        error "No backup found for rollback"
        exit 1
    fi
}

# Main deployment function
deploy() {
    log "Starting VoiceCore AI deployment..."
    
    # Pull latest images
    log "Pulling latest Docker images..."
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Build application image
    log "Building application image..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache voicecore
    
    # Stop services gracefully
    log "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" down --timeout 30
    
    # Start services
    log "Starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be ready
    log "Waiting for services to start..."
    sleep 30
    
    # Run database migrations
    log "Running database migrations..."
    docker-compose -f "$COMPOSE_FILE" exec -T voicecore alembic upgrade head
    
    # Perform health check
    if ! health_check; then
        rollback
        exit 1
    fi
    
    # Cleanup old images
    log "Cleaning up old Docker images..."
    docker image prune -f
    
    success "Deployment completed successfully!"
}

# Update SSL certificates
update_ssl() {
    log "Updating SSL certificates..."
    
    # Check if certificates exist
    if [[ ! -f "nginx/ssl/voicecore.crt" ]] || [[ ! -f "nginx/ssl/voicecore.key" ]]; then
        warning "SSL certificates not found, generating self-signed certificates..."
        mkdir -p nginx/ssl
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/voicecore.key \
            -out nginx/ssl/voicecore.crt \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=voicecore.local"
    fi
    
    # Reload nginx configuration
    if docker-compose -f "$COMPOSE_FILE" ps nginx | grep -q "Up"; then
        docker-compose -f "$COMPOSE_FILE" exec nginx nginx -s reload
        success "SSL certificates updated and nginx reloaded"
    fi
}

# Show usage
usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy     Deploy the application (default)"
    echo "  backup     Create a backup only"
    echo "  rollback   Rollback to the latest backup"
    echo "  health     Perform health check only"
    echo "  ssl        Update SSL certificates"
    echo "  logs       Show application logs"
    echo "  status     Show service status"
    echo "  help       Show this help message"
}

# Show logs
show_logs() {
    docker-compose -f "$COMPOSE_FILE" logs -f --tail=100 voicecore
}

# Show status
show_status() {
    log "Service Status:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    log "System Resources:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Main script logic
main() {
    cd "$PROJECT_ROOT"
    
    case "${1:-deploy}" in
        deploy)
            check_prerequisites
            create_backup
            deploy
            ;;
        backup)
            create_backup
            ;;
        rollback)
            rollback
            ;;
        health)
            health_check
            ;;
        ssl)
            update_ssl
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        help)
            usage
            ;;
        *)
            error "Unknown command: $1"
            usage
            exit 1
            ;;
    esac
}

# Trap errors and perform rollback
trap 'error "Deployment script failed"; rollback' ERR

# Run main function
main "$@"