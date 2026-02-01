# VoiceCore AI System Structure Validation Script
# PowerShell script to validate project structure and completeness

Write-Host "🚀 VoiceCore AI System Structure Validation" -ForegroundColor Green
Write-Host "📅 Validation Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Yellow

$validationResults = @{}
$errors = @()
$warnings = @()

# Function to check if file exists
function Test-FileExists {
    param($FilePath, $Description)
    
    if (Test-Path $FilePath) {
        Write-Host "✅ $Description" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ $Description" -ForegroundColor Red
        return $false
    }
}

# Function to check if directory exists
function Test-DirectoryExists {
    param($DirPath, $Description)
    
    if (Test-Path $DirPath -PathType Container) {
        Write-Host "✅ $Description" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ $Description" -ForegroundColor Red
        return $false
    }
}

Write-Host "`n🔍 Validating Core Project Structure..." -ForegroundColor Cyan

# Core files validation
$coreFiles = @(
    @{Path="voicecore/__init__.py"; Desc="VoiceCore package init"},
    @{Path="voicecore/main.py"; Desc="Main application entry point"},
    @{Path="voicecore/config.py"; Desc="Configuration module"},
    @{Path="voicecore/database.py"; Desc="Database configuration"},
    @{Path="voicecore/logging.py"; Desc="Logging configuration"},
    @{Path="voicecore/middleware.py"; Desc="Middleware configuration"},
    @{Path="requirements.txt"; Desc="Python dependencies"},
    @{Path="pyproject.toml"; Desc="Project configuration"},
    @{Path="alembic.ini"; Desc="Database migration config"},
    @{Path="docker-compose.yml"; Desc="Docker compose config"},
    @{Path="Dockerfile"; Desc="Docker container config"}
)

$coreFilesValid = $true
foreach ($file in $coreFiles) {
    if (-not (Test-FileExists $file.Path $file.Desc)) {
        $coreFilesValid = $false
        $errors += "Missing core file: $($file.Path)"
    }
}

$validationResults["Core Files"] = if ($coreFilesValid) { "✅ PASS" } else { "❌ FAIL" }

Write-Host "`n🔍 Validating Directory Structure..." -ForegroundColor Cyan

# Directory structure validation
$directories = @(
    @{Path="voicecore/api"; Desc="API routes directory"},
    @{Path="voicecore/services"; Desc="Business services directory"},
    @{Path="voicecore/models"; Desc="Database models directory"},
    @{Path="voicecore/middleware"; Desc="Middleware directory"},
    @{Path="voicecore/utils"; Desc="Utilities directory"},
    @{Path="voicecore/static"; Desc="Static files directory"},
    @{Path="tests"; Desc="Tests directory"},
    @{Path="tests/integration"; Desc="Integration tests directory"},
    @{Path="alembic/versions"; Desc="Database migrations directory"},
    @{Path="kubernetes"; Desc="Kubernetes configs directory"},
    @{Path="monitoring"; Desc="Monitoring configs directory"},
    @{Path="nginx"; Desc="Nginx configs directory"},
    @{Path="scripts"; Desc="Deployment scripts directory"},
    @{Path="docs"; Desc="Documentation directory"},
    @{Path="examples"; Desc="Examples directory"}
)

$directoriesValid = $true
foreach ($dir in $directories) {
    if (-not (Test-DirectoryExists $dir.Path $dir.Desc)) {
        $directoriesValid = $false
        $errors += "Missing directory: $($dir.Path)"
    }
}

$validationResults["Directory Structure"] = if ($directoriesValid) { "✅ PASS" } else { "❌ FAIL" }

Write-Host "`n🔍 Validating API Routes..." -ForegroundColor Cyan

# API routes validation
$apiRoutes = @(
    "voicecore/api/tenant_routes.py",
    "voicecore/api/agent_routes.py",
    "voicecore/api/webhook_routes.py",
    "voicecore/api/admin_routes.py",
    "voicecore/api/tenant_admin_routes.py",
    "voicecore/api/analytics_routes.py",
    "voicecore/api/vip_routes.py",
    "voicecore/api/voicemail_routes.py",
    "voicecore/api/callback_routes.py",
    "voicecore/api/credit_routes.py",
    "voicecore/api/auth_routes.py",
    "voicecore/api/ai_training_routes.py",
    "voicecore/api/learning_feedback_routes.py",
    "voicecore/api/emotion_detection_routes.py",
    "voicecore/api/data_export_routes.py",
    "voicecore/api/scaling_routes.py",
    "voicecore/api/ha_routes.py",
    "voicecore/api/error_handling_routes.py",
    "voicecore/api/websocket_routes.py",
    "voicecore/api/pwa_routes.py",
    "voicecore/api/call_logging_routes.py"
)

$apiRoutesValid = $true
foreach ($route in $apiRoutes) {
    if (-not (Test-Path $route)) {
        $apiRoutesValid = $false
        $errors += "Missing API route: $route"
    }
}

$validationResults["API Routes"] = if ($apiRoutesValid) { "✅ PASS" } else { "❌ FAIL" }

Write-Host "`n🔍 Validating Services..." -ForegroundColor Cyan

# Services validation
$services = @(
    "voicecore/services/tenant_service.py",
    "voicecore/services/agent_service.py",
    "voicecore/services/call_routing_service.py",
    "voicecore/services/twilio_service.py",
    "voicecore/services/openai_service.py",
    "voicecore/services/analytics_service.py",
    "voicecore/services/spam_detection_service.py",
    "voicecore/services/vip_service.py",
    "voicecore/services/voicemail_service.py",
    "voicecore/services/callback_service.py",
    "voicecore/services/credit_management_service.py",
    "voicecore/services/auth_service.py",
    "voicecore/services/privacy_service.py",
    "voicecore/services/auto_scaling_service.py",
    "voicecore/services/high_availability_service.py",
    "voicecore/services/ai_training_service.py",
    "voicecore/services/learning_feedback_service.py",
    "voicecore/services/emotion_detection_service.py",
    "voicecore/services/data_export_service.py",
    "voicecore/services/error_handling_service.py",
    "voicecore/services/webrtc_gateway_service.py",
    "voicecore/services/websocket_service.py",
    "voicecore/services/pwa_service.py",
    "voicecore/services/call_logging_service.py",
    "voicecore/services/conversation_manager.py",
    "voicecore/services/performance_monitoring_service.py",
    "voicecore/services/intrusion_detection_service.py",
    "voicecore/services/scheduler_service.py"
)

$servicesValid = $true
foreach ($service in $services) {
    if (-not (Test-Path $service)) {
        $servicesValid = $false
        $errors += "Missing service: $service"
    }
}

$validationResults["Services"] = if ($servicesValid) { "✅ PASS" } else { "❌ FAIL" }

Write-Host "`n🔍 Validating Database Models..." -ForegroundColor Cyan

# Models validation
$models = @(
    "voicecore/models/base.py",
    "voicecore/models/tenant.py",
    "voicecore/models/agent.py",
    "voicecore/models/call.py",
    "voicecore/models/analytics.py",
    "voicecore/models/vip.py",
    "voicecore/models/voicemail.py",
    "voicecore/models/callback.py",
    "voicecore/models/billing.py",
    "voicecore/models/security.py",
    "voicecore/models/knowledge.py"
)

$modelsValid = $true
foreach ($model in $models) {
    if (-not (Test-Path $model)) {
        $modelsValid = $false
        $errors += "Missing model: $model"
    }
}

$validationResults["Database Models"] = if ($modelsValid) { "✅ PASS" } else { "❌ FAIL" }

Write-Host "`n🔍 Validating Database Migrations..." -ForegroundColor Cyan

# Migrations validation
$migrations = @(
    "alembic/versions/001_initial_schema.py",
    "alembic/versions/002_enhance_rls_policies.py",
    "alembic/versions/003_add_call_routing.py",
    "alembic/versions/004_add_vip_management.py",
    "alembic/versions/005_add_callback_system.py",
    "alembic/versions/006_add_security_models.py",
    "alembic/versions/007_add_credit_system.py"
)

$migrationsValid = $true
foreach ($migration in $migrations) {
    if (-not (Test-Path $migration)) {
        $migrationsValid = $false
        $errors += "Missing migration: $migration"
    }
}

$validationResults["Database Migrations"] = if ($migrationsValid) { "✅ PASS" } else { "❌ FAIL" }

Write-Host "`n🔍 Validating Tests..." -ForegroundColor Cyan

# Tests validation
$tests = @(
    "tests/conftest.py",
    "tests/test_properties.py",
    "tests/test_ai_properties.py",
    "tests/test_call_routing_properties.py",
    "tests/test_agent_properties.py",
    "tests/test_spam_detection_properties.py",
    "tests/test_webrtc_properties.py",
    "tests/test_call_logging_properties.py",
    "tests/test_advanced_features_properties.py",
    "tests/test_analytics_properties.py",
    "tests/test_security_properties.py",
    "tests/test_scalability_properties.py",
    "tests/test_ai_learning_properties.py",
    "tests/test_credit_system_properties.py",
    "tests/integration/test_end_to_end_call_flows.py",
    "tests/integration/test_multitenant_isolation.py",
    "tests/integration/test_external_service_integrations.py"
)

$testsValid = $true
$missingTests = @()
foreach ($test in $tests) {
    if (-not (Test-Path $test)) {
        $testsValid = $false
        $missingTests += $test
    }
}

if ($missingTests.Count -gt 0 -and $missingTests.Count -lt $tests.Count) {
    $validationResults["Tests"] = "⚠️ PARTIAL"
    $warnings += "Missing some test files: $($missingTests -join ', ')"
} elseif ($testsValid) {
    $validationResults["Tests"] = "✅ PASS"
} else {
    $validationResults["Tests"] = "❌ FAIL"
    $errors += "Most test files are missing"
}

Write-Host "`n🔍 Validating Deployment Configuration..." -ForegroundColor Cyan

# Deployment files validation
$deploymentFiles = @(
    "docker-compose.prod.yml",
    "kubernetes/deployment.yaml",
    "kubernetes/service.yaml",
    "kubernetes/configmap.yaml",
    "kubernetes/secrets.yaml",
    "kubernetes/ingress.yaml",
    "kubernetes/hpa.yaml",
    "kubernetes/pvc.yaml",
    "kubernetes/namespace.yaml",
    "kubernetes/kustomization.yaml",
    "monitoring/prometheus.yml",
    "monitoring/alert_rules.yml",
    "nginx/nginx.prod.conf",
    "scripts/deploy.sh",
    "scripts/setup-production.ps1"
)

$deploymentValid = $true
$missingDeployment = @()
foreach ($file in $deploymentFiles) {
    if (-not (Test-Path $file)) {
        $missingDeployment += $file
    }
}

if ($missingDeployment.Count -gt 0 -and $missingDeployment.Count -lt $deploymentFiles.Count) {
    $validationResults["Deployment"] = "⚠️ PARTIAL"
    $warnings += "Missing some deployment files: $($missingDeployment -join ', ')"
} elseif ($missingDeployment.Count -eq 0) {
    $validationResults["Deployment"] = "✅ PASS"
} else {
    $validationResults["Deployment"] = "❌ FAIL"
    $errors += "Most deployment files are missing"
}

Write-Host "`n🔍 Validating Documentation..." -ForegroundColor Cyan

# Documentation validation
$docFiles = @(
    "README.md",
    "DEPLOYMENT.md",
    "docs/VIP_MANAGEMENT.md",
    "CHECKPOINT_5_VERIFICATION.md",
    "CHECKPOINT_10_CORE_FUNCTIONALITY.md"
)

$docsValid = $true
foreach ($doc in $docFiles) {
    if (-not (Test-Path $doc)) {
        $docsValid = $false
        $warnings += "Missing documentation: $doc"
    }
}

$validationResults["Documentation"] = if ($docsValid) { "✅ PASS" } else { "⚠️ PARTIAL" }

Write-Host "`n🔍 Validating Configuration Files..." -ForegroundColor Cyan

# Configuration files validation
$configFiles = @(
    ".env.example",
    ".env.production",
    "redis.conf"
)

$configValid = $true
foreach ($config in $configFiles) {
    if (-not (Test-Path $config)) {
        $configValid = $false
        $warnings += "Missing configuration file: $config"
    }
}

$validationResults["Configuration"] = if ($configValid) { "✅ PASS" } else { "⚠️ PARTIAL" }

# Print Summary
Write-Host "`n" + ("=" * 60) -ForegroundColor Yellow
Write-Host "🎯 SYSTEM VALIDATION SUMMARY" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Yellow

Write-Host "`n📊 Validation Results:" -ForegroundColor Cyan
foreach ($component in $validationResults.Keys) {
    $result = $validationResults[$component]
    Write-Host "  $component`: $result"
}

if ($errors.Count -gt 0) {
    Write-Host "`n❌ Errors ($($errors.Count)):" -ForegroundColor Red
    for ($i = 0; $i -lt $errors.Count; $i++) {
        Write-Host "  $($i + 1). $($errors[$i])" -ForegroundColor Red
    }
}

if ($warnings.Count -gt 0) {
    Write-Host "`n⚠️ Warnings ($($warnings.Count)):" -ForegroundColor Yellow
    for ($i = 0; $i -lt $warnings.Count; $i++) {
        Write-Host "  $($i + 1). $($warnings[$i])" -ForegroundColor Yellow
    }
}

# Calculate overall status
$totalComponents = $validationResults.Count
$passedComponents = ($validationResults.Values | Where-Object { $_ -like "*✅*" }).Count
$partialComponents = ($validationResults.Values | Where-Object { $_ -like "*⚠️*" }).Count
$failedComponents = ($validationResults.Values | Where-Object { $_ -like "*❌*" }).Count

Write-Host "`n📈 Overall Status:" -ForegroundColor Cyan
Write-Host "  Total Components: $totalComponents"
Write-Host "  Passed: $passedComponents" -ForegroundColor Green
Write-Host "  Partial: $partialComponents" -ForegroundColor Yellow
Write-Host "  Failed: $failedComponents" -ForegroundColor Red
Write-Host "  Success Rate: $([math]::Round(($passedComponents / $totalComponents * 100), 1))%"

if ($failedComponents -eq 0 -and $errors.Count -eq 0) {
    Write-Host "`n🎉 SYSTEM VALIDATION COMPLETED SUCCESSFULLY!" -ForegroundColor Green
    Write-Host "   VoiceCore AI is ready for deployment." -ForegroundColor Green
} elseif ($failedComponents -eq 0) {
    Write-Host "`n✅ SYSTEM VALIDATION PASSED WITH WARNINGS" -ForegroundColor Yellow
    Write-Host "   VoiceCore AI is functional but has minor issues to address." -ForegroundColor Yellow
} else {
    Write-Host "`n❌ SYSTEM VALIDATION FAILED" -ForegroundColor Red
    Write-Host "   Please fix the errors before deployment." -ForegroundColor Red
}

Write-Host ("=" * 60) -ForegroundColor Yellow

# Count files and provide statistics
$totalPyFiles = (Get-ChildItem -Path "voicecore" -Recurse -Filter "*.py" | Measure-Object).Count
$totalTestFiles = (Get-ChildItem -Path "tests" -Recurse -Filter "*.py" -ErrorAction SilentlyContinue | Measure-Object).Count
$totalConfigFiles = (Get-ChildItem -Path "." -Filter "*.yml" -ErrorAction SilentlyContinue | Measure-Object).Count + 
                   (Get-ChildItem -Path "." -Filter "*.yaml" -ErrorAction SilentlyContinue | Measure-Object).Count +
                   (Get-ChildItem -Path "kubernetes" -Filter "*.yaml" -ErrorAction SilentlyContinue | Measure-Object).Count

Write-Host "`n📊 Project Statistics:" -ForegroundColor Cyan
Write-Host "  Python Files: $totalPyFiles"
Write-Host "  Test Files: $totalTestFiles"
Write-Host "  Config Files: $totalConfigFiles"

# Check spec completion
if (Test-Path ".kiro/specs/voicecore-ai/tasks.md") {
    $tasksContent = Get-Content ".kiro/specs/voicecore-ai/tasks.md" -Raw
    $completedTasks = ([regex]::Matches($tasksContent, '\[x\]')).Count
    $totalTasks = ([regex]::Matches($tasksContent, '\[.\]')).Count
    $completionRate = if ($totalTasks -gt 0) { [math]::Round(($completedTasks / $totalTasks * 100), 1) } else { 0 }
    
    Write-Host "  Completed Tasks: $completedTasks/$totalTasks ($completionRate%)"
}

Write-Host "`n🚀 VoiceCore AI System Validation Complete!" -ForegroundColor Green