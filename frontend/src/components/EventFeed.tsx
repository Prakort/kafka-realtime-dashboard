import React from 'react';
import { UserEvent } from '../types/events';

interface EventFeedProps {
  events: UserEvent[];
}

const EventFeed: React.FC<EventFeedProps> = ({ events }) => {
  const getEventTypeColor = (eventType: string) => {
    switch (eventType) {
      case 'page_view':
        return 'bg-blue-100 text-blue-800';
      case 'button_click':
        return 'bg-green-100 text-green-800';
      case 'form_submit':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Live Event Feed</h2>
      
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {events.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="animate-pulse">Waiting for events...</div>
          </div>
        ) : (
          events.map((event) => (
            <div
              key={event.id}
              className="border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${getEventTypeColor(
                      event.event_type
                    )}`}
                  >
                    {event.event_type.replace('_', ' ').toUpperCase()}
                  </span>
                  <span className="text-sm font-medium text-gray-700">
                    {event.user_id}
                  </span>
                </div>
                <span className="text-xs text-gray-500">
                  {formatTimestamp(event.timestamp)}
                </span>
              </div>
              
              {event.element_id && (
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Element:</span> {event.element_id}
                </div>
              )}
              
              {(event as any).message && (
                <div className="text-sm text-gray-700 mt-2 p-2 bg-gray-50 rounded">
                  <span className="font-medium">Message:</span> {(event as any).message}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default EventFeed;
