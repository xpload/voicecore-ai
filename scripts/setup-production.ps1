# VoiceCore AI - Production Setup Script for Windows
# PowerShell script for Windows production deployment

param(
    [Parameter(Mandatory=$false)]
    [string]$Action = "deploy",
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production"
)

# Configuration
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = "docker-compose.prod.yml"
$EnvFile = ".env.production"
$BackupDir = "backups"
$LogFile = "deploy.log"

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"

# Logging functions
function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage -ForegroundColor $Color
    Add-Content -Path $LogFile -Value $LogMessage
}

function Write-Error-Log {
    param([string]$Message)
    Write-Log "[ERROR] $Message" $Red
}

function Write-Success-Log {
    param([string]$Message)
    Write-Log "[SUCCESS] $Message" $Green
}

function Write-Warning-Log {
    param([string]$Message)
    Write-Log "[WARNING] $Message" $Yellow
}

# Check prerequisites
function Test-Prerequisites {
    Write-Log "Checking prerequisites..." $Blue
    
    # Check Docker
    try {
        docker --version | Out-Null
        docker info | Out-Null
    }
    catch {
        Write-Error-Log "Docker is not installed or not running"
        exit 1
    }
    
    # Check Docker Compose
    try {
        docker-compose --version | Out-Null
    }
    catch {
        try {
            docker compose version | Out-Null
        }
        catch {
            Write-Error-Log "Docker Compose is not installed"
            exit 1
        }
    }
    
    # Check environment file
    if (-not (Test-Path $EnvFile)) {
        Write-Error-Log "Environment file $EnvFile not found"
        exit 1
    }
    
    # Check compose file
    if (-not (Test-Path $ComposeFile)) {
        Write-Error-Log "Compose file $ComposeFile not found"
        exit 1
    }
    
    Write-Success-Log "Prerequisites check passed"
}

# Create backup
function New-Backup {
    Write-Log "Creating backup..." $Blue
    
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir | Out-Null
    }
    
    $BackupName = "voicecore-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    
    # Backup database (if using local PostgreSQL)
    try {
        $PostgresStatus = docker-compose -f $ComposeFile ps postgres 2>$null
        if ($PostgresStatus -match "Up") {
            Write-Log "Backing up PostgreSQL database..."
            docker-compose -f $ComposeFile exec -T postgres pg_dump -U voicecore voicecore > "$BackupDir\$BackupName-db.sql"
        }
    }
    catch {
        Write-Warning-Log "Could not backup PostgreSQL database"
    }
    
    # Backup Redis data
    try {
        $RedisStatus = docker-compose -f $ComposeFile ps redis 2>$null
        if ($RedisStatus -match "Up") {
            Write-Log "Backing up Redis data..."
            docker-compose -f $ComposeFile exec -T redis redis-cli BGSAVE
            $RedisContainer = docker-compose -f $ComposeFile ps -q redis
            docker cp "${RedisContainer}:/data/dump.rdb" "$BackupDir\$BackupName-redis.rdb"
        }
    }
    catch {
        Write-Warning-Log "Could not backup Redis data"
    }
    
    # Backup configuration files
    Write-Log "Backing up configuration files..."
    $ConfigFiles = @($EnvFile, $ComposeFile)
    $ConfigDirs = @("nginx", "monitoring")
    
    $BackupPath = "$BackupDir\$BackupName-config.zip"
    Compress-Archive -Path $ConfigFiles -DestinationPath $BackupPath -Force
    
    foreach ($Dir in $ConfigDirs) {
        if (Test-Path $Dir) {
            Compress-Archive -Path $Dir -DestinationPath $BackupPath -Update
        }
    }
    
    Write-Success-Log "Backup created: $BackupName"
    Set-Content -Path "$BackupDir\latest-backup.txt" -Value $BackupName
    
    return $BackupName
}

# Health check
function Test-Health {
    param([int]$MaxAttempts = 30)
    
    Write-Log "Performing health check..." $Blue
    
    for ($Attempt = 1; $Attempt -le $MaxAttempts; $Attempt++) {
        try {
            $Response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing
            if ($Response.StatusCode -eq 200) {
                Write-Success-Log "Health check passed"
                return $true
            }
        }
        catch {
            Write-Log "Health check attempt $Attempt/$MaxAttempts failed, retrying in 10 seconds..."
            Start-Sleep -Seconds 10
        }
    }
    
    Write-Error-Log "Health check failed after $MaxAttempts attempts"
    return $false
}

# Rollback function
function Invoke-Rollback {
    Write-Error-Log "Deployment failed, initiating rollback..."
    
    if (Test-Path "$BackupDir\latest-backup.txt") {
        $BackupName = Get-Content "$BackupDir\latest-backup.txt"
        Write-Log "Rolling back to backup: $BackupName" $Blue
        
        # Stop current services
        docker-compose -f $ComposeFile down
        
        # Restore configuration
        $ConfigBackup = "$BackupDir\$BackupName-config.zip"
        if (Test-Path $ConfigBackup) {
            Expand-Archive -Path $ConfigBackup -DestinationPath . -Force
        }
        
        # Restore database
        $DbBackup = "$BackupDir\$BackupName-db.sql"
        if (Test-Path $DbBackup) {
            docker-compose -f $ComposeFile up -d postgres
            Start-Sleep -Seconds 10
            Get-Content $DbBackup | docker-compose -f $ComposeFile exec -T postgres psql -U voicecore -d voicecore
        }
        
        # Restore Redis
        $RedisBackup = "$BackupDir\$BackupName-redis.rdb"
        if (Test-Path $RedisBackup) {
            $RedisContainer = docker-compose -f $ComposeFile ps -q redis
            docker cp $RedisBackup "${RedisContainer}:/data/dump.rdb"
            docker-compose -f $ComposeFile restart redis
        }
        
        # Start services
        docker-compose -f $ComposeFile up -d
        
        if (Test-Health) {
            Write-Success-Log "Rollback completed successfully"
        }
        else {
            Write-Error-Log "Rollback failed"
            exit 1
        }
    }
    else {
        Write-Error-Log "No backup found for rollback"
        exit 1
    }
}

# Main deployment function
function Invoke-Deploy {
    Write-Log "Starting VoiceCore AI deployment..." $Blue
    
    try {
        # Pull latest images
        Write-Log "Pulling latest Docker images..."
        docker-compose -f $ComposeFile pull
        
        # Build application image
        Write-Log "Building application image..."
        docker-compose -f $ComposeFile build --no-cache voicecore
        
        # Stop services gracefully
        Write-Log "Stopping existing services..."
        docker-compose -f $ComposeFile down --timeout 30
        
        # Start services
        Write-Log "Starting services..."
        docker-compose -f $ComposeFile up -d
        
        # Wait for services to be ready
        Write-Log "Waiting for services to start..."
        Start-Sleep -Seconds 30
        
        # Run database migrations
        Write-Log "Running database migrations..."
        docker-compose -f $ComposeFile exec -T voicecore alembic upgrade head
        
        # Perform health check
        if (-not (Test-Health)) {
            throw "Health check failed"
        }
        
        # Cleanup old images
        Write-Log "Cleaning up old Docker images..."
        docker image prune -f
        
        Write-Success-Log "Deployment completed successfully!"
    }
    catch {
        Write-Error-Log "Deployment failed: $($_.Exception.Message)"
        Invoke-Rollback
        exit 1
    }
}

# Update SSL certificates
function Update-SSL {
    Write-Log "Updating SSL certificates..." $Blue
    
    $SslDir = "nginx\ssl"
    $CertFile = "$SslDir\voicecore.crt"
    $KeyFile = "$SslDir\voicecore.key"
    
    # Check if certificates exist
    if (-not (Test-Path $CertFile) -or -not (Test-Path $KeyFile)) {
        Write-Warning-Log "SSL certificates not found, generating self-signed certificates..."
        
        if (-not (Test-Path $SslDir)) {
            New-Item -ItemType Directory -Path $SslDir -Force | Out-Null
        }
        
        # Generate self-signed certificate (requires OpenSSL)
        try {
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $KeyFile -out $CertFile -subj "/C=US/ST=State/L=City/O=Organization/CN=voicecore.local"
        }
        catch {
            Write-Warning-Log "OpenSSL not found. Please install OpenSSL or provide SSL certificates manually."
            return
        }
    }
    
    # Reload nginx configuration
    try {
        $NginxStatus = docker-compose -f $ComposeFile ps nginx 2>$null
        if ($NginxStatus -match "Up") {
            docker-compose -f $ComposeFile exec nginx nginx -s reload
            Write-Success-Log "SSL certificates updated and nginx reloaded"
        }
    }
    catch {
        Write-Warning-Log "Could not reload nginx configuration"
    }
}

# Show logs
function Show-Logs {
    docker-compose -f $ComposeFile logs -f --tail=100 voicecore
}

# Show status
function Show-Status {
    Write-Log "Service Status:" $Blue
    docker-compose -f $ComposeFile ps
    
    Write-Log "System Resources:" $Blue
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Show usage
function Show-Usage {
    Write-Host "Usage: .\setup-production.ps1 [-Action <action>] [-Environment <env>]"
    Write-Host ""
    Write-Host "Actions:"
    Write-Host "  deploy     Deploy the application (default)"
    Write-Host "  backup     Create a backup only"
    Write-Host "  rollback   Rollback to the latest backup"
    Write-Host "  health     Perform health check only"
    Write-Host "  ssl        Update SSL certificates"
    Write-Host "  logs       Show application logs"
    Write-Host "  status     Show service status"
    Write-Host "  help       Show this help message"
}

# Main script logic
function Main {
    Set-Location $ProjectRoot
    
    switch ($Action.ToLower()) {
        "deploy" {
            Test-Prerequisites
            New-Backup | Out-Null
            Invoke-Deploy
        }
        "backup" {
            New-Backup
        }
        "rollback" {
            Invoke-Rollback
        }
        "health" {
            Test-Health
        }
        "ssl" {
            Update-SSL
        }
        "logs" {
            Show-Logs
        }
        "status" {
            Show-Status
        }
        "help" {
            Show-Usage
        }
        default {
            Write-Error-Log "Unknown action: $Action"
            Show-Usage
            exit 1
        }
    }
}

# Error handling
trap {
    Write-Error-Log "Deployment script failed: $($_.Exception.Message)"
    if ($Action -eq "deploy") {
        Invoke-Rollback
    }
    exit 1
}

# Run main function
Main