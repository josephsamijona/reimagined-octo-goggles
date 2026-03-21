// JHBridge - Interpreter Detail Modal
import { useState, useEffect } from "react";
import { Modal } from "@/components/shared/Modal";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { showToast } from "@/components/shared/Toast";
import { interpreterService } from "@/services/interpreterService";
import { EditInterpreterModal } from "./EditInterpreterModal";
import {
  Edit, MapPin, Mail, Phone, Star, Calendar, CheckCircle,
  XCircle, MessageSquare, Ban, Unlock, Clock, FileText,
  Shield, Loader2, Link as LinkIcon, User, Briefcase, KeyRound,
  CreditCard, Building2, Hash, Send, Paperclip, X as XIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar } from "@/components/shared/UIComponents";

const InfoRow = ({ icon: Icon, label, value, mono = false }) => {
  if (!value && value !== 0) return null;
  return (
    <div className="flex items-start gap-2 text-sm">
      {Icon && <Icon className="w-3.5 h-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />}
      <div className="min-w-0">
        <span className="text-muted-foreground text-xs">{label}: </span>
        <span className={cn("text-foreground", mono && "font-mono")}>{value}</span>
      </div>
    </div>
  );
};

const Section = ({ title, children }) => (
  <div className="bg-card border border-border rounded-lg p-4">
    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">{title}</h4>
    <div className="space-y-2">{children}</div>
  </div>
);

export const InterpreterDetailModal = ({
  isOpen,
  onClose,
  initialData,
  interpreterId,
  onAssignMission,
  onStatusChange,
}) => {
  const [interpreter, setInterpreter] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [bankingData, setBankingData] = useState(null);
  const [loadingBanking, setLoadingBanking] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState({ isOpen: false, type: null });
  const [blockReason, setBlockReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [messageDialog, setMessageDialog] = useState({ isOpen: false, subject: "", body: "", attachment: null });
  const [sendingMessage, setSendingMessage] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);

  // Reset and fetch fresh data whenever the modal opens with a new interpreterId
  useEffect(() => {
    if (!isOpen || !interpreterId) return;

    // Immediately show initialData to avoid blank modal while loading
    setInterpreter(initialData || null);
    setBankingData(null);
    setLoadingDetail(true);

    const controller = new AbortController();

    interpreterService.getInterpreterById(interpreterId)
      .then(data => {
        if (controller.signal.aborted) return;
        setInterpreter({
          id: data.id,
          name: `${data.user?.first_name || ''} ${data.user?.last_name || ''}`.trim() || "Unknown",
          langs: data.interpreter_languages?.map(l => l.language?.name).filter(Boolean) || [],
          rating: Number(data.avg_rating) ? Number(data.avg_rating).toFixed(1) : "New",
          missions: data.missions_count || 0,
          radius: data.radius_of_service || null,
          status: data.is_manually_blocked ? "blocked" : data.is_on_mission ? "on_mission" : "available",
          _raw: data,
        });
      })
      .catch(err => {
        if (controller.signal.aborted) return;
        console.error("Failed to fetch interpreter details", err);
        showToast.error("Failed to load interpreter details");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingDetail(false);
      });

    return () => controller.abort();
  }, [isOpen, interpreterId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!isOpen) return null;

  const raw = interpreter?._raw || {};

  const statusColors = {
    available: { bg: "bg-success/10", text: "text-success", label: "Available" },
    on_mission: { bg: "bg-gold/10", text: "text-gold", label: "On Mission" },
    blocked: { bg: "bg-danger/10", text: "text-danger", label: "Blocked" },
  };
  const status = statusColors[interpreter?.status] || statusColors.available;

  const handleBlock = async () => {
    if (!blockReason.trim()) { showToast.error("A reason is required"); return; }
    setIsSubmitting(true);
    try {
      await interpreterService.blockInterpreter(interpreter.id, blockReason);
      setConfirmDialog({ isOpen: false, type: null });
      setBlockReason("");
      showToast.warning(`${interpreter.name} has been blocked`);
      onStatusChange?.();
    } catch { showToast.error("Failed to block interpreter"); }
    finally { setIsSubmitting(false); }
  };

  const handleUnblock = async () => {
    setIsSubmitting(true);
    try {
      await interpreterService.unblockInterpreter(interpreter.id);
      setConfirmDialog({ isOpen: false, type: null });
      showToast.success(`${interpreter.name} has been unblocked`);
      onStatusChange?.();
    } catch { showToast.error("Failed to unblock interpreter"); }
    finally { setIsSubmitting(false); }
  };

  const fetchUnmaskedBanking = async () => {
    setLoadingBanking(true);
    try {
      const data = await interpreterService.getInterpreterBanking(interpreter.id);
      setBankingData(data);
      showToast.success("Banking info revealed");
    } catch { showToast.error("Unauthorized or failed to fetch banking details"); }
    finally { setLoadingBanking(false); }
  };

  const handleSendPasswordReset = async () => {
    try {
      await interpreterService.sendPasswordReset(interpreter.id);
      showToast.success("Password reset email sent");
    } catch { showToast.error("Failed to send password reset email"); }
  };

  const handleSendMessage = async () => {
    if (!messageDialog.subject.trim() || !messageDialog.body.trim()) {
      showToast.error("Subject and message are required");
      return;
    }
    setSendingMessage(true);
    try {
      await interpreterService.sendMessage(
        interpreter.id,
        messageDialog.subject,
        messageDialog.body,
        messageDialog.attachment || null,
      );
      showToast.success(`Message sent to ${interpreter.name}`);
      setMessageDialog({ isOpen: false, subject: "", body: "", attachment: null });
    } catch { showToast.error("Failed to send message"); }
    finally { setSendingMessage(false); }
  };

  const refetchDetail = () => {
    if (!interpreterId) return;
    setLoadingDetail(true);
    interpreterService.getInterpreterById(interpreterId)
      .then(data => {
        setInterpreter({
          id: data.id,
          name: `${data.user?.first_name || ''} ${data.user?.last_name || ''}`.trim() || "Unknown",
          langs: data.interpreter_languages?.map(l => l.language?.name).filter(Boolean) || [],
          rating: Number(data.avg_rating) ? Number(data.avg_rating).toFixed(1) : "New",
          missions: data.missions_count || 0,
          radius: data.radius_of_service || null,
          status: data.is_manually_blocked ? "blocked" : data.is_on_mission ? "on_mission" : "available",
          _raw: data,
        });
      })
      .catch(() => showToast.error("Failed to refresh interpreter details"))
      .finally(() => setLoadingDetail(false));
  };

  const recentMissions = raw.recent_assignments || [];

  const formatDate = (val) => val ? new Date(val).toLocaleDateString() : null;
  const formatDateTime = (val) => val ? new Date(val).toLocaleString() : null;
  const formatJsonList = (val) => {
    if (!val) return null;
    if (Array.isArray(val)) return val.join(", ");
    if (typeof val === "string") {
      try { const p = JSON.parse(val); return Array.isArray(p) ? p.join(", ") : val; }
      catch { return val; }
    }
    return String(val);
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
              {interpreter?.status === "blocked" ? (
                <Button variant="outline" size="sm" className="gap-1.5 text-success border-success/30"
                  onClick={() => setConfirmDialog({ isOpen: true, type: "unblock" })}>
                  <Unlock className="w-4 h-4" /> Unblock
                </Button>
              ) : (
                <Button variant="outline" size="sm" className="gap-1.5 text-danger border-danger/30"
                  onClick={() => setConfirmDialog({ isOpen: true, type: "block" })}>
                  <Ban className="w-4 h-4" /> Block
                </Button>
              )}
              <Button variant="outline" size="sm" className="gap-1.5"
                onClick={handleSendPasswordReset}>
                <KeyRound className="w-4 h-4" /> Send Reset Link
              </Button>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="gap-1.5"
                onClick={() => setMessageDialog({ isOpen: true, subject: "", body: "" })}>
                <MessageSquare className="w-4 h-4" /> Send Message
              </Button>
              {interpreter?.status === "available" && (
                <Button size="sm" className="gap-1.5 bg-navy hover:bg-navy-light text-white"
                  onClick={() => onAssignMission?.(interpreter)}>
                  <Calendar className="w-4 h-4" /> Assign Mission
                </Button>
              )}
            </div>
          </div>
        }
      >
        {/* Loading overlay */}
        {loadingDetail && !interpreter && (
          <div className="flex h-64 items-center justify-center text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin text-gold" />
          </div>
        )}

        {interpreter && (
          <div className="space-y-4">
            {/* Header */}
            <div className="flex items-start gap-4">
              <div className="relative">
                <Avatar name={interpreter.name} src={raw.profile_image_url} size="xl" />
                {loadingDetail && (
                  <div className="absolute inset-0 rounded-full bg-background/60 flex items-center justify-center">
                    <Loader2 className="w-4 h-4 animate-spin text-gold" />
                  </div>
                )}
              </div>

              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-semibold font-display">{interpreter.name}</h2>
                  <div className="flex items-center gap-1 text-gold">
                    <Star className="w-4 h-4 fill-gold" />
                    <span className="font-mono font-medium">{interpreter.rating}</span>
                  </div>
                </div>
                <div className="flex items-center flex-wrap gap-2 mt-1">
                  <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium", status.bg, status.text)}>
                    {status.label}
                  </span>
                  <span className="text-sm text-muted-foreground border-l pl-2 border-border">
                    {interpreter.missions} missions completed
                  </span>
                  {raw.is_manually_blocked && raw.blocked_reason && (
                    <span className="text-sm text-danger border-l pl-2 border-border flex items-center gap-1">
                      <Shield className="w-3 h-3" /> {raw.blocked_reason}
                    </span>
                  )}
                </div>
              </div>
              <Button variant="outline" size="sm" className="flex-shrink-0"
                onClick={() => setEditModalOpen(true)}>
                <Edit className="w-4 h-4 mr-1.5" /> Edit
              </Button>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              {/* Contact Info */}
              <Section title="Contact Info">
                <InfoRow icon={User} label="Username" value={raw.user?.username} mono />
                <InfoRow icon={Mail} label="Email" value={raw.user?.email} />
                <InfoRow icon={Phone} label="Phone" value={raw.user?.phone} mono />
                <InfoRow icon={MapPin} label="Address" value={raw.address} />
                <InfoRow icon={MapPin} label="City / State" value={raw.city && raw.state ? `${raw.city}, ${raw.state} ${raw.zip_code || ''}`.trim() : null} />
                <InfoRow icon={MapPin} label="Radius" value={interpreter.radius ? `${interpreter.radius} miles` : null} />
              </Section>

              {/* Profile */}
              <Section title="Profile">
                <InfoRow icon={Calendar} label="Date of Birth" value={formatDate(raw.date_of_birth)} />
                <InfoRow icon={Briefcase} label="Experience" value={raw.years_of_experience ? `${raw.years_of_experience} yrs` : null} />
                <InfoRow icon={Calendar} label="Joined" value={formatDate(raw.user?.created_at)} />
                <InfoRow icon={Clock} label="Last Login" value={formatDateTime(raw.user?.last_login)} />
                {raw.bio && (
                  <div className="pt-1">
                    <p className="text-xs text-muted-foreground mb-0.5">Bio</p>
                    <p className="text-sm leading-relaxed">{raw.bio}</p>
                  </div>
                )}
              </Section>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              {/* Languages & Assignment */}
              <Section title="Languages & Assignment">
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {interpreter.langs.length > 0
                    ? interpreter.langs.map((lang, idx) => (
                        <span key={idx} className="px-2.5 py-1 bg-muted rounded-md text-xs font-medium">{lang}</span>
                      ))
                    : <span className="text-xs text-muted-foreground">No languages on file</span>
                  }
                </div>
                <InfoRow icon={Briefcase} label="Preferred Type" value={raw.preferred_assignment_type} />
                <InfoRow icon={Briefcase} label="Assignment Types" value={formatJsonList(raw.assignment_types)} />
                <InfoRow icon={MapPin} label="Cities Willing to Cover" value={formatJsonList(raw.cities_willing_to_cover)} />
              </Section>

              {/* Compliance */}
              <Section title="Compliance & Certifications">
                <InfoRow icon={Shield} label="Background Check" value={formatDate(raw.background_check_date)} />
                <div className="flex items-center gap-2 text-sm">
                  <Shield className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-muted-foreground text-xs">BG Status: </span>
                  <span className={raw.background_check_status ? "text-success font-medium" : "text-warning font-medium"}>
                    {raw.background_check_status ? "Cleared" : "Pending"}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <FileText className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-muted-foreground text-xs">W-9: </span>
                  <span className={raw.w9_on_file ? "text-success font-medium" : "text-warning font-medium"}>
                    {raw.w9_on_file ? "On File" : "Not on File"}
                  </span>
                </div>
                {raw.certifications && (
                  <InfoRow icon={CheckCircle} label="Certifications" value={formatJsonList(raw.certifications)} />
                )}
              </Section>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              {/* Contract */}
              <Section title="Contract & Files">
                {raw.contract_acceptance_date ? (
                  <div className="text-success text-xs font-medium flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> Accepted {formatDate(raw.contract_acceptance_date)}
                  </div>
                ) : (
                  <div className="text-warning text-xs font-medium flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> Pending Signature
                  </div>
                )}
                {raw.contract_url ? (
                  <a href={raw.contract_url} target="_blank" rel="noreferrer" className="block mt-2">
                    <Button variant="outline" size="sm" className="w-full justify-start text-xs border-dashed gap-2">
                      <FileText className="w-4 h-4 text-primary" />
                      View / Download Contract (PDF)
                      <LinkIcon className="w-3 h-3 ml-auto opacity-50" />
                    </Button>
                  </a>
                ) : (
                  <Button variant="outline" size="sm" disabled className="w-full justify-start text-xs border-dashed gap-2 mt-2">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    No Signed Contract on File
                  </Button>
                )}
              </Section>

              {/* Banking */}
              <div className="bg-card border border-border rounded-lg p-4 flex flex-col relative overflow-hidden">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex justify-between">
                  Banking Info
                  {raw.w9_on_file && <span className="text-success flex items-center gap-1 font-normal"><CheckCircle className="w-3 h-3" /> W-9</span>}
                </h4>
                <div className="space-y-2 text-sm">
                  <InfoRow icon={Building2} label="Bank Name" value={bankingData?.bank_name || raw.bank_name} />
                  <InfoRow icon={User} label="Account Holder" value={bankingData?.account_holder_name || raw.account_holder_name} />
                  <InfoRow icon={Hash} label="Routing #" value={bankingData?.routing_number || raw.routing_number} mono />
                  <InfoRow icon={CreditCard} label="Account #" value={bankingData?.account_number || raw.account_number} mono />
                  <InfoRow icon={CreditCard} label="Account Type" value={bankingData?.account_type || raw.account_type} />
                </div>
                {!bankingData && (
                  <div className="absolute inset-x-0 bottom-0 top-10 bg-background/80 backdrop-blur-[2px] flex items-center justify-center">
                    <Button size="sm" variant="secondary" onClick={fetchUnmaskedBanking} disabled={loadingBanking} className="shadow-sm">
                      {loadingBanking
                        ? <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        : <Shield className="w-4 h-4 mr-2 text-primary" />}
                      Reveal Banking Details
                    </Button>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Missions */}
            <div className="bg-card border border-border rounded-lg p-4">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Recent Missions</h4>
              {recentMissions.length > 0 ? (
                <div className="space-y-1">
                  {recentMissions.map((mission, idx) => {
                    const missionStatus = mission.status || "";
                    const isCompleted = missionStatus === "COMPLETED";
                    const isCancelled = missionStatus === "CANCELLED";
                    const rate = mission.interpreter_rate ? `$${Number(mission.interpreter_rate).toFixed(2)}/hr` : null;
                    const paid = mission.total_interpreter_payment ? `$${Number(mission.total_interpreter_payment).toFixed(2)}` : null;
                    const langs = [mission.source_language_name, mission.target_language_name].filter(Boolean).join(" → ");

                    return (
                      <div key={idx} className="py-2.5 border-b border-border/50 last:border-0 hover:bg-muted/30 px-2 rounded-sm transition-colors">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            {isCompleted ? <CheckCircle className="w-3.5 h-3.5 text-success flex-shrink-0" />
                              : isCancelled ? <XCircle className="w-3.5 h-3.5 text-danger flex-shrink-0" />
                              : <Clock className="w-3.5 h-3.5 text-warning flex-shrink-0" />}
                            <span className="text-sm font-medium">{mission.client_display || mission.client_name || "—"}</span>
                            {mission.service_type_name && (
                              <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">{mission.service_type_name}</span>
                            )}
                          </div>
                          <span className={cn("text-[10px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded",
                            isCompleted ? "bg-success/10 text-success" :
                            isCancelled ? "bg-danger/10 text-danger" :
                            "bg-warning/10 text-warning"
                          )}>{missionStatus}</span>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-muted-foreground pl-5 flex-wrap">
                          {mission.start_time && (
                            <span className="font-mono">{new Date(mission.start_time).toLocaleDateString()} {mission.start_time_local ? `(${new Date(mission.start_time_local).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})})` : ""}</span>
                          )}
                          {(mission.city || mission.state) && (
                            <span>{[mission.city, mission.state].filter(Boolean).join(", ")}</span>
                          )}
                          {langs && <span className="text-primary font-medium">{langs}</span>}
                          {rate && <span className="font-mono">{rate}</span>}
                          {paid && <span className="font-mono font-semibold text-success">{paid} paid</span>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-sm text-muted-foreground text-center py-6 border border-dashed rounded-md bg-muted/20">
                  No recent missions on record
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* Block Dialog */}
      <Modal
        isOpen={confirmDialog.isOpen && confirmDialog.type === "block"}
        onClose={() => !isSubmitting && setConfirmDialog({ isOpen: false, type: null })}
        size="sm"
        showClose={false}
      >
        <div className="flex flex-col text-center pt-2 pb-4">
          <div className="w-12 h-12 rounded-full bg-danger/10 text-danger flex items-center justify-center mx-auto mb-4">
            <Ban className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Block {interpreter?.name}?</h3>
          <p className="text-sm text-muted-foreground mb-4">
            This interpreter will be hidden from the dispatch board and prevented from accepting new missions.
          </p>
          <div className="text-left w-full mb-6">
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Reason (Required):</label>
            <textarea
              className="w-full flex min-h-[80px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="e.g. No show, compliance issue..."
              value={blockReason}
              onChange={(e) => setBlockReason(e.target.value)}
            />
          </div>
          <div className="flex gap-3 w-full">
            <Button variant="outline" className="flex-1" onClick={() => setConfirmDialog({ isOpen: false, type: null })} disabled={isSubmitting}>Cancel</Button>
            <Button variant="destructive" className="flex-1" onClick={handleBlock} disabled={isSubmitting || !blockReason.trim()}>
              {isSubmitting ? "Processing..." : "Block Interpreter"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Unblock Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen && confirmDialog.type === "unblock"}
        onConfirm={handleUnblock}
        onCancel={() => setConfirmDialog({ isOpen: false, type: null })}
        title={`Unblock ${interpreter?.name}?`}
        message={`Reason they were blocked: "${raw.blocked_reason || 'Unknown'}".\nThis will restore them to Active status.`}
        confirmText="Yes, Unblock"
        variant="info"
        loading={isSubmitting}
      />

      {/* Send Message Dialog */}
      <Modal
        isOpen={messageDialog.isOpen}
        onClose={() => !sendingMessage && setMessageDialog({ isOpen: false, subject: "", body: "", attachment: null })}
        size="sm"
      >
        <div className="space-y-4 pb-2">
          <div className="flex items-center gap-2 mb-1">
            <MessageSquare className="w-5 h-5 text-primary" />
            <h3 className="text-base font-semibold">Send Message to {interpreter?.name}</h3>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Subject</label>
            <input
              type="text"
              className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="e.g. Upcoming assignment, Schedule update..."
              value={messageDialog.subject}
              onChange={e => setMessageDialog(d => ({ ...d, subject: e.target.value }))}
              disabled={sendingMessage}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Message</label>
            <textarea
              className="w-full flex min-h-[120px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
              placeholder="Type your message here..."
              value={messageDialog.body}
              onChange={e => setMessageDialog(d => ({ ...d, body: e.target.value }))}
              disabled={sendingMessage}
            />
          </div>
          {/* Attachment */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Attachment (optional)</label>
            {messageDialog.attachment ? (
              <div className="flex items-center gap-2 px-3 py-2 border border-border rounded-md bg-muted/30">
                <Paperclip className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                <span className="text-sm truncate flex-1">{messageDialog.attachment.name}</span>
                <button
                  onClick={() => setMessageDialog(d => ({ ...d, attachment: null }))}
                  className="text-muted-foreground hover:text-foreground"
                  disabled={sendingMessage}
                >
                  <XIcon className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <label className={cn(
                "flex items-center gap-2 px-3 py-2 border border-dashed border-border rounded-md cursor-pointer",
                "text-sm text-muted-foreground hover:bg-muted/30 transition-colors",
                sendingMessage && "pointer-events-none opacity-50"
              )}>
                <Paperclip className="w-3.5 h-3.5" />
                Click to attach a file
                <input
                  type="file"
                  className="hidden"
                  onChange={e => setMessageDialog(d => ({ ...d, attachment: e.target.files?.[0] || null }))}
                  disabled={sendingMessage}
                />
              </label>
            )}
          </div>
          <div className="flex gap-3 pt-1">
            <Button variant="outline" className="flex-1"
              onClick={() => setMessageDialog({ isOpen: false, subject: "", body: "", attachment: null })}
              disabled={sendingMessage}>
              Cancel
            </Button>
            <Button className="flex-1 gap-1.5 bg-navy hover:bg-navy-light text-white"
              onClick={handleSendMessage}
              disabled={sendingMessage || !messageDialog.subject.trim() || !messageDialog.body.trim()}>
              {sendingMessage ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Send Email
            </Button>
          </div>
        </div>
      </Modal>

      {/* Edit Interpreter Modal */}
      <EditInterpreterModal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        interpreter={interpreter}
        onSaved={() => {
          refetchDetail();
          onStatusChange?.();
        }}
      />
    </>
  );
};
