import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { useAdHocQuery, useAdHocQueries } from "@/hooks/useEdgeCaseData";
import { PlayCircle, Camera } from "lucide-react";

interface AdHocQueryProps {
  onViewThumbnail: (frameData: any) => void;
}

export const AdHocQuery = ({ onViewThumbnail }: AdHocQueryProps) => {
  const [selectedQuery, setSelectedQuery] = useState<string | null>(null);
  const { data: queries, isLoading: isLoadingQueries } = useAdHocQueries();
  const { data: results, isLoading } = useAdHocQuery(selectedQuery);

  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PlayCircle className="h-5 w-5 text-accent" />
          Ad-Hoc Query Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-end gap-4">
          <div className="flex-1 space-y-2">
            <label className="text-sm font-medium">Run Ad-Hoc Analysis</label>
            <Select value={selectedQuery || ""} onValueChange={setSelectedQuery}>
              <SelectTrigger>
                <SelectValue placeholder={isLoadingQueries ? "Loading queries..." : "Select a query to run"} />
              </SelectTrigger>
              <SelectContent className="bg-popover z-50">
                {queries?.map((query: { value: string; label: string }) => (
                  <SelectItem key={query.value} value={query.value}>
                    {query.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {selectedQuery && (
          <div className="space-y-2">
            <h4 className="font-medium text-sm">Results:</h4>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-pulse-subtle text-muted-foreground">Loading results...</div>
              </div>
            ) : results && results.length > 0 ? (
              <div className="border rounded-lg overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Frame ID</TableHead>
                      <TableHead>File</TableHead>
                      {Object.keys(results[0])
                        .filter((key) => key !== "frame_id" && key !== "file_name" && key !== "panorama_thumbnail")
                        .map((key) => (
                          <TableHead key={key} className="capitalize">
                            {key.replace(/_/g, " ")}
                          </TableHead>
                        ))}
                      <TableHead>Thumbnail</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results?.map((row: any, index: number) => (
                      <TableRow key={index}>
                        <TableCell className="font-mono text-xs">{row.frame_id}</TableCell>
                        <TableCell className="text-sm truncate max-w-xs" title={row.file_name}>
                          {row.file_name}
                        </TableCell>
                        {Object.keys(results[0])
                          .filter((key) => key !== "frame_id" && key !== "file_name" && key !== "panorama_thumbnail")
                          .map((key) => (
                            <TableCell key={key} className="text-sm">
                              {typeof row[key] === "number" 
                                ? row[key].toFixed(3) 
                                : row[key]}
                            </TableCell>
                          ))}
                        <TableCell>
                          {row.panorama_thumbnail ? (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => onViewThumbnail(row)}
                            >
                              <Camera className="h-4 w-4" />
                            </Button>
                          ) : (
                            <span className="text-xs text-muted-foreground">N/A</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                No results found
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
