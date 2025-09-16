import React, { useState } from 'react';

interface ActionPanelProps {
  onEventCreated?: () => void;
}

const ActionPanel: React.FC<ActionPanelProps> = ({ onEventCreated }) => {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendEvent = async (eventType: string, elementId: string, customMessage?: string, delaySeconds?: number, shouldFail?: boolean) => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/events/create/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: 'dashboard_user',
          event_type: eventType,
          element_id: elementId,
          message: customMessage || `User performed ${eventType} on ${elementId}`,
          delay_seconds: delaySeconds || 0,
          should_fail: shouldFail || false
        }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Event created:', data);
        if (onEventCreated) {
          onEventCreated();
        }
      } else {
        console.error('Failed to create event:', await response.text());
      }
    } catch (error) {
      console.error('Error creating event:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = () => {
    if (message.trim()) {
      sendEvent('form_submit', 'message_input', `User sent message: "${message}"`);
      setMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Interactive Actions</h2>
      <p className="text-sm text-gray-600 mb-6">
        Click the buttons below to generate events that will appear in the real-time feed:
      </p>
      
      {/* Action Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <button
          onClick={() => sendEvent('button_click', 'button_1')}
          disabled={isLoading}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors"
        >
          Button 1
        </button>
        
        <button
          onClick={() => sendEvent('button_click', 'button_2')}
          disabled={isLoading}
          className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors"
        >
          Button 2
        </button>
        
        <button
          onClick={() => sendEvent('button_click', 'button_3')}
          disabled={isLoading}
          className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors"
        >
          Button 3
        </button>

        <button
          onClick={() => sendEvent('button_click', 'button_4', 'Button 4 - 5 second delay', 5)}
          disabled={isLoading}
          className="bg-orange-600 hover:bg-orange-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors"
        >
          Button 4 (5s delay)
        </button>

        <button
          onClick={() => sendEvent('button_click', 'button_5', 'Button 5 - Simulated failure', 0, true)}
          disabled={isLoading}
          className="bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors"
        >
          Button 5 (Failed)
        </button>
      </div>

      {/* Message Input */}
      <div className="space-y-4">
        <div>
          <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
            Send a Message
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              id="message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !message.trim()}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors"
            >
              Send Message
            </button>
          </div>
        </div>
      </div>

      {/* Additional Actions */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Quick Actions</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <button
            onClick={() => sendEvent('page_view', 'dashboard_home')}
            disabled={isLoading}
            className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 text-gray-700 px-3 py-2 rounded text-sm font-medium transition-colors"
          >
            View Home
          </button>
          
          <button
            onClick={() => sendEvent('page_view', 'dashboard_settings')}
            disabled={isLoading}
            className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 text-gray-700 px-3 py-2 rounded text-sm font-medium transition-colors"
          >
            View Settings
          </button>
          
          <button
            onClick={() => sendEvent('form_submit', 'search_form')}
            disabled={isLoading}
            className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 text-gray-700 px-3 py-2 rounded text-sm font-medium transition-colors"
          >
            Search
          </button>
          
          <button
            onClick={() => sendEvent('button_click', 'logout_button')}
            disabled={isLoading}
            className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 text-gray-700 px-3 py-2 rounded text-sm font-medium transition-colors"
          >
            Logout
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="mt-4 text-center">
          <div className="inline-flex items-center text-sm text-gray-500">
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Creating event...
          </div>
        </div>
      )}
    </div>
  );
};

export default ActionPanel;
