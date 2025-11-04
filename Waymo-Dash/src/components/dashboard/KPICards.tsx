import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, FileText, AlertTriangle, Activity } from "lucide-react";
import { useStats } from "@/hooks/useEdgeCaseData";

export const KPICards = () => {
  const { data: stats, isLoading } = useStats();

  const kpis = [
    {
      title: "Total Edge Cases",
      value: stats?.totalEdgeCases || 0,
      icon: AlertTriangle,
      color: "text-chart-1",
    },
    {
      title: "Files Processed",
      value: stats?.filesProcessed || 0,
      icon: FileText,
      color: "text-chart-2",
    },
    {
      title: "Edge Case Types",
      value: stats?.edgeCaseTypes || 0,
      icon: Activity,
      color: "text-chart-3",
    },
    {
      title: "Max Severity",
      value: stats?.maxSeverity?.toFixed(2) || "0.00",
      icon: TrendingUp,
      color: "text-severity-critical",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-fade-in">
      {kpis.map((kpi, index) => (
        <Card key={index} className="shadow-card hover:shadow-elevated transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {kpi.title}
            </CardTitle>
            <kpi.icon className={`h-5 w-5 ${kpi.color}`} />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-10 w-24 bg-muted animate-pulse-subtle rounded" />
            ) : (
              <div className="text-3xl font-bold">{kpi.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
};
