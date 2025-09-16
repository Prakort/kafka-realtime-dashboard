from django.core.management.base import BaseCommand
from tracking.kafka_consumer import KafkaEventConsumer


class Command(BaseCommand):
    help = 'Start Kafka consumer for user events'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Kafka consumer...')
        )
        
        consumer = KafkaEventConsumer()
        
        try:
            consumer.start_consuming()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('Stopping Kafka consumer...')
            )
            consumer.stop_consuming()
            self.stdout.write(
                self.style.SUCCESS('Kafka consumer stopped.')
            )
