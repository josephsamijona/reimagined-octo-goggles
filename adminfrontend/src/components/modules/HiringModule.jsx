// JHBridge Command Center - Hiring Module
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MOCK, ONBOARDING_PHASES } from "@/data/mockData";
import { SectionHeader, DataTable } from "@/components/shared/UIComponents";
import { Plus, Send, X } from "lucide-react";
import { cn } from "@/lib/utils";

export const HiringModule = () => {
  const phases = ["INVITED", "WELCOME_VIEWED", "ACCOUNT_CREATED", "PROFILE_COMPLETED", "CONTRACT_STARTED", "COMPLETED"];
  
  const getPhaseColor = (phase) => {
    const p = ONBOARDING_PHASES[phase];
    const colors = {
      "muted-foreground": "border-t-muted-foreground",
      "warning": "border-t-warning",
      "info": "border-t-info",
      "gold": "border-t-gold",
      "navy": "border-t-navy",
      "success": "border-t-success",
    };
    return colors[p?.color] || colors["muted-foreground"];
  };

  const getTextColor = (color) => {
    const colors = {
      "muted-foreground": "text-muted-foreground",
      "warning": "text-warning",
      "info": "text-info",
      "gold": "text-gold",
      "navy": "text-navy dark:text-gold",
      "success": "text-success",
    };
    return colors[color] || colors["muted-foreground"];
  };

  const getBgColor = (color) => {
    const colors = {
      "muted-foreground": "bg-muted-foreground",
      "warning": "bg-warning",
      "info": "bg-info",
      "gold": "bg-gold",
      "navy": "bg-navy",
      "success": "bg-success",
    };
    return colors[color] || colors["muted-foreground"];
  };
  
  return (
    <div className="flex flex-col gap-4" data-testid="hiring-module">
      <SectionHeader 
        title="Hiring & Onboarding" 
        subtitle="Interpreter recruitment pipeline" 
        action={
          <Button size="sm" className="gap-1.5 bg-navy hover:bg-navy-light" data-testid="new-invitation-btn">
            <Plus className="w-3.5 h-3.5" /> New Invitation
          </Button>
        } 
      />

      {/* Pipeline Kanban */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 overflow-x-auto">
        {phases.map(phase => {
          const p = ONBOARDING_PHASES[phase];
          const items = MOCK.onboardings.filter(o => o.phase === phase);
          return (
            <Card 
              key={phase} 
              className={cn("shadow-sm border-t-2", getPhaseColor(phase))}
              data-testid={`kanban-column-${phase}`}
            >
              {/* Column Header */}
              <div className="px-3 py-2 border-b border-border flex justify-between items-center">
                <span className="text-[10px] font-semibold uppercase tracking-wider truncate">
                  {p.label}
                </span>
                <span className={cn(
                  "text-[10px] font-semibold font-mono px-1.5 py-0.5 rounded",
                  `${getBgColor(p.color)}/10`,
                  getTextColor(p.color)
                )}>
                  {items.length}
                </span>
              </div>
              
              {/* Column Items */}
              <CardContent className="p-2 flex flex-col gap-1.5 min-h-[100px]">
                {items.map((o, i) => (
                  <div 
                    key={i}
                    className={cn(
                      "p-2 bg-muted/50 rounded-sm border border-border cursor-pointer transition-colors",
                      "hover:border-gold"
                    )}
                    data-testid={`kanban-card-${o.id}`}
                  >
                    <div className="text-xs font-semibold truncate">{o.name}</div>
                    <div className="text-[10px] text-muted-foreground font-mono truncate">{o.id}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5 truncate">{o.lang}</div>
                  </div>
                ))}
                {items.length === 0 && (
                  <div className="p-3 text-center text-[10px] text-muted-foreground">
                    Empty
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Onboarding Table */}
      <DataTable 
        columns={[
          { 
            label: "Invitation #", 
            render: r => (
              <span className="font-mono font-semibold text-navy dark:text-gold text-xs">
                {r.id}
              </span>
            )
          },
          { label: "Name", render: r => <span className="font-medium">{r.name}</span> },
          { 
            label: "Email", 
            render: r => (
              <span className="font-mono text-[11px] text-muted-foreground">{r.email}</span>
            )
          },
          { label: "Languages", key: "lang" },
          { 
            label: "Phase", 
            render: r => {
              const p = ONBOARDING_PHASES[r.phase];
              return (
                <span className={cn("text-[11px] font-semibold", getTextColor(p?.color))}>
                  {p?.label}
                </span>
              );
            }
          },
          { 
            label: "Progress", 
            render: r => {
              const p = ONBOARDING_PHASES[r.phase];
              return (
                <div className="flex gap-0.5">
                  {[1, 2, 3, 4, 5, 6, 7].map(s => (
                    <div 
                      key={s} 
                      className={cn(
                        "w-4 h-1 rounded-sm",
                        s <= p?.step ? getBgColor(p?.color) : "bg-muted"
                      )}
                    />
                  ))}
                </div>
              );
            }
          },
          { label: "Created", key: "created" },
          { 
            label: "", 
            render: r => (
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" className="h-7 px-2 gap-1 text-[10px]" data-testid={`resend-btn-${r.id}`}>
                  <Send className="w-3 h-3" /> Resend
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-danger" data-testid={`delete-btn-${r.id}`}>
                  <X className="w-3.5 h-3.5" />
                </Button>
              </div>
            )
          },
        ]} 
        data={MOCK.onboardings} 
      />
    </div>
  );
};

export default HiringModule;
