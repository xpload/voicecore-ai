import React from 'react';
import { Box, Chip, Tooltip } from '@mui/material';
import { Circle } from '@mui/icons-material';

interface WebSocketStatusProps {
  isConnected: boolean;
  error?: Error | null;
}

const WebSocketStatus: React.FC<WebSocketStatusProps> = ({ isConnected, error }) => {
  const getStatusColor = () => {
    if (error) return 'error';
    return isConnected ? 'success' : 'warning';
  };

  const getStatusText = () => {
    if (error) return 'Connection Error';
    return isConnected ? 'Connected' : 'Disconnected';
  };

  const getTooltipText = () => {
    if (error) return `Error: ${error.message}`;
    return isConnected 
      ? 'Real-time updates active' 
      : 'Attempting to reconnect...';
  };

  return (
    <Tooltip title={getTooltipText()}>
      <Chip
        icon={<Circle sx={{ fontSize: 12 }} />}
        label={getStatusText()}
        color={getStatusColor()}
        size="small"
        variant="outlined"
      />
    </Tooltip>
  );
};

export default WebSocketStatus;
