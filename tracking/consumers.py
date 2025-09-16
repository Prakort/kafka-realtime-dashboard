import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import UserEvent


class EventConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time event updates"""
    
    async def connect(self):
        self.room_group_name = 'event_updates'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial data
        await self.send_initial_data()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def send_initial_data(self):
        """Send the latest 20 events when client connects"""
        events = await self.get_latest_events()
        stats = await self.get_event_stats()
        
        await self.send(text_data=json.dumps({
            'type': 'initial_data',
            'events': events,
            'stats': stats
        }))
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'get_stats':
                stats = await self.get_event_stats()
                await self.send(text_data=json.dumps({
                    'type': 'stats_update',
                    'stats': stats
                }))
        except json.JSONDecodeError:
            pass
    
    async def event_update(self, event):
        """Handle event updates from Kafka consumer"""
        await self.send(text_data=json.dumps({
            'type': 'new_event',
            'event': event['event']
        }))
    
    async def stats_update(self, event):
        """Handle stats updates"""
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': event['stats']
        }))
    
    async def queue_update(self, event):
        """Handle queue updates"""
        await self.send(text_data=json.dumps({
            'type': 'queue_update',
            'queue_message': event['queue_message']
        }))
    
    @database_sync_to_async
    def get_latest_events(self):
        """Get the latest 20 events"""
        events = UserEvent.objects.all()[:20]
        return [
            {
                'id': event.id,
                'user_id': event.user_id,
                'event_type': event.event_type,
                'element_id': event.element_id,
                'timestamp': event.timestamp.isoformat(),
            }
            for event in events
        ]
    
    @database_sync_to_async
    def get_event_stats(self):
        """Get event statistics"""
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
        
        return {
            'total_events': total_events,
            'event_type_breakdown': event_type_stats,
            'top_clicked_elements': top_elements,
        }
