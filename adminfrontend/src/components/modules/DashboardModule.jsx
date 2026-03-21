// JHBridge Command Center - Dashboard Module
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MOCK } from "@/data/mockData";
import { 
  KPICard, 
  SectionHeader, 
  StatusBadge, 
  MiniChart, 
  AlertItem,
  ProgressBar 
} from "@/components/shared/UIComponents";

export const DashboardModule = () => {
  const k = MOCK.kpis;
  const revenueData = [32000, 35000, 38000, 41000, 39000, 43000, 48750];
  const expenseData = [21000, 23000, 25000, 27000, 26000, 29000, 31200];
  
  return (
    <div className="flex flex-col gap-5" data-testid="dashboard-module">
      <SectionHeader 
        title="Command Center" 
        subtitle="Real-time operational overview — March 14, 2026" 
      />
      
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <KPICard label="Active Missions" value={k.activeAssignments} sub="↑ 3 vs yesterday" trend="up" accent="navy" />
        <KPICard label="Available Interpreters" value={k.availableInterpreters} sub={`of ${k.availableInterpreters + 15} total`} accent="success" />
        <KPICard label="Pending Requests" value={k.pendingRequests} sub="8 emails unresolved" trend="down" accent="warning" />
        <KPICard label="MTD Revenue" value={`$${(k.monthRevenue / 1000).toFixed(1)}k`} sub="↑ 12% vs last month" trend="up" accent="gold" />
        <KPICard label="Net Margin" value={`${k.margin}%`} sub={`$${((k.monthRevenue - k.monthExpenses) / 1000).toFixed(1)}k profit`} trend="up" accent="success" />
      </div>

      {/* Charts & Alerts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Revenue Chart */}
        <Card className="lg:col-span-2 shadow-sm">
          <CardContent className="p-4">
            <div className="flex justify-between items-center mb-3">
              <span className="text-sm font-semibold">Revenue vs Expenses</span>
              <span className="text-[10px] text-muted-foreground font-mono">Last 7 months</span>
            </div>
            <div className="relative h-20">
              <MiniChart data={revenueData} color="stroke-navy dark:stroke-gold" height={80} />
              <div className="absolute top-0 left-0 right-0">
                <MiniChart data={expenseData} color="stroke-gold dark:stroke-navy-light" height={80} />
              </div>
            </div>
            <div className="flex gap-4 mt-2">
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <span className="w-3 h-0.5 bg-navy dark:bg-gold inline-block" /> Revenue
              </span>
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <span className="w-3 h-0.5 bg-gold dark:bg-navy-light inline-block" /> Expenses
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Alerts Panel */}
        <Card className="shadow-sm">
          <CardContent className="p-4 flex flex-col gap-2">
            <span className="text-sm font-semibold mb-1">Alerts</span>
            <AlertItem text="ASG-1045: No interpreter assigned" level="danger" />
            <AlertItem text="2 onboardings stalled > 3 days" level="warning" />
            <AlertItem text="3 payment stubs pending" level="warning" />
            <AlertItem text="INV-0034 payment confirmed" level="success" />
          </CardContent>
        </Card>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Today's Missions */}
        <Card className="shadow-sm">
          <CardContent className="p-4">
            <span className="text-sm font-semibold block mb-3">Today's Missions</span>
            <div className="space-y-0">
              {MOCK.assignments
                .filter(a => a.date === "Mar 15" || a.date === "Mar 14")
                .slice(0, 4)
                .map((a, i) => (
                  <div 
                    key={i} 
                    className="flex justify-between items-center py-2 border-b border-border last:border-0"
                    data-testid={`mission-item-${a.id}`}
                  >
                    <div>
                      <span className="text-xs font-mono font-semibold text-navy dark:text-gold">{a.id}</span>
                      <span className="text-xs text-foreground ml-2">{a.client}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground font-mono">{a.time}</span>
                      <StatusBadge status={a.status} />
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card className="shadow-sm">
          <CardContent className="p-4">
            <span className="text-sm font-semibold block mb-3">Quick Stats</span>
            <div className="space-y-3">
              {[
                { label: "Acceptance Rate", value: `${k.acceptanceRate}%`, bar: k.acceptanceRate, color: "bg-success" },
                { label: "No-Show Rate", value: `${k.noShowRate}%`, bar: k.noShowRate * 10, color: "bg-danger" },
                { label: "Onboardings Active", value: k.onboardingsActive, bar: (k.onboardingsActive / 10) * 100, color: "bg-gold" },
                { label: "Emails Unresolved", value: k.unresolvedEmails, bar: (k.unresolvedEmails / 20) * 100, color: "bg-warning" },
              ].map((s, i) => (
                <div key={i} data-testid={`stat-${s.label.toLowerCase().replace(/\s+/g, '-')}`}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">{s.label}</span>
                    <span className="font-semibold font-mono">{s.value}</span>
                  </div>
                  <ProgressBar value={s.bar} color={s.color} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DashboardModule;
