from rest_framework import serializers
from .models import UserEvent, MessageQueue


class UserEventSerializer(serializers.ModelSerializer):
    """Serializer for UserEvent model"""
    
    class Meta:
        model = UserEvent
        fields = ['id', 'user_id', 'event_type', 'element_id', 'timestamp', 'created_at']
        read_only_fields = ['id', 'created_at']


class MessageQueueSerializer(serializers.ModelSerializer):
    """Serializer for MessageQueue model"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    processing_duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageQueue
        fields = [
            'id', 'message_id', 'status', 'status_display', 'source', 'source_display',
            'user_id', 'event_type', 'element_id', 'message_data',
            'queued_at', 'processing_started_at', 'completed_at',
            'processing_duration_ms', 'processing_duration_seconds',
            'error_message', 'retry_count', 'user_event'
        ]
        read_only_fields = ['id', 'queued_at', 'processing_started_at', 'completed_at', 'processing_duration_ms']
    
    def get_processing_duration_seconds(self, obj):
        if obj.processing_duration_ms:
            return round(obj.processing_duration_ms / 1000.0, 3)
        return None
