import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

interface ThumbnailModalProps {
  frameData: any | null;
  onClose: () => void;
}

export const ThumbnailModal = ({ frameData, onClose }: ThumbnailModalProps) => {
  // No API call needed - data is already passed from the table!
  const frame = frameData;

  return (
    <Dialog open={!!frameData} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            Frame {frame?.frame_id} - {frame?.edge_case_type}
          </DialogTitle>
          <DialogDescription>
            Detailed view of edge case frame and motion metrics
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6">
            {/* Thumbnail Image */}
            {frame?.panorama_thumbnail ? (
              <div className="bg-muted rounded-lg overflow-hidden">
                <img
                  src={`data:image/jpeg;base64,${frame.panorama_thumbnail}`}
                  alt={`Frame ${frame?.frame_id}`}
                  className="w-full h-auto"
                />
              </div>
            ) : (
              <div className="bg-muted rounded-lg overflow-hidden flex items-center justify-center h-64">
                <p className="text-muted-foreground">No thumbnail available for this frame</p>
              </div>
            )}

            {/* Metadata */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-semibold text-muted-foreground">Frame ID:</span>
                <p className="font-mono">{frame?.frame_id}</p>
              </div>
              <div>
                <span className="font-semibold text-muted-foreground">File:</span>
                <p>{frame?.file}</p>
              </div>
              <div>
                <span className="font-semibold text-muted-foreground">Edge Case Type:</span>
                <p>{frame?.edge_case_type}</p>
              </div>
              <div>
                <span className="font-semibold text-muted-foreground">Severity:</span>
                <p className="font-semibold">{frame?.severity}</p>
              </div>
              <div>
                <span className="font-semibold text-muted-foreground">Intent:</span>
                <p>{frame?.intent}</p>
              </div>
              <div>
                <span className="font-semibold text-muted-foreground">Speed:</span>
                <p>{frame?.speed} m/s</p>
              </div>
              <div>
                <span className="font-semibold text-muted-foreground">Acceleration:</span>
                <p>{frame?.accel} m/s²</p>
              </div>
              <div>
                <span className="font-semibold text-muted-foreground">Timestamp:</span>
                <p className="font-mono text-xs">{frame?.timestamp}</p>
              </div>
              <div className="col-span-2">
                <span className="font-semibold text-muted-foreground">Reason:</span>
                <p>{frame?.reason}</p>
              </div>
            </div>
          </div>
      </DialogContent>
    </Dialog>
  );
};
