import { useEffect, useRef, useCallback } from 'react';
import { useBotStore } from '@/store/botStore';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

type WebSocketStatus = 'connected' | 'disconnected' | 'connecting';

export const useWebSocket = () => {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { setStatus } = useBotStore();
  const callbacksRef = useRef<Record<string, Function[]>>({});

  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    // Get token from cookie
    const wsToken = document.cookie
      .split('; ')
      .find((row) => row.startsWith('ws_token='))
      ?.split('=')[1];

    if (!wsToken) {
      console.warn('WebSocket: No ws_token found in cookies');
      setStatus('disconnected');
      return;
    }

    setStatus('connecting');
    
    const url = `${WS_URL}/ws?token=${wsToken}`;
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('WebSocket: Connected');
      setStatus('connected');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const { type, payload } = data;
        
        if (type && callbacksRef.current[type]) {
          callbacksRef.current[type].forEach((cb) => cb(payload));
        }
      } catch (err) {
        console.error('WebSocket: Failed to parse message', err);
      }
    };

    socket.onclose = () => {
      console.log('WebSocket: Disconnected');
      setStatus('disconnected');
      
      // Auto-reconnect after 3s
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('WebSocket: Attempting to reconnect...');
        connect();
      }, 3000);
    };

    socket.onerror = (error) => {
      console.error('WebSocket: Error', error);
      socket.close();
    };
  }, [setStatus]);

  useEffect(() => {
    connect();
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const on = useCallback((type: string, callback: Function) => {
    if (!callbacksRef.current[type]) {
      callbacksRef.current[type] = [];
    }
    callbacksRef.current[type].push(callback);
  }, []);

  const off = useCallback((type: string, callback: Function) => {
    if (callbacksRef.current[type]) {
      callbacksRef.current[type] = callbacksRef.current[type].filter((cb) => cb !== callback);
    }
  }, []);

  return { on, off };
};
