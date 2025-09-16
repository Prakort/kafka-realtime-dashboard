from django.db import models
from django.utils import timezone
import uuid


class UserEvent(models.Model):
    """Model to store user events from Kafka"""
    
    EVENT_TYPE_CHOICES = [
        ('page_view', 'Page View'),
        ('button_click', 'Button Click'),
        ('form_submit', 'Form Submit'),
    ]
    
    user_id = models.CharField(max_length=255, db_index=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, db_index=True)
    element_id = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user_id', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user_id} - {self.event_type} - {self.timestamp}"


class MessageQueue(models.Model):
    """Model to track message states in the queue"""
    
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    SOURCE_CHOICES = [
        ('kafka', 'Kafka'),
        ('api', 'API'),
        ('mock', 'Mock'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message_id = models.CharField(max_length=255, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued', db_index=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='api')
    
    # Message content
    user_id = models.CharField(max_length=255, db_index=True)
    event_type = models.CharField(max_length=50, db_index=True)
    element_id = models.CharField(max_length=255, blank=True, null=True)
    message_data = models.JSONField(default=dict)
    
    # Timestamps
    queued_at = models.DateTimeField(default=timezone.now, db_index=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Processing info
    processing_duration_ms = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    
    # Related event (if successfully processed)
    user_event = models.ForeignKey(UserEvent, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-queued_at']
        indexes = [
            models.Index(fields=['status', 'queued_at']),
            models.Index(fields=['source', 'status']),
            models.Index(fields=['user_id', 'queued_at']),
        ]
    
    def __str__(self):
        return f"{self.message_id} - {self.status} - {self.event_type}"
    
    @property
    def is_processing(self):
        return self.status == 'processing'
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def is_failed(self):
        return self.status == 'failed'
    
    def mark_processing(self):
        """Mark message as being processed"""
        self.status = 'processing'
        self.processing_started_at = timezone.now()
        self.save(update_fields=['status', 'processing_started_at'])
    
    def mark_completed(self, user_event=None):
        """Mark message as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if user_event:
            self.user_event = user_event
        
        if self.processing_started_at:
            duration = self.completed_at - self.processing_started_at
            self.processing_duration_ms = int(duration.total_seconds() * 1000)
        
        self.save(update_fields=['status', 'completed_at', 'user_event', 'processing_duration_ms'])
    
    def mark_failed(self, error_message=None):
        """Mark message as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.retry_count += 1
        
        if self.processing_started_at:
            duration = self.completed_at - self.processing_started_at
            self.processing_duration_ms = int(duration.total_seconds() * 1000)
        
        self.save(update_fields=['status', 'completed_at', 'error_message', 'retry_count', 'processing_duration_ms'])