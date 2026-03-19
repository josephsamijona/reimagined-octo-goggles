// JHBridge Command Center - Payroll Module
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MOCK } from "@/data/mockData";
import { 
  SectionHeader, 
  DataTable, 
  StatusBadge,
  KPICard 
} from "@/components/shared/UIComponents";
import { FileText, Plus, Send, Check } from "lucide-react";

export const PayrollModule = () => (
  <div className="flex flex-col gap-4" data-testid="payroll-module">
    <SectionHeader 
      title="Payroll & Payment Stubs" 
      subtitle="Interpreter payments, stubs, reimbursements & deductions" 
      action={
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" data-testid="batch-generate-btn">
            <FileText className="w-3.5 h-3.5" /> Batch Generate
          </Button>
          <Button size="sm" className="gap-1.5 bg-navy hover:bg-navy-light" data-testid="new-payment-btn">
            <Plus className="w-3.5 h-3.5" /> New Payment Stub
          </Button>
        </div>
      } 
    />

    {/* KPI Cards */}
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <KPICard label="Pending Payments" value="2" sub="$360 total" accent="warning" />
      <KPICard label="Processing" value="1" sub="$180" accent="info" />
      <KPICard label="Completed (MTD)" value="2" sub="$560 paid" accent="success" />
      <KPICard label="Total Payroll (MTD)" value="$1,100" sub="5 interpreters" accent="navy" />
    </div>

    {/* Payments Table */}
    <DataTable 
      columns={[
        { 
          label: "Ref #", 
          render: r => (
            <span className="font-mono font-semibold text-navy dark:text-gold text-xs">
              {r.id}
            </span>
          )
        },
        { label: "Interpreter", render: r => <span className="font-medium">{r.interpreter}</span> },
        { 
          label: "Amount", 
          render: r => <span className="font-mono font-semibold">${r.amount}</span> 
        },
        { 
          label: "Method", 
          render: r => <span className="font-mono text-[11px]">{r.method}</span> 
        },
        { 
          label: "Date", 
          render: r => <span className="font-mono text-xs">{r.date}</span> 
        },
        { label: "Status", render: r => <StatusBadge status={r.status} /> },
        { 
          label: "", 
          render: r => (
            <div className="flex gap-1">
              <Button 
                variant="outline" 
                size="sm" 
                className="h-7 px-2 gap-1 text-[10px]" 
                data-testid={`stub-pdf-btn-${r.id}`}
              >
                <FileText className="w-3 h-3" /> Stub PDF
              </Button>
              <Button 
                variant="ghost" 
                size="sm" 
                className="h-7 px-2 gap-1 text-[10px]" 
                data-testid={`send-btn-${r.id}`}
              >
                <Send className="w-3 h-3" /> Send
              </Button>
              {r.status === "PENDING" && (
                <Button 
                  size="sm" 
                  className="h-7 px-2 gap-1 text-[10px] bg-success hover:bg-success/90" 
                  data-testid={`process-btn-${r.id}`}
                >
                  <Check className="w-3 h-3" /> Process
                </Button>
              )}
            </div>
          )
        },
      ]} 
      data={MOCK.payments} 
    />
  </div>
);

export default PayrollModule;
