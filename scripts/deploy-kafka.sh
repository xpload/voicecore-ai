#!/bin/bash

# Deploy Apache Kafka Cluster with High Availability
# This script deploys Kafka, ZooKeeper, Schema Registry, and Kafka Connect

set -e

echo "=========================================="
echo "Deploying Apache Kafka Cluster"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

print_status "Kubernetes cluster is accessible"

# Step 1: Create namespace
print_status "Creating Kafka namespace..."
kubectl apply -f kubernetes/kafka/namespace.yaml

# Step 2: Deploy ZooKeeper
print_status "Deploying ZooKeeper ensemble (3 nodes)..."
kubectl apply -f kubernetes/kafka/zookeeper-statefulset.yaml

print_status "Waiting for ZooKeeper to be ready (this may take a few minutes)..."
kubectl wait --for=condition=ready pod -l app=zookeeper -n kafka --timeout=600s || {
    print_error "ZooKeeper failed to start. Check logs with: kubectl logs -l app=zookeeper -n kafka"
    exit 1
}

print_status "ZooKeeper is ready!"

# Verify ZooKeeper status
print_status "Verifying ZooKeeper cluster status..."
for i in 0 1 2; do
    echo "ZooKeeper-$i status:"
    kubectl exec -it zookeeper-$i -n kafka -- zkServer.sh status || true
done

# Step 3: Deploy Kafka brokers
print_status "Deploying Kafka brokers (3 brokers with replication factor 3)..."
kubectl apply -f kubernetes/kafka/kafka-statefulset.yaml

print_status "Waiting for Kafka brokers to be ready (this may take a few minutes)..."
kubectl wait --for=condition=ready pod -l app=kafka -n kafka --timeout=600s || {
    print_error "Kafka brokers failed to start. Check logs with: kubectl logs -l app=kafka -n kafka"
    exit 1
}

print_status "Kafka brokers are ready!"

# Verify Kafka broker status
print_status "Verifying Kafka broker status..."
kubectl exec -it kafka-0 -n kafka -- kafka-broker-api-versions --bootstrap-server localhost:9092 | head -n 5

# Step 4: Deploy Schema Registry
print_status "Deploying Schema Registry for event versioning..."
kubectl apply -f kubernetes/kafka/schema-registry.yaml

print_status "Waiting for Schema Registry to be ready..."
kubectl wait --for=condition=ready pod -l app=schema-registry -n kafka --timeout=300s || {
    print_warning "Schema Registry may not be fully ready. Check logs with: kubectl logs -l app=schema-registry -n kafka"
}

print_status "Schema Registry is ready!"

# Step 5: Deploy Kafka Connect
print_status "Deploying Kafka Connect for external integrations..."
kubectl apply -f kubernetes/kafka/kafka-connect.yaml

print_status "Waiting for Kafka Connect to be ready..."
kubectl wait --for=condition=ready pod -l app=kafka-connect -n kafka --timeout=300s || {
    print_warning "Kafka Connect may not be fully ready. Check logs with: kubectl logs -l app=kafka-connect -n kafka"
}

print_status "Kafka Connect is ready!"

# Step 6: Create topics
print_status "Creating Kafka topics with exactly-once semantics for critical topics..."
kubectl apply -f kubernetes/kafka/kafka-topics.yaml

print_status "Waiting for topic creation job to complete..."
kubectl wait --for=condition=complete job/kafka-topics-setup -n kafka --timeout=300s || {
    print_warning "Topic creation may have failed. Check logs with: kubectl logs job/kafka-topics-setup -n kafka"
}

# List created topics
print_status "Listing created topics..."
kubectl exec -it kafka-0 -n kafka -- kafka-topics --bootstrap-server localhost:9092 --list

# Step 7: Deploy monitoring
print_status "Deploying Prometheus monitoring and alerts..."
kubectl apply -f kubernetes/kafka/kafka-monitoring.yaml || {
    print_warning "Monitoring deployment failed. This is optional if Prometheus operator is not installed."
}

# Step 8: Display cluster information
echo ""
echo "=========================================="
echo "Kafka Cluster Deployment Complete!"
echo "=========================================="
echo ""
print_status "Cluster Information:"
echo ""
echo "Kafka Brokers:"
kubectl get pods -n kafka -l app=kafka -o wide
echo ""
echo "ZooKeeper Ensemble:"
kubectl get pods -n kafka -l app=zookeeper -o wide
echo ""
echo "Schema Registry:"
kubectl get pods -n kafka -l app=schema-registry -o wide
echo ""
echo "Kafka Connect:"
kubectl get pods -n kafka -l app=kafka-connect -o wide
echo ""
echo "Services:"
kubectl get svc -n kafka
echo ""
echo "=========================================="
echo "Connection Information:"
echo "=========================================="
echo ""
echo "Kafka Bootstrap Servers (internal):"
echo "  kafka.kafka.svc.cluster.local:9092"
echo ""
echo "Schema Registry:"
echo "  http://schema-registry.kafka.svc.cluster.local:8081"
echo ""
echo "Kafka Connect:"
echo "  http://kafka-connect.kafka.svc.cluster.local:8083"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Verify topics:"
echo "   kubectl exec -it kafka-0 -n kafka -- kafka-topics --bootstrap-server localhost:9092 --list"
echo ""
echo "2. Test producer:"
echo "   kubectl exec -it kafka-0 -n kafka -- kafka-console-producer --bootstrap-server localhost:9092 --topic test"
echo ""
echo "3. Test consumer:"
echo "   kubectl exec -it kafka-0 -n kafka -- kafka-console-consumer --bootstrap-server localhost:9092 --topic test --from-beginning"
echo ""
echo "4. Check Schema Registry:"
echo "   kubectl exec -it kafka-0 -n kafka -- curl http://schema-registry.kafka.svc.cluster.local:8081/subjects"
echo ""
echo "5. Check Kafka Connect:"
echo "   kubectl exec -it kafka-0 -n kafka -- curl http://kafka-connect.kafka.svc.cluster.local:8083/connectors"
echo ""
echo "6. Monitor cluster:"
echo "   kubectl logs -f kafka-0 -n kafka"
echo ""
print_status "Deployment completed successfully!"
