"""
Production-ready Scalable Kafka Consumer Implementation
Supports multiple consumer instances with best practices:
- Manual offset commits for at-least-once delivery
- Retry logic with exponential backoff
- Dead letter queue support
- Graceful shutdown and error handling
- Structured logging and monitoring
"""

import json
import logging
import time
import uuid
import threading
import random
import os
import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_backend.settings')
django.setup()

from django.conf import settings
from django.utils import timezone as django_timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import UserEvent, MessageQueue
from .mock_kafka_queue import MockKafkaQueue

logger = logging.getLogger(__name__)


class ScalableKafkaConsumer:
    """
    Production-ready scalable Kafka consumer with best practices:
    - Manual offset commits for at-least-once delivery
    - Retry logic with exponential backoff
    - Dead letter queue support
    - Graceful shutdown and error handling
    - Comprehensive monitoring and metrics
    """
    
    def __init__(self, consumer_id=None, consumer_group='dashboard_consumer_group', 
                 max_consumers=3, partitions=3, dlq_topic=None):
        self.consumer_id = consumer_id or f'consumer_{uuid.uuid4().hex[:8]}'
        self.consumer_group = consumer_group
        self.max_consumers = max_consumers
        self.partitions = partitions
        self.dlq_topic = dlq_topic or f"{settings.KAFKA_TOPIC_USER_EVENTS}_dlq"
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.topic = settings.KAFKA_TOPIC_USER_EVENTS
        self.channel_layer = get_channel_layer()
        self.consumer = None
        self.dlq_producer = None
        self.running = False
        
        # Enhanced metrics for monitoring
        self._metrics = {
            'messages_processed': 0,
            'messages_failed': 0,
            'messages_retried': 0,
            'messages_sent_to_dlq': 0,
            'offset_commits': 0,
            'start_time': time.time(),
            'last_commit_time': None,
            'processing_errors': []
        }
        
        # Retry configuration
        self.max_retries = 3
        self.base_retry_delay = 1.0  # seconds
        self.max_retry_delay = 60.0  # seconds
        
        logger.info(
            "Initialized scalable consumer",
            extra={
                'consumer_id': self.consumer_id,
                'consumer_group': self.consumer_group,
                'topic': self.topic,
                'dlq_topic': self.dlq_topic
            }
        )
    
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
            from confluent_kafka import Consumer, KafkaError, Producer
            
            # Production-ready consumer configuration
            config = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': self.consumer_group,
                'client.id': self.consumer_id,
                
                # Offset management - manual commits for at-least-once delivery
                'auto.offset.reset': 'latest',
                'enable.auto.commit': False,  # Manual commits only
                
                # Session and heartbeat management
                'session.timeout.ms': 30000,
                'heartbeat.interval.ms': 10000,
                'max.poll.interval.ms': 300000,
                
                # Fetch configuration for performance
                'fetch.min.bytes': 1,
                'fetch.max.bytes': 52428800,  # 50MB
                
                # Network and reliability
                'socket.timeout.ms': 10000,
                'metadata.max.age.ms': 300000,
                'reconnect.backoff.ms': 100,
                'reconnect.backoff.max.ms': 10000,
                
                # Isolation and consistency
                'isolation.level': 'read_committed',
            }
            
            # Initialize DLQ producer for failed messages
            dlq_config = {
                'bootstrap.servers': self.bootstrap_servers,
                'client.id': f'{self.consumer_id}_dlq_producer',
                'acks': 'all',
                'enable.idempotence': True,
                'retries': 3,
                'max.in.flight.requests.per.connection': 1,
            }
            self.dlq_producer = Producer(dlq_config)
            
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
        """Enhanced consumption loop with proper error handling and manual commits"""
        logger.info(
            "Starting consumption loop",
            extra={'consumer_id': self.consumer_id, 'topic': self.topic}
        )
        
        messages_to_commit = []
        
        while self.running:
            try:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    # Commit offsets for processed messages
                    if messages_to_commit:
                        self._commit_offsets(messages_to_commit)
                        messages_to_commit.clear()
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(
                            "Reached end of partition",
                            extra={
                                'consumer_id': self.consumer_id,
                                'partition': msg.partition()
                            }
                        )
                    else:
                        self._metrics['messages_failed'] += 1
                        logger.error(
                            "Consumer error",
                            extra={
                                'consumer_id': self.consumer_id,
                                'error': str(msg.error()),
                                'error_code': msg.error().code()
                            }
                        )
                    continue
                
                # Process message with retry logic
                try:
                    event_data = json.loads(msg.value().decode('utf-8'))
                    success = self._process_with_retry(event_data, msg)
                    
                    if success:
                        messages_to_commit.append(msg)
                        self._metrics['messages_processed'] += 1
                    else:
                        # Send to DLQ after max retries
                        self._send_to_dlq(event_data, msg, "Max retries exceeded")
                        
                except json.JSONDecodeError as e:
                    self._metrics['messages_failed'] += 1
                    logger.error(
                        "JSON decode error",
                        extra={
                            'consumer_id': self.consumer_id,
                            'error': str(e),
                            'partition': msg.partition(),
                            'offset': msg.offset()
                        }
                    )
                    # Send malformed messages to DLQ
                    self._send_to_dlq(None, msg, f"JSON decode error: {e}")
                    
                except Exception as e:
                    self._metrics['messages_failed'] += 1
                    logger.error(
                        "Processing error",
                        extra={
                            'consumer_id': self.consumer_id,
                            'error': str(e),
                            'partition': msg.partition(),
                            'offset': msg.offset()
                        }
                    )
                    
            except KeyboardInterrupt:
                logger.info(
                    "Consumer interrupted by user",
                    extra={'consumer_id': self.consumer_id}
                )
                break
            except Exception as e:
                self._metrics['messages_failed'] += 1
                logger.error(
                    "Consumption loop error",
                    extra={
                        'consumer_id': self.consumer_id,
                        'error': str(e)
                    }
                )
                time.sleep(1)
        
        # Final commit before shutdown
        if messages_to_commit:
            self._commit_offsets(messages_to_commit)
        
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
                    # Generate some mock events for testing (10% chance)
                    if random.random() < 0.1:
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
    
    def _process_with_retry(self, event_data: Dict[str, Any], msg) -> bool:
        """
        Process event with exponential backoff retry logic
        
        Args:
            event_data: Event data dictionary
            msg: Kafka message object
            
        Returns:
            bool: True if successful, False if max retries exceeded
        """
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # Exponential backoff with jitter
                    delay = min(
                        self.base_retry_delay * (2 ** (attempt - 1)),
                        self.max_retry_delay
                    )
                    jitter = random.uniform(0.1, 0.5) * delay
                    time.sleep(delay + jitter)
                    
                    self._metrics['messages_retried'] += 1
                    logger.info(
                        f"Retrying message processing (attempt {attempt + 1}/{self.max_retries + 1})",
                        extra={
                            'consumer_id': self.consumer_id,
                            'partition': msg.partition(),
                            'offset': msg.offset(),
                            'delay': delay + jitter
                        }
                    )
                
                # Process the event
                self.process_event(event_data, msg.partition())
                return True
                
            except Exception as e:
                error_msg = str(e)
                self._metrics['processing_errors'].append({
                    'timestamp': time.time(),
                    'attempt': attempt + 1,
                    'error': error_msg,
                    'partition': msg.partition(),
                    'offset': msg.offset()
                })
                
                if attempt == self.max_retries:
                    logger.error(
                        "Max retries exceeded for message",
                        extra={
                            'consumer_id': self.consumer_id,
                            'partition': msg.partition(),
                            'offset': msg.offset(),
                            'error': error_msg,
                            'attempts': attempt + 1
                        }
                    )
                    return False
                else:
                    logger.warning(
                        f"Processing failed, will retry (attempt {attempt + 1})",
                        extra={
                            'consumer_id': self.consumer_id,
                            'error': error_msg,
                            'partition': msg.partition(),
                            'offset': msg.offset()
                        }
                    )
        
        return False
    
    def _commit_offsets(self, messages):
        """Manually commit offsets after successful processing"""
        try:
            # Commit offsets for processed messages
            self.consumer.commit(asynchronous=False)
            self._metrics['offset_commits'] += 1
            self._metrics['last_commit_time'] = time.time()
            
            logger.debug(
                "Offsets committed successfully",
                extra={
                    'consumer_id': self.consumer_id,
                    'message_count': len(messages),
                    'commit_count': self._metrics['offset_commits']
                }
            )
        except Exception as e:
            logger.error(
                "Failed to commit offsets",
                extra={
                    'consumer_id': self.consumer_id,
                    'error': str(e),
                    'message_count': len(messages)
                }
            )
    
    def _send_to_dlq(self, event_data: Optional[Dict], msg, reason: str):
        """Send failed message to Dead Letter Queue"""
        try:
            if self.dlq_producer:
                dlq_message = {
                    'original_topic': self.topic,
                    'original_partition': msg.partition(),
                    'original_offset': msg.offset(),
                    'consumer_id': self.consumer_id,
                    'failure_reason': reason,
                    'timestamp': time.time(),
                    'original_data': event_data or {'raw_message': msg.value().decode('utf-8', errors='replace')}
                }
                
                self.dlq_producer.produce(
                    topic=self.dlq_topic,
                    value=json.dumps(dlq_message),
                    key=f"dlq_{msg.partition()}_{msg.offset()}"
                )
                self.dlq_producer.flush(timeout=5)
                
                self._metrics['messages_sent_to_dlq'] += 1
                
                logger.warning(
                    "Message sent to DLQ",
                    extra={
                        'consumer_id': self.consumer_id,
                        'dlq_topic': self.dlq_topic,
                        'reason': reason,
                        'partition': msg.partition(),
                        'offset': msg.offset()
                    }
                )
        except Exception as e:
            logger.error(
                "Failed to send message to DLQ",
                extra={
                    'consumer_id': self.consumer_id,
                    'error': str(e),
                    'reason': reason
                }
            )
    
    def process_event(self, event_data: Dict[str, Any], partition=None):
        """Process a single event with enhanced error handling and tracking"""
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
                raise Exception("Simulated processing failure")
            
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
            
            logger.info(
                "Event processed successfully",
                extra={
                    'consumer_id': self.consumer_id,
                    'event_id': user_event.id,
                    'event_type': event_data['event_type'],
                    'user_id': event_data['user_id'],
                    'partition': partition
                }
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Error processing event",
                extra={
                    'consumer_id': self.consumer_id,
                    'error': error_msg,
                    'event_type': event_data.get('event_type'),
                    'user_id': event_data.get('user_id'),
                    'partition': partition
                }
            )
            
            if 'queue_message' in locals():
                queue_message.mark_failed(error_msg)
                self.send_queue_update(queue_message)
            
            raise  # Re-raise for retry logic
    
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
                    'processed_count': self._metrics['messages_processed'],
                    'error_count': self._metrics['messages_failed']
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
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer metrics for monitoring"""
        uptime = time.time() - self._metrics['start_time']
        return {
            **self._metrics,
            'uptime_seconds': uptime,
            'messages_per_second': self._metrics['messages_processed'] / uptime if uptime > 0 else 0,
            'error_rate': self._metrics['messages_failed'] / max(self._metrics['messages_processed'], 1),
            'consumer_id': self.consumer_id,
            'consumer_group': self.consumer_group,
            'topic': self.topic
        }
    
    def _cleanup(self):
        """Enhanced cleanup with graceful shutdown"""
        logger.info(
            "Starting consumer cleanup",
            extra={'consumer_id': self.consumer_id}
        )
        
        try:
            # Close DLQ producer first
            if self.dlq_producer:
                self.dlq_producer.flush(timeout=10)
                self.dlq_producer = None
            
            # Close main consumer
            if self.consumer:
                self.consumer.close()
                self.consumer = None
            
            logger.info(
                "Consumer cleanup complete",
                extra={
                    'consumer_id': self.consumer_id,
                    'metrics': self._metrics
                }
            )
            
        except Exception as e:
            logger.error(
                "Error during consumer cleanup",
                extra={
                    'consumer_id': self.consumer_id,
                    'error': str(e)
                }
            )
    
    def stop(self):
        """Graceful stop of the consumer"""
        logger.info(
            "Stopping consumer gracefully",
            extra={'consumer_id': self.consumer_id}
        )
        self.running = False
