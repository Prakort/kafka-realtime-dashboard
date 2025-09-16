import { useEffect, useRef, useState, useCallback } from 'react';
import { UserEvent, EventStats, MessageQueue, WebSocketMessage } from '../types/events';

interface UseWebSocketReturn {
  events: UserEvent[];
  stats: EventStats | null;
  queueMessages: MessageQueue[];
  isConnected: boolean;
  error: string | null;
}

export const useWebSocket = (url: string): UseWebSocketReturn => {
  const [events, setEvents] = useState<UserEvent[]>([]);
  const [stats, setStats] = useState<EventStats | null>(null);
  const [queueMessages, setQueueMessages] = useState<MessageQueue[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setError(null);
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          switch (message.type) {
            case 'initial_data':
              if (message.events) {
                setEvents(message.events);
              }
              if (message.stats) {
                setStats(message.stats);
              }
              break;
              
            case 'new_event':
              if (message.event) {
                setEvents(prev => {
                  // Check if event already exists to prevent duplicates
                  const eventExists = prev.some(event => event.id === message.event!.id);
                  if (eventExists) {
                    return prev;
                  }
                  return [message.event!, ...prev].slice(0, 100); // Keep last 100 events
                });
              }
              break;
              
            case 'stats_update':
              if (message.stats) {
                setStats(message.stats);
              }
              break;
              
            case 'queue_update':
              if (message.queue_message) {
                setQueueMessages(prev => {
                  // Check if message already exists to prevent duplicates
                  const messageExists = prev.some(msg => msg.id === message.queue_message!.id);
                  if (messageExists) {
                    // Update existing message
                    return prev.map(msg => 
                      msg.id === message.queue_message!.id ? message.queue_message! : msg
                    );
                  } else {
                    // Add new message
                    return [message.queue_message!, ...prev].slice(0, 100); // Keep last 100 messages
                  }
                });
              }
              break;
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        
        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...');
          connect();
        }, 3000);
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
        setIsConnected(false);
      };

    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
      setError('Failed to create WebSocket connection');
    }
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  return { events, stats, queueMessages, isConnected, error };
};
