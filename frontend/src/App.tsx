import React from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import EventFeed from './components/EventFeed';
import StatsPanel from './components/StatsPanel';
import ConnectionStatus from './components/ConnectionStatus';
import ActionPanel from './components/ActionPanel';
import QueueMonitor from './components/QueueMonitor';

function App() {
  const { events, stats, queueMessages, isConnected, error } = useWebSocket(
    'ws://localhost:8000/ws/events/'
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Kafka Real-time Dashboard
              </h1>
              <p className="text-sm text-gray-600">
                Live user action tracking with WebSocket updates
              </p>
            </div>
            <ConnectionStatus isConnected={isConnected} error={error} />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Action Panel - Full width at top */}
        <div className="mb-8">
          <ActionPanel />
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Event Feed - Takes 2 columns on large screens */}
          <div className="lg:col-span-2">
            <EventFeed events={events} />
          </div>
          
          {/* Stats Panel - Takes 1 column on large screens */}
          <div className="lg:col-span-1">
            <StatsPanel stats={stats} />
          </div>
        </div>

        {/* Queue Monitor - Full width below */}
        <div className="mt-8">
          <QueueMonitor queueMessages={queueMessages} queueStats={null} />
        </div>

        {/* Instructions */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-blue-900 mb-2">
            Interactive Dashboard Instructions:
          </h3>
          <div className="text-sm text-blue-800 space-y-1">
            <p>1. Use the <strong>Interactive Actions</strong> panel above to generate events</p>
            <p>2. Click <strong>Button 1, 2, or 3</strong> to simulate button clicks</p>
            <p>3. Type a message and click <strong>Send Message</strong> to create form submissions</p>
            <p>4. Use <strong>Quick Actions</strong> for common user behaviors</p>
            <p>5. Watch your events appear in real-time in the feed below!</p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
