import { useState, useEffect, useRef } from "react";

// Automatically use production API in production, localhost in development
const API_BASE = import.meta.env.PROD
  ? "https://waymodataset-production.up.railway.app"
  : "http://localhost:8000";

interface EdgeCaseEvent {
  timestamp: number;
  frame_id: number;
  accel: number;
  jerk: number;
  intent: string;
  error?: string;
  raw?: string;
}

/**
 * Hook that connects to the SSE endpoint for real-time edge case signals
 * from the C++ engine via Redis.
 */
export const useLiveEdgeCases = (maxEvents: number = 50) => {
  const [events, setEvents] = useState<EdgeCaseEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(`${API_BASE}/api/live/edge-cases`);
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setError(null);
    };

    es.onmessage = (event) => {
      try {
        const data: EdgeCaseEvent = JSON.parse(event.data);
        if (data.error) {
          setError(data.error);
          return;
        }
        setEvents((prev) => [data, ...prev].slice(0, maxEvents));
      } catch {
        console.warn("Failed to parse SSE event:", event.data);
      }
    };

    es.onerror = () => {
      setConnected(false);
      setError("Connection lost. Reconnecting...");
    };

    return () => {
      es.close();
    };
  }, [maxEvents]);

  return { events, connected, error };
};
