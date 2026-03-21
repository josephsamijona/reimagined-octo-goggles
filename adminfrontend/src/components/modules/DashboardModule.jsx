// JHBridge Command Center - Dashboard Module (Live API Data)
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, RefreshCw, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDashboard } from "@/hooks/useDashboard";
import {
  KPICard,
  SectionHeader,
  StatusBadge,
  MiniChart,
  AlertItem,
  ProgressBar,
} from "@/components/shared/UIComponents";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Format an ISO datetime string to "9:00 AM" */
function fmtTime(isoString) {
  if (!isoString) return "—";
  return new Date(isoString).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Format a dollar string from backend (e.g. "48750.00" → "$48.8k") */
function fmtCurrency(str) {
  const n = parseFloat(str) || 0;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}k`;
  return `$${n.toFixed(0)}`;
}

/**
 * Flatten the alerts response object into a list of { text, level } items
 * for the <AlertItem> component.
 */
function buildAlertItems(alerts) {
  const items = [];

  (alerts.unassigned_assignments || []).forEach((a) =>
    items.push({ text: `ASG-${a.id}: No interpreter assigned`, level: "danger" })
  );

  (alerts.stalled_onboardings || []).forEach((o) =>
    items.push({
      text: `${o.first_name} ${o.last_name}: onboarding stalled (${o.current_phase})`,
      level: "warning",
    })
  );

  (alerts.overdue_invoices || []).forEach((i) =>
    items.push({
      text: `${i.invoice_number} overdue — ${i["client__company_name"]}`,
      level: "danger",
    })
  );

  (alerts.pending_payment_stubs || []).forEach((p) =>
    items.push({
      text: `Payment stub pending: ${p["interpreter__user__first_name"]} ${p["interpreter__user__last_name"]}`,
      level: "warning",
    })
  );

  (alerts.recently_paid_invoices || []).forEach((i) =>
    items.push({ text: `${i.invoice_number} payment confirmed`, level: "success" })
  );

  return items.slice(0, 6); // cap display to 6 most relevant alerts
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-5" data-testid="dashboard-loading">
      <div className="h-8 w-48 bg-muted rounded animate-pulse" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-24 bg-muted rounded animate-pulse" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2 h-44 bg-muted rounded animate-pulse" />
        <div className="h-44 bg-muted rounded animate-pulse" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="h-52 bg-muted rounded animate-pulse" />
        <div className="h-52 bg-muted rounded animate-pulse" />
      </div>
    </div>
  );
}

// ─── Error state ──────────────────────────────────────────────────────────────

function DashboardError({ onRetry }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-4 py-20 text-muted-foreground"
      data-testid="dashboard-error"
    >
      <AlertTriangle className="w-10 h-10 text-danger" />
      <p className="text-sm font-medium">Failed to load dashboard data</p>
      <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5">
        <RefreshCw className="w-3.5 h-3.5" /> Retry
      </Button>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export const DashboardModule = () => {
  const { data, isLoading, error, refetch } = useDashboard();

  if (isLoading) return <DashboardSkeleton />;
  if (error || !data) return <DashboardError onRetry={refetch} />;

  const { kpis, alerts, chart, missions } = data;

  // ── KPI derived values ─────────────────────────────────────────────────────
  const mtdRevenue = parseFloat(kpis.mtd_revenue) || 0;
  const mtdExpenses = parseFloat(kpis.mtd_expenses) || 0;
  const netMargin =
    mtdRevenue > 0 ? ((mtdRevenue - mtdExpenses) / mtdRevenue) * 100 : 0;

  // ── Revenue chart arrays ───────────────────────────────────────────────────
  const revenueData = chart.length
    ? chart.map((d) => parseFloat(d.revenue))
    : [0];
  const expenseData = chart.length
    ? chart.map((d) => parseFloat(d.expenses))
    : [0];

  // ── Alert items ────────────────────────────────────────────────────────────
  const alertItems = buildAlertItems(alerts);
  const hasAlerts = alertItems.length > 0;

  // ── Today's missions ───────────────────────────────────────────────────────
  const todayMissions = missions.slice(0, 4);

  // ── Quick stats ────────────────────────────────────────────────────────────
  const quickStats = [
    {
      label: "Acceptance Rate",
      value: `${kpis.acceptance_rate}%`,
      bar: kpis.acceptance_rate,
      color: "bg-success",
    },
    {
      label: "No-Show Rate",
      value: `${kpis.no_show_rate}%`,
      bar: Math.min(kpis.no_show_rate * 10, 100),
      color: "bg-danger",
    },
    {
      label: "Onboardings Active",
      value: kpis.active_onboardings,
      bar: Math.min((kpis.active_onboardings / 10) * 100, 100),
      color: "bg-gold",
    },
    {
      label: "Emails Unresolved",
      value: kpis.unresolved_emails,
      bar: Math.min((kpis.unresolved_emails / 20) * 100, 100),
      color: "bg-warning",
    },
  ];

  // ── Today's date subtitle ──────────────────────────────────────────────────
  const todayLabel = new Date().toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="flex flex-col gap-5" data-testid="dashboard-module">
      <SectionHeader
        title="Command Center"
        subtitle={`Real-time operational overview — ${todayLabel}`}
        action={
          <Button
            variant="ghost"
            size="sm"
            onClick={refetch}
            className="gap-1.5 text-muted-foreground h-8"
            data-testid="dashboard-refresh-btn"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </Button>
        }
      />

      {/* ── KPI Cards ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <KPICard
          label="Active Missions"
          value={kpis.active_assignments}
          sub="PENDING + CONFIRMED + IN PROGRESS"
          accent="navy"
        />
        <KPICard
          label="Available Interpreters"
          value={kpis.available_interpreters}
          sub="Active &amp; unblocked"
          accent="success"
        />
        <KPICard
          label="Pending Requests"
          value={kpis.pending_requests}
          sub={`${kpis.unresolved_emails} emails unresolved`}
          trend="down"
          accent="warning"
        />
        <KPICard
          label="MTD Revenue"
          value={fmtCurrency(kpis.mtd_revenue)}
          sub={`Expenses: ${fmtCurrency(kpis.mtd_expenses)}`}
          trend="up"
          accent="gold"
        />
        <KPICard
          label="Net Margin"
          value={`${netMargin.toFixed(1)}%`}
          sub={`${fmtCurrency(kpis.net_margin)} profit MTD`}
          trend={netMargin >= 0 ? "up" : "down"}
          accent="success"
        />
      </div>

      {/* ── Charts & Alerts Row ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Revenue Chart */}
        <Card className="lg:col-span-2 shadow-sm">
          <CardContent className="p-4">
            <div className="flex justify-between items-center mb-3">
              <span className="text-sm font-semibold">Revenue vs Expenses</span>
              <span className="text-[10px] text-muted-foreground font-mono">
                Last {chart.length} months
              </span>
            </div>
            <div className="relative h-20">
              <MiniChart
                data={revenueData}
                color="stroke-navy dark:stroke-gold"
                height={80}
              />
              <div className="absolute top-0 left-0 right-0">
                <MiniChart
                  data={expenseData}
                  color="stroke-gold dark:stroke-navy-light"
                  height={80}
                />
              </div>
            </div>
            <div className="flex gap-4 mt-2">
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <span className="w-3 h-0.5 bg-navy dark:bg-gold inline-block" />{" "}
                Revenue
              </span>
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <span className="w-3 h-0.5 bg-gold dark:bg-navy-light inline-block" />{" "}
                Expenses
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Alerts Panel */}
        <Card className="shadow-sm">
          <CardContent className="p-4 flex flex-col gap-2">
            <span className="text-sm font-semibold mb-1">
              Alerts
              {hasAlerts && (
                <span className="ml-2 text-[10px] font-mono text-muted-foreground">
                  ({alertItems.length})
                </span>
              )}
            </span>
            {hasAlerts ? (
              alertItems.map((a, i) => (
                <AlertItem key={i} text={a.text} level={a.level} />
              ))
            ) : (
              <span
                className="text-xs text-muted-foreground"
                data-testid="alerts-empty"
              >
                No active alerts — all systems nominal.
              </span>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Bottom Row ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Today's Missions */}
        <Card className="shadow-sm">
          <CardContent className="p-4">
            <span className="text-sm font-semibold block mb-3">
              Today's Missions
              <span className="ml-2 text-[10px] font-mono text-muted-foreground">
                ({missions.length} total)
              </span>
            </span>
            <div className="space-y-0">
              {todayMissions.length > 0 ? (
                todayMissions.map((m) => (
                  <div
                    key={m.id}
                    className="flex justify-between items-center py-2 border-b border-border last:border-0"
                    data-testid={`mission-item-${m.id}`}
                  >
                    <div>
                      <span className="text-xs font-mono font-semibold text-navy dark:text-gold">
                        ASG-{m.id}
                      </span>
                      <span className="text-xs text-foreground ml-2">
                        {m.client}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {fmtTime(m.start_time)}
                      </span>
                      <StatusBadge status={m.status} />
                    </div>
                  </div>
                ))
              ) : (
                <span
                  className="text-xs text-muted-foreground"
                  data-testid="missions-empty"
                >
                  No missions scheduled for today.
                </span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card className="shadow-sm">
          <CardContent className="p-4">
            <span className="text-sm font-semibold block mb-3">Quick Stats</span>
            <div className="space-y-3">
              {quickStats.map((s, i) => (
                <div
                  key={i}
                  data-testid={`stat-${s.label
                    .toLowerCase()
                    .replace(/\s+/g, "-")}`}
                >
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
