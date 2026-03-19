// JHBridge - Interpreter Detail Modal
import { useState } from "react";
import { Modal } from "@/components/shared/Modal";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { showToast } from "@/components/shared/Toast";
import { MOCK } from "@/data/mockData";
import { 
  Edit, 
  MapPin, 
  Mail, 
  Phone, 
  Star, 
  Calendar,
  CheckCircle,
  XCircle,
  MessageSquare,
  Ban,
  Unlock,
  TrendingUp,
  Clock
} from "lucide-react";
import { cn } from "@/lib/utils";

export const InterpreterDetailModal = ({ 
  isOpen, 
  onClose, 
  interpreter,
  onAssignMission,
  onStatusChange 
}) => {
  const [confirmDialog, setConfirmDialog] = useState({ isOpen: false, type: null });
  const [loading, setLoading] = useState(false);

  if (!interpreter) return null;

  // Get interpreter's recent missions
  const recentMissions = MOCK.assignments
    .filter(a => a.interpreter === interpreter.name)
    .slice(0, 5);

  const statusColors = {
    available: { bg: "bg-success/10", text: "text-success", label: "Available" },
    on_mission: { bg: "bg-gold/10", text: "text-gold", label: "On Mission" },
    blocked: { bg: "bg-danger/10", text: "text-danger", label: "Blocked" },
  };

  const status = statusColors[interpreter.status] || statusColors.available;

  const handleBlock = async () => {
    setLoading(true);
    await new Promise(resolve => setTimeout(resolve, 500));
    setLoading(false);
    setConfirmDialog({ isOpen: false, type: null });
    showToast.warning(`${interpreter.name} has been blocked`);
    if (onStatusChange) {
      onStatusChange(interpreter.id, "blocked");
    }
  };

  const handleUnblock = async () => {
    setLoading(true);
    await new Promise(resolve => setTimeout(resolve, 500));
    setLoading(false);
    setConfirmDialog({ isOpen: false, type: null });
    showToast.success(`${interpreter.name} has been unblocked`);
    if (onStatusChange) {
      onStatusChange(interpreter.id, "available");
    }
  };

  const handleSendMessage = () => {
    showToast.info(`Opening message composer for ${interpreter.name}`);
  };

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        size="lg"
        footer={
          <div className="flex items-center justify-between w-full">
            <div className="flex gap-2">
              {interpreter.status === "blocked" ? (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-success border-success/30"
                  onClick={() => setConfirmDialog({ isOpen: true, type: "unblock" })}
                  data-testid="interpreter-unblock-btn"
                >
                  <Unlock className="w-4 h-4" />
                  Unblock
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-danger border-danger/30"
                  onClick={() => setConfirmDialog({ isOpen: true, type: "block" })}
                  data-testid="interpreter-block-btn"
                >
                  <Ban className="w-4 h-4" />
                  Block
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={handleSendMessage}
                data-testid="interpreter-message-btn"
              >
                <MessageSquare className="w-4 h-4" />
                Send Message
              </Button>
              {interpreter.status === "available" && (
                <Button
                  size="sm"
                  className="gap-1.5 bg-navy hover:bg-navy-light"
                  onClick={() => onAssignMission?.(interpreter)}
                  data-testid="interpreter-assign-btn"
                >
                  <Calendar className="w-4 h-4" />
                  Assign Mission
                </Button>
              )}
            </div>
          </div>
        }
      >
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-full bg-navy text-white flex items-center justify-center text-xl font-bold flex-shrink-0">
              {interpreter.name.split(" ").map(n => n[0]).join("")}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-semibold font-display">{interpreter.name}</h2>
                <div className="flex items-center gap-1 text-gold">
                  <Star className="w-4 h-4 fill-gold" />
                  <span className="font-mono font-medium">{interpreter.rating}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium", status.bg, status.text)}>
                  {status.label}
                </span>
                <span className="text-sm text-muted-foreground">
                  {interpreter.missions} missions completed
                </span>
              </div>
            </div>
            <Button variant="outline" size="sm" className="flex-shrink-0">
              <Edit className="w-4 h-4 mr-1.5" />
              Edit
            </Button>
          </div>

          {/* Contact Info */}
          <div className="bg-muted/30 rounded-lg p-4">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Contact</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-muted-foreground" />
                <a href={`mailto:${interpreter.name.toLowerCase().replace(" ", ".")}@gmail.com`} className="text-primary hover:underline">
                  {interpreter.name.toLowerCase().replace(" ", ".")}@gmail.com
                </a>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-muted-foreground" />
                <span>+1 617-555-{String(interpreter.id).padStart(4, "0")}</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-muted-foreground" />
                <span>{interpreter.city}, {interpreter.state}</span>
                <span className="text-muted-foreground">({interpreter.radius}mi radius)</span>
              </div>
            </div>
          </div>

          {/* Languages */}
          <div className="bg-muted/30 rounded-lg p-4">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Languages</h4>
            <div className="flex flex-wrap gap-2">
              {interpreter.langs.map((lang, idx) => (
                <span 
                  key={idx}
                  className="px-3 py-1.5 bg-card border border-border rounded-md text-sm font-medium"
                >
                  {lang}
                </span>
              ))}
            </div>
          </div>

          {/* Rates */}
          <div className="bg-muted/30 rounded-lg p-4">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Rates</h4>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-muted-foreground">Standard</div>
                <div className="text-lg font-bold font-mono">${interpreter.rate}/hr</div>
              </div>
              <div>
                <div className="text-muted-foreground">Legal</div>
                <div className="text-lg font-bold font-mono">${interpreter.rate + 10}/hr</div>
              </div>
              <div>
                <div className="text-muted-foreground">Rush (+25%)</div>
                <div className="text-lg font-bold font-mono">${Math.round(interpreter.rate * 1.25)}/hr</div>
              </div>
            </div>
          </div>

          {/* Performance */}
          <div className="bg-muted/30 rounded-lg p-4">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Performance</h4>
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-navy dark:text-gold">{interpreter.missions}</div>
                <div className="text-xs text-muted-foreground">Total Missions</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-success">94%</div>
                <div className="text-xs text-muted-foreground">Acceptance</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-danger">0.7%</div>
                <div className="text-xs text-muted-foreground">No-shows</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-gold flex items-center justify-center gap-1">
                  <Star className="w-5 h-5 fill-gold" />
                  {interpreter.rating}
                </div>
                <div className="text-xs text-muted-foreground">Avg Rating</div>
              </div>
            </div>
          </div>

          {/* Recent Missions */}
          <div className="bg-muted/30 rounded-lg p-4">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Recent Missions</h4>
            {recentMissions.length > 0 ? (
              <div className="space-y-2">
                {recentMissions.map((mission, idx) => (
                  <div 
                    key={idx}
                    className="flex items-center justify-between py-2 border-b border-border last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <Clock className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">{mission.date}</span>
                      <span className="text-sm font-medium">{mission.client}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {mission.status === "COMPLETED" ? (
                        <CheckCircle className="w-4 h-4 text-success" />
                      ) : mission.status === "CANCELLED" ? (
                        <XCircle className="w-4 h-4 text-danger" />
                      ) : (
                        <Clock className="w-4 h-4 text-warning" />
                      )}
                      <span className="text-xs text-muted-foreground">{mission.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground text-center py-4">
                No recent missions
              </div>
            )}
            <Button variant="link" size="sm" className="mt-2 p-0 h-auto">
              View All Missions
            </Button>
          </div>
        </div>
      </Modal>

      {/* Confirm Dialogs */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen && confirmDialog.type === "block"}
        onConfirm={handleBlock}
        onCancel={() => setConfirmDialog({ isOpen: false, type: null })}
        title={`Block ${interpreter.name}?`}
        message="This interpreter will no longer be available for assignments. You can unblock them later."
        confirmText="Block Interpreter"
        variant="danger"
        loading={loading}
      />

      <ConfirmDialog
        isOpen={confirmDialog.isOpen && confirmDialog.type === "unblock"}
        onConfirm={handleUnblock}
        onCancel={() => setConfirmDialog({ isOpen: false, type: null })}
        title={`Unblock ${interpreter.name}?`}
        message="This interpreter will be available for new assignments again."
        confirmText="Unblock"
        variant="info"
        loading={loading}
      />
    </>
  );
};

export default InterpreterDetailModal;
