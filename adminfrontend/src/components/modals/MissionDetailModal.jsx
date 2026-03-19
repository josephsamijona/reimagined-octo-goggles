// JHBridge - Mission Detail Modal
import { useState } from "react";
import { Modal } from "@/components/shared/Modal";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/shared/UIComponents";
import { showToast } from "@/components/shared/Toast";
import { MOCK } from "@/data/mockData";
import { 
  Edit, 
  CheckCircle, 
  XCircle, 
  Bell, 
  MapPin, 
  Clock, 
  Calendar,
  Phone,
  Mail,
  Star,
  Building2,
  User,
  RefreshCw,
  FileText
} from "lucide-react";
import { cn } from "@/lib/utils";

export const MissionDetailModal = ({ 
  isOpen, 
  onClose, 
  mission,
  onEdit,
  onStatusChange 
}) => {
  const [confirmDialog, setConfirmDialog] = useState({ isOpen: false, type: null });
  const [loading, setLoading] = useState(false);

  if (!mission) return null;

  // Find related data
  const interpreter = MOCK.interpreters.find(i => i.name === mission.interpreter);
  const client = MOCK.clients.find(c => c.company === mission.client);

  // Timeline mock
  const timeline = [
    { time: "Mar 14 09:23", action: "Mission created", user: "Marc-Henry V." },
    { time: "Mar 14 09:45", action: "Interpreter assigned", user: "System" },
    { time: "Mar 14 10:02", action: "Interpreter confirmed", user: interpreter?.name || "—" },
  ];

  const handleStatusChange = async (newStatus) => {
    setLoading(true);
    await new Promise(resolve => setTimeout(resolve, 600));
    setLoading(false);
    
    setConfirmDialog({ isOpen: false, type: null });
    
    if (newStatus === "COMPLETED") {
      showToast.success(`Mission ${mission.id} marked as completed`);
    } else if (newStatus === "CANCELLED") {
      showToast.warning(`Mission ${mission.id} cancelled`);
    }
    
    if (onStatusChange) {
      onStatusChange(mission.id, newStatus);
    }
  };

  const handleSendReminder = async () => {
    setLoading(true);
    await new Promise(resolve => setTimeout(resolve, 500));
    setLoading(false);
    showToast.success(`Reminder sent to ${interpreter?.name || "interpreter"}`);
  };

  const canComplete = ["CONFIRMED", "IN_PROGRESS"].includes(mission.status);
  const canCancel = ["PENDING", "CONFIRMED"].includes(mission.status);

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title={mission.id}
        size="lg"
        footer={
          <div className="flex items-center justify-between w-full">
            <div className="flex gap-2">
              {canComplete && (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-success border-success/30 hover:bg-success/10"
                  onClick={() => setConfirmDialog({ isOpen: true, type: "complete" })}
                  data-testid="mission-complete-btn"
                >
                  <CheckCircle className="w-4 h-4" />
                  Mark Complete
                </Button>
              )}
              {canCancel && (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-danger border-danger/30 hover:bg-danger/10"
                  onClick={() => setConfirmDialog({ isOpen: true, type: "cancel" })}
                  data-testid="mission-cancel-btn"
                >
                  <XCircle className="w-4 h-4" />
                  Cancel Mission
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={handleSendReminder}
                disabled={loading || !interpreter}
                data-testid="mission-reminder-btn"
              >
                <Bell className="w-4 h-4" />
                Send Reminder
              </Button>
              <Button
                size="sm"
                className="gap-1.5 bg-navy hover:bg-navy-light"
                onClick={() => onEdit?.(mission)}
                data-testid="mission-edit-btn"
              >
                <Edit className="w-4 h-4" />
                Edit
              </Button>
            </div>
          </div>
        }
      >
        <div className="space-y-6">
          {/* Header with Status */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <StatusBadge status={mission.status} />
              <span className="text-lg font-semibold">{mission.client}</span>
            </div>
            <div className="text-right">
              <div className="text-sm text-muted-foreground font-mono">{mission.type}</div>
            </div>
          </div>

          {/* Details Section */}
          <div className="bg-muted/30 rounded-lg p-4 space-y-3">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Details</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">Type:</span>
                <span className="font-medium">{mission.type}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Languages:</span>
                <span className="font-mono font-medium">{mission.lang}</span>
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">Date:</span>
                <span className="font-medium">{mission.date}</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">Time:</span>
                <span className="font-medium">{mission.time}</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">Location:</span>
                <span className="font-medium">{mission.city}, {mission.state}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Rate:</span>
                <span className="font-mono font-medium">${mission.rate}/hr</span>
              </div>
            </div>
          </div>

          {/* Interpreter Section */}
          <div className="bg-muted/30 rounded-lg p-4">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Interpreter</h4>
            {interpreter ? (
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-navy text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                  {interpreter.name.split(" ").map(n => n[0]).join("")}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{interpreter.name}</span>
                    <div className="flex items-center gap-1 text-gold">
                      <Star className="w-3.5 h-3.5 fill-gold" />
                      <span className="text-xs font-mono">{interpreter.rating}</span>
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {interpreter.city}, {interpreter.state} · {interpreter.missions} missions
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-sm">
                    <a href={`tel:+1617555${interpreter.id}123`} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
                      <Phone className="w-3.5 h-3.5" />
                      +1 617-555-{interpreter.id}123
                    </a>
                    <a href={`mailto:${interpreter.name.toLowerCase().replace(" ", ".")}@gmail.com`} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
                      <Mail className="w-3.5 h-3.5" />
                      Email
                    </a>
                  </div>
                </div>
                <Button variant="outline" size="sm" className="flex-shrink-0">
                  <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                  Change
                </Button>
              </div>
            ) : (
              <div className="flex items-center justify-between p-3 bg-danger/10 rounded border border-danger/30">
                <div className="flex items-center gap-2 text-danger">
                  <User className="w-4 h-4" />
                  <span className="font-medium">No interpreter assigned</span>
                </div>
                <Button size="sm" variant="outline" className="text-danger border-danger/30">
                  Assign Now
                </Button>
              </div>
            )}
          </div>

          {/* Client Contact Section */}
          {client && (
            <div className="bg-muted/30 rounded-lg p-4">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Client Contact</h4>
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-gold/20 text-gold flex items-center justify-center">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="font-medium">{client.contact}</div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <a href={`mailto:${client.email}`} className="flex items-center gap-1 hover:text-foreground">
                      <Mail className="w-3.5 h-3.5" />
                      {client.email}
                    </a>
                    <span className="flex items-center gap-1">
                      <Phone className="w-3.5 h-3.5" />
                      +1 617-555-0456
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Timeline Section */}
          <div className="bg-muted/30 rounded-lg p-4">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Timeline</h4>
            <div className="space-y-2">
              {timeline.map((item, idx) => (
                <div key={idx} className="flex items-center gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-navy dark:bg-gold flex-shrink-0" />
                  <span className="text-muted-foreground font-mono text-xs w-28">{item.time}</span>
                  <span>{item.action}</span>
                  <span className="text-muted-foreground">by {item.user}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Modal>

      {/* Confirm Dialogs */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen && confirmDialog.type === "complete"}
        onConfirm={() => handleStatusChange("COMPLETED")}
        onCancel={() => setConfirmDialog({ isOpen: false, type: null })}
        title="Mark Mission Complete?"
        message={`This will mark mission ${mission.id} as completed and notify the client.`}
        confirmText="Mark Complete"
        variant="info"
        loading={loading}
      />

      <ConfirmDialog
        isOpen={confirmDialog.isOpen && confirmDialog.type === "cancel"}
        onConfirm={() => handleStatusChange("CANCELLED")}
        onCancel={() => setConfirmDialog({ isOpen: false, type: null })}
        title="Cancel Mission?"
        message={`This will cancel mission ${mission.id} and notify the interpreter and client. This action cannot be undone.`}
        confirmText="Cancel Mission"
        variant="danger"
        loading={loading}
      />
    </>
  );
};

export default MissionDetailModal;
