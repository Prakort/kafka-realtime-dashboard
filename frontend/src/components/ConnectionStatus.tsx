import React from 'react';

interface ConnectionStatusProps {
  isConnected: boolean;
  error: string | null;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ isConnected, error }) => {
  return (
    <div className="flex items-center space-x-2">
      <div
        className={`w-3 h-3 rounded-full ${
          isConnected ? 'bg-green-500' : 'bg-red-500'
        }`}
      ></div>
      <span className="text-sm text-gray-600">
        {isConnected ? 'Connected' : error || 'Disconnected'}
      </span>
    </div>
  );
};

export default ConnectionStatus;
