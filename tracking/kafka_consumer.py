import json
import asyncio
import logging
import time
import random
import uuid
from datetime import datetime, timezone
from django.conf import settings
from django.utils import timezone as django_timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import UserEvent, MessageQueue

logger = logging.getLogger(__name__)


class KafkaEventConsumer:
    """Kafka consumer for user events"""
    
    def __init__(self):
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.topic = settings.KAFKA_TOPIC_USER_EVENTS
        self.channel_layer = get_channel_layer()
        self.consumer = None
    
    def start_consuming(self):
        """Start consuming messages from Kafka"""
        # First, try to check if Kafka is available
        if not self._is_kafka_available():
            logger.warning("Kafka is not available. Using mock consumer.")
            self.mock_consumer()
            return
            
        try:
            from confluent_kafka import Consumer, KafkaError
            
            # Configure consumer with connection timeout
            config = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': 'dashboard_consumer_group',
                'auto.offset.reset': 'latest',
                'enable.auto.commit': True,
                'socket.timeout.ms': 5000,  # 5 second timeout
                'session.timeout.ms': 10000,  # 10 second session timeout
            }
            
            self.consumer = Consumer(config)
            
            # Test connection by getting metadata (doesn't require messages)
            try:
                metadata = self.consumer.list_topics(timeout=5.0)
                if self.topic not in metadata.topics:
                    logger.warning(f"Topic {self.topic} not found. Using mock consumer.")
                    self.mock_consumer()
                    return
                logger.info(f"Successfully connected to Kafka. Topic {self.topic} exists.")
            except Exception as e:
                logger.warning(f"Could not connect to Kafka: {e}. Using mock consumer.")
                self.mock_consumer()
                return
            
            # Subscribe to topic after confirming it exists
            self.consumer.subscribe([self.topic])
            logger.info(f"Started consuming from topic: {self.topic}")
            
            # Main consumer loop
            while True:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.info(f"Reached end of partition {msg.partition()}")
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        logger.warning("Kafka connection error. Using mock consumer.")
                        self.mock_consumer()
                        return
                    continue
                
                try:
                    # Parse message
                    event_data = json.loads(msg.value().decode('utf-8'))
                    self.process_event(event_data)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except ImportError:
            logger.warning("confluent-kafka not available. Using mock consumer.")
            self.mock_consumer()
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}")
            logger.warning("Falling back to mock consumer due to Kafka connection issues.")
            self.mock_consumer()
    
    def _is_kafka_available(self):
        """Check if Kafka is available by trying to connect"""
        import socket
        try:
            # Parse bootstrap servers (e.g., "kafka:9092" or "localhost:9092")
            host, port = self.bootstrap_servers.split(':')
            port = int(port)
            
            # Try to connect to Kafka port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 2 second timeout
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def mock_consumer(self):
        """Mock consumer for development when Kafka is not available"""
        logger.info("Mock Kafka consumer running - consuming from mock queue")
        
        from .mock_kafka_queue import MockKafkaQueue
        
        while True:
            try:
                # Try to get an event from the mock queue
                logger.info("Mock consumer checking for events...")
                event_data = MockKafkaQueue.get_event(timeout=5.0)
                
                if event_data is not None:
                    logger.info(f"Mock consumer received event: {event_data['event_type']}")
                    self.process_event(event_data)
                else:
                    # No events in queue, sleep briefly
                    logger.info("Mock consumer: No events in queue, sleeping...")
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("Mock consumer stopped")
                break
            except Exception as e:
                logger.error(f"Mock consumer error: {e}")
                time.sleep(1)
    
    def process_event(self, event_data):
        """Process a single event"""
        try:
            # Create MessageQueue entry to track Kafka processing
            message_id = str(uuid.uuid4())
            queue_message = MessageQueue.objects.create(
                message_id=message_id,
                status='queued',
                source='kafka',
                user_id=event_data['user_id'],
                event_type=event_data['event_type'],
                element_id=event_data.get('element_id'),
                message_data=event_data
            )
            
            # Mark as processing to set processing_started_at timestamp
            queue_message.mark_processing()
            
            # Send initial queue update
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
                logger.info(f"Simulated failure for event: {event_data['event_type']}")
                return
            
            # Save to database
            user_event = UserEvent.objects.create(
                user_id=event_data['user_id'],
                event_type=event_data['event_type'],
                element_id=event_data.get('element_id'),
                timestamp=datetime.fromisoformat(event_data['timestamp'].replace('Z', '+00:00'))
            )
            
            # Mark queue message as completed
            queue_message.mark_completed(user_event)
            
            # Send to WebSocket clients
            self.send_to_websocket(user_event)
            
            # Send queue update
            self.send_queue_update(queue_message)
            
            # Send stats update
            self.send_stats_update()
            
            logger.info(f"Processed Kafka event: {user_event}")
            
        except Exception as e:
            logger.error(f"Error processing event {event_data}: {e}")
            # Mark as failed if we have a queue message
            if 'queue_message' in locals():
                queue_message.mark_failed(str(e))
                self.send_queue_update(queue_message)
    
    def send_to_websocket(self, user_event):
        """Send event to WebSocket clients"""
        try:
            event_data = {
                'id': user_event.id,
                'user_id': user_event.user_id,
                'event_type': user_event.event_type,
                'element_id': user_event.element_id,
                'timestamp': user_event.timestamp.isoformat(),
            }
            
            async_to_sync(self.channel_layer.group_send)(
                'event_updates',
                {
                    'type': 'event_update',
                    'event': event_data
                }
            )
            
            # Send updated stats every 10 events
            if user_event.id % 10 == 0:
                self.send_stats_update()
                
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")
    
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
            }
            
            async_to_sync(self.channel_layer.group_send)(
                'event_updates',
                {
                    'type': 'queue_update',
                    'queue_message': queue_data
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending queue update to WebSocket: {e}")
    
    def send_stats_update(self):
        """Send updated statistics to WebSocket clients"""
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
            }
            
            async_to_sync(self.channel_layer.group_send)(
                'event_updates',
                {
                    'type': 'stats_update',
                    'stats': stats
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending stats update: {e}")
    
    def stop_consuming(self):
        """Stop consuming messages"""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer stopped")
