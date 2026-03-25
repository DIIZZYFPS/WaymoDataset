import { useState, useEffect } from "react";
import { KPICards } from "@/components/dashboard/KPICards";
import { FilterControls } from "@/components/dashboard/FilterControls";
import { Charts } from "@/components/dashboard/Charts";
import { AdHocQuery } from "@/components/dashboard/AdHocQuery";
import { PreFlaggedTable } from "@/components/dashboard/PreFlaggedTable";
import { ThumbnailModal } from "@/components/dashboard/ThumbnailModal";
import { LiveEdgeCases } from "@/components/dashboard/LiveEdgeCases";
import { BotMessageSquare } from "lucide-react";
import { ChatSidebar } from "@/components/dashboard/ChatSidebar";
import { useAgentChat } from "@/hooks/useAgentChat";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface Message {
  role: "user" | "agent";
  content: string;
}

const Index = () => {
  const [selectedType, setSelectedType] = useState("all");
  const [selectedFile, setSelectedFile] = useState("all");
  const [severityRange, setSeverityRange] = useState([0, 1]);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedFrame, setSelectedFrame] = useState<any | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  
  const chatMutation = useAgentChat();

  const handleSendMessage = (message: string) => {
    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: message }]);

    // Send to API
    chatMutation.mutate(message, {
      onSuccess: (data) => {
        setMessages((prev) => [...prev, { role: "agent", content: data.response }]);
      },
      onError: () => {
        toast.error("Failed to send message. Please try again.");
      },
    });
  };
  // Debounced severity range for filtering (updates after user stops dragging)
  const [debouncedSeverityRange, setDebouncedSeverityRange] = useState([0, 1]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSeverityRange(severityRange);
    }, 150); // Wait 150ms after user stops dragging

    return () => clearTimeout(timer);
  }, [severityRange]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card shadow-sm">
        <div className="container mx-auto px-6 py-6 flex items-center justify-between">
          <h1 className="text-4xl font-bold bg-linear-to-r from-primary to-secondary bg-clip-text text-transparent">
            🚗 Waymo Edge Case Detection Dashboard
          </h1>
          <Button onClick={() => setChatOpen(true)} variant="outline" size="lg">
            <BotMessageSquare className="mr-2 h-5 w-5" />
            Chat with Data
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8 space-y-8">
        {/* KPI Stats Row */}
        <KPICards />

        {/* Live Edge Case Feed from C++ Engine → Redis */}
        <LiveEdgeCases />

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
        <Charts 
          selectedType={selectedType}
          selectedFile={selectedFile}
          severityRange={debouncedSeverityRange}
        />

        {/* Ad-Hoc Query Section */}
        <AdHocQuery onViewThumbnail={setSelectedFrame} />

        {/* Pre-Flagged Cases Table */}
        <PreFlaggedTable
          page={currentPage}
          onPageChange={setCurrentPage}
          onViewThumbnail={setSelectedFrame}
          selectedType={selectedType}
          selectedFile={selectedFile}
          severityRange={debouncedSeverityRange}
        />
        <Button onClick={() => setChatOpen(true)} 
         variant="ghost" 
         size="lg"
         className="fixed bottom-6 right-6 z-50 shadow-elevated hover:shadow-xl transition-shadow rounded-full w-14 h-14 p-0 animate-bounce hover:animate-none"
       >
            <BotMessageSquare />
          </Button>
      </main>

      {/* Thumbnail Modal */}
      <ThumbnailModal frameData={selectedFrame} onClose={() => setSelectedFrame(null)} />

              {/* Chat Sidebar */}
      <ChatSidebar
        open={chatOpen}
        onOpenChange={setChatOpen}
        messages={messages}
        onSendMessage={handleSendMessage}
        isLoading={chatMutation.isPending}
      />

    </div>
  );
};

export default Index;
