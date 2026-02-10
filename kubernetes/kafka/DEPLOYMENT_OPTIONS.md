# Kafka Deployment Options

## Overview

VoiceCore AI 3.0 Enterprise supports two deployment options for Apache Kafka cluster coordination:

1. **ZooKeeper-based** (Traditional, Production-proven)
2. **KRaft-based** (Modern, ZooKeeper-less)

Both options provide:
- High availability with 3-node replication
- Exactly-once semantics for critical topics
- 1M+ events/second throughput
- Schema Registry for event versioning
- Kafka Connect for external integrations

## Option 1: ZooKeeper-based Deployment (Recommended)

### Overview

The traditional Kafka deployment uses Apache ZooKeeper for cluster coordination. This is the most battle-tested and production-proven option.

### Architecture

```
┌─────────────────────────────────────────┐
│         ZooKeeper Ensemble              │
│  ┌──────────┬──────────┬──────────┐    │
│  │  ZK-0    │  ZK-1    │  ZK-2    │    │
│  └──────────┴──────────┴──────────┘    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          Kafka Brokers                  │
│  ┌──────────┬──────────┬──────────┐    │
│  │ Kafka-0  │ Kafka-1  │ Kafka-2  │    │
│  └──────────┴──────────┴──────────┘    │
└─────────────────────────────────────────┘
```

### Components

- **3 ZooKeeper nodes**: Cluster coordination and metadata management
- **3 Kafka brokers**: Message storage and processing
- **Schema Registry**: Event schema management
- **Kafka Connect**: External system integrations

### Deployment

```bash
# Deploy using the standard script
./scripts/deploy-kafka.sh

# Or manually:
kubectl apply -f kubernetes/kafka/namespace.yaml
kubectl apply -f kubernetes/kafka/zookeeper-statefulset.yaml
kubectl apply -f kubernetes/kafka/kafka-statefulset.yaml
kubectl apply -f kubernetes/kafka/schema-registry.yaml
kubectl apply -f kubernetes/kafka/kafka-connect.yaml
kubectl apply -f kubernetes/kafka/kafka-topics.yaml
kubectl apply -f kubernetes/kafka/kafka-monitoring.yaml
```

### Advantages

✅ **Production-proven**: Used by thousands of companies for years
✅ **Mature ecosystem**: Extensive tooling and documentation
✅ **Stable**: Well-understood failure modes and recovery procedures
✅ **Compatible**: Works with all Kafka versions

### Considerations

⚠️ **Additional complexity**: Requires managing separate ZooKeeper cluster
⚠️ **Resource overhead**: ZooKeeper requires additional CPU/memory
⚠️ **Operational burden**: Two systems to monitor and maintain

### Resource Requirements

- **ZooKeeper**: 3 pods × (1 CPU, 2GB RAM, 10GB storage each)
- **Kafka**: 3 pods × (4 CPU, 8GB RAM, 100GB storage each)
- **Total**: 15 CPU, 30GB RAM, 330GB storage

## Option 2: KRaft-based Deployment (Modern)

### Overview

KRaft (Kafka Raft) is the new consensus protocol that eliminates the need for ZooKeeper. It's production-ready as of Kafka 3.3+ and will become the default in future versions.

### Architecture

```
┌─────────────────────────────────────────┐
│    Kafka with KRaft (Combined Mode)     │
│  ┌──────────┬──────────┬──────────┐    │
│  │ Kafka-0  │ Kafka-1  │ Kafka-2  │    │
│  │ (Broker+ │ (Broker+ │ (Broker+ │    │
│  │Controller│Controller│Controller│    │
│  └──────────┴──────────┴──────────┘    │
└─────────────────────────────────────────┘
```

### Components

- **3 Kafka nodes**: Combined broker + controller roles
- **Schema Registry**: Event schema management
- **Kafka Connect**: External system integrations

### Deployment

```bash
# Deploy KRaft-based Kafka
kubectl apply -f kubernetes/kafka/namespace.yaml
kubectl apply -f kubernetes/kafka/kafka-kraft-statefulset.yaml
kubectl apply -f kubernetes/kafka/schema-registry.yaml
kubectl apply -f kubernetes/kafka/kafka-connect.yaml
kubectl apply -f kubernetes/kafka/kafka-topics.yaml
kubectl apply -f kubernetes/kafka/kafka-monitoring.yaml
```

### Advantages

✅ **Simplified architecture**: No separate ZooKeeper cluster
✅ **Reduced resource usage**: ~30% less CPU/memory overhead
✅ **Faster operations**: Metadata operations are 10x faster
✅ **Better scalability**: Supports millions of partitions
✅ **Future-proof**: Will be the default in Kafka 4.0+

### Considerations

⚠️ **Newer technology**: Less battle-tested than ZooKeeper
⚠️ **Migration complexity**: Migrating from ZooKeeper requires downtime
⚠️ **Tooling gaps**: Some third-party tools may not fully support KRaft yet

### Resource Requirements

- **Kafka**: 3 pods × (4 CPU, 8GB RAM, 100GB storage each)
- **Total**: 12 CPU, 24GB RAM, 300GB storage

## Comparison Matrix

| Feature | ZooKeeper | KRaft |
|---------|-----------|-------|
| **Maturity** | Production-proven (10+ years) | Production-ready (1+ year) |
| **Architecture** | Separate ZooKeeper cluster | Integrated consensus |
| **Resource Usage** | Higher (ZK + Kafka) | Lower (Kafka only) |
| **Metadata Operations** | Slower | 10x faster |
| **Max Partitions** | ~200K | Millions |
| **Operational Complexity** | Higher (2 systems) | Lower (1 system) |
| **Migration Path** | N/A | Requires downtime |
| **Kafka Version** | All versions | 3.3+ |
| **Future Support** | Deprecated in 4.0+ | Default in 4.0+ |

## Recommendation

### For Production (Current)

**Use ZooKeeper-based deployment** if:
- You need maximum stability and proven reliability
- You're using existing Kafka tooling that may not support KRaft
- You want the most extensive community support and documentation
- You're risk-averse and prefer battle-tested technology

### For New Deployments (Future-Ready)

**Use KRaft-based deployment** if:
- You want simplified operations and reduced resource usage
- You're starting fresh without existing ZooKeeper infrastructure
- You want faster metadata operations and better scalability
- You want to be ready for Kafka 4.0+ (where ZooKeeper will be removed)

### Migration Path

If you start with ZooKeeper and want to migrate to KRaft later:

1. **Upgrade to Kafka 3.3+**: Ensure you're on a KRaft-compatible version
2. **Enable dual-write mode**: Configure Kafka to write to both ZooKeeper and KRaft
3. **Migrate metadata**: Use Kafka's migration tool to copy metadata
4. **Switch to KRaft**: Update configuration to use KRaft exclusively
5. **Decommission ZooKeeper**: Remove ZooKeeper cluster

**Note**: This migration requires careful planning and typically involves downtime.

## Configuration Differences

### ZooKeeper-based Configuration

```yaml
env:
- name: KAFKA_ZOOKEEPER_CONNECT
  value: "zookeeper-0.zookeeper:2181,zookeeper-1.zookeeper:2181,zookeeper-2.zookeeper:2181"
```

### KRaft-based Configuration

```yaml
env:
- name: KAFKA_PROCESS_ROLES
  value: "broker,controller"
- name: KAFKA_CONTROLLER_QUORUM_VOTERS
  value: "0@kafka-kraft-0:9093,1@kafka-kraft-1:9093,2@kafka-kraft-2:9093"
```

## Validation

Both deployments can be validated using the same script:

```bash
./scripts/validate-kafka.sh
```

The validation script checks:
- ✅ All pods are running
- ✅ Cluster health and connectivity
- ✅ Topic configuration (partitions, replication)
- ✅ Producer/consumer functionality
- ✅ Schema Registry accessibility
- ✅ Kafka Connect accessibility
- ✅ No under-replicated partitions
- ✅ Persistent volumes are bound

## Monitoring

Both deployments use the same monitoring stack:

- **Kafka Exporter**: Prometheus metrics exporter
- **ServiceMonitor**: Prometheus Operator integration
- **PrometheusRule**: Alert rules for critical conditions
- **Grafana Dashboard**: Pre-built visualization

Key metrics monitored:
- Broker availability
- Offline partitions
- Under-replicated partitions
- Consumer lag
- Producer latency
- Disk usage
- ISR shrink rate
- Leader election rate

## High Availability Features (Both Options)

Both deployment options provide:

1. **Replication Factor 3**: All data replicated across 3 brokers
2. **Min In-Sync Replicas 2**: Requires 2 replicas to acknowledge writes
3. **Exactly-Once Semantics**: Idempotent producers and transactional writes
4. **Pod Anti-Affinity**: Ensures pods run on different nodes
5. **Persistent Storage**: StatefulSets with persistent volumes
6. **Automatic Recovery**: Kubernetes restarts failed pods automatically
7. **Rolling Updates**: Zero-downtime upgrades

## Performance Tuning (Both Options)

Both deployments are optimized for 1M+ events/second:

- **Network Threads**: 8 threads for handling requests
- **I/O Threads**: 8 threads for disk operations
- **Compression**: Snappy compression for reduced network overhead
- **Batching**: 10ms linger time for efficient batching
- **JVM Tuning**: G1GC with 4GB heap per broker
- **Partitioning**: 12-24 partitions per topic for parallelism

## Troubleshooting

### Common Issues (Both Options)

1. **Pods not starting**: Check resource availability and PVC binding
2. **Under-replicated partitions**: Check network connectivity between brokers
3. **High consumer lag**: Scale consumers or increase partitions
4. **Disk full**: Adjust retention policies or add storage

### ZooKeeper-specific Issues

- **ZooKeeper connection timeout**: Check ZooKeeper ensemble health
- **Split brain**: Ensure odd number of ZooKeeper nodes (3, 5, 7)

### KRaft-specific Issues

- **Controller election failure**: Check quorum voter configuration
- **Metadata log corruption**: Restore from backup or reformat storage

## References

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [KRaft: Apache Kafka Without ZooKeeper](https://kafka.apache.org/documentation/#kraft)
- [Kafka Improvement Proposal (KIP-500)](https://cwiki.apache.org/confluence/display/KAFKA/KIP-500%3A+Replace+ZooKeeper+with+a+Self-Managed+Metadata+Quorum)
- [Confluent Platform Documentation](https://docs.confluent.io/)

## Support

For issues or questions:
1. Check the [README.md](README.md) for basic troubleshooting
2. Review Kafka logs: `kubectl logs -l app=kafka -n kafka`
3. Check cluster events: `kubectl get events -n kafka --sort-by='.lastTimestamp'`
4. Run validation: `./scripts/validate-kafka.sh`
