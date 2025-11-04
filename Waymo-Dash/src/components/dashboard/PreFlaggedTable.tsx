import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { usePreFlaggedData } from "@/hooks/useEdgeCaseData";
import { ChevronLeft, ChevronRight, Camera, Flag } from "lucide-react";
import { useMemo } from "react";

interface PreFlaggedTableProps {
  page: number;
  onPageChange: (page: number) => void;
  onViewThumbnail: (frameData: any) => void;
  selectedType: string;
  selectedFile: string;
  severityRange: number[];
}

export const PreFlaggedTable = ({ 
  page, 
  onPageChange, 
  onViewThumbnail,
  selectedType,
  selectedFile,
  severityRange 
}: PreFlaggedTableProps) => {
  const { data, isLoading } = usePreFlaggedData(page);

  // Apply client-side filtering
  const filteredData = useMemo(() => {
    if (!data?.data) return null;
    
    const filtered = data.data.filter((row: any) => {
      // Filter by edge case type
      if (selectedType !== "all" && row.edge_case_type !== selectedType) {
        return false;
      }
      
      // Filter by file name
      if (selectedFile !== "all" && row.file !== selectedFile) {
        return false;
      }
      
      // Filter by severity range
      const severity = parseFloat(row.severity);
      if (severity < severityRange[0] || severity > severityRange[1]) {
        return false;
      }
      
      return true;
    });
    
    return {
      ...data,
      data: filtered,
      total: filtered.length
    };
  }, [data, selectedType, selectedFile, severityRange]);

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
        {isLoading || !filteredData ? (
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
                  {filteredData.data.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                        No edge cases match the current filters
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredData.data.map((row: any, index: number) => (
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
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                Showing {filteredData.data.length} of {data.total} cases (Page {data.page} of {data.pages})
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
