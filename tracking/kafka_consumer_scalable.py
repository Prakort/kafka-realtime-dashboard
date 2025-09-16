"""
Scalable Kafka Consumer Implementation
Supports multiple consumer instances with load balancing and partition assignment
"""

import json
import logging
import time
import uuid
import threading
from datetime import datetime, timezone
from django.conf import settings
from django.utils import timezone as django_timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import UserEvent, MessageQueue
from .mock_kafka_queue import MockKafkaQueue

logger = logging.getLogger(__name__)


class ScalableKafkaConsumer:
    """Scalable Kafka consumer with load balancing support"""
    
    def __init__(self, consumer_id=None, consumer_group='dashboard_consumer_group', 
                 max_consumers=3, partitions=3):
        self.consumer_id = consumer_id or f'consumer_{uuid.uuid4().hex[:8]}'
        self.consumer_group = consumer_group
        self.max_consumers = max_consumers
        self.partitions = partitions
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.topic = settings.KAFKA_TOPIC_USER_EVENTS
        self.channel_layer = get_channel_layer()
        self.consumer = None
        self.running = False
        self.processed_count = 0
        self.error_count = 0
        
        logger.info(f"Initialized scalable consumer: {self.consumer_id}")
    
    def _is_kafka_available(self):
        """Check if Kafka is available"""
        import socket
        try:
            host, port = self.bootstrap_servers.split(':')
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def start_consuming(self):
        """Start the Kafka consumer with scalable configuration"""
        logger.info(f"Starting scalable consumer {self.consumer_id}...")
        
        if not self._is_kafka_available():
            logger.warning(f"Kafka not available. Consumer {self.consumer_id} using mock mode.")
            self._mock_consumer()
            return
        
        try:
            from confluent_kafka import Consumer, KafkaError
            
            # Configure consumer for scalability
            config = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': self.consumer_group,
                'client.id': self.consumer_id,
                'auto.offset.reset': 'latest',
                'enable.auto.commit': True,
                'auto.commit.interval.ms': 1000,
                'session.timeout.ms': 30000,
                'heartbeat.interval.ms': 10000,
                'max.poll.interval.ms': 300000,
                'fetch.wait.max.ms': 500,
                'fetch.min.bytes': 1,
                'fetch.max.bytes': 52428800,  # 50MB
                'socket.timeout.ms': 10000,
                'metadata.max.age.ms': 300000,
            }
            
            self.consumer = Consumer(config)
            
            # Test connection and topic existence
            try:
                metadata = self.consumer.list_topics(timeout=10.0)
                if self.topic not in metadata.topics:
                    logger.warning(f"Topic {self.topic} not found. Consumer {self.consumer_id} using mock mode.")
                    self._mock_consumer()
                    return
                
                # Log partition information
                topic_metadata = metadata.topics[self.topic]
                logger.info(f"Consumer {self.consumer_id} connected. Topic partitions: {list(topic_metadata.partitions.keys())}")
                
            except Exception as e:
                logger.warning(f"Consumer {self.consumer_id} connection test failed: {e}. Using mock mode.")
                self._mock_consumer()
                return
            
            # Subscribe to topic
            self.consumer.subscribe([self.topic])
            logger.info(f"Consumer {self.consumer_id} subscribed to topic: {self.topic}")
            
            self.running = True
            self._consume_loop()
            
        except ImportError:
            logger.warning(f"confluent-kafka not available. Consumer {self.consumer_id} using mock mode.")
            self._mock_consumer()
        except Exception as e:
            logger.error(f"Consumer {self.consumer_id} failed to initialize: {e}")
            self._mock_consumer()
    
    def _consume_loop(self):
        """Main consumption loop"""
        logger.info(f"Consumer {self.consumer_id} starting consumption loop...")
        
        while self.running:
            try:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"Consumer {self.consumer_id} reached end of partition {msg.partition()}")
                    else:
                        logger.error(f"Consumer {self.consumer_id} error: {msg.error()}")
                        self.error_count += 1
                    continue
                
                # Process message
                try:
                    event_data = json.loads(msg.value().decode('utf-8'))
                    self.process_event(event_data, msg.partition())
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Consumer {self.consumer_id} JSON decode error: {e}")
                    self.error_count += 1
                except Exception as e:
                    logger.error(f"Consumer {self.consumer_id} processing error: {e}")
                    self.error_count += 1
                    
            except KeyboardInterrupt:
                logger.info(f"Consumer {self.consumer_id} interrupted by user")
                break
            except Exception as e:
                logger.error(f"Consumer {self.consumer_id} loop error: {e}")
                self.error_count += 1
                time.sleep(1)
        
        self._cleanup()
    
    def _mock_consumer(self):
        """Mock consumer for development"""
        logger.info(f"Consumer {self.consumer_id} running in mock mode")
        
        while True:
            try:
                # Check mock queue
                event_data = MockKafkaQueue.get_event(timeout=5.0)
                
                if event_data is not None:
                    logger.info(f"Consumer {self.consumer_id} received mock event: {event_data['event_type']}")
                    self.process_event(event_data, partition=0)
                else:
                    # Generate some mock events for testing
                    if hasattr(event_data, '__getitem__') and random.random() < 0.1:  # 10% chance
                        mock_event = self._generate_mock_event()
                        self.process_event(mock_event, partition=0)
                    
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info(f"Mock consumer {self.consumer_id} stopped")
                break
            except Exception as e:
                logger.error(f"Mock consumer {self.consumer_id} error: {e}")
                time.sleep(1)
    
    def _generate_mock_event(self):
        """Generate a mock event for testing"""
        import random
        
        return {
            'user_id': f'mock_user_{random.randint(1, 100)}',
            'event_type': random.choice(['page_view', 'button_click', 'form_submit']),
            'element_id': f'mock_element_{random.randint(1, 10)}',
            'message': f'Mock event from consumer {self.consumer_id}',
            'timestamp': django_timezone.now().isoformat(),
            'consumer_id': self.consumer_id,
            'batch_id': f'mock_batch_{uuid.uuid4().hex[:8]}'
        }
    
    def process_event(self, event_data, partition=None):
        """Process a single event with consumer tracking"""
        try:
            # Create MessageQueue entry
            message_id = str(uuid.uuid4())
            queue_message = MessageQueue.objects.create(
                message_id=message_id,
                status='queued',
                source='kafka',
                user_id=event_data['user_id'],
                event_type=event_data['event_type'],
                element_id=event_data.get('element_id'),
                message_data={
                    **event_data,
                    'consumer_id': self.consumer_id,
                    'partition': partition,
                    'processed_at': django_timezone.now().isoformat()
                }
            )
            
            # Mark as processing
            queue_message.mark_processing()
            self.send_queue_update(queue_message)
            
            # Apply delay if specified
            delay_seconds = event_data.get('delay_seconds', 0)
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            
            # Check if should fail
            should_fail = event_data.get('should_fail', False)
            if should_fail:
                queue_message.mark_failed("Simulated processing failure")
                self.send_queue_update(queue_message)
                logger.info(f"Consumer {self.consumer_id} simulated failure for event: {event_data['event_type']}")
                self.error_count += 1
                return
            
            # Create UserEvent
            user_event = UserEvent.objects.create(
                user_id=event_data['user_id'],
                event_type=event_data['event_type'],
                element_id=event_data.get('element_id'),
                timestamp=datetime.fromisoformat(event_data['timestamp'].replace('Z', '+00:00'))
            )
            
            # Mark as completed
            queue_message.mark_completed(user_event)
            
            # Send updates
            self.send_to_websocket(user_event)
            self.send_queue_update(queue_message)
            self.send_stats_update()
            
            self.processed_count += 1
            logger.info(f"Consumer {self.consumer_id} processed event: {user_event} (Total: {self.processed_count})")
            
        except Exception as e:
            logger.error(f"Consumer {self.consumer_id} error processing event: {e}")
            self.error_count += 1
            
            if 'queue_message' in locals():
                queue_message.mark_failed(str(e))
                self.send_queue_update(queue_message)
    
    def send_to_websocket(self, user_event):
        """Send event update to WebSocket clients"""
        try:
            async_to_sync(self.channel_layer.group_send)(
                'event_updates',
                {
                    'type': 'event_update',
                    'event': {
                        'id': user_event.id,
                        'user_id': user_event.user_id,
                        'event_type': user_event.event_type,
                        'element_id': user_event.element_id,
                        'timestamp': user_event.timestamp.isoformat(),
                        'consumer_id': self.consumer_id
                    }
                }
            )
        except Exception as e:
            logger.error(f"Consumer {self.consumer_id} WebSocket error: {e}")
    
    def send_queue_update(self, queue_message):
        """Send queue update to WebSocket clients"""
        try:
            queue_data = {
                'id': str(queue_message.id),
                'message_id': queue_message.message_id,
                'status': queue_message.status,
                'source': queue_message.source,
                'user_id': queue_message.user_id,
                'event_type': queue_message.event_type,
                'element_id': queue_message.element_id,
                'queued_at': queue_message.queued_at.isoformat(),
                'processing_started_at': queue_message.processing_started_at.isoformat() if queue_message.processing_started_at else None,
                'completed_at': queue_message.completed_at.isoformat() if queue_message.completed_at else None,
                'processing_duration_ms': queue_message.processing_duration_ms,
                'error_message': queue_message.error_message,
                'retry_count': queue_message.retry_count,
                'consumer_id': self.consumer_id
            }
            
            async_to_sync(self.channel_layer.group_send)(
                'event_updates',
                {
                    'type': 'queue_update',
                    'queue_message': queue_data
                }
            )
        except Exception as e:
            logger.error(f"Consumer {self.consumer_id} queue update error: {e}")
    
    def send_stats_update(self):
        """Send stats update to WebSocket clients"""
        try:
            from django.db.models import Count
            
            total_events = UserEvent.objects.count()
            event_type_stats = list(
                UserEvent.objects.values('event_type').annotate(
                    count=Count('event_type')
                ).order_by('-count')
            )
            
            top_elements = list(
                UserEvent.objects.filter(
                    element_id__isnull=False
                ).values('element_id').annotate(
                    count=Count('element_id')
                ).order_by('-count')[:10]
            )
            
            stats = {
                'total_events': total_events,
                'event_type_breakdown': event_type_stats,
                'top_clicked_elements': top_elements,
                'consumer_stats': {
                    'consumer_id': self.consumer_id,
                    'processed_count': self.processed_count,
                    'error_count': self.error_count
                }
            }
            
            async_to_sync(self.channel_layer.group_send)(
                'event_updates',
                {
                    'type': 'stats_update',
                    'stats': stats
                }
            )
        except Exception as e:
            logger.error(f"Consumer {self.consumer_id} stats update error: {e}")
    
    def _cleanup(self):
        """Clean up consumer resources"""
        logger.info(f"Consumer {self.consumer_id} cleaning up...")
        if self.consumer:
            self.consumer.close()
        logger.info(f"Consumer {self.consumer_id} cleanup complete. Processed: {self.processed_count}, Errors: {self.error_count}")
    
    def stop(self):
        """Stop the consumer"""
        logger.info(f"Stopping consumer {self.consumer_id}...")
        self.running = False
