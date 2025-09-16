import React, { useState, useEffect } from 'react';
import { MessageQueue, QueueStats } from '../types/events';

interface QueueMonitorProps {
  queueMessages: MessageQueue[];
  queueStats: QueueStats | null;
}

const QueueMonitor: React.FC<QueueMonitorProps> = ({ queueMessages, queueStats }) => {
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [selectedSource, setSelectedSource] = useState<string>('');
  const [filteredMessages, setFilteredMessages] = useState<MessageQueue[]>([]);

  useEffect(() => {
    let filtered = queueMessages;

    if (selectedStatus) {
      filtered = filtered.filter(msg => msg.status === selectedStatus);
    }

    if (selectedSource) {
      filtered = filtered.filter(msg => msg.source === selectedSource);
    }

    setFilteredMessages(filtered);
  }, [queueMessages, selectedStatus, selectedSource]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'queued':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'processing':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'kafka':
        return 'bg-purple-100 text-purple-800';
      case 'api':
        return 'bg-blue-100 text-blue-800';
      case 'mock':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Message Queue Monitor</h2>
      
      {/* Queue Statistics */}
      {queueStats && (
        <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{queueStats.total_messages}</div>
            <div className="text-sm text-blue-600">Total Messages</div>
          </div>
          <div className="bg-yellow-50 p-3 rounded-lg">
            <div className="text-2xl font-bold text-yellow-600">{queueStats.queued_count}</div>
            <div className="text-sm text-yellow-600">Queued</div>
          </div>
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{queueStats.currently_processing}</div>
            <div className="text-sm text-blue-600">Processing</div>
          </div>
          <div className="bg-green-50 p-3 rounded-lg">
            <div className="text-2xl font-bold text-green-600">
              {queueStats.status_breakdown.completed || 0}
            </div>
            <div className="text-sm text-green-600">Completed</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Status Filter:</label>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Source Filter:</label>
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          >
            <option value="">All Sources</option>
            <option value="kafka">Kafka</option>
            <option value="api">API</option>
            <option value="mock">Mock</option>
          </select>
        </div>
      </div>

      {/* Message List */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {filteredMessages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No messages found with current filters
          </div>
        ) : (
          filteredMessages.map((message) => (
            <div
              key={message.id}
              className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(message.status)}`}>
                    {message.status_display}
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSourceColor(message.source)}`}>
                    {message.source_display}
                  </span>
                  <span className="text-sm text-gray-600">
                    {message.user_id} - {message.event_type}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  {formatTimestamp(message.queued_at)}
                </div>
              </div>

              {message.element_id && (
                <div className="text-sm text-gray-600 mb-2">
                  <span className="font-medium">Element:</span> {message.element_id}
                </div>
              )}

              {message.message_data?.message && (
                <div className="text-sm text-gray-700 mb-2 p-2 bg-gray-50 rounded">
                  <span className="font-medium">Message:</span> {message.message_data.message}
                </div>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-gray-600">
                <div>
                  <span className="font-medium">Processing:</span>
                  <br />
                  {formatTimestamp(message.processing_started_at)}
                </div>
                <div>
                  <span className="font-medium">Completed:</span>
                  <br />
                  {formatTimestamp(message.completed_at)}
                </div>
                <div>
                  <span className="font-medium">Duration:</span>
                  <br />
                  {formatDuration(message.processing_duration_ms)}
                </div>
                <div>
                  <span className="font-medium">Retries:</span>
                  <br />
                  {message.retry_count}
                </div>
              </div>

              {message.error_message && (
                <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                  <span className="font-medium">Error:</span> {message.error_message}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default QueueMonitor;
