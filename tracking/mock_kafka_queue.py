import queue
import threading
import logging

logger = logging.getLogger(__name__)


class MockKafkaQueue:
    """In-memory queue to simulate Kafka for development"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._queue = queue.Queue()
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._queue = queue.Queue()
            self._initialized = True
    
    @classmethod
    def add_event(cls, event_data):
        """Add an event to the mock queue"""
        instance = cls()
        instance._queue.put(event_data)
        logger.debug(f"Event added to mock queue: {event_data.get('event_type', 'unknown')}")
    
    @classmethod
    def get_event(cls, timeout=None):
        """Get an event from the mock queue"""
        instance = cls()
        try:
            return instance._queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    @classmethod
    def is_empty(cls):
        """Check if the queue is empty"""
        instance = cls()
        return instance._queue.empty()
    
    @classmethod
    def size(cls):
        """Get the current size of the queue"""
        instance = cls()
        return instance._queue.qsize()
    
    @classmethod
    def clear(cls):
        """Clear all events from the queue"""
        instance = cls()
        while not instance._queue.empty():
            try:
                instance._queue.get_nowait()
            except queue.Empty:
                break
        logger.info("Mock Kafka queue cleared")
