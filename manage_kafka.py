#!/usr/bin/env python3
"""
Kafka Topic Management Script
Creates and configures Kafka topics for scalable processing
"""

import argparse
import logging
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_topic_with_partitions(bootstrap_servers: str, topic_name: str, partitions: int = 3, replication_factor: int = 1):
    """Create a Kafka topic with specified partitions"""
    try:
        from confluent_kafka.admin import AdminClient, NewTopic
        
        # Create admin client
        admin_client = AdminClient({
            'bootstrap.servers': bootstrap_servers
        })
        
        # Create topic
        topic = NewTopic(
            topic=topic_name,
            num_partitions=partitions,
            replication_factor=replication_factor
        )
        
        # Create topic
        fs = admin_client.create_topics([topic])
        
        # Wait for result
        for topic_name, f in fs.items():
            try:
                f.result()  # The result itself is None
                logger.info(f"Topic {topic_name} created successfully with {partitions} partitions")
            except Exception as e:
                logger.error(f"Failed to create topic {topic_name}: {e}")
                
    except ImportError:
        logger.error("confluent-kafka not installed. Cannot create topics.")
    except Exception as e:
        logger.error(f"Error creating topic: {e}")


def list_topics(bootstrap_servers: str):
    """List all Kafka topics"""
    try:
        from confluent_kafka.admin import AdminClient
        
        admin_client = AdminClient({
            'bootstrap.servers': bootstrap_servers
        })
        
        metadata = admin_client.list_topics(timeout=10)
        
        logger.info("Kafka Topics:")
        for topic_name, topic_metadata in metadata.topics.items():
            partitions = len(topic_metadata.partitions)
            logger.info(f"  {topic_name} - {partitions} partitions")
            
    except ImportError:
        logger.error("confluent-kafka not installed. Cannot list topics.")
    except Exception as e:
        logger.error(f"Error listing topics: {e}")


def delete_topic(bootstrap_servers: str, topic_name: str):
    """Delete a Kafka topic"""
    try:
        from confluent_kafka.admin import AdminClient
        
        admin_client = AdminClient({
            'bootstrap.servers': bootstrap_servers
        })
        
        fs = admin_client.delete_topics([topic_name])
        
        for topic_name, f in fs.items():
            try:
                f.result()
                logger.info(f"Topic {topic_name} deleted successfully")
            except Exception as e:
                logger.error(f"Failed to delete topic {topic_name}: {e}")
                
    except ImportError:
        logger.error("confluent-kafka not installed. Cannot delete topics.")
    except Exception as e:
        logger.error(f"Error deleting topic: {e}")


def main():
    parser = argparse.ArgumentParser(description='Kafka Topic Management')
    parser.add_argument('--bootstrap-servers', default='localhost:9092',
                       help='Kafka bootstrap servers')
    parser.add_argument('--action', choices=['create', 'list', 'delete'], required=True,
                       help='Action to perform')
    parser.add_argument('--topic', default='user_events',
                       help='Topic name')
    parser.add_argument('--partitions', type=int, default=3,
                       help='Number of partitions')
    parser.add_argument('--replication-factor', type=int, default=1,
                       help='Replication factor')
    
    args = parser.parse_args()
    
    if args.action == 'create':
        create_topic_with_partitions(
            args.bootstrap_servers,
            args.topic,
            args.partitions,
            args.replication_factor
        )
    elif args.action == 'list':
        list_topics(args.bootstrap_servers)
    elif args.action == 'delete':
        delete_topic(args.bootstrap_servers, args.topic)


if __name__ == '__main__':
    main()
