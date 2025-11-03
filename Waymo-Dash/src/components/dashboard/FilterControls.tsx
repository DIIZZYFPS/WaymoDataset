import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { useFilters } from "@/hooks/useEdgeCaseData";
import { Filter } from "lucide-react";

interface FilterControlsProps {
  selectedType: string;
  selectedFile: string;
  severityRange: number[];
  onTypeChange: (value: string) => void;
  onFileChange: (value: string) => void;
  onSeverityChange: (value: number[]) => void;
}

export const FilterControls = ({
  selectedType,
  selectedFile,
  severityRange,
  onTypeChange,
  onFileChange,
  onSeverityChange,
}: FilterControlsProps) => {
  const { data: filters } = useFilters();

  return (
    <Card className="shadow-card">
      <CardContent className="pt-6">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">Filters</h3>
          <span className="text-xs text-muted-foreground ml-auto">
            (Affects charts and table below)
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Edge Case Type</label>
            <Select value={selectedType} onValueChange={onTypeChange}>
              <SelectTrigger>
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent className="bg-popover z-50">
                <SelectItem value="all">All types</SelectItem>
                {filters?.types.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type.replace(/_/g, " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-medium">File</label>
            <Select value={selectedFile} onValueChange={onFileChange}>
              <SelectTrigger>
                <SelectValue placeholder="All files" />
              </SelectTrigger>
              <SelectContent className="bg-popover z-50">
                <SelectItem value="all">All files</SelectItem>
                {filters?.files.map((file) => (
                  <SelectItem key={file} value={file}>
                    {file}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Severity Range: {severityRange[0].toFixed(1)} - {severityRange[1].toFixed(1)}
            </label>
            <Slider
              min={0}
              max={1}
              step={0.1}
              value={severityRange}
              onValueChange={onSeverityChange}
              className="pt-2"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
