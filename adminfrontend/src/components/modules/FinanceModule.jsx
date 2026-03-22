// JHBridge Command Center — Finance & Accounting Module (live API)
import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { SectionHeader, TabBar, KPICard, ProgressBar } from '@/components/shared/UIComponents';
import { showToast } from '@/components/shared/Toast';
import { financeService } from '@/services/financeService';
import { cn } from '@/lib/utils';
import {
  Plus, RefreshCw, Loader2, X, Send, CheckCircle, Bell,
  Check, DollarSign, TrendingUp, TrendingDown, Search,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fmtAmt = (v) =>
  v != null ? '$' + parseFloat(v).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '—';

const fmt = (v) =>
  v ? new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';

const INVOICE_STATUS_COLORS = {
  DRAFT:     'text-muted-foreground',
  SENT:      'text-info',
  PAID:      'text-success',
  OVERDUE:   'text-red-500',
  CANCELLED: 'text-muted-foreground',
  DISPUTED:  'text-warning',
};

const EXPENSE_STATUS_COLORS = {
  PENDING:  'text-warning',
  APPROVED: 'text-info',
  PAID:     'text-success',
  REJECTED: 'text-red-500',
};

const EXPENSE_TYPES = [
  'OPERATIONAL', 'ADMINISTRATIVE', 'MARKETING', 'SALARY', 'TAX', 'OTHER',
];

const PAYMENT_METHODS = [
  'BANK_TRANSFER', 'CHECK', 'ACH', 'ZELLE', 'CASH', 'OTHER',
];

// ---------------------------------------------------------------------------
// Create Invoice Modal
// ---------------------------------------------------------------------------

const CreateInvoiceModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({
    client: '', subtotal: '', tax_amount: '0', due_date: '', notes: '',
  });
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    import('@/services/dispatchService').then(({ dispatchService }) =>
      dispatchService.getClients({ page_size: 200 }).then((r) => {
        setClients(r.data.results ?? r.data);
      })
    );
  }, []);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const validate = () => {
    const err = {};
    if (!form.client) err.client = 'Required';
    if (!form.subtotal || isNaN(parseFloat(form.subtotal))) err.subtotal = 'Valid amount required';
    if (!form.due_date) err.due_date = 'Required';
    setErrors(err);
    return Object.keys(err).length === 0;
  };

  const submit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const subtotal = parseFloat(form.subtotal);
      const tax = parseFloat(form.tax_amount) || 0;
      await financeService.createInvoice({
        client: parseInt(form.client),
        subtotal,
        tax_amount: tax,
        total: subtotal + tax,
        due_date: form.due_date,
        notes: form.notes,
      });
      showToast.success('Invoice created');
      onCreated();
      onClose();
    } catch (err) {
      showToast.error(err?.response?.data?.detail || 'Failed to create invoice');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-background border border-border rounded-lg shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold">New Invoice</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Client</label>
            <select value={form.client} onChange={set('client')}
              className={cn('mt-1 w-full h-8 text-sm border border-border rounded px-2 bg-background', errors.client && 'border-red-500')}>
              <option value="">Select client…</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.company_name}</option>
              ))}
            </select>
            {errors.client && <p className="text-[11px] text-red-500 mt-0.5">{errors.client}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Subtotal ($)</label>
              <Input type="number" step="0.01" value={form.subtotal} onChange={set('subtotal')}
                className={cn('mt-1 h-8 text-sm', errors.subtotal && 'border-red-500')} placeholder="0.00" />
              {errors.subtotal && <p className="text-[11px] text-red-500 mt-0.5">{errors.subtotal}</p>}
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Tax ($)</label>
              <Input type="number" step="0.01" value={form.tax_amount} onChange={set('tax_amount')}
                className="mt-1 h-8 text-sm" placeholder="0.00" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Due Date</label>
            <Input type="date" value={form.due_date} onChange={set('due_date')}
              className={cn('mt-1 h-8 text-sm', errors.due_date && 'border-red-500')} />
            {errors.due_date && <p className="text-[11px] text-red-500 mt-0.5">{errors.due_date}</p>}
          </div>
          {(form.subtotal || form.tax_amount) && (
            <div className="p-2 bg-muted/50 rounded text-xs font-semibold">
              Total: {fmtAmt((parseFloat(form.subtotal) || 0) + (parseFloat(form.tax_amount) || 0))}
            </div>
          )}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Notes <span className="text-muted-foreground/60">(optional)</span></label>
            <textarea value={form.notes} onChange={set('notes')} rows={2}
              className="mt-1 w-full text-sm border border-border rounded px-2 py-1.5 bg-background resize-none"
              placeholder="Payment terms, reference…" />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" size="sm" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button size="sm" onClick={submit} disabled={loading} className="bg-navy hover:bg-navy-light gap-1.5">
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
            Create Invoice
          </Button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Create Expense Modal
// ---------------------------------------------------------------------------

const CreateExpenseModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({
    expense_type: 'OPERATIONAL', amount: '', description: '', date_incurred: '', notes: '',
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const validate = () => {
    const err = {};
    if (!form.amount || isNaN(parseFloat(form.amount))) err.amount = 'Valid amount required';
    if (!form.description.trim()) err.description = 'Required';
    if (!form.date_incurred) err.date_incurred = 'Required';
    setErrors(err);
    return Object.keys(err).length === 0;
  };

  const submit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      await financeService.createExpense({
        expense_type: form.expense_type,
        amount: parseFloat(form.amount),
        description: form.description,
        date_incurred: form.date_incurred + 'T00:00:00Z',
        status: 'PENDING',
        notes: form.notes,
      });
      showToast.success('Expense recorded');
      onCreated();
      onClose();
    } catch (err) {
      showToast.error(err?.response?.data?.detail || 'Failed to create expense');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-background border border-border rounded-lg shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold">Record Expense</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Type</label>
              <select value={form.expense_type} onChange={set('expense_type')}
                className="mt-1 w-full h-8 text-sm border border-border rounded px-2 bg-background">
                {EXPENSE_TYPES.map((t) => (
                  <option key={t} value={t}>{t.charAt(0) + t.slice(1).toLowerCase()}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Amount ($)</label>
              <Input type="number" step="0.01" value={form.amount} onChange={set('amount')}
                className={cn('mt-1 h-8 text-sm', errors.amount && 'border-red-500')} placeholder="0.00" />
              {errors.amount && <p className="text-[11px] text-red-500 mt-0.5">{errors.amount}</p>}
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Description</label>
            <Input value={form.description} onChange={set('description')}
              className={cn('mt-1 h-8 text-sm', errors.description && 'border-red-500')}
              placeholder="Office supplies, software subscription…" />
            {errors.description && <p className="text-[11px] text-red-500 mt-0.5">{errors.description}</p>}
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Date</label>
            <Input type="date" value={form.date_incurred} onChange={set('date_incurred')}
              className={cn('mt-1 h-8 text-sm', errors.date_incurred && 'border-red-500')} />
            {errors.date_incurred && <p className="text-[11px] text-red-500 mt-0.5">{errors.date_incurred}</p>}
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Notes <span className="text-muted-foreground/60">(optional)</span></label>
            <textarea value={form.notes} onChange={set('notes')} rows={2}
              className="mt-1 w-full text-sm border border-border rounded px-2 py-1.5 bg-background resize-none"
              placeholder="Additional details…" />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" size="sm" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button size="sm" onClick={submit} disabled={loading} className="bg-navy hover:bg-navy-light gap-1.5">
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
            Save Expense
          </Button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Overview Tab
// ---------------------------------------------------------------------------

const OverviewTab = ({ summary, refreshSummary }) => {
  const [revenueByService, setRevenueByService] = useState([]);
  const [topClients, setTopClients] = useState([]);
  const [loadingCharts, setLoadingCharts] = useState(true);

  useEffect(() => {
    Promise.all([
      financeService.getRevenueByService(),
      financeService.getRevenueByClient(),
    ]).then(([svc, cli]) => {
      setRevenueByService(svc.data.slice(0, 6));
      setTopClients(cli.data.slice(0, 5));
    }).catch(() => {}).finally(() => setLoadingCharts(false));
  }, []);

  const maxRevSvc = Math.max(...revenueByService.map((s) => parseFloat(s.total_revenue || 0)), 1);
  const maxRevCli = Math.max(...topClients.map((c) => parseFloat(c.total_revenue || 0)), 1);

  return (
    <div className="space-y-4">
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard
          label="MTD Revenue"
          value={fmtAmt(summary?.mtd_revenue)}
          sub="This month"
          accent="success"
        />
        <KPICard
          label="MTD Expenses"
          value={fmtAmt(summary?.mtd_expenses)}
          sub="This month"
          accent="danger"
        />
        <KPICard
          label="Net Profit"
          value={fmtAmt(summary?.net_profit)}
          sub="All time"
          accent="gold"
        />
        <KPICard
          label="Outstanding"
          value={fmtAmt(summary?.outstanding_invoices)}
          sub="Unpaid invoices"
          accent="warning"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Revenue by service */}
        <Card className="shadow-sm">
          <CardContent className="p-4">
            <span className="text-sm font-semibold block mb-3">Revenue by Service Type</span>
            {loadingCharts ? (
              <div className="flex items-center justify-center h-20 text-muted-foreground text-xs">
                <Loader2 className="w-4 h-4 animate-spin mr-2" />Loading…
              </div>
            ) : revenueByService.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-4">No data yet</p>
            ) : (
              <div className="space-y-3">
                {revenueByService.map((s, i) => {
                  const pct = Math.round((parseFloat(s.total_revenue) / maxRevSvc) * 100);
                  return (
                    <div key={i}>
                      <div className="flex justify-between text-xs mb-1">
                        <span>{s.service_type__name || 'Unknown'}</span>
                        <span className="font-mono font-semibold">
                          {fmtAmt(s.total_revenue)} ({s.count})
                        </span>
                      </div>
                      <ProgressBar value={pct} color="bg-navy dark:bg-gold" />
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top clients */}
        <Card className="shadow-sm">
          <CardContent className="p-4">
            <span className="text-sm font-semibold block mb-3">Top Clients by Revenue</span>
            {loadingCharts ? (
              <div className="flex items-center justify-center h-20 text-muted-foreground text-xs">
                <Loader2 className="w-4 h-4 animate-spin mr-2" />Loading…
              </div>
            ) : topClients.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-4">No data yet</p>
            ) : (
              <div className="space-y-0">
                {topClients.map((c, i) => (
                  <div key={i} className="flex justify-between items-center py-2 border-b border-border last:border-0">
                    <div>
                      <span className="text-xs font-medium">{c.client__company_name || 'Unknown'}</span>
                      <span className="text-[10px] text-muted-foreground font-mono ml-2">{c.count} payments</span>
                    </div>
                    <span className="text-sm font-bold font-mono text-success">{fmtAmt(c.total_revenue)}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Invoices Tab
// ---------------------------------------------------------------------------

const InvoicesTab = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [actionLoading, setActionLoading] = useState('');
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const PAGE_SIZE = 15;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (statusFilter) params.status = statusFilter;
      const r = await financeService.getInvoices(params);
      setInvoices(r.data.results ?? r.data);
      setTotalCount(r.data.count ?? (r.data.results ?? r.data).length);
    } catch { showToast.error('Failed to load invoices'); }
    finally { setLoading(false); }
  }, [page, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const doAction = async (type, invoice) => {
    const key = `${type}-${invoice.id}`;
    setActionLoading(key);
    try {
      if (type === 'send') {
        await financeService.sendInvoice(invoice.id);
        showToast.success(`Invoice ${invoice.invoice_number} sent`);
      } else if (type === 'paid') {
        await financeService.markInvoicePaid(invoice.id, 'BANK_TRANSFER');
        showToast.success(`Invoice ${invoice.invoice_number} marked as paid`);
      } else if (type === 'remind') {
        await financeService.remindInvoice(invoice.id);
        showToast.success(`Reminder sent for ${invoice.invoice_number}`);
      }
      load();
    } catch (err) {
      showToast.error(err?.response?.data?.detail || `Failed to ${type}`);
    } finally { setActionLoading(''); }
  };

  const filtered = search
    ? invoices.filter((i) => i.invoice_number?.includes(search) || i.client_name?.toLowerCase().includes(search.toLowerCase()))
    : invoices;

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search invoice #, client…" className="h-8 pl-8 text-sm" />
        </div>
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="h-8 text-sm border border-border rounded px-2 bg-background">
          <option value="">All statuses</option>
          {['DRAFT', 'SENT', 'PAID', 'OVERDUE', 'CANCELLED'].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <Button size="sm" onClick={() => setShowCreate(true)} className="gap-1.5 bg-navy hover:bg-navy-light ml-auto">
          <Plus className="w-3.5 h-3.5" /> New Invoice
        </Button>
      </div>

      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50 border-b border-border text-xs text-muted-foreground">
              <th className="text-left px-3 py-2 font-medium">Invoice #</th>
              <th className="text-left px-3 py-2 font-medium">Client</th>
              <th className="text-left px-3 py-2 font-medium">Total</th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
              <th className="text-left px-3 py-2 font-medium">Issued</th>
              <th className="text-left px-3 py-2 font-medium">Due</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-muted-foreground text-xs">
                <Loader2 className="w-4 h-4 animate-spin inline mr-2" />Loading…
              </td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-muted-foreground text-xs">No invoices found.</td></tr>
            ) : filtered.map((r) => (
              <tr key={r.id} className="border-b border-border hover:bg-muted/40 transition-colors">
                <td className="px-3 py-2">
                  <span className="font-mono font-semibold text-navy dark:text-gold text-xs">{r.invoice_number}</span>
                </td>
                <td className="px-3 py-2 text-xs font-medium">{r.client_name}</td>
                <td className="px-3 py-2 text-xs font-mono font-semibold">{fmtAmt(r.total)}</td>
                <td className="px-3 py-2">
                  <span className={cn('text-[11px] font-semibold', INVOICE_STATUS_COLORS[r.status] || '')}>{r.status}</span>
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">{fmt(r.issued_date)}</td>
                <td className="px-3 py-2 text-xs text-muted-foreground">{fmt(r.due_date)}</td>
                <td className="px-3 py-2">
                  <div className="flex gap-1 justify-end">
                    {r.status === 'DRAFT' && (
                      <Button variant="ghost" size="sm" className="h-7 px-2 gap-1 text-[10px]"
                        disabled={actionLoading === `send-${r.id}`}
                        onClick={() => doAction('send', r)}>
                        {actionLoading === `send-${r.id}` ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                        Send
                      </Button>
                    )}
                    {['SENT', 'OVERDUE'].includes(r.status) && (
                      <>
                        <Button variant="ghost" size="sm" className="h-7 px-2 gap-1 text-[10px] text-success"
                          disabled={!!actionLoading} onClick={() => doAction('paid', r)}>
                          {actionLoading === `paid-${r.id}` ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
                          Paid
                        </Button>
                        <Button variant="ghost" size="sm" className="h-7 px-2 gap-1 text-[10px]"
                          disabled={!!actionLoading} onClick={() => doAction('remind', r)}>
                          <Bell className="w-3 h-3" /> Remind
                        </Button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-3 py-2 border-t border-border text-xs text-muted-foreground">
            <span>{totalCount} total</span>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="sm" className="h-7 px-2"
                onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>Prev</Button>
              <span className="px-2">{page} / {totalPages}</span>
              <Button variant="outline" size="sm" className="h-7 px-2"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Next</Button>
            </div>
          </div>
        )}
      </div>

      {showCreate && <CreateInvoiceModal onClose={() => setShowCreate(false)} onCreated={load} />}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Expenses Tab
// ---------------------------------------------------------------------------

const ExpensesTab = () => {
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [actionLoading, setActionLoading] = useState('');
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const PAGE_SIZE = 15;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (statusFilter) params.status = statusFilter;
      const r = await financeService.getExpenses(params);
      setExpenses(r.data.results ?? r.data);
      setTotalCount(r.data.count ?? (r.data.results ?? r.data).length);
    } catch { showToast.error('Failed to load expenses'); }
    finally { setLoading(false); }
  }, [page, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const doAction = async (type, expense) => {
    const key = `${type}-${expense.id}`;
    setActionLoading(key);
    try {
      if (type === 'approve') await financeService.approveExpense(expense.id);
      if (type === 'pay') await financeService.payExpense(expense.id);
      showToast.success(type === 'approve' ? 'Expense approved' : 'Expense marked as paid');
      load();
    } catch (err) {
      showToast.error(err?.response?.data?.detail || `Failed to ${type}`);
    } finally { setActionLoading(''); }
  };

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="h-8 text-sm border border-border rounded px-2 bg-background">
          <option value="">All statuses</option>
          {['PENDING', 'APPROVED', 'PAID', 'REJECTED'].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <Button size="sm" onClick={() => setShowCreate(true)} className="gap-1.5 bg-navy hover:bg-navy-light ml-auto">
          <Plus className="w-3.5 h-3.5" /> Record Expense
        </Button>
      </div>

      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50 border-b border-border text-xs text-muted-foreground">
              <th className="text-left px-3 py-2 font-medium">Description</th>
              <th className="text-left px-3 py-2 font-medium">Type</th>
              <th className="text-left px-3 py-2 font-medium">Amount</th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
              <th className="text-left px-3 py-2 font-medium">Date</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-3 py-8 text-center text-muted-foreground text-xs">
                <Loader2 className="w-4 h-4 animate-spin inline mr-2" />Loading…
              </td></tr>
            ) : expenses.length === 0 ? (
              <tr><td colSpan={6} className="px-3 py-8 text-center text-muted-foreground text-xs">No expenses found.</td></tr>
            ) : expenses.map((r) => (
              <tr key={r.id} className="border-b border-border hover:bg-muted/40 transition-colors">
                <td className="px-3 py-2 text-xs font-medium max-w-[200px] truncate">{r.description}</td>
                <td className="px-3 py-2">
                  <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded font-medium">
                    {r.expense_type}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs font-mono font-semibold">{fmtAmt(r.amount)}</td>
                <td className="px-3 py-2">
                  <span className={cn('text-[11px] font-semibold', EXPENSE_STATUS_COLORS[r.status] || '')}>{r.status}</span>
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">{fmt(r.date_incurred)}</td>
                <td className="px-3 py-2">
                  <div className="flex gap-1 justify-end">
                    {r.status === 'PENDING' && (
                      <Button variant="ghost" size="sm" className="h-7 px-2 gap-1 text-[10px] text-info"
                        disabled={!!actionLoading} onClick={() => doAction('approve', r)}>
                        {actionLoading === `approve-${r.id}` ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                        Approve
                      </Button>
                    )}
                    {r.status === 'APPROVED' && (
                      <Button variant="ghost" size="sm" className="h-7 px-2 gap-1 text-[10px] text-success"
                        disabled={!!actionLoading} onClick={() => doAction('pay', r)}>
                        {actionLoading === `pay-${r.id}` ? <Loader2 className="w-3 h-3 animate-spin" /> : <DollarSign className="w-3 h-3" />}
                        Mark Paid
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-3 py-2 border-t border-border text-xs text-muted-foreground">
            <span>{totalCount} total</span>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="sm" className="h-7 px-2"
                onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>Prev</Button>
              <span className="px-2">{page} / {totalPages}</span>
              <Button variant="outline" size="sm" className="h-7 px-2"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Next</Button>
            </div>
          </div>
        )}
      </div>

      {showCreate && <CreateExpenseModal onClose={() => setShowCreate(false)} onCreated={load} />}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Reports Tab (P&L)
// ---------------------------------------------------------------------------

const ReportsTab = () => {
  const [pnl, setPnl] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    financeService.getPnl()
      .then((r) => setPnl(r.data))
      .catch(() => showToast.error('Failed to load P&L data'))
      .finally(() => setLoading(false));
  }, []);

  const maxVal = Math.max(...pnl.flatMap((m) => [parseFloat(m.revenue), parseFloat(m.expenses)]), 1);

  return (
    <div className="space-y-4">
      <Card className="shadow-sm">
        <CardContent className="p-4">
          <span className="text-sm font-semibold block mb-4">Profit & Loss — Last 12 Months</span>
          {loading ? (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-xs">
              <Loader2 className="w-4 h-4 animate-spin mr-2" />Loading…
            </div>
          ) : pnl.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-6">No financial data yet</p>
          ) : (
            <>
              {/* Bar chart */}
              <div className="flex items-end gap-1 h-32 mb-3">
                {pnl.map((m) => {
                  const revPct = (parseFloat(m.revenue) / maxVal) * 100;
                  const expPct = (parseFloat(m.expenses) / maxVal) * 100;
                  return (
                    <div key={m.month} className="flex-1 flex flex-col items-center gap-0.5" title={`${m.month}\nRevenue: ${fmtAmt(m.revenue)}\nExpenses: ${fmtAmt(m.expenses)}\nProfit: ${fmtAmt(m.profit)}`}>
                      <div className="w-full flex items-end gap-px h-28">
                        <div className="flex-1 bg-success/70 rounded-t-sm transition-all" style={{ height: `${revPct}%` }} />
                        <div className="flex-1 bg-red-400/70 rounded-t-sm transition-all" style={{ height: `${expPct}%` }} />
                      </div>
                      <span className="text-[9px] text-muted-foreground">{m.month.slice(5)}</span>
                    </div>
                  );
                })}
              </div>
              <div className="flex gap-4 text-[11px] text-muted-foreground">
                <div className="flex items-center gap-1"><div className="w-3 h-2 bg-success/70 rounded-sm" /><span>Revenue</span></div>
                <div className="flex items-center gap-1"><div className="w-3 h-2 bg-red-400/70 rounded-sm" /><span>Expenses</span></div>
              </div>

              {/* Table */}
              <div className="mt-4 border border-border rounded overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-muted/50 border-b border-border text-muted-foreground">
                      <th className="text-left px-3 py-1.5 font-medium">Month</th>
                      <th className="text-right px-3 py-1.5 font-medium">Revenue</th>
                      <th className="text-right px-3 py-1.5 font-medium">Expenses</th>
                      <th className="text-right px-3 py-1.5 font-medium">Profit</th>
                      <th className="text-right px-3 py-1.5 font-medium">Margin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pnl.map((m) => {
                      const rev = parseFloat(m.revenue);
                      const exp = parseFloat(m.expenses);
                      const profit = parseFloat(m.profit);
                      const margin = rev > 0 ? Math.round((profit / rev) * 100) : 0;
                      return (
                        <tr key={m.month} className="border-b border-border last:border-0 hover:bg-muted/30">
                          <td className="px-3 py-1.5 font-mono">{m.month}</td>
                          <td className="px-3 py-1.5 text-right font-mono text-success">{fmtAmt(m.revenue)}</td>
                          <td className="px-3 py-1.5 text-right font-mono text-red-500">{fmtAmt(m.expenses)}</td>
                          <td className={cn('px-3 py-1.5 text-right font-mono font-semibold', profit >= 0 ? 'text-success' : 'text-red-500')}>
                            {fmtAmt(m.profit)}
                          </td>
                          <td className={cn('px-3 py-1.5 text-right font-mono', margin >= 0 ? 'text-success' : 'text-red-500')}>
                            {margin}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main FinanceModule
// ---------------------------------------------------------------------------

export const FinanceModule = () => {
  const [tab, setTab] = useState('overview');
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  const loadSummary = useCallback(async () => {
    setSummaryLoading(true);
    try {
      const r = await financeService.getSummary();
      setSummary(r.data);
    } catch { showToast.error('Failed to load financial summary'); }
    finally { setSummaryLoading(false); }
  }, []);

  useEffect(() => { loadSummary(); }, [loadSummary]);

  return (
    <div className="flex flex-col gap-4" data-testid="finance-module">
      <SectionHeader
        title="Finance & Accounting"
        subtitle="Revenue, expenses & financial reports"
        action={
          <Button variant="outline" size="sm" onClick={loadSummary} disabled={summaryLoading}>
            <RefreshCw className={cn('w-3.5 h-3.5', summaryLoading && 'animate-spin')} />
          </Button>
        }
      />

      <TabBar
        tabs={[
          { key: 'overview',  label: 'Overview' },
          { key: 'invoices',  label: 'Client Invoices' },
          { key: 'expenses',  label: 'Expenses' },
          { key: 'reports',   label: 'Reports / P&L' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'overview' && <OverviewTab summary={summary} refreshSummary={loadSummary} />}
      {tab === 'invoices' && <InvoicesTab />}
      {tab === 'expenses' && <ExpensesTab />}
      {tab === 'reports'  && <ReportsTab />}
    </div>
  );
};

export default FinanceModule;
