// JHBridge Command Center - Dispatch Module (Updated with all functionalities)
import { useState, useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MOCK } from "@/data/mockData";
import { 
  SectionHeader, 
  TabBar, 
  DataTable, 
  StatusBadge 
} from "@/components/shared/UIComponents";
import { FilterDropdown } from "@/components/shared/FilterDropdown";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { MissionFormModal } from "@/components/modals/MissionFormModal";
import { MissionDetailModal } from "@/components/modals/MissionDetailModal";
import { showToast } from "@/components/shared/Toast";
import { Plus, Check, X, MapPin, User } from "lucide-react";
import { cn } from "@/lib/utils";

export const DispatchModule = () => {
  const [tab, setTab] = useState("all");
  const [assignments, setAssignments] = useState(MOCK.assignments);
  const [activeFilters, setActiveFilters] = useState({});
  
  // Modal states
  const [missionFormOpen, setMissionFormOpen] = useState(false);
  const [editingMission, setEditingMission] = useState(null);
  const [selectedMission, setSelectedMission] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  
  // Confirm dialog states
  const [confirmDialog, setConfirmDialog] = useState({ isOpen: false, mission: null, action: null });
  const [confirmLoading, setConfirmLoading] = useState(false);

  // Popup state for map
  const [mapPopup, setMapPopup] = useState({ visible: false, interpreter: null, x: 0, y: 0 });

  // Filter configuration
  const filterConfig = [
    {
      key: "status",
      label: "Status",
      options: [
        { value: "PENDING", label: "Pending", count: assignments.filter(a => a.status === "PENDING").length },
        { value: "CONFIRMED", label: "Confirmed", count: assignments.filter(a => a.status === "CONFIRMED").length },
        { value: "IN_PROGRESS", label: "In Progress", count: assignments.filter(a => a.status === "IN_PROGRESS").length },
        { value: "COMPLETED", label: "Completed", count: assignments.filter(a => a.status === "COMPLETED").length },
        { value: "CANCELLED", label: "Cancelled", count: assignments.filter(a => a.status === "CANCELLED").length },
      ],
    },
    {
      key: "type",
      label: "Service Type",
      options: [
        { value: "Medical", label: "Medical" },
        { value: "Legal", label: "Legal" },
        { value: "Conference", label: "Conference" },
        { value: "Other", label: "Other" },
      ],
    },
    {
      key: "city",
      label: "Location",
      options: [
        { value: "Boston", label: "Boston" },
        { value: "Cambridge", label: "Cambridge" },
        { value: "Worcester", label: "Worcester" },
      ],
    },
  ];

  // Apply filters
  const filteredAssignments = useMemo(() => {
    let result = assignments;
    
    // Tab filter
    if (tab !== "all") {
      result = result.filter(a => a.status === tab);
    }
    
    // Active filters
    Object.entries(activeFilters).forEach(([key, values]) => {
      if (values && values.length > 0) {
        result = result.filter(a => values.includes(a[key]));
      }
    });
    
    return result;
  }, [assignments, tab, activeFilters]);

  const counts = useMemo(() => {
    const c = { all: assignments.length, PENDING: 0, CONFIRMED: 0, IN_PROGRESS: 0, COMPLETED: 0, CANCELLED: 0 };
    assignments.forEach(a => c[a.status] = (c[a.status] || 0) + 1);
    return c;
  }, [assignments]);

  // Handle confirm/cancel mission
  const handleConfirmAction = async () => {
    if (!confirmDialog.mission) return;
    
    setConfirmLoading(true);
    await new Promise(resolve => setTimeout(resolve, 600));
    
    const newStatus = confirmDialog.action === "confirm" ? "CONFIRMED" : "CANCELLED";
    
    setAssignments(prev => 
      prev.map(a => a.id === confirmDialog.mission.id ? { ...a, status: newStatus } : a)
    );
    
    if (confirmDialog.action === "confirm") {
      showToast.success(`Mission ${confirmDialog.mission.id} confirmed`);
    } else {
      showToast.warning(`Mission ${confirmDialog.mission.id} cancelled`);
    }
    
    setConfirmLoading(false);
    setConfirmDialog({ isOpen: false, mission: null, action: null });
  };

  // Handle new mission created
  const handleMissionCreated = (newMission) => {
    if (editingMission) {
      // Update existing
      setAssignments(prev => 
        prev.map(a => a.id === editingMission.id ? { ...a, ...newMission } : a)
      );
    } else {
      // Add new
      setAssignments(prev => [newMission, ...prev]);
    }
    setEditingMission(null);
  };

  // Handle row click
  const handleRowClick = (mission) => {
    setSelectedMission(mission);
    setDetailModalOpen(true);
  };

  // Handle edit from detail modal
  const handleEdit = (mission) => {
    setDetailModalOpen(false);
    setEditingMission(mission);
    setMissionFormOpen(true);
  };

  // Handle status change from detail modal
  const handleStatusChange = (missionId, newStatus) => {
    setAssignments(prev => 
      prev.map(a => a.id === missionId ? { ...a, status: newStatus } : a)
    );
    setDetailModalOpen(false);
  };

  // Handle map dot click
  const handleMapDotClick = (e, interpreter) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMapPopup({
      visible: true,
      interpreter,
      x: rect.left + rect.width / 2,
      y: rect.top,
    });
  };

  return (
    <div className="flex flex-col gap-4" data-testid="dispatch-module">
      <SectionHeader 
        title="Dispatch Center" 
        subtitle="Mission control & interpreter assignment" 
        action={
          <div className="flex gap-2">
            <FilterDropdown
              filters={filterConfig}
              activeFilters={activeFilters}
              onChange={setActiveFilters}
            />
            <Button 
              size="sm" 
              className="gap-1.5 bg-navy hover:bg-navy-light" 
              onClick={() => {
                setEditingMission(null);
                setMissionFormOpen(true);
              }}
              data-testid="new-mission-btn"
            >
              <Plus className="w-3.5 h-3.5" /> New Mission
            </Button>
          </div>
        } 
      />

      {/* Map Placeholder */}
      <Card className="shadow-sm overflow-hidden">
        <CardContent className="p-0 h-56 bg-muted/30 relative">
          {/* Grid Pattern */}
          <div 
            className="absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage: `repeating-linear-gradient(0deg, currentColor 0px, currentColor 1px, transparent 1px, transparent 40px), 
                               repeating-linear-gradient(90deg, currentColor 0px, currentColor 1px, transparent 1px, transparent 40px)`
            }}
          />
          
          {/* Interpreter Dots */}
          {MOCK.interpreters.map((interp, i) => {
            const x = ((interp.lng + 74) / 5) * 100;
            const y = ((43 - interp.lat) / 4) * 100;
            const statusColor = interp.status === "available" 
              ? "bg-success" 
              : interp.status === "on_mission" 
                ? "bg-gold" 
                : "bg-danger";
            
            return (
              <div 
                key={i}
                onClick={(e) => handleMapDotClick(e, interp)}
                className={cn(
                  "absolute w-3 h-3 rounded-full border-2 border-white dark:border-card shadow-md cursor-pointer hover:scale-150 transition-transform z-10",
                  statusColor
                )}
                style={{ 
                  left: `${Math.max(5, Math.min(95, x))}%`, 
                  top: `${Math.max(10, Math.min(90, y))}%` 
                }}
                title={`${interp.name} — ${interp.status.replace("_", " ")}`}
                data-testid={`map-dot-${interp.id}`}
              />
            );
          })}
          
          {/* Center Label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center z-0">
            <MapPin className="w-8 h-8 text-muted-foreground/50 mb-2" />
            <span className="text-sm font-medium text-muted-foreground">Interactive Map</span>
            <span className="text-[10px] text-muted-foreground/70 font-mono">
              {MOCK.interpreters.length} interpreters · Click dots for details
            </span>
          </div>
          
          {/* Legend */}
          <div className="absolute bottom-3 left-3 flex gap-3">
            {[
              { label: "Available", color: "bg-success" },
              { label: "On Mission", color: "bg-gold" },
              { label: "Blocked", color: "bg-danger" },
            ].map((l, i) => (
              <span key={i} className="text-[10px] text-muted-foreground flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${l.color}`} /> {l.label}
              </span>
            ))}
          </div>

          {/* Map Popup */}
          {mapPopup.visible && mapPopup.interpreter && (
            <div 
              className="absolute z-20 bg-card border border-border rounded-lg shadow-lg p-3 w-56 animate-in fade-in zoom-in-95 duration-150"
              style={{
                left: `${((mapPopup.interpreter.lng + 74) / 5) * 100}%`,
                top: `${((43 - mapPopup.interpreter.lat) / 4) * 100 + 5}%`,
                transform: "translateX(-50%)",
              }}
              onMouseLeave={() => setMapPopup({ visible: false, interpreter: null, x: 0, y: 0 })}
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 rounded-full bg-navy text-white flex items-center justify-center text-xs font-bold">
                  {mapPopup.interpreter.name.split(" ").map(n => n[0]).join("")}
                </div>
                <div>
                  <div className="font-semibold text-sm">{mapPopup.interpreter.name}</div>
                  <div className={cn(
                    "text-[10px] font-medium",
                    mapPopup.interpreter.status === "available" ? "text-success" :
                    mapPopup.interpreter.status === "on_mission" ? "text-gold" : "text-danger"
                  )}>
                    {mapPopup.interpreter.status.replace("_", " ").toUpperCase()}
                  </div>
                </div>
              </div>
              <div className="text-xs space-y-1 text-muted-foreground mb-2">
                <div className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {mapPopup.interpreter.city}, {mapPopup.interpreter.state} ({mapPopup.interpreter.radius}mi)
                </div>
                <div>Languages: {mapPopup.interpreter.langs.join(", ")}</div>
                <div>Rate: ${mapPopup.interpreter.rate}/hr · Rating: {mapPopup.interpreter.rating}★</div>
              </div>
              <div className="flex gap-1">
                <Button size="sm" variant="outline" className="flex-1 h-7 text-xs">
                  View Profile
                </Button>
                {mapPopup.interpreter.status === "available" && (
                  <Button size="sm" className="flex-1 h-7 text-xs bg-navy hover:bg-navy-light">
                    Assign
                  </Button>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabs */}
      <TabBar 
        tabs={[
          { key: "all", label: "All", count: counts.all },
          { key: "PENDING", label: "Pending", count: counts.PENDING },
          { key: "CONFIRMED", label: "Confirmed", count: counts.CONFIRMED },
          { key: "IN_PROGRESS", label: "In Progress", count: counts.IN_PROGRESS },
          { key: "COMPLETED", label: "Completed", count: counts.COMPLETED },
        ]} 
        active={tab} 
        onChange={setTab} 
      />

      {/* Active Filters Display */}
      {Object.values(activeFilters).flat().length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground">Active filters:</span>
          {Object.entries(activeFilters).map(([key, values]) =>
            values?.map(value => (
              <span 
                key={`${key}-${value}`}
                className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded flex items-center gap-1"
              >
                {value}
                <button
                  onClick={() => setActiveFilters(prev => ({
                    ...prev,
                    [key]: prev[key].filter(v => v !== value)
                  }))}
                  className="hover:text-danger"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))
          )}
          <button
            onClick={() => setActiveFilters({})}
            className="text-xs text-muted-foreground hover:text-foreground underline"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Assignments Table */}
      <DataTable 
        columns={[
          { 
            label: "ID", 
            render: r => (
              <span className="font-mono font-semibold text-navy dark:text-gold text-xs">
                {r.id}
              </span>
            )
          },
          { label: "Client", key: "client" },
          { 
            label: "Interpreter", 
            render: r => (
              <span className={cn(
                r.interpreter === "Unassigned" && "text-danger font-semibold flex items-center gap-1"
              )}>
                {r.interpreter === "Unassigned" && <User className="w-3.5 h-3.5" />}
                {r.interpreter}
              </span>
            )
          },
          { 
            label: "Languages", 
            render: r => <span className="font-mono text-[11px]">{r.lang}</span> 
          },
          { label: "Type", key: "type" },
          { 
            label: "Date", 
            render: r => <span className="font-mono text-xs">{r.date} · {r.time}</span> 
          },
          { label: "Location", render: r => `${r.city}, ${r.state}` },
          { 
            label: "Rate", 
            render: r => <span className="font-mono">${r.rate}/hr</span> 
          },
          { label: "Status", render: r => <StatusBadge status={r.status} /> },
          { 
            label: "", 
            render: r => (
              <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                {r.status === "PENDING" && (
                  <>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-7 w-7 text-success hover:bg-success/10"
                      onClick={() => setConfirmDialog({ isOpen: true, mission: r, action: "confirm" })}
                      data-testid={`confirm-btn-${r.id}`}
                    >
                      <Check className="w-3.5 h-3.5" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-7 w-7 text-danger hover:bg-danger/10"
                      onClick={() => setConfirmDialog({ isOpen: true, mission: r, action: "cancel" })}
                      data-testid={`cancel-btn-${r.id}`}
                    >
                      <X className="w-3.5 h-3.5" />
                    </Button>
                  </>
                )}
              </div>
            )
          },
        ]} 
        data={filteredAssignments}
        onRowClick={handleRowClick}
      />

      {/* Empty State */}
      {filteredAssignments.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <MapPin className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No missions found with current filters</p>
          <Button 
            variant="link" 
            onClick={() => {
              setTab("all");
              setActiveFilters({});
            }}
          >
            Clear filters
          </Button>
        </div>
      )}

      {/* Modals */}
      <MissionFormModal
        isOpen={missionFormOpen}
        onClose={() => {
          setMissionFormOpen(false);
          setEditingMission(null);
        }}
        mission={editingMission}
        onSuccess={handleMissionCreated}
      />

      <MissionDetailModal
        isOpen={detailModalOpen}
        onClose={() => {
          setDetailModalOpen(false);
          setSelectedMission(null);
        }}
        mission={selectedMission}
        onEdit={handleEdit}
        onStatusChange={handleStatusChange}
      />

      {/* Confirm Dialogs */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen && confirmDialog.action === "confirm"}
        onConfirm={handleConfirmAction}
        onCancel={() => setConfirmDialog({ isOpen: false, mission: null, action: null })}
        title="Confirm Mission?"
        message={`Confirm mission ${confirmDialog.mission?.id}? This will notify the interpreter.`}
        confirmText="Confirm"
        variant="info"
        loading={confirmLoading}
      />

      <ConfirmDialog
        isOpen={confirmDialog.isOpen && confirmDialog.action === "cancel"}
        onConfirm={handleConfirmAction}
        onCancel={() => setConfirmDialog({ isOpen: false, mission: null, action: null })}
        title="Cancel Mission?"
        message={`Cancel mission ${confirmDialog.mission?.id}? This will notify the interpreter and client.`}
        confirmText="Cancel Mission"
        variant="danger"
        loading={confirmLoading}
      />
    </div>
  );
};

export default DispatchModule;
