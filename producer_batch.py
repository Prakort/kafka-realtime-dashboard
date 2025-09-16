#!/usr/bin/env python3
"""
Batch Event Producer for Kafka Real-time Dashboard
This producer simulates high-volume event generation for testing scalability.
"""

import json
import time
import random
import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, List
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Event types for batch generation
EVENT_TYPES = ['page_view', 'button_click', 'form_submit', 'api_call', 'user_login']
ELEMENT_IDS = [
    'header_nav', 'footer_links', 'search_box', 'product_card', 'checkout_btn',
    'login_form', 'signup_btn', 'profile_menu', 'notification_bell', 'cart_icon'
]
USER_IDS = [f'user_{i:04d}' for i in range(1, 1001)]  # 1000 users
MESSAGES = [
    'User interaction detected',
    'Navigation event captured',
    'Form submission processed',
    'API endpoint accessed',
    'Authentication event logged'
]


class BatchEventProducer:
    """High-volume event producer for testing Kafka scalability"""
    
    def __init__(self, bootstrap_servers: str = 'localhost:9092', topic: str = 'user_events'):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        self.event_count = 0
        
    def _get_producer(self):
        """Get or create Kafka producer"""
        if self.producer is None:
            try:
                from confluent_kafka import Producer
                
                config = {
                    'bootstrap.servers': self.bootstrap_servers,
                    'client.id': f'batch_producer_{uuid.uuid4().hex[:8]}',
                    'acks': 'all',
                    'retries': 3,
                    'retry.backoff.ms': 100,
                    'request.timeout.ms': 5000,
                    'batch.size': 16384,  # 16KB batch size
                    'linger.ms': 10,      # Wait 10ms for batching
                }
                
                self.producer = Producer(config)
                logger.info(f"Batch producer initialized for topic: {self.topic}")
                
            except ImportError:
                logger.warning("confluent-kafka not available. Using mock mode.")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize producer: {e}")
                return None
        
        return self.producer
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation"""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            self.event_count += 1
            if self.event_count % 100 == 0:
                logger.info(f"Successfully sent {self.event_count} events")
    
    def generate_batch_event(self) -> Dict:
        """Generate a single batch event"""
        return {
            'user_id': random.choice(USER_IDS),
            'event_type': random.choice(EVENT_TYPES),
            'element_id': random.choice(ELEMENT_IDS),
            'message': random.choice(MESSAGES),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'batch_id': f'batch_{uuid.uuid4().hex[:8]}',
            'producer_id': 'batch_producer',
            'session_id': f'session_{random.randint(1000, 9999)}',
            'metadata': {
                'user_agent': f'Browser_{random.randint(1, 5)}',
                'ip_address': f'192.168.1.{random.randint(1, 254)}',
                'response_time': random.randint(50, 500)
            }
        }
    
    def send_event(self, event_data: Dict) -> bool:
        """Send event to Kafka"""
        producer = self._get_producer()
        
        if producer is None:
            logger.info(f"Mock sending event: {event_data['event_type']}")
            return True
        
        try:
            message = json.dumps(event_data)
            
            producer.produce(
                topic=self.topic,
                value=message,
                callback=self._delivery_callback
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
            return False
    
    def flush(self):
        """Flush pending messages"""
        if self.producer:
            self.producer.flush(timeout=10)
            logger.info(f"Flushed producer. Total events sent: {self.event_count}")
    
    def generate_batch(self, batch_size: int = 100, interval: float = 0.1):
        """Generate a batch of events"""
        logger.info(f"Generating batch of {batch_size} events...")
        
        for i in range(batch_size):
            event = self.generate_batch_event()
            self.send_event(event)
            
            if interval > 0:
                time.sleep(interval)
        
        self.flush()
        logger.info(f"Batch completed. Sent {batch_size} events")
    
    def continuous_generation(self, events_per_second: int = 50, duration: int = 60):
        """Generate events continuously"""
        logger.info(f"Starting continuous generation: {events_per_second} events/sec for {duration} seconds")
        
        start_time = time.time()
        end_time = start_time + duration
        interval = 1.0 / events_per_second
        
        while time.time() < end_time:
            event = self.generate_batch_event()
            self.send_event(event)
            time.sleep(interval)
        
        self.flush()
        logger.info(f"Continuous generation completed. Total events: {self.event_count}")


def main():
    parser = argparse.ArgumentParser(description='Batch Event Producer for Kafka Dashboard')
    parser.add_argument('--bootstrap-servers', default='localhost:9092',
                       help='Kafka bootstrap servers')
    parser.add_argument('--topic', default='user_events',
                       help='Kafka topic name')
    parser.add_argument('--mode', choices=['batch', 'continuous'], default='batch',
                       help='Generation mode')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Number of events per batch')
    parser.add_argument('--events-per-second', type=int, default=50,
                       help='Events per second for continuous mode')
    parser.add_argument('--duration', type=int, default=60,
                       help='Duration in seconds for continuous mode')
    parser.add_argument('--interval', type=float, default=0.1,
                       help='Interval between events in batch mode')
    
    args = parser.parse_args()
    
    producer = BatchEventProducer(args.bootstrap_servers, args.topic)
    
    try:
        if args.mode == 'batch':
            producer.generate_batch(args.batch_size, args.interval)
        else:
            producer.continuous_generation(args.events_per_second, args.duration)
            
    except KeyboardInterrupt:
        logger.info("Producer stopped by user")
    except Exception as e:
        logger.error(f"Producer error: {e}")
    finally:
        producer.flush()


if __name__ == '__main__':
    main()
