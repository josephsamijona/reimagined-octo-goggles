// JHBridge Command Center - Finance Module
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { MOCK } from "@/data/mockData";
import { 
  SectionHeader, 
  TabBar, 
  KPICard,
  ProgressBar 
} from "@/components/shared/UIComponents";

export const FinanceModule = () => {
  const [tab, setTab] = useState("overview");
  
  return (
    <div className="flex flex-col gap-4" data-testid="finance-module">
      <SectionHeader 
        title="Finance & Accounting" 
        subtitle="Revenue, expenses, taxes & financial reports" 
      />

      <TabBar 
        tabs={[
          { key: "overview", label: "Overview" },
          { key: "invoices", label: "Client Invoices" },
          { key: "expenses", label: "Expenses" },
          { key: "reports", label: "Reports" },
        ]} 
        active={tab} 
        onChange={setTab} 
      />

      {tab === "overview" && (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KPICard label="MTD Revenue" value="$48,750" sub="↑ 12% MoM" trend="up" accent="success" />
            <KPICard label="MTD Expenses" value="$31,200" sub="↑ 5% MoM" trend="up" accent="danger" />
            <KPICard label="Net Profit" value="$17,550" sub="36% margin" trend="up" accent="gold" />
            <KPICard label="Outstanding" value="$8,400" sub="4 unpaid invoices" accent="warning" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {/* Revenue by Service Type */}
            <Card className="shadow-sm">
              <CardContent className="p-4">
                <span className="text-sm font-semibold block mb-3">Revenue by Service Type</span>
                <div className="space-y-3">
                  {[
                    { label: "Medical Interpretation", amount: 22400, pct: 46 },
                    { label: "Legal Interpretation", amount: 14200, pct: 29 },
                    { label: "Conference", amount: 7800, pct: 16 },
                    { label: "Other", amount: 4350, pct: 9 },
                  ].map((s, i) => (
                    <div key={i}>
                      <div className="flex justify-between text-xs mb-1">
                        <span>{s.label}</span>
                        <span className="font-mono font-semibold">
                          ${s.amount.toLocaleString()} ({s.pct}%)
                        </span>
                      </div>
                      <ProgressBar value={s.pct} color="bg-navy dark:bg-gold" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Top Clients */}
            <Card className="shadow-sm">
              <CardContent className="p-4">
                <span className="text-sm font-semibold block mb-3">Top Clients by Revenue</span>
                <div className="space-y-0">
                  {MOCK.clients
                    .sort((a, b) => b.revenue - a.revenue)
                    .slice(0, 5)
                    .map((c, i) => (
                      <div 
                        key={i} 
                        className="flex justify-between items-center py-2 border-b border-border last:border-0"
                      >
                        <div>
                          <span className="text-xs font-medium">{c.company}</span>
                          <span className="text-[10px] text-muted-foreground font-mono ml-2">
                            {c.missions} missions
                          </span>
                        </div>
                        <span className="text-sm font-bold font-mono text-success">
                          ${c.revenue.toLocaleString()}
                        </span>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {tab !== "overview" && (
        <Card className="shadow-sm">
          <CardContent className="py-12 text-center">
            <span className="text-sm text-muted-foreground">
              {tab === "invoices" && "Invoice management — generate, send, track payments"}
              {tab === "expenses" && "Expense tracking — operational, admin, marketing, salary, tax"}
              {tab === "reports" && "Financial reports — P&L, balance sheets, tax reports, CSV/PDF export"}
            </span>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default FinanceModule;
