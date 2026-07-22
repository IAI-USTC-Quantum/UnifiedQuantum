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
  const generationRef = useRef(0);

  const connect = useCallback((generation: number) => {
    if (generationRef.current !== generation) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}${path}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (generationRef.current === generation) setConnected(true);
    };
    ws.onclose = () => {
      if (generationRef.current !== generation) return;
      setConnected(false);
      reconnectTimer.current = setTimeout(() => {
        reconnectTimer.current = null;
        connect(generation);
      }, 5000);
    };
    ws.onerror = () => ws.close();

    ws.onmessage = (ev) => {
      if (generationRef.current !== generation) return;
      try {
        const event: WsEvent = JSON.parse(ev.data);
        setLastEvent(event);
      } catch {
        // ignore parse errors
      }
    };
  }, [path]);

  useEffect(() => {
    const generation = ++generationRef.current;
    setConnected(false);
    connect(generation);

    return () => {
      generationRef.current++;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [connect]);

  return { lastEvent, connected };
}
