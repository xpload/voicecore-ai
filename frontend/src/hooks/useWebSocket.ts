// WebSocket hook for real-time updates
import { useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { WebSocketMessage } from '@/types';

const WS_URL = process.env.REACT_APP_WS_URL || 'http://localhost:8000';

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  autoConnect?: boolean;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoConnect = true,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<Error | null>(null);
  const socketRef = useRef<Socket | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      return;
    }

    const token = localStorage.getItem('auth_token');
    
    const socket = io(WS_URL, {
      auth: { token },
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: maxReconnectAttempts,
      transports: ['websocket', 'polling'],
    });

    socket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      setConnectionError(null);
      reconnectAttempts.current = 0;
      if (onConnect) {
        onConnect();
      }
    });

    socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      setIsConnected(false);
      if (onDisconnect) {
        onDisconnect();
      }
    });

    socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      reconnectAttempts.current += 1;
      
      if (reconnectAttempts.current >= maxReconnectAttempts) {
        const err = new Error(`Failed to connect after ${maxReconnectAttempts} attempts`);
        setConnectionError(err);
        if (onError) {
          onError(err);
        }
      }
    });

    socket.on('error', (error) => {
      console.error('WebSocket error:', error);
      const err = new Error(error.message || 'WebSocket error');
      setConnectionError(err);
      if (onError) {
        onError(err);
      }
    });

    socket.on('message', (message: WebSocketMessage) => {
      if (onMessage) {
        onMessage(message);
      }
    });

    // Handle specific event types
    socket.on('call_update', (data) => {
      if (onMessage) {
        onMessage({ type: 'call_update', payload: data, timestamp: new Date().toISOString() });
      }
    });

    socket.on('notification', (data) => {
      if (onMessage) {
        onMessage({ type: 'notification', payload: data, timestamp: new Date().toISOString() });
      }
    });

    socket.on('metrics_update', (data) => {
      if (onMessage) {
        onMessage({ type: 'metrics_update', payload: data, timestamp: new Date().toISOString() });
      }
    });

    socketRef.current = socket;
  }, [onMessage, onConnect, onDisconnect, onError]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
    }
  }, []);

  const sendMessage = useCallback((type: string, payload: any) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('message', { type, payload, timestamp: new Date().toISOString() });
      return true;
    }
    console.warn('Cannot send message: WebSocket not connected');
    return false;
  }, []);

  const subscribe = useCallback((event: string, handler: (data: any) => void) => {
    if (socketRef.current) {
      socketRef.current.on(event, handler);
      return () => {
        socketRef.current?.off(event, handler);
      };
    }
    return () => {};
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    isConnected,
    connectionError,
    connect,
    disconnect,
    sendMessage,
    subscribe,
  };
};
