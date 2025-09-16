# Kafka Scalability Guide

This guide explains how to scale the Kafka Real-time Dashboard for high-volume event processing.

## 🏗️ Architecture Overview

### Current Scalable Setup
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Batch         │    │   Interactive   │
│   (React)       │    │   Producer      │    │   Producer      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Kafka Topic   │
                    │   (3 Partitions)│
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Consumer 1    │    │   Consumer 2    │    │   Consumer 3    │
│   (Partition 0) │    │   (Partition 1) │    │   (Partition 2) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   Database      │
                    └─────────────────┘
```

## 🚀 Scaling Components

### 1. Multiple Producers
- **Interactive Producer**: `producer.py` - Real-time user interactions
- **Batch Producer**: `producer_batch.py` - High-volume event generation
- **Custom Producers**: Add your own producers for specific use cases

### 2. Consumer Groups
- **Consumer Group**: `dashboard_consumer_group`
- **Multiple Instances**: 3 consumers by default
- **Load Balancing**: Automatic partition assignment
- **Fault Tolerance**: Consumers can fail and recover

### 3. Topic Partitions
- **Default**: 3 partitions for `user_events` topic
- **Scalable**: Add more partitions for higher throughput
- **Ordering**: Events within a partition maintain order

## 🛠️ Configuration

### Environment Variables
```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_USER_EVENTS=user_events

# Consumer Configuration
CONSUMER_GROUP=dashboard_consumer_group
MAX_CONSUMERS=3
TOPIC_PARTITIONS=3
```

### Docker Compose Services
```yaml
# Multiple Consumers
kafka-consumer-1:
  command: python manage.py consume_kafka_scalable --consumer-id consumer-1

kafka-consumer-2:
  command: python manage.py consume_kafka_scalable --consumer-id consumer-2

kafka-consumer-3:
  command: python manage.py consume_kafka_scalable --consumer-id consumer-3

# Batch Producer
batch-producer:
  command: python producer_batch.py --mode batch --batch-size 50
```

## 📊 Performance Tuning

### Producer Configuration
```python
config = {
    'bootstrap.servers': 'kafka:9092',
    'batch.size': 16384,        # 16KB batch size
    'linger.ms': 10,            # Wait 10ms for batching
    'compression.type': 'snappy', # Compress messages
    'acks': 'all',              # Wait for all replicas
    'retries': 3,               # Retry failed sends
}
```

### Consumer Configuration
```python
config = {
    'group.id': 'dashboard_consumer_group',
    'auto.offset.reset': 'latest',
    'enable.auto.commit': True,
    'auto.commit.interval.ms': 1000,
    'session.timeout.ms': 30000,
    'max.poll.interval.ms': 300000,
    'fetch.min.bytes': 1,
    'fetch.max.bytes': 52428800,  # 50MB
}
```

## 🧪 Testing Scalability

### 1. Start the Scalable System
```bash
# Start all services
docker-compose up -d

# Check running consumers
docker-compose ps | grep consumer
```

### 2. Generate Load
```bash
# Interactive events (from frontend)
# Click buttons in the dashboard

# Batch events (from command line)
docker-compose exec batch-producer python producer_batch.py --mode batch --batch-size 100

# Continuous events
docker-compose exec batch-producer python producer_batch.py --mode continuous --events-per-second 100 --duration 300
```

### 3. Monitor Performance
```bash
# Check consumer logs
docker-compose logs kafka-consumer-1
docker-compose logs kafka-consumer-2
docker-compose logs kafka-consumer-3

# Check topic partitions
python manage_kafka.py --action list
```

## 📈 Scaling Strategies

### Horizontal Scaling (More Consumers)
```bash
# Add more consumers to docker-compose.yml
kafka-consumer-4:
  command: python manage.py consume_kafka_scalable --consumer-id consumer-4

# Scale up
docker-compose up -d kafka-consumer-4
```

### Vertical Scaling (More Partitions)
```bash
# Create topic with more partitions
python manage_kafka.py --action create --topic user_events --partitions 6

# Update consumers to handle more partitions
docker-compose restart kafka-consumer-1 kafka-consumer-2 kafka-consumer-3
```

### Producer Scaling
```bash
# Multiple batch producers
batch-producer-1:
  command: python producer_batch.py --mode continuous --events-per-second 50

batch-producer-2:
  command: python producer_batch.py --mode continuous --events-per-second 50
```

## 🔍 Monitoring

### Consumer Metrics
- **Processed Events**: Tracked per consumer
- **Error Count**: Failed message processing
- **Processing Time**: Duration per event
- **Consumer Lag**: Messages behind latest offset

### Topic Metrics
- **Partition Count**: Number of partitions
- **Message Rate**: Messages per second
- **Consumer Groups**: Active consumer groups
- **Offset Lag**: Consumer lag per partition

### Database Metrics
- **Event Count**: Total events processed
- **Queue Status**: Message queue states
- **Processing Stats**: Average processing time

## 🚨 Troubleshooting

### Common Issues

1. **Consumer Not Processing**
   ```bash
   # Check consumer logs
   docker-compose logs kafka-consumer-1
   
   # Restart consumer
   docker-compose restart kafka-consumer-1
   ```

2. **Topic Not Found**
   ```bash
   # Create topic
   python manage_kafka.py --action create --topic user_events --partitions 3
   ```

3. **Consumer Group Rebalancing**
   ```bash
   # Check consumer group status
   docker-compose exec kafka kafka-consumer-groups --bootstrap-server kafka:9092 --list
   ```

4. **High Memory Usage**
   ```bash
   # Reduce batch size
   docker-compose exec batch-producer python producer_batch.py --batch-size 25
   ```

## 🎯 Best Practices

1. **Partition Strategy**
   - Use partition key for related events
   - Balance partition count with consumer count
   - Monitor partition distribution

2. **Consumer Management**
   - Use unique consumer IDs
   - Monitor consumer health
   - Implement graceful shutdown

3. **Error Handling**
   - Retry failed messages
   - Dead letter queues for persistent failures
   - Monitor error rates

4. **Performance Monitoring**
   - Track throughput metrics
   - Monitor resource usage
   - Set up alerts for failures

## 📚 Additional Resources

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Consumer Groups](https://kafka.apache.org/documentation/#intro_consumers)
- [Partitioning](https://kafka.apache.org/documentation/#intro_topics)
- [Performance Tuning](https://kafka.apache.org/documentation/#tuning)
