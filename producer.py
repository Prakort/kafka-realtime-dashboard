#!/usr/bin/env python3
"""
Kafka Producer Script for User Events

This script simulates user events and sends them to the Kafka topic.
Run this script to generate test data for the dashboard.
"""

import json
import time
import random
import argparse
from datetime import datetime
from typing import Dict, Any


class UserEventProducer:
    """Producer for user events to Kafka"""
    
    def __init__(self, bootstrap_servers: str = 'localhost:9092', topic: str = 'user_events'):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        
        # Sample data for generating realistic events
        self.user_ids = [f'user_{i:03d}' for i in range(1, 101)]  # 100 users
        self.event_types = ['page_view', 'button_click', 'form_submit']
        self.page_elements = {
            'page_view': ['home', 'products', 'about', 'contact', 'login', 'signup'],
            'button_click': [
                'btn_submit', 'btn_cancel', 'btn_save', 'btn_delete', 'btn_edit',
                'btn_login', 'btn_signup', 'btn_logout', 'btn_search', 'btn_filter',
                'btn_add_to_cart', 'btn_checkout', 'btn_continue', 'btn_back'
            ],
            'form_submit': [
                'form_login', 'form_signup', 'form_contact', 'form_feedback',
                'form_checkout', 'form_profile', 'form_password_reset'
            ]
        }
    
    def create_producer(self):
        """Create Kafka producer"""
        try:
            from confluent_kafka import Producer
            
            config = {
                'bootstrap.servers': self.bootstrap_servers,
                'client.id': 'user_event_producer'
            }
            
            self.producer = Producer(config)
            print(f"✅ Connected to Kafka at {self.bootstrap_servers}")
            return True
            
        except ImportError:
            print("❌ confluent-kafka not available. Install with: pip install confluent-kafka")
            return False
        except Exception as e:
            print(f"❌ Failed to create Kafka producer: {e}")
            return False
    
    def generate_event(self) -> Dict[str, Any]:
        """Generate a random user event"""
        event_type = random.choice(self.event_types)
        user_id = random.choice(self.user_ids)
        
        # Generate element_id based on event type
        if event_type == 'page_view':
            element_id = random.choice(self.page_elements['page_view'])
        elif event_type == 'button_click':
            element_id = random.choice(self.page_elements['button_click'])
        else:  # form_submit
            element_id = random.choice(self.page_elements['form_submit'])
        
        return {
            'user_id': user_id,
            'event_type': event_type,
            'element_id': element_id,
            'timestamp': datetime.now().isoformat()
        }
    
    def send_event(self, event: Dict[str, Any]) -> bool:
        """Send event to Kafka"""
        try:
            message = json.dumps(event).encode('utf-8')
            
            self.producer.produce(
                topic=self.topic,
                value=message,
                callback=self.delivery_callback
            )
            
            # Trigger delivery callbacks
            self.producer.poll(0)
            return True
            
        except Exception as e:
            print(f"❌ Failed to send event: {e}")
            return False
    
    def delivery_callback(self, err, msg):
        """Callback for message delivery"""
        if err:
            print(f"❌ Message delivery failed: {err}")
        else:
            print(f"✅ Event sent to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
    
    def run_mock_mode(self, duration: int = 60, interval: float = 2.0):
        """Run in mock mode (without Kafka)"""
        print(f"🎭 Running in mock mode for {duration} seconds...")
        print("📊 Events will be generated but not sent to Kafka")
        
        start_time = time.time()
        event_count = 0
        
        while time.time() - start_time < duration:
            event = self.generate_event()
            event_count += 1
            
            print(f"📝 Event {event_count}: {event['user_id']} - {event['event_type']} - {event['element_id']}")
            
            time.sleep(interval)
        
        print(f"✅ Mock mode completed. Generated {event_count} events.")
    
    def run_producer_mode(self, duration: int = 60, interval: float = 2.0):
        """Run in producer mode (with Kafka)"""
        if not self.create_producer():
            print("🔄 Falling back to mock mode...")
            self.run_mock_mode(duration, interval)
            return
        
        print(f"🚀 Running producer for {duration} seconds...")
        print(f"📡 Sending events to topic: {self.topic}")
        
        start_time = time.time()
        event_count = 0
        
        try:
            while time.time() - start_time < duration:
                event = self.generate_event()
                
                if self.send_event(event):
                    event_count += 1
                    print(f"📤 Sent event {event_count}: {event['user_id']} - {event['event_type']}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  Producer stopped by user")
        
        finally:
            if self.producer:
                # Wait for any outstanding messages to be delivered
                self.producer.flush()
                print(f"✅ Producer completed. Sent {event_count} events.")
    
    def run_continuous(self, interval: float = 2.0):
        """Run continuously until stopped"""
        if not self.create_producer():
            print("🔄 Falling back to mock mode...")
            self.run_mock_mode(duration=3600, interval=interval)  # 1 hour
            return
        
        print("🔄 Running producer continuously...")
        print("Press Ctrl+C to stop")
        print(f"📡 Sending events to topic: {self.topic}")
        
        event_count = 0
        
        try:
            while True:
                event = self.generate_event()
                
                if self.send_event(event):
                    event_count += 1
                    print(f"📤 Sent event {event_count}: {event['user_id']} - {event['event_type']}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  Producer stopped by user")
        
        finally:
            if self.producer:
                self.producer.flush()
                print(f"✅ Producer completed. Sent {event_count} events.")


def main():
    parser = argparse.ArgumentParser(description='Kafka User Event Producer')
    parser.add_argument('--bootstrap-servers', default='localhost:9092',
                       help='Kafka bootstrap servers (default: localhost:9092)')
    parser.add_argument('--topic', default='user_events',
                       help='Kafka topic name (default: user_events)')
    parser.add_argument('--duration', type=int, default=60,
                       help='Duration to run in seconds (default: 60)')
    parser.add_argument('--interval', type=float, default=2.0,
                       help='Interval between events in seconds (default: 2.0)')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuously until stopped')
    parser.add_argument('--mock', action='store_true',
                       help='Run in mock mode (no Kafka)')
    
    args = parser.parse_args()
    
    producer = UserEventProducer(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic
    )
    
    print("🎯 Kafka User Event Producer")
    print("=" * 40)
    print(f"📡 Bootstrap servers: {args.bootstrap_servers}")
    print(f"📋 Topic: {args.topic}")
    print(f"⏱️  Interval: {args.interval}s")
    
    if args.mock:
        producer.run_mock_mode(args.duration, args.interval)
    elif args.continuous:
        producer.run_continuous(args.interval)
    else:
        producer.run_producer_mode(args.duration, args.interval)


if __name__ == '__main__':
    main()
