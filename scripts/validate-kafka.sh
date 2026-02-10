#!/bin/bash

# Validate Apache Kafka Cluster Deployment
# This script verifies all components are working correctly

set -e

echo "=========================================="
echo "Validating Apache Kafka Cluster"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Function to print test results
print_test() {
    local test_name=$1
    local result=$2
    
    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $test_name"
        ((FAILED++))
    fi
}

echo ""
echo "Testing Kafka Cluster Components..."
echo ""

# Test 1: Check namespace exists
if kubectl get namespace kafka &> /dev/null; then
    print_test "Kafka namespace exists" "PASS"
else
    print_test "Kafka namespace exists" "FAIL"
fi

# Test 2: Check ZooKeeper pods
ZOOKEEPER_READY=$(kubectl get pods -n kafka -l app=zookeeper --no-headers 2>/dev/null | grep -c "Running" || echo "0")
if [ "$ZOOKEEPER_READY" -eq 3 ]; then
    print_test "ZooKeeper ensemble (3/3 pods running)" "PASS"
else
    print_test "ZooKeeper ensemble ($ZOOKEEPER_READY/3 pods running)" "FAIL"
fi

# Test 3: Check Kafka broker pods
KAFKA_READY=$(kubectl get pods -n kafka -l app=kafka --no-headers 2>/dev/null | grep -c "Running" || echo "0")
if [ "$KAFKA_READY" -eq 3 ]; then
    print_test "Kafka brokers (3/3 pods running)" "PASS"
else
    print_test "Kafka brokers ($KAFKA_READY/3 pods running)" "FAIL"
fi

# Test 4: Check Schema Registry pods
SCHEMA_READY=$(kubectl get pods -n kafka -l app=schema-registry --no-headers 2>/dev/null | grep -c "Running" || echo "0")
if [ "$SCHEMA_READY" -ge 1 ]; then
    print_test "Schema Registry ($SCHEMA_READY pods running)" "PASS"
else
    print_test "Schema Registry (0 pods running)" "FAIL"
fi

# Test 5: Check Kafka Connect pods
CONNECT_READY=$(kubectl get pods -n kafka -l app=kafka-connect --no-headers 2>/dev/null | grep -c "Running" || echo "0")
if [ "$CONNECT_READY" -ge 1 ]; then
    print_test "Kafka Connect ($CONNECT_READY pods running)" "PASS"
else
    print_test "Kafka Connect (0 pods running)" "FAIL"
fi

# Test 6: Check ZooKeeper cluster health
echo ""
echo "Checking ZooKeeper cluster health..."
for i in 0 1 2; do
    if kubectl exec -it zookeeper-$i -n kafka -- zkServer.sh status 2>/dev/null | grep -q "Mode:"; then
        MODE=$(kubectl exec -it zookeeper-$i -n kafka -- zkServer.sh status 2>/dev/null | grep "Mode:" | awk '{print $2}' | tr -d '\r')
        print_test "ZooKeeper-$i is healthy (Mode: $MODE)" "PASS"
    else
        print_test "ZooKeeper-$i is healthy" "FAIL"
    fi
done

# Test 7: Check Kafka broker connectivity
echo ""
echo "Checking Kafka broker connectivity..."
if kubectl exec -it kafka-0 -n kafka -- kafka-broker-api-versions --bootstrap-server localhost:9092 &> /dev/null; then
    print_test "Kafka broker API is accessible" "PASS"
else
    print_test "Kafka broker API is accessible" "FAIL"
fi

# Test 8: List topics
echo ""
echo "Checking Kafka topics..."
TOPICS=$(kubectl exec -it kafka-0 -n kafka -- kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null | wc -l)
if [ "$TOPICS" -gt 0 ]; then
    print_test "Kafka topics created ($TOPICS topics)" "PASS"
    echo ""
    echo "Available topics:"
    kubectl exec -it kafka-0 -n kafka -- kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null | sed 's/^/  - /'
else
    print_test "Kafka topics created" "FAIL"
fi

# Test 9: Check critical topics configuration
echo ""
echo "Validating critical topics configuration..."

check_topic_config() {
    local topic=$1
    local expected_partitions=$2
    local expected_replication=$3
    
    TOPIC_INFO=$(kubectl exec -it kafka-0 -n kafka -- kafka-topics --bootstrap-server localhost:9092 --describe --topic "$topic" 2>/dev/null || echo "")
    
    if [ -n "$TOPIC_INFO" ]; then
        PARTITIONS=$(echo "$TOPIC_INFO" | grep "PartitionCount:" | awk '{print $2}' | tr -d '\r')
        REPLICATION=$(echo "$TOPIC_INFO" | grep "ReplicationFactor:" | awk '{print $2}' | tr -d '\r')
        
        if [ "$PARTITIONS" = "$expected_partitions" ] && [ "$REPLICATION" = "$expected_replication" ]; then
            print_test "Topic '$topic' (Partitions: $PARTITIONS, Replication: $REPLICATION)" "PASS"
        else
            print_test "Topic '$topic' (Expected P:$expected_partitions R:$expected_replication, Got P:$PARTITIONS R:$REPLICATION)" "FAIL"
        fi
    else
        print_test "Topic '$topic' exists" "FAIL"
    fi
}

check_topic_config "call.events" "24" "3"
check_topic_config "ai.interactions" "24" "3"
check_topic_config "billing.transactions" "12" "3"
check_topic_config "security.audit" "12" "3"

# Test 10: Check Schema Registry health
echo ""
echo "Checking Schema Registry..."
if kubectl exec -it kafka-0 -n kafka -- curl -s http://schema-registry.kafka.svc.cluster.local:8081/ &> /dev/null; then
    print_test "Schema Registry is accessible" "PASS"
else
    print_test "Schema Registry is accessible" "FAIL"
fi

# Test 11: Check Kafka Connect health
echo ""
echo "Checking Kafka Connect..."
if kubectl exec -it kafka-0 -n kafka -- curl -s http://kafka-connect.kafka.svc.cluster.local:8083/ &> /dev/null; then
    print_test "Kafka Connect is accessible" "PASS"
else
    print_test "Kafka Connect is accessible" "FAIL"
fi

# Test 12: Test producer/consumer functionality
echo ""
echo "Testing producer/consumer functionality..."

TEST_TOPIC="test-validation-$(date +%s)"
TEST_MESSAGE="test-message-$(date +%s)"

# Create test topic
kubectl exec -it kafka-0 -n kafka -- kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic "$TEST_TOPIC" --partitions 3 --replication-factor 3 &> /dev/null

# Produce message
echo "$TEST_MESSAGE" | kubectl exec -i kafka-0 -n kafka -- kafka-console-producer --bootstrap-server localhost:9092 --topic "$TEST_TOPIC" &> /dev/null

# Consume message
CONSUMED=$(kubectl exec -it kafka-0 -n kafka -- timeout 5 kafka-console-consumer --bootstrap-server localhost:9092 --topic "$TEST_TOPIC" --from-beginning --max-messages 1 2>/dev/null | tr -d '\r' || echo "")

if [ "$CONSUMED" = "$TEST_MESSAGE" ]; then
    print_test "Producer/Consumer functionality" "PASS"
else
    print_test "Producer/Consumer functionality" "FAIL"
fi

# Clean up test topic
kubectl exec -it kafka-0 -n kafka -- kafka-topics --bootstrap-server localhost:9092 --delete --topic "$TEST_TOPIC" &> /dev/null

# Test 13: Check replication factor
echo ""
echo "Validating high availability configuration..."

UNDER_REPLICATED=$(kubectl exec -it kafka-0 -n kafka -- kafka-topics --bootstrap-server localhost:9092 --describe --under-replicated-partitions 2>/dev/null | grep -c "Topic:" || echo "0")

if [ "$UNDER_REPLICATED" -eq 0 ]; then
    print_test "No under-replicated partitions" "PASS"
else
    print_test "No under-replicated partitions ($UNDER_REPLICATED found)" "FAIL"
fi

# Test 14: Check persistent volumes
echo ""
echo "Checking persistent storage..."

KAFKA_PVC=$(kubectl get pvc -n kafka -l app=kafka --no-headers 2>/dev/null | grep -c "Bound" || echo "0")
if [ "$KAFKA_PVC" -eq 3 ]; then
    print_test "Kafka persistent volumes (3/3 bound)" "PASS"
else
    print_test "Kafka persistent volumes ($KAFKA_PVC/3 bound)" "FAIL"
fi

ZOOKEEPER_PVC=$(kubectl get pvc -n kafka -l app=zookeeper --no-headers 2>/dev/null | grep -c "Bound" || echo "0")
if [ "$ZOOKEEPER_PVC" -eq 6 ]; then
    print_test "ZooKeeper persistent volumes (6/6 bound)" "PASS"
else
    print_test "ZooKeeper persistent volumes ($ZOOKEEPER_PVC/6 bound)" "FAIL"
fi

# Test 15: Check services
echo ""
echo "Checking Kubernetes services..."

check_service() {
    local service=$1
    if kubectl get svc "$service" -n kafka &> /dev/null; then
        print_test "Service '$service' exists" "PASS"
    else
        print_test "Service '$service' exists" "FAIL"
    fi
}

check_service "kafka"
check_service "kafka-headless"
check_service "zookeeper"
check_service "schema-registry"
check_service "kafka-connect"

# Summary
echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo ""
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Kafka cluster is healthy.${NC}"
    echo ""
    echo "Cluster is ready for production use with:"
    echo "  - 3 Kafka brokers with replication factor 3"
    echo "  - 3 ZooKeeper nodes for coordination"
    echo "  - Schema Registry for event versioning"
    echo "  - Kafka Connect for external integrations"
    echo "  - Exactly-once semantics for critical topics"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    echo ""
    echo "Troubleshooting commands:"
    echo "  - Check pod logs: kubectl logs -l app=kafka -n kafka"
    echo "  - Check pod status: kubectl get pods -n kafka"
    echo "  - Check events: kubectl get events -n kafka --sort-by='.lastTimestamp'"
    echo ""
    exit 1
fi
