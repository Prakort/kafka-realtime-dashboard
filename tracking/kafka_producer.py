import json
import logging
import hashlib
import time
from typing import Dict, Optional, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """
    Production-ready Kafka producer with best practices:
    - Idempotence enabled for exactly-once semantics
    - Durability with acks=all
    - Proper partitioning with keys
    - Graceful error handling and retries
    - Structured logging for monitoring
    """
    
    def __init__(self):
        self.bootstrap_servers = getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic = getattr(settings, 'KAFKA_TOPIC_USER_EVENTS', 'user_events')
        self.producer = None
        self._metrics = {
            'messages_sent': 0,
            'messages_failed': 0,
            'retries_count': 0
        }
        
    def _get_producer(self):
        """Get or create Kafka producer with production-ready configuration"""
        if self.producer is None:
            # Check if Kafka is available first
            if not self._is_kafka_available():
                logger.info("Kafka not available, using mock producer")
                return None
                
            try:
                from confluent_kafka import Producer
                
                # Production-ready configuration with best practices
                config = {
                    # Connection settings
                    'bootstrap.servers': self.bootstrap_servers,
                    'client.id': 'dashboard_producer',
                    
                    # Durability and reliability
                    'acks': 'all',  # Wait for all replicas to acknowledge
                    'enable.idempotence': True,  # Exactly-once semantics
                    'retries': 10,  # Increased retries for reliability
                    'retry.backoff.ms': 100,
                    'max.in.flight.requests.per.connection': 1,  # Preserve order
                    
                    # Timeout settings
                    'request.timeout.ms': 30000,
                    'delivery.timeout.ms': 120000,
                    
                    # Compression and batching for performance
                    'compression.type': 'snappy',
                    'batch.size': 16384,  # 16KB
                    'linger.ms': 10,  # Wait 10ms for batching
                    
                    # Monitoring and debugging
                    'statistics.interval.ms': 30000,
                    'debug': 'msg',  # Enable message debugging
                }
                
                self.producer = Producer(config)
                logger.info(
                    "Kafka producer initialized",
                    extra={
                        'topic': self.topic,
                        'bootstrap_servers': self.bootstrap_servers,
                        'idempotence': True,
                        'acks': 'all'
                    }
                )
                
            except ImportError:
                logger.error("confluent-kafka not installed. Using mock producer.")
                self.producer = None
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}")
                self.producer = None
                
        return self.producer
    
    def send_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Send event to Kafka topic with proper partitioning and error handling
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        producer = self._get_producer()
        
        if producer is None:
            # Use mock producer if Kafka is not available
            return self._mock_send_event(event_data)
        
        try:
            # Validate event data
            if not self._validate_event_data(event_data):
                logger.error("Invalid event data", extra={'event_data': event_data})
                return False
            
            # Generate partition key for even distribution
            partition_key = self._generate_partition_key(event_data)
            
            # Add metadata for tracking
            event_data['producer_metadata'] = {
                'timestamp': time.time(),
                'producer_id': 'dashboard_producer',
                'partition_key': partition_key
            }
            
            # Convert event data to JSON
            message = json.dumps(event_data, ensure_ascii=False)
            
            # Send to Kafka with proper partitioning
            producer.produce(
                topic=self.topic,
                key=partition_key,  # Use key for partitioning
                value=message,
                callback=self._delivery_callback
            )
            
            # Flush to ensure message is sent (with timeout)
            producer.flush(timeout=10)
            
            self._metrics['messages_sent'] += 1
            
            logger.info(
                "Event sent to Kafka",
                extra={
                    'topic': self.topic,
                    'event_type': event_data.get('event_type'),
                    'user_id': event_data.get('user_id'),
                    'partition_key': partition_key,
                    'message_size': len(message)
                }
            )
            return True
            
        except Exception as e:
            self._metrics['messages_failed'] += 1
            logger.error(
                "Failed to send event to Kafka",
                extra={
                    'error': str(e),
                    'event_type': event_data.get('event_type'),
                    'user_id': event_data.get('user_id')
                }
            )
            logger.info("Falling back to mock producer")
            return self._mock_send_event(event_data)
    
    def _validate_event_data(self, event_data: Dict[str, Any]) -> bool:
        """Validate event data structure"""
        required_fields = ['user_id', 'event_type', 'timestamp']
        return all(field in event_data for field in required_fields)
    
    def _generate_partition_key(self, event_data: Dict[str, Any]) -> str:
        """
        Generate partition key for even distribution across partitions
        Combines user_id and event_type to avoid hotspots
        """
        # Use combination of user_id and event_type for better distribution
        key_data = f"{event_data.get('user_id', 'unknown')}:{event_data.get('event_type', 'unknown')}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _delivery_callback(self, err, msg):
        """Enhanced callback for message delivery confirmation with metrics"""
        if err is not None:
            self._metrics['messages_failed'] += 1
            logger.error(
                "Message delivery failed",
                extra={
                    'error': str(err),
                    'topic': msg.topic() if msg else 'unknown',
                    'partition': msg.partition() if msg else 'unknown'
                }
            )
        else:
            logger.debug(
                "Message delivered successfully",
                extra={
                    'topic': msg.topic(),
                    'partition': msg.partition(),
                    'offset': msg.offset(),
                    'key': msg.key().decode() if msg.key() else None
                }
            )
    
    def _mock_send_event(self, event_data):
        """Mock producer when Kafka is not available"""
        logger.info(f"Mock Kafka producer - sending event: {event_data['event_type']}")
        
        # Store event in a simple in-memory queue to simulate Kafka
        try:
            from .mock_kafka_queue import MockKafkaQueue
            MockKafkaQueue.add_event(event_data)
            logger.info(f"Event added to mock Kafka queue: {event_data['event_type']}")
            return True
        except Exception as e:
            logger.error(f"Failed to add event to mock queue: {e}")
            return False
    
    def _is_kafka_available(self):
        """Check if Kafka is available by trying to connect"""
        import socket
        try:
            # Try to connect to Kafka bootstrap servers
            host, port = self.bootstrap_servers.split(':')
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get producer metrics for monitoring"""
        return self._metrics.copy()
    
    def close(self):
        """Graceful shutdown of the producer"""
        if self.producer:
            try:
                # Flush any remaining messages
                self.producer.flush(timeout=30)
                logger.info("Producer closed gracefully", extra=self._metrics)
            except Exception as e:
                logger.error(f"Error during producer shutdown: {e}")
            finally:
                self.producer = None
