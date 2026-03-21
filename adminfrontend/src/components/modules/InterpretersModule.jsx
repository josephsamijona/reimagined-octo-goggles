// JHBridge Command Center - Interpreters Module
import { useState, useMemo, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  SectionHeader,
  DataTable,
  Avatar,
  LanguageTag,
  StatusDot
} from "@/components/shared/UIComponents";
import { FilterDropdown } from "@/components/shared/FilterDropdown";
import { InterpreterDetailModal } from "@/components/modals/InterpreterDetailModal";
import { MissionFormModal } from "@/components/modals/MissionFormModal";
import { InterpretersMap } from "./InterpretersMap";
import { Modal } from "@/components/shared/Modal";
import { showToast } from "@/components/shared/Toast";
import { interpreterService } from "@/services/interpreterService";
import {
  Loader2, Map as MapIcon, Grid, List,
  CheckSquare, Square, ChevronDown,
  Paperclip, X as XIcon, Send, MessageSquare, Ban,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useInterpreters } from "@/hooks/useInterpreters";

// ------------------------------------------------------------------
// Bulk action options
// ------------------------------------------------------------------
const BULK_ACTIONS = [
  { value: "activate",           label: "Activate" },
  { value: "deactivate",         label: "Deactivate" },
  { value: "block",              label: "Block (requires reason)" },
  { value: "unblock",            label: "Unblock" },
  { value: "suspend",            label: "Suspend" },
  { value: "send_contract",      label: "Send Contract Invitation" },
  { value: "send_onboarding",    label: "Send Onboarding Email" },
  { value: "send_reminder_1",    label: "Send Reminder — Level 1" },
  { value: "send_reminder_2",    label: "Send Reminder — Level 2" },
  { value: "send_reminder_3",    label: "Send Reminder — Level 3" },
  { value: "send_password_reset","label": "Reset Passwords" },
  { value: "send_message",       label: "Send Message (email)" },
];

const ACTIONS_NEEDING_REASON = new Set(["block", "suspend"]);
const ACTIONS_NEEDING_MESSAGE = new Set(["send_message"]);

export const InterpretersModule = () => {
  const [view, setView] = useState("grid"); // "grid" | "table" | "map"
  const [activeFilters, setActiveFilters] = useState({});
  const [selectedInterpreter, setSelectedInterpreter] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [missionFormOpen, setMissionFormOpen] = useState(false);
  const [assigningInterpreter, setAssigningInterpreter] = useState(null);

  // Bulk selection
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [pendingBulkAction, setPendingBulkAction] = useState("");
  const [bulkSubmitting, setBulkSubmitting] = useState(false);

  // Bulk — block/suspend dialog
  const [blockDialog, setBlockDialog] = useState({ isOpen: false, reason: "" });

  // Bulk — message dialog
  const [msgDialog, setMsgDialog] = useState({ isOpen: false, subject: "", body: "", attachment: null });
  const attachRef = useRef(null);

  // Hook for API data
  const { interpreters: apiInterpreters, loading, error, refreshAction } = useInterpreters();

  // Map API shape → UI shape
  const interpreters = useMemo(() => apiInterpreters.map(apiData => ({
    id: apiData.id,
    name: `${apiData.first_name || apiData.user?.first_name || ''} ${apiData.last_name || apiData.user?.last_name || ''}`.trim() || "Unknown",
    langs: apiData.languages?.map(l => l.name) || [],
    rating: Number(apiData.avg_rating) ? Number(apiData.avg_rating).toFixed(1) : "New",
    missions: apiData.missions_count || 0,
    radius: apiData.radius_of_service || null,
    status: apiData.is_manually_blocked ? "blocked" : apiData.is_on_mission ? "on_mission" : "available",
    address: apiData.address || "",
    city: apiData.city || "Unknown",
    state: apiData.state || "",
    lat: apiData.lat || null,
    lng: apiData.lng || null,
    _raw: apiData,
  })), [apiInterpreters]);

  const allLanguages = [...new Set(interpreters.flatMap(i => i.langs))].filter(Boolean);
  const allStates    = [...new Set(interpreters.map(i => i.state))].filter(Boolean);

  const filterConfig = [
    {
      key: "status", label: "Status",
      options: [
        { value: "available",  label: "Available",  count: interpreters.filter(i => i.status === "available").length },
        { value: "on_mission", label: "On Mission", count: interpreters.filter(i => i.status === "on_mission").length },
        { value: "blocked",    label: "Blocked",    count: interpreters.filter(i => i.status === "blocked").length },
      ],
    },
    {
      key: "langs", label: "Languages",
      options: allLanguages.map(lang => ({
        value: lang, label: lang,
        count: interpreters.filter(i => i.langs.includes(lang)).length,
      })),
    },
    {
      key: "state", label: "State",
      options: allStates.map(state => ({
        value: state, label: state,
        count: interpreters.filter(i => i.state === state).length,
      })),
    },
  ];

  const filteredInterpreters = useMemo(() => {
    let result = interpreters;
    Object.entries(activeFilters).forEach(([key, values]) => {
      if (values?.length > 0) {
        if (key === "langs") result = result.filter(i => i.langs.some(l => values.includes(l)));
        else result = result.filter(i => values.includes(i[key]));
      }
    });
    return result;
  }, [interpreters, activeFilters]);

  // ------------------------------------------------------------------
  // Selection helpers
  // ------------------------------------------------------------------
  const allSelected = filteredInterpreters.length > 0 && filteredInterpreters.every(i => selectedIds.has(i.id));
  const someSelected = selectedIds.size > 0;

  const toggleSelect = (id, e) => {
    e.stopPropagation();
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredInterpreters.map(i => i.id)));
    }
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
    setPendingBulkAction("");
  };

  // ------------------------------------------------------------------
  // Bulk action execution
  // ------------------------------------------------------------------
  const applyBulkAction = async (action, options = {}) => {
    setBulkSubmitting(true);
    const ids = [...selectedIds];
    try {
      const result = await interpreterService.bulkAction(action, ids, options);
      const label = BULK_ACTIONS.find(a => a.value === action)?.label || action;
      showToast.success(`${label} applied to ${result.affected ?? ids.length} interpreter(s)`);
      clearSelection();
      refreshAction();
    } catch {
      showToast.error("Bulk action failed. Please try again.");
    } finally {
      setBulkSubmitting(false);
    }
  };

  const handleApplyBulkAction = () => {
    if (!pendingBulkAction) return;
    if (ACTIONS_NEEDING_REASON.has(pendingBulkAction)) {
      setBlockDialog({ isOpen: true, reason: "" });
    } else if (ACTIONS_NEEDING_MESSAGE.has(pendingBulkAction)) {
      setMsgDialog({ isOpen: true, subject: "", body: "", attachment: null });
    } else {
      applyBulkAction(pendingBulkAction);
    }
  };

  const handleBulkBlock = async () => {
    if (!blockDialog.reason.trim()) { showToast.error("A reason is required"); return; }
    await applyBulkAction(pendingBulkAction, { reason: blockDialog.reason });
    setBlockDialog({ isOpen: false, reason: "" });
  };

  const handleBulkMessage = async () => {
    if (!msgDialog.subject.trim() || !msgDialog.body.trim()) {
      showToast.error("Subject and message are required");
      return;
    }
    await applyBulkAction("send_message", {
      subject: msgDialog.subject,
      body: msgDialog.body,
      attachment: msgDialog.attachment || undefined,
    });
    setMsgDialog({ isOpen: false, subject: "", body: "", attachment: null });
  };

  // ------------------------------------------------------------------
  // Detail modal handlers
  // ------------------------------------------------------------------
  const getStatusLabel = (status) => ({ available: "Available", on_mission: "On Mission", blocked: "Blocked" }[status] || status);
  const getStatusColor = (status) => ({ available: "text-success", on_mission: "text-gold", blocked: "text-danger" }[status] || "text-muted-foreground");

  const handleInterpreterClick = (interpreter) => {
    setSelectedInterpreter(interpreter);
    setDetailModalOpen(true);
  };

  const handleAssignMission = (interpreter) => {
    setAssigningInterpreter(interpreter);
    setDetailModalOpen(false);
    setMissionFormOpen(true);
  };

  const handleStatusChange = () => {
    refreshAction();
    setDetailModalOpen(false);
  };

  // ------------------------------------------------------------------
  // Loading / error states
  // ------------------------------------------------------------------
  if (loading) {
    return (
      <div className="flex flex-col gap-4">
        <SectionHeader title="Interpreters" subtitle="Loading staff network..." />
        <div className="flex h-64 items-center justify-center text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin text-gold mb-2" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col gap-4">
        <SectionHeader title="Interpreters" subtitle="Error Loading" />
        <div className="flex flex-col h-64 items-center justify-center text-danger gap-2">
          <p className="font-medium text-lg">{error}</p>
          <Button onClick={refreshAction} variant="outline" className="mt-2 text-foreground">Retry</Button>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  const inputCls = "w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

  return (
    <div className="flex flex-col gap-4" data-testid="interpreters-module">
      <SectionHeader
        title="Interpreters"
        subtitle={`${filteredInterpreters.length} interpreters${Object.values(activeFilters).flat().length > 0 ? ' (filtered)' : ' across the US'}`}
        action={
          <div className="flex gap-2">
            {/* View Toggle */}
            <div className="flex border border-border rounded-md overflow-hidden bg-muted/30 p-0.5">
              {[
                { id: "grid",  Icon: Grid,    label: "Grid" },
                { id: "table", Icon: List,    label: "Table" },
                { id: "map",   Icon: MapIcon, label: "Map" },
              ].map(({ id, Icon, label }) => (
                <button
                  key={id}
                  onClick={() => setView(id)}
                  className={cn(
                    "px-3 py-1.5 text-xs font-medium flex items-center gap-1.5 transition-colors rounded-sm",
                    view === id ? "bg-background text-foreground shadow-sm" : "bg-transparent text-muted-foreground hover:bg-muted"
                  )}
                >
                  <Icon className="w-3.5 h-3.5" /> {label}
                </button>
              ))}
            </div>
            <FilterDropdown filters={filterConfig} activeFilters={activeFilters} onChange={setActiveFilters} />
          </div>
        }
      />

      {/* Bulk Action Bar */}
      {someSelected && (
        <div className="bg-navy text-white rounded-lg px-4 py-2.5 flex items-center gap-3 shadow-lg flex-wrap">
          <button
            onClick={toggleSelectAll}
            className="flex items-center gap-1.5 text-sm font-medium hover:text-white/80"
          >
            {allSelected
              ? <CheckSquare className="w-4 h-4" />
              : <Square className="w-4 h-4" />}
            {selectedIds.size} selected
          </button>
          <button onClick={clearSelection} className="text-white/50 hover:text-white text-xs underline underline-offset-2">
            Clear
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <div className="relative">
              <select
                value={pendingBulkAction}
                onChange={e => setPendingBulkAction(e.target.value)}
                className="appearance-none bg-white/10 border border-white/20 rounded px-3 py-1.5 text-sm text-white pr-7 focus:outline-none focus:ring-1 focus:ring-white/40 cursor-pointer"
              >
                <option value="">Choose action…</option>
                {BULK_ACTIONS.map(a => (
                  <option key={a.value} value={a.value} className="text-foreground bg-background">
                    {a.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-white/60" />
            </div>
            <Button
              size="sm"
              onClick={handleApplyBulkAction}
              disabled={!pendingBulkAction || bulkSubmitting}
              className="bg-gold text-navy hover:bg-gold/90 font-semibold"
            >
              {bulkSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Apply"}
            </Button>
          </div>
        </div>
      )}

      {/* Select All row when nothing selected yet (table + grid only) */}
      {!someSelected && view !== "map" && filteredInterpreters.length > 0 && (
        <div className="flex items-center gap-2">
          <button
            onClick={toggleSelectAll}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <Square className="w-3.5 h-3.5" />
            Select all {filteredInterpreters.length}
          </button>
        </div>
      )}

      {/* Views */}
      {view === "map" ? (
        <InterpretersMap interpreters={filteredInterpreters} onInterpreterClick={handleInterpreterClick} />
      ) : view === "grid" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {filteredInterpreters.map((interp, i) => {
            const isSelected = selectedIds.has(interp.id);
            return (
              <Card
                key={interp.id || i}
                className={cn(
                  "shadow-sm cursor-pointer transition-all hover:border-gold hover:shadow-md",
                  isSelected && "border-gold ring-1 ring-gold/50"
                )}
                onClick={() => handleInterpreterClick(interp)}
                data-testid={`interpreter-card-${interp.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-center gap-2.5 mb-3">
                    {/* Checkbox */}
                    <button
                      className="flex-shrink-0 text-muted-foreground hover:text-foreground"
                      onClick={e => toggleSelect(interp.id, e)}
                    >
                      {isSelected
                        ? <CheckSquare className="w-4 h-4 text-gold" />
                        : <Square className="w-4 h-4" />}
                    </button>
                    <Avatar name={interp.name} src={interp._raw?.profile_image_url} size="md" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold truncate">{interp.name}</div>
                      <div className="text-[11px] text-muted-foreground font-mono">
                        {interp.city}, {interp.state}
                      </div>
                    </div>
                    <StatusDot status={interp.status} size="md" />
                  </div>

                  <div className="flex flex-wrap gap-1 mb-3">
                    {interp.langs.map((l, j) => <LanguageTag key={j} lang={l} />)}
                  </div>

                  <div className="grid grid-cols-2 gap-1 text-[11px] font-mono">
                    {interp.address && (
                      <span className="col-span-2 text-muted-foreground truncate">
                        <span className="text-foreground">{interp.address}</span>
                      </span>
                    )}
                    <span className="text-muted-foreground">
                      Radius: <span className="text-foreground font-medium">{interp.radius ? `${interp.radius}mi` : "N/A"}</span>
                    </span>
                    <span className="text-muted-foreground">
                      Missions: <span className="text-foreground font-medium">{interp.missions}</span>
                    </span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <DataTable
          columns={[
            {
              label: (
                <button onClick={toggleSelectAll} className="text-muted-foreground hover:text-foreground">
                  {allSelected ? <CheckSquare className="w-4 h-4 text-gold" /> : <Square className="w-4 h-4" />}
                </button>
              ),
              render: r => (
                <button
                  onClick={e => toggleSelect(r.id, e)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  {selectedIds.has(r.id) ? <CheckSquare className="w-4 h-4 text-gold" /> : <Square className="w-4 h-4" />}
                </button>
              ),
            },
            { label: "Name", render: r => (
                <div className="flex items-center gap-2">
                  <Avatar name={r.name} src={r._raw?.profile_image_url} size="sm" />
                  <span className="font-semibold">{r.name}</span>
                </div>
              )
            },
            { label: "Address", render: r => r.address || "—" },
            { label: "City",    render: r => r.city },
            { label: "State",   render: r => r.state },
            { label: "Languages", render: r => r.langs.length > 0 ? r.langs.join(", ") : "—" },
            {
              label: "Status",
              render: r => (
                <span className={cn("text-[11px] font-semibold", getStatusColor(r.status))}>
                  {getStatusLabel(r.status)}
                </span>
              ),
            },
          ]}
          data={filteredInterpreters}
          onRowClick={handleInterpreterClick}
        />
      )}

      {/* Empty State */}
      {filteredInterpreters.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <p>No interpreters found with current filters</p>
          <Button variant="link" onClick={() => setActiveFilters({})}>Clear filters</Button>
        </div>
      )}

      {/* Detail Modal */}
      <InterpreterDetailModal
        isOpen={detailModalOpen}
        onClose={() => { setDetailModalOpen(false); setSelectedInterpreter(null); }}
        interpreterId={selectedInterpreter?.id}
        initialData={selectedInterpreter}
        onAssignMission={handleAssignMission}
        onStatusChange={handleStatusChange}
      />

      <MissionFormModal
        isOpen={missionFormOpen}
        onClose={() => { setMissionFormOpen(false); setAssigningInterpreter(null); }}
        prefillData={assigningInterpreter ? {
          interpreterId: assigningInterpreter.id?.toString(),
          sourceLang: assigningInterpreter.langs[0] || "",
          rate: assigningInterpreter.rate,
        } : null}
        onSuccess={() => { setMissionFormOpen(false); setAssigningInterpreter(null); }}
      />

      {/* Bulk — Block/Suspend Dialog */}
      <Modal
        isOpen={blockDialog.isOpen}
        onClose={() => !bulkSubmitting && setBlockDialog({ isOpen: false, reason: "" })}
        size="sm"
        showClose={false}
      >
        <div className="flex flex-col text-center pt-2 pb-4">
          <div className="w-12 h-12 rounded-full bg-danger/10 text-danger flex items-center justify-center mx-auto mb-4">
            <Ban className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-semibold mb-1">
            {pendingBulkAction === "block" ? "Block" : "Suspend"} {selectedIds.size} interpreter(s)?
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            Provide a reason — this will be recorded on each interpreter's profile.
          </p>
          <div className="text-left w-full mb-6">
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Reason (required)</label>
            <textarea
              className={`${inputCls} min-h-[80px] resize-none`}
              placeholder="e.g. No show, compliance issue..."
              value={blockDialog.reason}
              onChange={e => setBlockDialog(d => ({ ...d, reason: e.target.value }))}
              disabled={bulkSubmitting}
            />
          </div>
          <div className="flex gap-3 w-full">
            <Button variant="outline" className="flex-1" onClick={() => setBlockDialog({ isOpen: false, reason: "" })} disabled={bulkSubmitting}>Cancel</Button>
            <Button variant="destructive" className="flex-1" onClick={handleBulkBlock} disabled={bulkSubmitting || !blockDialog.reason.trim()}>
              {bulkSubmitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Confirm
            </Button>
          </div>
        </div>
      </Modal>

      {/* Bulk — Send Message Dialog */}
      <Modal
        isOpen={msgDialog.isOpen}
        onClose={() => !bulkSubmitting && setMsgDialog({ isOpen: false, subject: "", body: "", attachment: null })}
        size="sm"
      >
        <div className="space-y-4 pb-2">
          <div className="flex items-center gap-2 mb-1">
            <MessageSquare className="w-5 h-5 text-primary" />
            <h3 className="text-base font-semibold">Send Message to {selectedIds.size} interpreter(s)</h3>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Subject</label>
            <input
              type="text"
              className={inputCls}
              placeholder="e.g. Schedule update, Important notice..."
              value={msgDialog.subject}
              onChange={e => setMsgDialog(d => ({ ...d, subject: e.target.value }))}
              disabled={bulkSubmitting}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Message</label>
            <textarea
              className={`${inputCls} min-h-[120px] resize-none`}
              placeholder="Type your message here..."
              value={msgDialog.body}
              onChange={e => setMsgDialog(d => ({ ...d, body: e.target.value }))}
              disabled={bulkSubmitting}
            />
          </div>
          {/* Attachment */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Attachment (optional)</label>
            {msgDialog.attachment ? (
              <div className="flex items-center gap-2 px-3 py-2 border border-border rounded-md bg-muted/30">
                <Paperclip className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                <span className="text-sm truncate flex-1">{msgDialog.attachment.name}</span>
                <button onClick={() => setMsgDialog(d => ({ ...d, attachment: null }))} disabled={bulkSubmitting}>
                  <XIcon className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
                </button>
              </div>
            ) : (
              <label className={cn(
                "flex items-center gap-2 px-3 py-2 border border-dashed border-border rounded-md cursor-pointer",
                "text-sm text-muted-foreground hover:bg-muted/30 transition-colors",
                bulkSubmitting && "pointer-events-none opacity-50"
              )}>
                <Paperclip className="w-3.5 h-3.5" />
                Click to attach a file
                <input
                  ref={attachRef}
                  type="file"
                  className="hidden"
                  onChange={e => setMsgDialog(d => ({ ...d, attachment: e.target.files?.[0] || null }))}
                  disabled={bulkSubmitting}
                />
              </label>
            )}
          </div>
          <div className="flex gap-3 pt-1">
            <Button variant="outline" className="flex-1"
              onClick={() => setMsgDialog({ isOpen: false, subject: "", body: "", attachment: null })}
              disabled={bulkSubmitting}>
              Cancel
            </Button>
            <Button className="flex-1 gap-1.5 bg-navy hover:bg-navy-light text-white"
              onClick={handleBulkMessage}
              disabled={bulkSubmitting || !msgDialog.subject.trim() || !msgDialog.body.trim()}>
              {bulkSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Send to {selectedIds.size}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default InterpretersModule;
