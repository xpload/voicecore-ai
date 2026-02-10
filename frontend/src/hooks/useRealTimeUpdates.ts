// Hook for handling real-time updates with React Query integration
import { useCallback } from 'react';
import { useQueryClient } from 'react-query';
import { useWebSocket } from './useWebSocket';
import { WebSocketMessage } from '@/types';

export const useRealTimeUpdates = () => {
  const queryClient = useQueryClient();

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'call_update':
        // Invalidate calls query to refetch
        queryClient.invalidateQueries(['calls']);
        // Optionally update specific call in cache
        if (message.payload.id) {
          queryClient.setQueryData(['call', message.payload.id], message.payload);
        }
        break;

      case 'metrics_update':
        // Update analytics metrics
        queryClient.invalidateQueries(['analytics']);
        queryClient.setQueryData(['metrics'], (old: any) => ({
          ...old,
          ...message.payload,
        }));
        break;

      case 'notification':
        // Handle notifications (could trigger toast/snackbar)
        console.log('Notification:', message.payload);
        break;

      default:
        console.log('Unknown message type:', message.type);
    }
  }, [queryClient]);

  const { isConnected, connectionError, sendMessage, subscribe } = useWebSocket({
    onMessage: handleMessage,
    onConnect: () => {
      console.log('Real-time updates connected');
      // Refetch all queries on reconnect
      queryClient.invalidateQueries();
    },
    onDisconnect: () => {
      console.log('Real-time updates disconnected');
    },
    onError: (error) => {
      console.error('Real-time updates error:', error);
    },
  });

  return {
    isConnected,
    connectionError,
    sendMessage,
    subscribe,
  };
};
