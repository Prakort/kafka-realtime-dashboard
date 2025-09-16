from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Avg
from django.utils import timezone
import uuid
from .models import UserEvent, MessageQueue
from .serializers import UserEventSerializer, MessageQueueSerializer


class LatestEventsView(generics.ListAPIView):
    """API view to get the latest 50 events"""
    
    serializer_class = UserEventSerializer
    
    def get_queryset(self):
        return UserEvent.objects.all()[:50]
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Get aggregate statistics
        total_events = UserEvent.objects.count()
        event_type_stats = UserEvent.objects.values('event_type').annotate(
            count=Count('event_type')
        ).order_by('-count')
        
        top_elements = UserEvent.objects.filter(
            element_id__isnull=False
        ).values('element_id').annotate(
            count=Count('element_id')
        ).order_by('-count')[:10]
        
        return Response({
            'events': serializer.data,
            'stats': {
                'total_events': total_events,
                'event_type_breakdown': list(event_type_stats),
                'top_clicked_elements': list(top_elements),
            }
        })


@api_view(['POST'])
def create_event(request):
    """API endpoint to create a new event from frontend actions"""
    import asyncio
    import threading
    
    try:
        # Get data from request
        user_id = request.data.get('user_id', 'frontend_user')
        event_type = request.data.get('event_type')
        element_id = request.data.get('element_id')
        message = request.data.get('message', '')
        delay_seconds = request.data.get('delay_seconds', 0)
        should_fail = request.data.get('should_fail', False)
        
        # Validate required fields
        if not event_type:
            return Response(
                {'error': 'event_type is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Send event to Kafka (no database writes yet)
        from .kafka_producer import KafkaEventProducer
        
        producer = KafkaEventProducer()
        success = producer.send_event({
            'user_id': user_id,
            'event_type': event_type,
            'element_id': element_id,
            'message': message,
            'delay_seconds': delay_seconds,
            'should_fail': should_fail,
            'timestamp': timezone.now().isoformat()
        })
        
        if not success:
            return Response(
                {'error': 'Failed to send event to Kafka'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'success': True,
            'message': 'Event sent to Kafka for processing',
            'event_data': {
                'user_id': user_id,
                'event_type': event_type,
                'element_id': element_id,
                'message': message
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class MessageQueueView(generics.ListAPIView):
    """API view to get message queue status"""
    
    serializer_class = MessageQueueSerializer
    queryset = MessageQueue.objects.all()
    
    def get_queryset(self):
        queryset = MessageQueue.objects.all()
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by source if provided
        source_filter = self.request.query_params.get('source')
        if source_filter:
            queryset = queryset.filter(source=source_filter)
        
        # Limit to recent messages if no specific filters
        if not status_filter and not source_filter:
            queryset = queryset[:100]  # Show last 100 messages
        
        return queryset


@api_view(['GET'])
def queue_stats(request):
    """Get queue statistics"""
    try:
        # Get counts by status
        status_counts = dict(
            MessageQueue.objects.values('status').annotate(
                count=Count('status')
            ).values_list('status', 'count')
        )
        
        # Get counts by source
        source_counts = dict(
            MessageQueue.objects.values('source').annotate(
                count=Count('source')
            ).values_list('source', 'count')
        )
        
        # Get processing times for completed messages
        completed_messages = MessageQueue.objects.filter(
            status='completed',
            processing_duration_ms__isnull=False
        )
        
        avg_processing_time = None
        if completed_messages.exists():
            avg_processing_time = completed_messages.aggregate(
                avg_time=Avg('processing_duration_ms')
            )['avg_time']
        
        # Get failed messages with retry counts
        failed_messages = MessageQueue.objects.filter(status='failed')
        avg_retry_count = None
        if failed_messages.exists():
            avg_retry_count = failed_messages.aggregate(
                avg_retries=Avg('retry_count')
            )['avg_retries']
        
        stats = {
            'total_messages': MessageQueue.objects.count(),
            'status_breakdown': status_counts,
            'source_breakdown': source_counts,
            'avg_processing_time_ms': avg_processing_time,
            'avg_retry_count': avg_retry_count,
            'currently_processing': MessageQueue.objects.filter(status='processing').count(),
            'queued_count': MessageQueue.objects.filter(status='queued').count(),
        }
        
        return Response(stats)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )