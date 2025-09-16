import React from 'react';
import { EventStats } from '../types/events';

interface StatsPanelProps {
  stats: EventStats | null;
}

const StatsPanel: React.FC<StatsPanelProps> = ({ stats }) => {
  if (!stats) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Statistics</h2>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  const getEventTypeColor = (eventType: string) => {
    switch (eventType) {
      case 'page_view':
        return 'bg-blue-500';
      case 'button_click':
        return 'bg-green-500';
      case 'form_submit':
        return 'bg-purple-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getEventTypeLabel = (eventType: string) => {
    switch (eventType) {
      case 'page_view':
        return 'Page Views';
      case 'button_click':
        return 'Button Clicks';
      case 'form_submit':
        return 'Form Submissions';
      default:
        return eventType;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold text-gray-800 mb-6">Statistics</h2>
      
      {/* Total Events */}
      <div className="mb-6">
        <div className="text-3xl font-bold text-primary-600 mb-2">
          {stats.total_events.toLocaleString()}
        </div>
        <div className="text-sm text-gray-600">Total Events</div>
      </div>

      {/* Event Type Breakdown */}
      <div className="mb-6">
        <h3 className="text-lg font-medium text-gray-700 mb-3">Event Types</h3>
        <div className="space-y-2">
          {stats.event_type_breakdown.map((item) => (
            <div key={item.event_type} className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${getEventTypeColor(item.event_type)}`}></div>
                <span className="text-sm text-gray-600">
                  {getEventTypeLabel(item.event_type)}
                </span>
              </div>
              <span className="text-sm font-medium text-gray-800">
                {item.count.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Clicked Elements */}
      {stats.top_clicked_elements.length > 0 && (
        <div>
          <h3 className="text-lg font-medium text-gray-700 mb-3">Top Clicked Elements</h3>
          <div className="space-y-2">
            {stats.top_clicked_elements.slice(0, 5).map((item, index) => (
              <div key={item.element_id} className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-gray-500 w-4">#{index + 1}</span>
                  <span className="text-sm text-gray-600 truncate max-w-32">
                    {item.element_id}
                  </span>
                </div>
                <span className="text-sm font-medium text-gray-800">
                  {item.count.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StatsPanel;
