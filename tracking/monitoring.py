"""
Kafka Monitoring and Metrics Collection
Provides Prometheus-compatible metrics and health checks
"""

import logging
from typing import Dict, Any, List
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import UserEvent, MessageQueue
from django.db.models import Count, Avg
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def kafka_health_check(request):
    """
    Health check endpoint for Kafka system
    Returns status of producers, consumers, and overall system health
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        # Check database connectivity
        try:
            event_count = UserEvent.objects.count()
            queue_count = MessageQueue.objects.count()
            health_status['components']['database'] = {
                'status': 'healthy',
                'event_count': event_count,
                'queue_count': queue_count
            }
        except Exception as e:
            health_status['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        # Check Kafka connectivity (if available)
        try:
            from .kafka_producer import KafkaEventProducer
            producer = KafkaEventProducer()
            kafka_available = producer._is_kafka_available()
            health_status['components']['kafka'] = {
                'status': 'healthy' if kafka_available else 'unavailable',
                'bootstrap_servers': producer.bootstrap_servers,
                'topic': producer.topic
            }
        except Exception as e:
            health_status['components']['kafka'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        return JsonResponse(health_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)


@require_http_methods(["GET"])
def kafka_metrics(request):
    """
    Prometheus-compatible metrics endpoint
    Returns system metrics in a format suitable for monitoring
    """
    try:
        metrics = {}
        
        # Event metrics
        total_events = UserEvent.objects.count()
        recent_events = UserEvent.objects.filter(
            timestamp__gte=datetime.now() - timedelta(minutes=5)
        ).count()
        
        # Event type breakdown
        event_type_stats = dict(
            UserEvent.objects.values('event_type')
            .annotate(count=Count('event_type'))
            .values_list('event_type', 'count')
        )
        
        # Queue metrics
        queue_stats = {
            'total': MessageQueue.objects.count(),
            'queued': MessageQueue.objects.filter(status='queued').count(),
            'processing': MessageQueue.objects.filter(status='processing').count(),
            'completed': MessageQueue.objects.filter(status='completed').count(),
            'failed': MessageQueue.objects.filter(status='failed').count()
        }
        
        # Processing time metrics
        completed_messages = MessageQueue.objects.filter(
            status='completed',
            processing_duration_ms__isnull=False
        )
        
        avg_processing_time = completed_messages.aggregate(
            avg_time=Avg('processing_duration_ms')
        )['avg_time'] or 0
        
        # Build Prometheus-style metrics
        metrics = {
            'kafka_events_total': total_events,
            'kafka_events_recent_5min': recent_events,
            'kafka_queue_total': queue_stats['total'],
            'kafka_queue_queued': queue_stats['queued'],
            'kafka_queue_processing': queue_stats['processing'],
            'kafka_queue_completed': queue_stats['completed'],
            'kafka_queue_failed': queue_stats['failed'],
            'kafka_processing_time_avg_ms': avg_processing_time,
            'kafka_event_types': event_type_stats
        }
        
        # Format for Prometheus
        prometheus_metrics = []
        for key, value in metrics.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    prometheus_metrics.append(f"{key}{{type=\"{sub_key}\"}} {sub_value}")
            else:
                prometheus_metrics.append(f"{key} {value}")
        
        return JsonResponse({
            'metrics': metrics,
            'prometheus_format': '\n'.join(prometheus_metrics),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return JsonResponse({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)


@require_http_methods(["GET"])
def consumer_metrics(request):
    """
    Get detailed metrics for individual consumers
    """
    try:
        # This would typically connect to actual consumer instances
        # For now, we'll return mock data structure
        consumer_metrics = {
            'consumers': [],
            'summary': {
                'total_consumers': 0,
                'active_consumers': 0,
                'total_messages_processed': 0,
                'total_errors': 0
            }
        }
        
        # In a real implementation, you would:
        # 1. Connect to consumer instances
        # 2. Get their metrics
        # 3. Aggregate the data
        
        return JsonResponse(consumer_metrics)
        
    except Exception as e:
        logger.error(f"Consumer metrics collection failed: {e}")
        return JsonResponse({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)
