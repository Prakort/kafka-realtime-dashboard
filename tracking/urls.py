from django.urls import path
from . import views
from . import monitoring

urlpatterns = [
    path('api/events/latest/', views.LatestEventsView.as_view(), name='latest_events'),
    path('api/events/create/', views.create_event, name='create_event'),
    path('api/queue/messages/', views.MessageQueueView.as_view(), name='message_queue'),
    path('api/queue/stats/', views.queue_stats, name='queue_stats'),
    
    # Monitoring and health check endpoints
    path('api/health/', monitoring.kafka_health_check, name='kafka_health'),
    path('api/metrics/', monitoring.kafka_metrics, name='kafka_metrics'),
    path('api/consumer_metrics/', monitoring.consumer_metrics, name='consumer_metrics'),
]
