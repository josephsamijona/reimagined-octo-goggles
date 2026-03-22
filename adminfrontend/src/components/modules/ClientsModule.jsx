// JHBridge Command Center — Clients & Sales Module (live API)
import { useState, useEffect, useCallback, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Modal } from "@/components/shared/Modal";
import { showToast } from "@/components/shared/Toast";
import {
  SectionHeader,
  TabBar,
  StatusBadge,
} from "@/components/shared/UIComponents";
import {
  Plus, Search, ChevronRight, X, RefreshCw,
  Building2, Users, DollarSign, TrendingUp,
  FileText, CheckCircle, Clock, Globe,
  Mail, Calendar, MapPin, Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { clientsService } from "@/services/clientsService";
import { ClientFormModal } from "@/components/modals/ClientFormModal";

// ─── small helpers ────────────────────────────────────────────────────────────
const fmt$ = (v) =>
  v != null ? `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 0 })}` : "—";
const fmtDate = (d) => (d ? new Date(d).toLocaleDateString() : "—");
// list serializer: user_name / user_email; detail serializer: nested user object
const contactName = (c) =>
  c?.user_name || (c?.user ? `${c.user.first_name || ""} ${c.user.last_name || ""}`.trim() : "");

function KpiCard({ icon: Icon, label, value, sub, colorClass = "border-l-navy" }) {
  return (
    <Card className={`shadow-sm border-l-[3px] ${colorClass}`}>
      <CardContent className="p-3 flex items-start gap-2.5">
        <div className="p-1.5 rounded-md bg-muted mt-0.5">
          <Icon className="w-3.5 h-3.5 text-muted-foreground" />
        </div>
        <div className="min-w-0">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider truncate">{label}</div>
          <div className="text-xl font-display font-bold leading-tight">{value}</div>
          {sub && <div className="text-[11px] text-muted-foreground truncate">{sub}</div>}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Client Detail Drawer ────────────────────────────────────────────────────
function ClientDrawer({ clientId, onClose, onEdit }) {
  const [client, setClient] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [history, setHistory] = useState([]);
  const [tab, setTab] = useState("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!clientId) return;
    setLoading(true);
    setTab("overview");
    Promise.all([
      clientsService.getClient(clientId),
      clientsService.getClientInvoices(clientId),
      clientsService.getClientAssignments(clientId),
      clientsService.getClientHistory(clientId),
    ])
      .then(([c, inv, asgn, hist]) => {
        setClient(c.data);
        setInvoices(inv.data || []);
        setAssignments(asgn.data || []);
        setHistory(hist.data || []);
      })
      .catch(() => showToast.error("Failed to load client"))
      .finally(() => setLoading(false));
  }, [clientId]);

  if (!clientId) return null;

  const tabs = [
    { key: "overview", label: "Overview" },
    { key: "finance", label: "Finance" },
    { key: "history", label: "Timeline" },
  ];

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative z-50 w-full max-w-xl bg-background shadow-xl flex flex-col h-full overflow-hidden">
        {/* header */}
        <div className="flex items-start justify-between p-4 border-b">
          {loading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading…
            </div>
          ) : client ? (
            <div>
              <div className="font-display font-bold text-lg leading-tight">{client.company_name}</div>
              <div className="text-sm text-muted-foreground">{contactName(client)}</div>
              {client.user?.email && (
                <div className="text-xs text-muted-foreground font-mono">{client.user.email}</div>
              )}
            </div>
          ) : (
            <div className="text-muted-foreground text-sm">Not found</div>
          )}
          <div className="flex items-center gap-2 ml-4">
            {client && (
              <Button size="sm" variant="outline" onClick={() => onEdit(client)}>
                Edit
              </Button>
            )}
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* tab strip */}
        <div className="flex gap-1 px-4 pt-3 border-b">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded-t-md -mb-px border-b-2 transition-colors",
                tab === t.key
                  ? "border-navy text-navy dark:text-gold dark:border-gold"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* body */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="flex justify-center py-12 text-muted-foreground">
              <Loader2 className="w-5 h-5 animate-spin" />
            </div>
          )}

          {!loading && client && tab === "overview" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <KpiCard icon={FileText} label="Missions" value={client.missions_count ?? 0} colorClass="border-l-navy" />
                <KpiCard icon={DollarSign} label="Total Revenue" value={fmt$(client.total_revenue)} colorClass="border-l-success" />
              </div>
              <div className="space-y-2 text-sm">
                {client.city && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
                    {client.city}{client.state ? `, ${client.state}` : ""}
                  </div>
                )}
                {client.tax_id && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                    Tax ID: {client.tax_id}
                  </div>
                )}
                {client.credit_limit != null && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <DollarSign className="w-3.5 h-3.5 flex-shrink-0" />
                    Credit limit: {fmt$(client.credit_limit)}
                  </div>
                )}
              </div>
              {client.notes && (
                <div className="rounded-md bg-muted p-3 text-sm text-muted-foreground">
                  {client.notes}
                </div>
              )}
            </div>
          )}

          {!loading && client && tab === "finance" && (
            <div className="space-y-3">
              {invoices.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No invoices</p>
              ) : invoices.map((inv) => (
                <div key={inv.id} className="flex items-center justify-between rounded-md border p-3">
                  <div>
                    <div className="text-sm font-mono font-semibold">{inv.invoice_number}</div>
                    <div className="text-xs text-muted-foreground">{fmtDate(inv.issued_date)}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono font-semibold">{fmt$(inv.total)}</div>
                    <StatusBadge status={inv.status} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {!loading && client && tab === "history" && (
            <div className="space-y-2">
              {history.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No history</p>
              ) : history.map((item, i) => (
                <div key={i} className="flex items-start gap-3 py-2 border-b last:border-0">
                  <div className="w-2 h-2 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="text-xs font-medium capitalize">
                      {item.type?.replace("_", " ")}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {fmtDate(item.date)} · {item.status || ""}
                      {item.service_type__name ? ` · ${item.service_type__name}` : ""}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Generate Quote Modal ────────────────────────────────────────────────────
function GenerateQuoteModal({ request, onClose, onSuccess }) {
  const [amount, setAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!amount || isNaN(Number(amount))) {
      showToast.error("Enter a valid amount");
      return;
    }
    setLoading(true);
    try {
      await clientsService.generateQuote(request.id, { amount: Number(amount), notes });
      showToast.success(`Quote generated for request #${request.id}`);
      onSuccess();
      onClose();
    } catch (err) {
      showToast.error(err?.response?.data?.detail || "Failed to generate quote");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={!!request}
      onClose={onClose}
      title="Generate Quote"
      subtitle={`Quote Request #${request?.id}`}
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={loading} className="bg-navy hover:bg-navy-light">
            {loading ? "Generating…" : "Generate Quote"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <Label className="mb-1.5">Quote Amount ($) *</Label>
          <Input
            type="number"
            min="0"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="250.00"
          />
        </div>
        <div>
          <Label className="mb-1.5">Notes</Label>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Any terms or conditions…"
            rows={3}
          />
        </div>
      </div>
    </Modal>
  );
}

// ─── Clients Tab ─────────────────────────────────────────────────────────────
function ClientsTab({ onNewClient, refresh }) {
  const [data, setData] = useState({ results: [], count: 0 });
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [drawerClientId, setDrawerClientId] = useState(null);
  const [editClient, setEditClient] = useState(null);
  const debounceRef = useRef(null);

  const load = useCallback((q, p) => {
    setLoading(true);
    const params = { page: p };
    if (q) params.search = q;
    clientsService
      .getClients(params)
      .then((r) => setData(r.data))
      .catch(() => showToast.error("Failed to load clients"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(search, page); }, [refresh]);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      load(search, 1);
    }, 350);
  }, [search]);

  useEffect(() => { load(search, page); }, [page]);

  const clients = data.results || [];
  const total = data.count || 0;
  const totalRevenue = clients.reduce((s, c) => s + Number(c.total_revenue || 0), 0);
  const topClient = clients.slice().sort((a, b) => Number(b.total_revenue || 0) - Number(a.total_revenue || 0))[0];

  return (
    <div className="space-y-4">
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard icon={Building2} label="Total Clients" value={total} colorClass="border-l-navy" />
        <KpiCard icon={DollarSign} label="Revenue (page)" value={fmt$(totalRevenue)} colorClass="border-l-success" />
        <KpiCard icon={Users} label="Active" value={clients.filter((c) => c.mission_count > 0).length} colorClass="border-l-info" sub="w/ missions" />
        <KpiCard icon={TrendingUp} label="Top Client" value={topClient?.company_name || "—"} colorClass="border-l-gold" sub={fmt$(topClient?.total_revenue)} />
      </div>

      {/* toolbar */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            className="pl-8 h-8 text-sm"
            placeholder="Search clients…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Button size="sm" variant="outline" onClick={() => load(search, page)} className="h-8">
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>
      </div>

      {/* table */}
      <div className="rounded-md border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/30">
              {["Company", "Contact", "City / State", "Missions", "Revenue", ""].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="py-10 text-center text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin inline" />
                </td>
              </tr>
            )}
            {!loading && clients.length === 0 && (
              <tr>
                <td colSpan={6} className="py-10 text-center text-muted-foreground text-sm">
                  No clients found
                </td>
              </tr>
            )}
            {!loading && clients.map((c) => (
              <tr
                key={c.id}
                className="border-b last:border-0 hover:bg-muted/20 cursor-pointer transition-colors"
                onClick={() => setDrawerClientId(c.id)}
              >
                <td className="px-3 py-2 font-semibold">{c.company_name}</td>
                <td className="px-3 py-2 text-muted-foreground text-xs">{contactName(c)}</td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {[c.city, c.state].filter(Boolean).join(", ") || "—"}
                </td>
                <td className="px-3 py-2 font-mono">{c.mission_count ?? 0}</td>
                <td className="px-3 py-2 font-mono font-semibold text-success">{fmt$(c.total_revenue)}</td>
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setDrawerClientId(c.id)}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Showing {clients.length} of {total}</span>
          <div className="flex gap-1">
            <Button variant="outline" size="sm" className="h-7" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Prev</Button>
            <Button variant="outline" size="sm" className="h-7" disabled={clients.length < 20} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </div>
      )}

      {/* drawer */}
      {drawerClientId && (
        <ClientDrawer
          clientId={drawerClientId}
          onClose={() => setDrawerClientId(null)}
          onEdit={(c) => { setDrawerClientId(null); setEditClient(c); }}
        />
      )}

      {/* edit modal */}
      <ClientFormModal
        isOpen={!!editClient}
        onClose={() => setEditClient(null)}
        client={editClient}
        onSuccess={() => load(search, page)}
      />
    </div>
  );
}

// ─── Quote Pipeline Tab ───────────────────────────────────────────────────────
function QuoteTab() {
  const [data, setData] = useState({ results: [], count: 0 });
  const [loading, setLoading] = useState(true);
  const [generateTarget, setGenerateTarget] = useState(null);
  const [sendingId, setSendingId] = useState(null);
  const refreshRef = useRef(0);

  const load = useCallback(() => {
    setLoading(true);
    clientsService
      .getQuoteRequests({ page: 1, page_size: 50 })
      .then((r) => setData(r.data))
      .catch(() => showToast.error("Failed to load quote requests"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [refreshRef.current]);

  const requests = data.results || [];
  const counts = {
    PENDING: requests.filter((q) => q.status === "PENDING").length,
    QUOTED: requests.filter((q) => q.status === "QUOTED").length,
    ACCEPTED: requests.filter((q) => q.status === "ACCEPTED").length,
    REJECTED: requests.filter((q) => q.status === "REJECTED").length,
  };

  const handleSendQuote = async (quoteId) => {
    setSendingId(quoteId);
    try {
      await clientsService.sendQuote(quoteId);
      showToast.success("Quote sent");
      load();
    } catch {
      showToast.error("Failed to send quote");
    } finally {
      setSendingId(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* funnel KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard icon={Clock} label="Pending" value={counts.PENDING} colorClass="border-l-warning" />
        <KpiCard icon={FileText} label="Quoted" value={counts.QUOTED} colorClass="border-l-info" />
        <KpiCard icon={CheckCircle} label="Accepted" value={counts.ACCEPTED} colorClass="border-l-success" />
        <KpiCard icon={X} label="Rejected" value={counts.REJECTED} colorClass="border-l-danger" />
      </div>

      {/* table */}
      <div className="rounded-md border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/30">
              {["#", "Client", "Service", "Languages", "Date", "Status", "Actions"].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="py-10 text-center text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin inline" />
                </td>
              </tr>
            )}
            {!loading && requests.length === 0 && (
              <tr>
                <td colSpan={7} className="py-10 text-center text-muted-foreground text-sm">No quote requests</td>
              </tr>
            )}
            {!loading && requests.map((q) => (
              <tr key={q.id} className="border-b last:border-0 hover:bg-muted/20">
                <td className="px-3 py-2 font-mono font-semibold text-xs text-navy dark:text-gold">#{q.id}</td>
                <td className="px-3 py-2">{q.client_name || q.client}</td>
                <td className="px-3 py-2 text-xs">{q.service_type_name || q.service_type}</td>
                <td className="px-3 py-2 font-mono text-xs">
                  {q.source_language && q.target_language
                    ? `${q.source_language} → ${q.target_language}`
                    : "—"}
                </td>
                <td className="px-3 py-2 font-mono text-xs">{fmtDate(q.created_at)}</td>
                <td className="px-3 py-2"><StatusBadge status={q.status} /></td>
                <td className="px-3 py-2">
                  <div className="flex gap-1">
                    {q.status === "PENDING" && (
                      <Button
                        size="sm"
                        className="h-7 text-[10px] bg-gold text-navy hover:bg-gold/90"
                        onClick={() => setGenerateTarget(q)}
                      >
                        Generate
                      </Button>
                    )}
                    {q.status === "QUOTED" && q.quote_id && (
                      <Button
                        size="sm"
                        className="h-7 text-[10px] bg-navy hover:bg-navy-light"
                        disabled={sendingId === q.quote_id}
                        onClick={() => handleSendQuote(q.quote_id)}
                      >
                        {sendingId === q.quote_id ? <Loader2 className="w-3 h-3 animate-spin" /> : "Send"}
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {generateTarget && (
        <GenerateQuoteModal
          request={generateTarget}
          onClose={() => setGenerateTarget(null)}
          onSuccess={load}
        />
      )}
    </div>
  );
}

// ─── Public Requests Tab ──────────────────────────────────────────────────────
function PublicTab() {
  const [data, setData] = useState({ results: [], count: 0 });
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    clientsService
      .getPublicRequests({ page: 1, page_size: 50 })
      .then((r) => setData(r.data))
      .catch(() => showToast.error("Failed to load public requests"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, []);

  const requests = data.results || [];

  const handleProcess = async (id) => {
    setProcessingId(id);
    try {
      await clientsService.processPublicRequest(id);
      showToast.success("Request processed");
      load();
    } catch {
      showToast.error("Failed to process request");
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{data.count || 0} public requests from website form</p>
        <Button size="sm" variant="outline" onClick={load} className="h-8">
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>
      </div>

      <div className="rounded-md border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/30">
              {["#", "Name", "Email", "Service", "Languages", "Date", "Status", "Actions"].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8} className="py-10 text-center text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin inline" />
                </td>
              </tr>
            )}
            {!loading && requests.length === 0 && (
              <tr>
                <td colSpan={8} className="py-10 text-center">
                  <Globe className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm text-muted-foreground">No public requests yet</p>
                </td>
              </tr>
            )}
            {!loading && requests.map((r) => (
              <tr key={r.id} className="border-b last:border-0 hover:bg-muted/20">
                <td className="px-3 py-2 font-mono text-xs text-navy dark:text-gold">#{r.id}</td>
                <td className="px-3 py-2 font-medium">{r.full_name || r.name || "—"}</td>
                <td className="px-3 py-2 font-mono text-xs">{r.email}</td>
                <td className="px-3 py-2 text-xs">{r.service_type_name || r.service_type || "—"}</td>
                <td className="px-3 py-2 font-mono text-xs">
                  {r.source_language && r.target_language
                    ? `${r.source_language} → ${r.target_language}`
                    : "—"}
                </td>
                <td className="px-3 py-2 font-mono text-xs">{fmtDate(r.created_at)}</td>
                <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
                <td className="px-3 py-2">
                  {r.status === "PENDING" && (
                    <Button
                      size="sm"
                      className="h-7 text-[10px] bg-navy hover:bg-navy-light"
                      disabled={processingId === r.id}
                      onClick={() => handleProcess(r.id)}
                    >
                      {processingId === r.id ? <Loader2 className="w-3 h-3 animate-spin" /> : "Process"}
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Revenue Tab ──────────────────────────────────────────────────────────────
function RevenueTab() {
  const [clientRevenue, setClientRevenue] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    clientsService
      .getClients({ ordering: "-total_revenue", page_size: 20 })
      .then((r) => setClientRevenue(r.data.results || []))
      .catch(() => showToast.error("Failed to load revenue data"))
      .finally(() => setLoading(false));
  }, []);

  const max = Math.max(...clientRevenue.map((c) => Number(c.total_revenue || 0)), 1);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <KpiCard
          icon={DollarSign}
          label="Top Client Revenue"
          value={fmt$(clientRevenue[0]?.total_revenue)}
          sub={clientRevenue[0]?.company_name}
          colorClass="border-l-gold"
        />
        <KpiCard
          icon={Users}
          label="Clients with Revenue"
          value={clientRevenue.filter((c) => Number(c.total_revenue) > 0).length}
          colorClass="border-l-navy"
        />
        <KpiCard
          icon={TrendingUp}
          label="Avg Revenue/Client"
          value={fmt$(
            clientRevenue.length
              ? clientRevenue.reduce((s, c) => s + Number(c.total_revenue || 0), 0) / clientRevenue.length
              : 0
          )}
          colorClass="border-l-success"
        />
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-4">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">
            Top Clients by Revenue
          </h4>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-2">
              {clientRevenue.map((c, i) => {
                const rev = Number(c.total_revenue || 0);
                const pct = (rev / max) * 100;
                return (
                  <div key={c.id} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-5 text-right">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-sm font-medium truncate">{c.company_name}</span>
                        <span className="text-sm font-mono font-semibold text-success ml-2 flex-shrink-0">
                          {fmt$(c.total_revenue)}
                        </span>
                      </div>
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-navy dark:bg-gold transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
              {clientRevenue.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8">No revenue data</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Main Module ──────────────────────────────────────────────────────────────
export const ClientsModule = () => {
  const [tab, setTab] = useState("clients");
  const [showNewClient, setShowNewClient] = useState(false);
  const [clientsRefresh, setClientsRefresh] = useState(0);

  const TABS = [
    { key: "clients",  label: "Clients" },
    { key: "quotes",   label: "Quote Pipeline" },
    { key: "public",   label: "Public Requests" },
    { key: "revenue",  label: "Revenue" },
  ];

  return (
    <div className="flex flex-col gap-4" data-testid="clients-module">
      <SectionHeader
        title="Clients & Sales"
        subtitle="Client relationship management & quote pipeline"
        action={
          <Button
            size="sm"
            className="gap-1.5 bg-navy hover:bg-navy-light"
            onClick={() => setShowNewClient(true)}
            data-testid="new-client-btn"
          >
            <Plus className="w-3.5 h-3.5" /> New Client
          </Button>
        }
      />

      <TabBar tabs={TABS} active={tab} onChange={setTab} />

      {tab === "clients" && (
        <ClientsTab
          refresh={clientsRefresh}
          onNewClient={() => setShowNewClient(true)}
        />
      )}
      {tab === "quotes"  && <QuoteTab />}
      {tab === "public"  && <PublicTab />}
      {tab === "revenue" && <RevenueTab />}

      <ClientFormModal
        isOpen={showNewClient}
        onClose={() => setShowNewClient(false)}
        onSuccess={() => {
          setClientsRefresh((n) => n + 1);
          setTab("clients");
        }}
      />
    </div>
  );
};

export default ClientsModule;
