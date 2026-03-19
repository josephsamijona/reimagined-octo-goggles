// JHBridge Command Center - Interpreters Module (Updated with all functionalities)
import { useState, useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MOCK } from "@/data/mockData";
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
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

export const InterpretersModule = () => {
  const [view, setView] = useState("grid");
  const [interpreters, setInterpreters] = useState(MOCK.interpreters);
  const [activeFilters, setActiveFilters] = useState({});
  const [selectedInterpreter, setSelectedInterpreter] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [missionFormOpen, setMissionFormOpen] = useState(false);
  const [assigningInterpreter, setAssigningInterpreter] = useState(null);

  // Get unique languages for filter
  const allLanguages = [...new Set(MOCK.interpreters.flatMap(i => i.langs))];

  // Filter configuration
  const filterConfig = [
    {
      key: "status",
      label: "Status",
      options: [
        { value: "available", label: "Available", count: interpreters.filter(i => i.status === "available").length },
        { value: "on_mission", label: "On Mission", count: interpreters.filter(i => i.status === "on_mission").length },
        { value: "blocked", label: "Blocked", count: interpreters.filter(i => i.status === "blocked").length },
      ],
    },
    {
      key: "langs",
      label: "Languages",
      options: allLanguages.map(lang => ({
        value: lang,
        label: lang,
        count: interpreters.filter(i => i.langs.includes(lang)).length,
      })),
    },
    {
      key: "state",
      label: "State",
      options: [
        { value: "MA", label: "Massachusetts" },
        { value: "NY", label: "New York" },
      ],
    },
  ];

  // Apply filters
  const filteredInterpreters = useMemo(() => {
    let result = interpreters;
    
    Object.entries(activeFilters).forEach(([key, values]) => {
      if (values && values.length > 0) {
        if (key === "langs") {
          result = result.filter(i => i.langs.some(l => values.includes(l)));
        } else {
          result = result.filter(i => values.includes(i[key]));
        }
      }
    });
    
    return result;
  }, [interpreters, activeFilters]);

  const getStatusLabel = (status) => {
    const labels = {
      available: "Available",
      on_mission: "On Mission",
      blocked: "Blocked",
    };
    return labels[status] || status;
  };

  const getStatusColor = (status) => {
    const colors = {
      available: "text-success",
      on_mission: "text-gold",
      blocked: "text-danger",
    };
    return colors[status] || "text-muted-foreground";
  };

  // Handle card/row click
  const handleInterpreterClick = (interpreter) => {
    setSelectedInterpreter(interpreter);
    setDetailModalOpen(true);
  };

  // Handle assign mission
  const handleAssignMission = (interpreter) => {
    setAssigningInterpreter(interpreter);
    setDetailModalOpen(false);
    setMissionFormOpen(true);
  };

  // Handle status change
  const handleStatusChange = (interpreterId, newStatus) => {
    setInterpreters(prev =>
      prev.map(i => i.id === interpreterId ? { ...i, status: newStatus } : i)
    );
    setDetailModalOpen(false);
  };
  
  return (
    <div className="flex flex-col gap-4" data-testid="interpreters-module">
      <SectionHeader 
        title="Interpreters" 
        subtitle={`${filteredInterpreters.length} interpreters${activeFilters && Object.values(activeFilters).flat().length > 0 ? ' (filtered)' : ' across the US'}`}
        action={
          <div className="flex gap-2">
            {/* View Toggle */}
            <div className="flex border border-border rounded-sm overflow-hidden">
              <button
                onClick={() => setView("grid")}
                data-testid="view-grid-btn"
                className={cn(
                  "px-2.5 py-1 text-[10px] font-medium transition-colors",
                  view === "grid" 
                    ? "bg-navy text-white dark:bg-gold dark:text-navy" 
                    : "bg-transparent text-muted-foreground hover:bg-muted"
                )}
              >
                Grid
              </button>
              <button
                onClick={() => setView("table")}
                data-testid="view-table-btn"
                className={cn(
                  "px-2.5 py-1 text-[10px] font-medium transition-colors",
                  view === "table" 
                    ? "bg-navy text-white dark:bg-gold dark:text-navy" 
                    : "bg-transparent text-muted-foreground hover:bg-muted"
                )}
              >
                Table
              </button>
            </div>
            <FilterDropdown
              filters={filterConfig}
              activeFilters={activeFilters}
              onChange={setActiveFilters}
            />
          </div>
        } 
      />

      {view === "grid" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {filteredInterpreters.map((interp, i) => (
            <Card 
              key={i}
              className="shadow-sm cursor-pointer transition-all hover:border-gold hover:shadow-md"
              onClick={() => handleInterpreterClick(interp)}
              data-testid={`interpreter-card-${interp.id}`}
            >
              <CardContent className="p-4">
                {/* Header */}
                <div className="flex items-center gap-2.5 mb-3">
                  <Avatar name={interp.name} size="md" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold truncate">{interp.name}</div>
                    <div className="text-[11px] text-muted-foreground font-mono">
                      {interp.city}, {interp.state}
                    </div>
                  </div>
                  <StatusDot status={interp.status} size="md" />
                </div>
                
                {/* Language Tags */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {interp.langs.map((l, j) => (
                    <LanguageTag key={j} lang={l} />
                  ))}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-1 text-[11px] font-mono">
                  <span className="text-muted-foreground">
                    Rate: <span className="text-foreground font-medium">${interp.rate}/hr</span>
                  </span>
                  <span className="text-muted-foreground">
                    Radius: <span className="text-foreground font-medium">{interp.radius}mi</span>
                  </span>
                  <span className="text-muted-foreground">
                    Missions: <span className="text-foreground font-medium">{interp.missions}</span>
                  </span>
                  <span className="text-muted-foreground flex items-center gap-0.5">
                    Rating: 
                    <Star className="w-3 h-3 text-gold fill-gold" />
                    <span className="text-gold font-medium">{interp.rating}</span>
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <DataTable 
          columns={[
            { label: "Name", render: r => <span className="font-semibold">{r.name}</span> },
            { label: "Languages", render: r => r.langs.join(", ") },
            { label: "Location", render: r => `${r.city}, ${r.state}` },
            { label: "Radius", render: r => <span className="font-mono">{r.radius}mi</span> },
            { label: "Rate", render: r => <span className="font-mono">${r.rate}/hr</span> },
            { label: "Missions", render: r => <span className="font-mono">{r.missions}</span> },
            { 
              label: "Rating", 
              render: r => (
                <span className="font-mono text-gold flex items-center gap-0.5">
                  <Star className="w-3 h-3 fill-gold" /> {r.rating}
                </span>
              )
            },
            { 
              label: "Status", 
              render: r => (
                <span className={cn("text-[11px] font-semibold", getStatusColor(r.status))}>
                  {getStatusLabel(r.status)}
                </span>
              )
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
          <Button 
            variant="link" 
            onClick={() => setActiveFilters({})}
          >
            Clear filters
          </Button>
        </div>
      )}

      {/* Modals */}
      <InterpreterDetailModal
        isOpen={detailModalOpen}
        onClose={() => {
          setDetailModalOpen(false);
          setSelectedInterpreter(null);
        }}
        interpreter={selectedInterpreter}
        onAssignMission={handleAssignMission}
        onStatusChange={handleStatusChange}
      />

      <MissionFormModal
        isOpen={missionFormOpen}
        onClose={() => {
          setMissionFormOpen(false);
          setAssigningInterpreter(null);
        }}
        prefillData={assigningInterpreter ? {
          interpreterId: assigningInterpreter.id.toString(),
          sourceLang: assigningInterpreter.langs[0] || "Portuguese",
          rate: assigningInterpreter.rate,
        } : null}
        onSuccess={() => {
          setMissionFormOpen(false);
          setAssigningInterpreter(null);
        }}
      />
    </div>
  );
};

export default InterpretersModule;
