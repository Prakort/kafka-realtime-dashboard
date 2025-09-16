import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """Kafka producer for sending user events to Kafka topic"""
    
    def __init__(self):
        self.bootstrap_servers = getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic = getattr(settings, 'KAFKA_TOPIC_USER_EVENTS', 'user_events')
        self.producer = None
        
    def _get_producer(self):
        """Get or create Kafka producer"""
        if self.producer is None:
            # Check if Kafka is available first
            if not self._is_kafka_available():
                logger.info("Kafka not available, using mock producer")
                return None
                
            try:
                from confluent_kafka import Producer
                
                config = {
                    'bootstrap.servers': self.bootstrap_servers,
                    'client.id': 'dashboard_producer',
                    'acks': 'all',  # Wait for all replicas to acknowledge
                    'retries': 3,
                    'retry.backoff.ms': 100,
                    'request.timeout.ms': 5000,
                }
                
                self.producer = Producer(config)
                logger.info(f"Kafka producer initialized for topic: {self.topic}")
                
            except ImportError:
                logger.error("confluent-kafka not installed. Using mock producer.")
                self.producer = None
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}")
                self.producer = None
                
        return self.producer
    
    def send_event(self, event_data):
        """Send event to Kafka topic"""
        producer = self._get_producer()
        
        if producer is None:
            # Use mock producer if Kafka is not available
            return self._mock_send_event(event_data)
        
        try:
            # Convert event data to JSON
            message = json.dumps(event_data)
            
            # Send to Kafka
            producer.produce(
                topic=self.topic,
                value=message,
                callback=self._delivery_callback
            )
            
            # Flush to ensure message is sent
            producer.flush(timeout=5)
            
            logger.info(f"Event sent to Kafka topic {self.topic}: {event_data['event_type']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send event to Kafka: {e}")
            logger.info("Falling back to mock producer")
            return self._mock_send_event(event_data)
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation"""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")
    
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
    
    def close(self):
        """Close the producer"""
        if self.producer:
            self.producer.flush()
            self.producer = None
