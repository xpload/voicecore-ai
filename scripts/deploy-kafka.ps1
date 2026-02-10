# Deploy Apache Kafka Cluster with High Availability
# PowerShell script for Windows environments

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deploying Apache Kafka Cluster" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

function Print-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Print-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check if kubectl is available
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Print-Error "kubectl is not installed. Please install kubectl first."
    exit 1
}

# Check if cluster is accessible
try {
    kubectl cluster-info | Out-Null
    Print-Status "Kubernetes cluster is accessible"
} catch {
    Print-Error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
}

# Step 1: Create namespace
Print-Status "Creating Kafka namespace..."
kubectl apply -f kubernetes/kafka/namespace.yaml

# Step 2: Deploy ZooKeeper
Print-Status "Deploying ZooKeeper ensemble (3 nodes)..."
kubectl apply -f kubernetes/kafka/zookeeper-statefulset.yaml

Print-Status "Waiting for ZooKeeper to be ready (this may take a few minutes)..."
try {
    kubectl wait --for=condition=ready pod -l app=zookeeper -n kafka --timeout=600s
    Print-Status "ZooKeeper is ready!"
} catch {
    Print-Error "ZooKeeper failed to start. Check logs with: kubectl logs -l app=zookeeper -n kafka"
    exit 1
}

# Verify ZooKeeper status
Print-Status "Verifying ZooKeeper cluster status..."
for ($i = 0; $i -lt 3; $i++) {
    Write-Host "ZooKeeper-$i status:"
    kubectl exec -it zookeeper-$i -n kafka -- zkServer.sh status
}

# Step 3: Deploy Kafka brokers
Print-Status "Deploying Kafka brokers (3 brokers with replication factor 3)..."
kubectl apply -f kubernetes/kafka/kafka-statefulset.yaml

Print-Status "Waiting for Kafka brokers to be ready (this may take a few minutes)..."
try {
    kubectl wait --for=condition=ready pod -l app=kafka -n kafka --timeout=600s
    Print-Status "Kafka brokers are ready!"
} catch {
    Print-Error "Kafka brokers failed to start. Check logs with: kubectl logs -l app=kafka -n kafka"
    exit 1
}

# Verify Kafka broker status
Print-Status "Verifying Kafka broker status..."
kubectl exec -it kafka-0 -n kafka -- kafka-broker-api-versions --bootstrap-server localhost:9092

# Step 4: Deploy Schema Registry
Print-Status "Deploying Schema Registry for event versioning..."
kubectl apply -f kubernetes/kafka/schema-registry.yaml

Print-Status "Waiting for Schema Registry to be ready..."
try {
    kubectl wait --for=condition=ready pod -l app=schema-registry -n kafka --timeout=300s
    Print-Status "Schema Registry is ready!"
} catch {
    Print-Warning "Schema Registry may not be fully ready. Check logs with: kubectl logs -l app=schema-registry -n kafka"
}

# Step 5: Deploy Kafka Connect
Print-Status "Deploying Kafka Connect for external integrations..."
kubectl apply -f kubernetes/kafka/kafka-connect.yaml

Print-Status "Waiting for Kafka Connect to be ready..."
try {
    kubectl wait --for=condition=ready pod -l app=kafka-connect -n kafka --timeout=300s
    Print-Status "Kafka Connect is ready!"
} catch {
    Print-Warning "Kafka Connect may not be fully ready. Check logs with: kubectl logs -l app=kafka-connect -n kafka"
}

# Step 6: Create topics
Print-Status "Creating Kafka topics with exactly-once semantics for critical topics..."
kubectl apply -f kubernetes/kafka/kafka-topics.yaml

Print-Status "Waiting for topic creation job to complete..."
try {
    kubectl wait --for=condition=complete job/kafka-topics-setup -n kafka --timeout=300s
} catch {
    Print-Warning "Topic creation may have failed. Check logs with: kubectl logs job/kafka-topics-setup -n kafka"
}

# List created topics
Print-Status "Listing created topics..."
kubectl exec -it kafka-0 -n kafka -- kafka-topics --bootstrap-server localhost:9092 --list

# Step 7: Deploy monitoring
Print-Status "Deploying Prometheus monitoring and alerts..."
try {
    kubectl apply -f kubernetes/kafka/kafka-monitoring.yaml
} catch {
    Print-Warning "Monitoring deployment failed. This is optional if Prometheus operator is not installed."
}

# Step 8: Display cluster information
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Kafka Cluster Deployment Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Print-Status "Cluster Information:"
Write-Host ""
Write-Host "Kafka Brokers:"
kubectl get pods -n kafka -l app=kafka -o wide
Write-Host ""
Write-Host "ZooKeeper Ensemble:"
kubectl get pods -n kafka -l app=zookeeper -o wide
Write-Host ""
Write-Host "Schema Registry:"
kubectl get pods -n kafka -l app=schema-registry -o wide
Write-Host ""
Write-Host "Kafka Connect:"
kubectl get pods -n kafka -l app=kafka-connect -o wide
Write-Host ""
Write-Host "Services:"
kubectl get svc -n kafka
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Connection Information:" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Kafka Bootstrap Servers (internal):"
Write-Host "  kafka.kafka.svc.cluster.local:9092"
Write-Host ""
Write-Host "Schema Registry:"
Write-Host "  http://schema-registry.kafka.svc.cluster.local:8081"
Write-Host ""
Write-Host "Kafka Connect:"
Write-Host "  http://kafka-connect.kafka.svc.cluster.local:8083"
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Verify topics:"
Write-Host "   kubectl exec -it kafka-0 -n kafka -- kafka-topics --bootstrap-server localhost:9092 --list"
Write-Host ""
Write-Host "2. Test producer:"
Write-Host "   kubectl exec -it kafka-0 -n kafka -- kafka-console-producer --bootstrap-server localhost:9092 --topic test"
Write-Host ""
Write-Host "3. Test consumer:"
Write-Host "   kubectl exec -it kafka-0 -n kafka -- kafka-console-consumer --bootstrap-server localhost:9092 --topic test --from-beginning"
Write-Host ""
Write-Host "4. Check Schema Registry:"
Write-Host "   kubectl exec -it kafka-0 -n kafka -- curl http://schema-registry.kafka.svc.cluster.local:8081/subjects"
Write-Host ""
Write-Host "5. Check Kafka Connect:"
Write-Host "   kubectl exec -it kafka-0 -n kafka -- curl http://kafka-connect.kafka.svc.cluster.local:8083/connectors"
Write-Host ""
Write-Host "6. Monitor cluster:"
Write-Host "   kubectl logs -f kafka-0 -n kafka"
Write-Host ""
Print-Status "Deployment completed successfully!"
