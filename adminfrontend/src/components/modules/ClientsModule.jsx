// JHBridge Command Center - Clients Module
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MOCK } from "@/data/mockData";
import { 
  SectionHeader, 
  TabBar, 
  DataTable, 
  StatusBadge 
} from "@/components/shared/UIComponents";
import { Plus, ChevronRight, Mail } from "lucide-react";

export const ClientsModule = () => {
  const [tab, setTab] = useState("clients");
  
  return (
    <div className="flex flex-col gap-4" data-testid="clients-module">
      <SectionHeader 
        title="Clients & Sales" 
        subtitle="Client relationship management & quote pipeline" 
        action={
          <Button size="sm" className="gap-1.5 bg-navy hover:bg-navy-light" data-testid="new-client-btn">
            <Plus className="w-3.5 h-3.5" /> New Client
          </Button>
        } 
      />

      <TabBar 
        tabs={[
          { key: "clients", label: "Clients", count: MOCK.clients.length },
          { key: "quotes", label: "Quote Pipeline", count: MOCK.quotes.length },
          { key: "public", label: "Public Requests", count: 2 },
        ]} 
        active={tab} 
        onChange={setTab} 
      />

      {tab === "clients" && (
        <DataTable 
          columns={[
            { label: "Company", render: r => <span className="font-semibold">{r.company}</span> },
            { label: "Contact", key: "contact" },
            { 
              label: "Email", 
              render: r => (
                <span className="font-mono text-[11px] text-muted-foreground">{r.email}</span>
              )
            },
            { label: "Missions", render: r => <span className="font-mono">{r.missions}</span> },
            { 
              label: "Revenue", 
              render: r => (
                <span className="font-mono font-semibold text-success">
                  ${r.revenue.toLocaleString()}
                </span>
              )
            },
            { 
              label: "Last Mission", 
              render: r => <span className="font-mono text-xs">{r.lastMission}</span> 
            },
            { label: "Status", render: r => <StatusBadge status={r.status} /> },
            { 
              label: "", 
              render: () => (
                <Button variant="ghost" size="icon" className="h-7 w-7" data-testid="view-client-btn">
                  <ChevronRight className="w-4 h-4" />
                </Button>
              )
            },
          ]} 
          data={MOCK.clients} 
        />
      )}

      {tab === "quotes" && (
        <>
          {/* Quote Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-2">
            {[
              { label: "Pending", count: MOCK.quotes.filter(q => q.status === "PENDING").length, color: "border-l-warning" },
              { label: "Quoted", count: MOCK.quotes.filter(q => q.status === "QUOTED").length, color: "border-l-info" },
              { label: "Accepted", count: MOCK.quotes.filter(q => q.status === "ACCEPTED").length, color: "border-l-success" },
              { label: "Rejected", count: 0, color: "border-l-danger" },
            ].map((s, i) => (
              <Card key={i} className={`shadow-sm border-l-[3px] ${s.color}`}>
                <CardContent className="p-3">
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">
                    {s.label}
                  </div>
                  <div className="text-xl font-display font-bold">{s.count}</div>
                </CardContent>
              </Card>
            ))}
          </div>
          
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
              { label: "Service", key: "service" },
              { 
                label: "Languages", 
                render: r => <span className="font-mono text-[11px]">{r.langs}</span> 
              },
              { 
                label: "Date", 
                render: r => <span className="font-mono text-xs">{r.date}</span> 
              },
              { 
                label: "Amount", 
                render: r => r.amount 
                  ? <span className="font-mono font-semibold">${r.amount}</span> 
                  : <span className="text-muted-foreground">—</span>
              },
              { label: "Status", render: r => <StatusBadge status={r.status} /> },
              { 
                label: "", 
                render: r => (
                  <div className="flex gap-1">
                    {r.status === "PENDING" && (
                      <Button 
                        size="sm" 
                        className="h-7 text-[10px] bg-gold text-navy hover:bg-gold/90" 
                        data-testid={`generate-quote-btn-${r.id}`}
                      >
                        Generate Quote
                      </Button>
                    )}
                    {r.status === "ACCEPTED" && (
                      <Button 
                        size="sm" 
                        className="h-7 text-[10px] bg-navy hover:bg-navy-light" 
                        data-testid={`create-assignment-btn-${r.id}`}
                      >
                        Create Assignment
                      </Button>
                    )}
                  </div>
                )
              },
            ]} 
            data={MOCK.quotes} 
          />
        </>
      )}

      {tab === "public" && (
        <Card className="shadow-sm">
          <CardContent className="py-12 text-center text-muted-foreground">
            <Mail className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">
              Public quote requests from website form will appear here
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ClientsModule;
