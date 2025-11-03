import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { usePreFlaggedData } from "@/hooks/useEdgeCaseData";
import { ChevronLeft, ChevronRight, Camera, Flag } from "lucide-react";

interface PreFlaggedTableProps {
  page: number;
  onPageChange: (page: number) => void;
  onViewThumbnail: (frameData: any) => void;
}

export const PreFlaggedTable = ({ page, onPageChange, onViewThumbnail }: PreFlaggedTableProps) => {
  const { data, isLoading } = usePreFlaggedData(page);

  const getSeverityColor = (severity: string) => {
    const val = parseFloat(severity);
    if (val >= 0.8) return "text-severity-critical font-semibold";
    if (val >= 0.6) return "text-severity-high font-semibold";
    if (val >= 0.4) return "text-severity-medium font-semibold";
    return "text-severity-low font-semibold";
  };

  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Flag className="h-5 w-5 text-primary" />
          Pre-Flagged Edge Cases
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading || !data ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-pulse-subtle text-muted-foreground">Loading data...</div>
          </div>
        ) : (
          <>
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Frame ID</TableHead>
                    <TableHead>File</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Intent</TableHead>
                    <TableHead>Speed (m/s)</TableHead>
                    <TableHead>Accel (m/s²)</TableHead>
                    <TableHead>Thumbnail</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Array.isArray(data.data) && data.data.map((row: any, index: number) => (
                    <TableRow key={index}>
                      <TableCell className="font-mono text-xs">{row.frame_id}</TableCell>
                      <TableCell className="text-sm">{row.file}</TableCell>
                      <TableCell className="text-sm">{row.edge_case_type}</TableCell>
                      <TableCell className={getSeverityColor(row.severity)}>{row.severity}</TableCell>
                      <TableCell className="text-sm">{row.intent}</TableCell>
                      <TableCell>{row.speed}</TableCell>
                      <TableCell>{row.accel}</TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onViewThumbnail(row)}
                        >
                          <Camera className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                Page {data.page} of {data.pages} ({data.total} total cases)
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onPageChange(page - 1)}
                  disabled={page === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onPageChange(page + 1)}
                  disabled={page === data?.pages}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};
