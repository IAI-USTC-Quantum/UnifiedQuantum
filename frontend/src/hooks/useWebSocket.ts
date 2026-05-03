import { useCallback, useEffect, useRef, useState } from "react";

interface WsEvent {
  type: string;
  payload: Record<string, unknown>;
}

interface UseWebSocketReturn {
  lastEvent: WsEvent | null;
  connected: boolean;
}

export function useWebSocket(path: string = "/ws/events"): UseWebSocketReturn {
  const [lastEvent, setLastEvent] = useState<WsEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}${path}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      // Reconnect after 5s
      reconnectTimer.current = setTimeout(connect, 5000);
    };
    ws.onerror = () => ws.close();

    ws.onmessage = (ev) => {
      try {
        const event: WsEvent = JSON.parse(ev.data);
        setLastEvent(event);
      } catch {
        // ignore parse errors
      }
    };
  }, [path]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { lastEvent, connected };
}
