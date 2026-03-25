import { useLiveEdgeCases } from "@/hooks/useLiveEdgeCases";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity } from "lucide-react";

export const LiveEdgeCases = () => {
  const { events, connected, error } = useLiveEdgeCases(30);

  return (
    <Card className="shadow-card border-l-4 border-l-red-500/60">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Activity className="h-5 w-5 text-red-500" />
          Live Edge Cases
        </CardTitle>
        <div className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              connected
                ? "bg-green-500 animate-pulse"
                : "bg-red-500"
            }`}
          />
          <span className="text-xs text-muted-foreground">
            {connected ? "Streaming" : error || "Disconnected"}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <div className="text-sm text-muted-foreground py-6 text-center">
            {connected
              ? "Waiting for edge cases from C++ engine..."
              : "Connecting to Redis stream..."}
          </div>
        ) : (
          <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
            {events.map((event, index) => (
              <div
                key={`${event.timestamp}-${index}`}
                className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-all ${
                  index === 0
                    ? "bg-red-500/10 border border-red-500/20 animate-fade-in"
                    : "bg-muted/50"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-muted-foreground w-28 shrink-0">
                    frame={event.frame_id}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                    {event.intent || "—"}
                  </span>
                </div>
                <div className="flex gap-4 text-xs font-mono">
                  <span
                    className={
                      Math.abs(event.accel) > 4
                        ? "text-red-500 font-bold"
                        : "text-muted-foreground"
                    }
                  >
                    a={event.accel?.toFixed(2)}
                  </span>
                  <span
                    className={
                      Math.abs(event.jerk) > 10
                        ? "text-orange-500 font-bold"
                        : "text-muted-foreground"
                    }
                  >
                    j={event.jerk?.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
