import { useState } from "react";
import { KPICards } from "@/components/dashboard/KPICards";
import { FilterControls } from "@/components/dashboard/FilterControls";
import { Charts } from "@/components/dashboard/Charts";
import { AdHocQuery } from "@/components/dashboard/AdHocQuery";
import { PreFlaggedTable } from "@/components/dashboard/PreFlaggedTable";
import { ThumbnailModal } from "@/components/dashboard/ThumbnailModal";

const Index = () => {
  const [selectedType, setSelectedType] = useState("all");
  const [selectedFile, setSelectedFile] = useState("all");
  const [severityRange, setSeverityRange] = useState([0, 1]);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedFrame, setSelectedFrame] = useState<any | null>(null);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card shadow-sm">
        <div className="container mx-auto px-6 py-6">
          <h1 className="text-4xl font-bold bg-linear-to-r from-primary to-secondary bg-clip-text text-transparent">
            🚗 Waymo Edge Case Detection Dashboard
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8 space-y-8">
        {/* KPI Stats Row */}
        <KPICards />

        {/* Filters Row */}
        <FilterControls
          selectedType={selectedType}
          selectedFile={selectedFile}
          severityRange={severityRange}
          onTypeChange={setSelectedType}
          onFileChange={setSelectedFile}
          onSeverityChange={setSeverityRange}
        />

        {/* Charts Grid */}
        <Charts />

        {/* Ad-Hoc Query Section */}
        <AdHocQuery onViewThumbnail={setSelectedFrame} />

        {/* Pre-Flagged Cases Table */}
        <PreFlaggedTable
          page={currentPage}
          onPageChange={setCurrentPage}
          onViewThumbnail={setSelectedFrame}
        />
      </main>

      {/* Thumbnail Modal */}
      <ThumbnailModal frameData={selectedFrame} onClose={() => setSelectedFrame(null)} />
    </div>
  );
};

export default Index;
