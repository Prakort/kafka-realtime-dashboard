from django.urls import path
from . import views

urlpatterns = [
    path('api/events/latest/', views.LatestEventsView.as_view(), name='latest_events'),
    path('api/events/create/', views.create_event, name='create_event'),
    path('api/queue/messages/', views.MessageQueueView.as_view(), name='message_queue'),
    path('api/queue/stats/', views.queue_stats, name='queue_stats'),
]
