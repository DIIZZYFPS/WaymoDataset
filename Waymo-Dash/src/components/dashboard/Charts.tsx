import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { memo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  ZAxis,
  ComposedChart,
  Area,
} from "recharts";
import {
  usePieChartData,
  useHistogramData,
  useBoxPlotData,
  useTopFilesData,
  useIntentData,
  useScatterData,
} from "@/hooks/useEdgeCaseData";

// Memoized chart components to prevent unnecessary re-renders
const PieChartCard = memo(() => {
  const { data: pieData } = usePieChartData();
  
  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle>Distribution of Edge Case Types</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              outerRadius={100}
              dataKey="value"
            >
              {pieData?.map((entry: any, index: number) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
});

const TopFilesChartCard = memo(() => {
  const { data: topFilesData } = useTopFilesData();
  
  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle>Top 10 Files with Most Edge Cases</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={topFilesData} layout="vertical" margin={{ left: 100 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis type="number" stroke="var(--foreground)" />
            <YAxis type="category" dataKey="file" stroke="var(--foreground)" />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--popover)",
                border: "1px solid var(--border)",
              }}
            />
            <Bar dataKey="count" fill="var(--chart-2)" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
});

const IntentChartCard = memo(() => {
  const { data: intentData } = useIntentData();
  
  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle>Edge Cases by Driving Intent</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={intentData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="intent" stroke="var(--foreground)" />
            <YAxis stroke="var(--foreground)" />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--popover)",
                border: "1px solid var(--border)",
              }}
            />
            <Bar dataKey="count" fill="var(--chart-3)" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
});

const ScatterChartCard = memo(() => {
  const { data: scatterData } = useScatterData();
  
  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle>Speed vs. Deceleration</CardTitle>
        <p className="text-sm text-muted-foreground">Bubble size = severity</p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              type="number"
              dataKey="speed"
              name="Speed"
              unit=" m/s"
              stroke="var(--foreground)"
            />
            <YAxis
              type="number"
              dataKey="accel"
              name="Accel"
              unit=" m/s²"
              stroke="var(--foreground)"
            />
            <ZAxis type="number" dataKey="severity" range={[20, 400]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              contentStyle={{
                backgroundColor: "var(--popover)",
                border: "1px solid var(--border)",
              }}
            />
            <Scatter data={scatterData} fill="var(--chart-1)" fillOpacity={0.6} />
          </ScatterChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
});

const HistogramChartCard = memo(() => {
  const { data: histogramData } = useHistogramData();
  
  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle>Severity Distribution (Histogram)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={histogramData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="range" stroke="var(--foreground)" />
            <YAxis stroke="var(--foreground)" />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--popover)",
                border: "1px solid var(--border)",
              }}
            />
            <Bar dataKey="count" fill="var(--chart-4)" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
});

const BoxPlotChartCard = memo(() => {
  const { data: boxPlotData } = useBoxPlotData();
  
  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle>Severity Range by Type (Box Plot)</CardTitle>
        <p className="text-sm text-muted-foreground">Shows min, Q1, median, Q3, max</p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={boxPlotData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="type" stroke="var(--foreground)" />
            <YAxis stroke="var(--foreground)" domain={[0, 1]} />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--popover)",
                border: "1px solid var(--border)",
              }}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="max"
              stroke="var(--chart-5)"
              fill="var(--chart-5)"
              fillOpacity={0.1}
            />
            <Bar dataKey="q3" stackId="box" fill="var(--chart-2)" fillOpacity={0.6} />
            <Bar dataKey="median" stackId="box" fill="var(--chart-1)" />
            <Bar dataKey="q1" stackId="box" fill="var(--chart-2)" fillOpacity={0.6} />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
});

export const Charts = () => {
  return (
    <div className="space-y-6">
      {/* First Row: 2x2 Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PieChartCard />
        <TopFilesChartCard />
        <IntentChartCard />
        <ScatterChartCard />
      </div>

      {/* Second Row: 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <HistogramChartCard />
        <BoxPlotChartCard />
      </div>
    </div>
  );
};
