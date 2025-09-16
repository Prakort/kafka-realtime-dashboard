"""
Scalable Kafka Consumer Management Command
Supports multiple consumer instances with load balancing
"""

import os
import sys
import django
from django.core.management.base import BaseCommand
from tracking.kafka_consumer_scalable import ScalableKafkaConsumer


class Command(BaseCommand):
    help = 'Start scalable Kafka consumer with configurable consumer group and instance ID'

    def add_arguments(self, parser):
        parser.add_argument(
            '--consumer-id',
            type=str,
            default=None,
            help='Unique consumer instance ID (auto-generated if not provided)'
        )
        parser.add_argument(
            '--consumer-group',
            type=str,
            default='dashboard_consumer_group',
            help='Consumer group ID for load balancing'
        )
        parser.add_argument(
            '--max-consumers',
            type=int,
            default=3,
            help='Maximum number of consumers in the group'
        )
        parser.add_argument(
            '--partitions',
            type=int,
            default=3,
            help='Number of topic partitions'
        )

    def handle(self, *args, **options):
        consumer_id = options['consumer_id']
        consumer_group = options['consumer_group']
        max_consumers = options['max_consumers']
        partitions = options['partitions']

        self.stdout.write(
            self.style.SUCCESS(f'Starting scalable Kafka consumer...')
        )
        self.stdout.write(f'Consumer ID: {consumer_id or "auto-generated"}')
        self.stdout.write(f'Consumer Group: {consumer_group}')
        self.stdout.write(f'Max Consumers: {max_consumers}')
        self.stdout.write(f'Topic Partitions: {partitions}')

        try:
            consumer = ScalableKafkaConsumer(
                consumer_id=consumer_id,
                consumer_group=consumer_group,
                max_consumers=max_consumers,
                partitions=partitions
            )
            consumer.start_consuming()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('Consumer stopped by user')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Consumer error: {e}')
            )
