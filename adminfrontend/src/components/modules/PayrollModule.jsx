// JHBridge Command Center — Payroll & Payment Stubs Module
import { useState, useCallback, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  SectionHeader, StatusBadge, KPICard,
} from '@/components/shared/UIComponents';
import { showToast } from '@/components/shared/Toast';
import { usePayroll } from '@/hooks/usePayroll';
import { payrollService } from '@/services/payrollService';
import { PaymentStubModal } from '@/components/modals/PaymentStubModal';
import { BatchStubModal } from '@/components/modals/BatchStubModal';
import { TaxSummaryModal } from '@/components/modals/TaxSummaryModal';
import { ManualStubModal } from '@/components/modals/ManualStubModal';
import {
  FileText, Plus, Send, Check, RefreshCw, Loader2,
  AlertCircle, ReceiptText, ChevronLeft, ChevronRight,
  Search, Filter, UserPlus, Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const TABS = ['Pay Stubs', 'Payments'];
const PAGE_SIZE = 15;

const PAYMENT_STATUSES = ['', 'PENDING', 'PROCESSING', 'COMPLETED'];

const fmt = (v) => v
  ? new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  : '—';
const fmtAmt = (v) => (v !== undefined && v !== null)
  ? `$${parseFloat(v).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
  : '—';

// ---------------------------------------------------------------------------
// Pagination controls
// ---------------------------------------------------------------------------
const Pagination = ({ page, count, pageSize, onChange }) => {
  const total = Math.ceil((count || 0) / pageSize);
  if (total <= 1) return null;
  return (
    <div className="flex items-center justify-between px-1 pt-2 text-xs text-muted-foreground">
      <span>
        {Math.min((page - 1) * pageSize + 1, count || 0)}–{Math.min(page * pageSize, count || 0)} of {count || 0}
      </span>
      <div className="flex gap-1">
        <button
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          className="h-7 w-7 flex items-center justify-center rounded border border-border disabled:opacity-30 hover:bg-muted transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>
        {Array.from({ length: Math.min(total, 7) }, (_, i) => {
          let p;
          if (total <= 7) p = i + 1;
          else if (page <= 4) p = i + 1;
          else if (page >= total - 3) p = total - 6 + i;
          else p = page - 3 + i;
          return (
            <button
              key={p}
              onClick={() => onChange(p)}
              className={cn(
                'h-7 w-7 flex items-center justify-center rounded border text-[11px] transition-colors',
                p === page
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'border-border hover:bg-muted',
              )}
            >
              {p}
            </button>
          );
        })}
        <button
          disabled={page >= total}
          onClick={() => onChange(page + 1)}
          className="h-7 w-7 flex items-center justify-center rounded border border-border disabled:opacity-30 hover:bg-muted transition-colors"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main module
// ---------------------------------------------------------------------------
export const PayrollModule = () => {
  const { data, isLoading, error, refresh } = usePayroll();
  const [activeTab, setActiveTab] = useState('Pay Stubs');

  // Modals
  const [stubModal, setStubModal]     = useState(false);
  const [batchModal, setBatchModal]   = useState(false);
  const [taxModal, setTaxModal]       = useState(false);
  const [manualModal, setManualModal] = useState(false);

  const [actionLoading, setActionLoading] = useState({});

  // Stubs tab state
  const [stubPage, setStubPage]       = useState(1);
  const [stubSearch, setStubSearch]   = useState('');
  const [stubSearchInput, setStubSearchInput] = useState('');
  const [stubs, setStubs]             = useState([]);
  const [stubCount, setStubCount]     = useState(0);
  const [stubsLoading, setStubsLoading] = useState(false);

  // Payments tab state
  const [payPage, setPayPage]         = useState(1);
  const [paySearch, setPaySearch]     = useState('');
  const [paySearchInput, setPaySearchInput] = useState('');
  const [payStatus, setPayStatus]     = useState('');
  const [payments, setPayments]       = useState([]);
  const [payCount, setPayCount]       = useState(0);
  const [paymentsLoading, setPaymentsLoading] = useState(false);

  // Selection (Payments tab)
  const [selectedPayIds, setSelectedPayIds] = useState(new Set());
  const [bulkGenerating, setBulkGenerating] = useState(false);

  const kpis = data?.kpis || {};
  const setLoading = (key, val) => setActionLoading(prev => ({ ...prev, [key]: val }));

  // ---- Fetch stubs --------------------------------------------------------
  const fetchStubs = useCallback(async (page, search) => {
    setStubsLoading(true);
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (search) params.search = search;
      const res = await payrollService.getStubs(params);
      const body = res.data || {};
      setStubs(body.results || []);
      setStubCount(body.count || 0);
    } catch {
      showToast.error('Failed to load pay stubs');
    } finally {
      setStubsLoading(false);
    }
  }, []);

  // ---- Fetch payments -----------------------------------------------------
  const fetchPayments = useCallback(async (page, search, status) => {
    setPaymentsLoading(true);
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (search) params.search = search;
      if (status) params.status = status;
      const res = await payrollService.getPayments(params);
      const body = res.data || {};
      setPayments(body.results || []);
      setPayCount(body.count || 0);
    } catch {
      showToast.error('Failed to load payments');
    } finally {
      setPaymentsLoading(false);
    }
  }, []);

  // Trigger fetches on filter / page changes
  useEffect(() => {
    if (activeTab === 'Pay Stubs') fetchStubs(stubPage, stubSearch);
  }, [activeTab, stubPage, stubSearch, fetchStubs]);

  useEffect(() => {
    if (activeTab === 'Payments') fetchPayments(payPage, paySearch, payStatus);
  }, [activeTab, payPage, paySearch, payStatus, fetchPayments]);

  // Also trigger when parent data refreshes (KPI refresh)
  const prevRefreshKey = useRef(null);
  useEffect(() => {
    const key = data ? JSON.stringify(data.kpis) : null;
    if (key && key !== prevRefreshKey.current) {
      prevRefreshKey.current = key;
      if (activeTab === 'Pay Stubs') fetchStubs(stubPage, stubSearch);
      else fetchPayments(payPage, paySearch, payStatus);
    }
  }, [data]); // eslint-disable-line

  // Search debounce — stubs
  const stubSearchTimer = useRef(null);
  const onStubSearchChange = (val) => {
    setStubSearchInput(val);
    clearTimeout(stubSearchTimer.current);
    stubSearchTimer.current = setTimeout(() => {
      setStubPage(1);
      setStubSearch(val);
    }, 400);
  };

  // Search debounce — payments
  const paySearchTimer = useRef(null);
  const onPaySearchChange = (val) => {
    setPaySearchInput(val);
    clearTimeout(paySearchTimer.current);
    paySearchTimer.current = setTimeout(() => {
      setPayPage(1);
      setPaySearch(val);
    }, 400);
  };

  // ---- Actions ------------------------------------------------------------
  const handleDownloadPdf = async (stub) => {
    const key = `pdf-${stub.id}`;
    setLoading(key, true);
    try {
      await payrollService.downloadStubPdf(stub.id, stub.interpreter_name, stub.document_number);
    } catch {
      showToast.error('Failed to download PDF');
    } finally {
      setLoading(key, false);
    }
  };

  const handleSendStub = async (stub) => {
    const key = `send-${stub.id}`;
    setLoading(key, true);
    try {
      await payrollService.sendStub(stub.id);
      showToast.success(`Stub sent to ${stub.interpreter_name}`);
    } catch {
      showToast.error('Failed to send stub');
    } finally {
      setLoading(key, false);
    }
  };

  const handleProcessPayment = async (payment) => {
    const key = `proc-${payment.id}`;
    setLoading(key, true);
    try {
      await payrollService.processPayment(payment.id);
      showToast.success(`Payment ${payment.reference_number} is now processing`);
      fetchPayments(payPage, paySearch, payStatus);
      refresh();
    } catch {
      showToast.error('Failed to process payment');
    } finally {
      setLoading(key, false);
    }
  };

  const handleCompletePayment = async (payment) => {
    const key = `complete-${payment.id}`;
    setLoading(key, true);
    try {
      const res = await payrollService.completePayment(payment.id);
      const name = res.data?.interpreter_name || payment.interpreter_name || '';
      showToast.success(`Payment completed${name ? ` for ${name}` : ''} — assignment marked as paid`);
      fetchPayments(payPage, paySearch, payStatus);
      refresh();
    } catch {
      showToast.error('Failed to complete payment');
    } finally {
      setLoading(key, false);
    }
  };

  // ---- Bulk generate stubs from selected payments -------------------------
  const handleBulkGenerate = async () => {
    if (selectedPayIds.size === 0) return;
    setBulkGenerating(true);
    try {
      const res = await payrollService.stubsFromPayments({
        payment_ids: [...selectedPayIds],
      });
      const created = res.data || [];
      showToast.success(
        `${created.length} stub${created.length !== 1 ? 's' : ''} generated (grouped by interpreter)`,
      );
      setSelectedPayIds(new Set());
      fetchStubs(stubPage, stubSearch);
      refresh();
    } catch {
      showToast.error('Failed to generate stubs from payments');
    } finally {
      setBulkGenerating(false);
    }
  };

  // ---- Payment row checkbox -----------------------------------------------
  const togglePaySel = (id) => {
    setSelectedPayIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const allPaySelected = payments.length > 0 && payments.every(p => selectedPayIds.has(p.id));
  const toggleAllPay = () => {
    if (allPaySelected) {
      setSelectedPayIds(prev => {
        const next = new Set(prev);
        payments.forEach(p => next.delete(p.id));
        return next;
      });
    } else {
      setSelectedPayIds(prev => {
        const next = new Set(prev);
        payments.forEach(p => next.add(p.id));
        return next;
      });
    }
  };

  const refreshAll = () => {
    refresh();
    if (activeTab === 'Pay Stubs') fetchStubs(stubPage, stubSearch);
    else fetchPayments(payPage, paySearch, payStatus);
  };

  return (
    <>
      <div className="flex flex-col gap-4" data-testid="payroll-module">
        <SectionHeader
          title="Payroll & Payment Stubs"
          subtitle="Interpreter payments, stubs, reimbursements & deductions"
          action={
            <div className="flex gap-2 flex-wrap">
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setTaxModal(true)}>
                <ReceiptText className="w-3.5 h-3.5" /> Tax Summary
              </Button>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setBatchModal(true)}>
                <Layers className="w-3.5 h-3.5" /> Batch Generate
              </Button>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setManualModal(true)}>
                <UserPlus className="w-3.5 h-3.5" /> Manual Stub
              </Button>
              <Button size="sm" className="gap-1.5 bg-navy hover:bg-navy-light" onClick={() => setStubModal(true)}>
                <Plus className="w-3.5 h-3.5" /> New Stub
              </Button>
            </div>
          }
        />

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KPICard
            label="Pending Payments"
            value={isLoading ? '…' : String(kpis.pending_payments_count ?? '—')}
            sub={isLoading ? '' : fmtAmt(kpis.total_pending_payments)}
            accent="warning"
          />
          <KPICard
            label="Processing"
            value={isLoading ? '…' : String(kpis.processing_payments_count ?? '—')}
            sub={isLoading ? '' : fmtAmt(kpis.total_processing_payments)}
            accent="info"
          />
          <KPICard
            label="Paid (MTD)"
            value={isLoading ? '…' : fmtAmt(kpis.total_paid_this_month)}
            sub="month-to-date"
            accent="success"
          />
          <KPICard
            label="Avg Payment"
            value={isLoading ? '…' : fmtAmt(kpis.average_payment_amount)}
            sub={`${kpis.interpreters_pending_payment ?? 0} interpreters pending`}
            accent="navy"
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tab
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {tab}
            </button>
          ))}
          <div className="ml-auto pb-1 flex items-center">
            <Button variant="ghost" size="sm" className="h-7 px-2" onClick={refreshAll} disabled={isLoading || stubsLoading || paymentsLoading}>
              <RefreshCw className={cn('w-3.5 h-3.5', (isLoading || stubsLoading || paymentsLoading) && 'animate-spin')} />
            </Button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-md bg-danger/10 border border-danger/20 text-danger text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            Failed to load payroll data.
            <button className="underline ml-1" onClick={refreshAll}>Retry</button>
          </div>
        )}

        {/* ============================================================== */}
        {/* PAY STUBS TAB                                                   */}
        {/* ============================================================== */}
        {activeTab === 'Pay Stubs' && (
          <div className="flex flex-col gap-3">
            {/* Filter bar */}
            <div className="flex gap-2 items-center">
              <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                <Input
                  placeholder="Search by name or doc #…"
                  value={stubSearchInput}
                  onChange={e => onStubSearchChange(e.target.value)}
                  className="pl-8 h-8 text-sm"
                />
              </div>
              <span className="text-xs text-muted-foreground ml-auto">{stubCount} stub{stubCount !== 1 ? 's' : ''}</span>
            </div>

            {/* Table */}
            <div className="rounded-md border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/50 border-b border-border text-xs text-muted-foreground">
                    <th className="text-left px-3 py-2 font-medium">Doc #</th>
                    <th className="text-left px-3 py-2 font-medium">Interpreter</th>
                    <th className="text-left px-3 py-2 font-medium">Date</th>
                    <th className="text-left px-3 py-2 font-medium">Email</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {stubsLoading ? (
                    <tr>
                      <td colSpan={5} className="text-center py-10 text-muted-foreground">
                        <Loader2 className="w-5 h-5 animate-spin inline mr-2" />Loading…
                      </td>
                    </tr>
                  ) : stubs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-10 text-muted-foreground text-sm">
                        No pay stubs found. Generate one using the buttons above.
                      </td>
                    </tr>
                  ) : stubs.map((r, i) => (
                    <tr key={r.id} className={cn('border-b border-border/50 last:border-0 transition-colors hover:bg-muted/30', i % 2 === 0 ? '' : 'bg-muted/10')}>
                      <td className="px-3 py-2">
                        <span className="font-mono font-semibold text-navy dark:text-gold text-xs">{r.document_number}</span>
                      </td>
                      <td className="px-3 py-2 font-medium">{r.interpreter_name || '—'}</td>
                      <td className="px-3 py-2 font-mono text-xs">{fmt(r.document_date)}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{r.interpreter_email || '—'}</td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1 justify-end">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 gap-1 text-[10px]"
                            onClick={() => handleDownloadPdf(r)}
                            disabled={!!actionLoading[`pdf-${r.id}`]}
                          >
                            {actionLoading[`pdf-${r.id}`]
                              ? <Loader2 className="w-3 h-3 animate-spin" />
                              : <FileText className="w-3 h-3" />}
                            PDF
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 gap-1 text-[10px]"
                            onClick={() => handleSendStub(r)}
                            disabled={!!actionLoading[`send-${r.id}`]}
                          >
                            {actionLoading[`send-${r.id}`]
                              ? <Loader2 className="w-3 h-3 animate-spin" />
                              : <Send className="w-3 h-3" />}
                            Send
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={stubPage} count={stubCount} pageSize={PAGE_SIZE} onChange={setStubPage} />
          </div>
        )}

        {/* ============================================================== */}
        {/* PAYMENTS TAB                                                    */}
        {/* ============================================================== */}
        {activeTab === 'Payments' && (
          <div className="flex flex-col gap-3">
            {/* Filter bar */}
            <div className="flex gap-2 items-center flex-wrap">
              <div className="relative flex-1 min-w-[180px] max-w-xs">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                <Input
                  placeholder="Search by name or ref #…"
                  value={paySearchInput}
                  onChange={e => onPaySearchChange(e.target.value)}
                  className="pl-8 h-8 text-sm"
                />
              </div>
              <div className="flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5 text-muted-foreground" />
                <select
                  value={payStatus}
                  onChange={e => { setPayStatus(e.target.value); setPayPage(1); }}
                  className="h-8 text-sm rounded-md border border-border bg-background px-2 pr-7 focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="">All statuses</option>
                  {PAYMENT_STATUSES.filter(Boolean).map(s => (
                    <option key={s} value={s}>{s.charAt(0) + s.slice(1).toLowerCase()}</option>
                  ))}
                </select>
              </div>
              <span className="text-xs text-muted-foreground ml-auto">{payCount} payment{payCount !== 1 ? 's' : ''}</span>
            </div>

            {/* Bulk action bar */}
            {selectedPayIds.size > 0 && (
              <div className="flex items-center gap-3 px-3 py-2 rounded-md bg-primary/5 border border-primary/20 text-sm">
                <span className="font-medium text-primary">{selectedPayIds.size} selected</span>
                <Button
                  size="sm"
                  className="h-7 px-3 gap-1.5 bg-navy hover:bg-navy-light text-white text-xs"
                  onClick={handleBulkGenerate}
                  disabled={bulkGenerating}
                >
                  {bulkGenerating
                    ? <Loader2 className="w-3 h-3 animate-spin" />
                    : <FileText className="w-3 h-3" />}
                  Generate Pay Stub{selectedPayIds.size !== 1 ? 's' : ''}
                </Button>
                <button
                  className="ml-auto text-xs text-muted-foreground hover:text-foreground"
                  onClick={() => setSelectedPayIds(new Set())}
                >
                  Clear selection
                </button>
              </div>
            )}

            {/* Table */}
            <div className="rounded-md border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/50 border-b border-border text-xs text-muted-foreground">
                    <th className="px-3 py-2 w-8">
                      <div
                        onClick={toggleAllPay}
                        className={cn('w-4 h-4 rounded border flex items-center justify-center cursor-pointer transition-colors',
                          allPaySelected ? 'bg-primary border-primary' : 'border-border bg-background hover:border-primary/50')}
                      >
                        {allPaySelected && <Check className="w-3 h-3 text-primary-foreground" />}
                      </div>
                    </th>
                    <th className="text-left px-3 py-2 font-medium">Ref #</th>
                    <th className="text-left px-3 py-2 font-medium">Interpreter</th>
                    <th className="text-left px-3 py-2 font-medium">Amount</th>
                    <th className="text-left px-3 py-2 font-medium">Assignment</th>
                    <th className="text-left px-3 py-2 font-medium">Date</th>
                    <th className="text-left px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {paymentsLoading ? (
                    <tr>
                      <td colSpan={8} className="text-center py-10 text-muted-foreground">
                        <Loader2 className="w-5 h-5 animate-spin inline mr-2" />Loading…
                      </td>
                    </tr>
                  ) : payments.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="text-center py-10 text-muted-foreground text-sm">
                        No payments found.
                      </td>
                    </tr>
                  ) : payments.map((r, i) => {
                    const ai = r.assignment_info;
                    const selected = selectedPayIds.has(r.id);
                    return (
                      <tr
                        key={r.id}
                        className={cn(
                          'border-b border-border/50 last:border-0 transition-colors hover:bg-muted/30',
                          selected && 'bg-primary/5',
                          i % 2 === 0 ? '' : 'bg-muted/10',
                        )}
                      >
                        <td className="px-3 py-2">
                          <div
                            onClick={() => togglePaySel(r.id)}
                            className={cn('w-4 h-4 rounded border flex items-center justify-center cursor-pointer transition-colors',
                              selected ? 'bg-primary border-primary' : 'border-border hover:border-primary/50')}
                          >
                            {selected && <Check className="w-3 h-3 text-primary-foreground" />}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <span className="font-mono font-semibold text-navy dark:text-gold text-xs">{r.reference_number}</span>
                        </td>
                        <td className="px-3 py-2 font-medium">{r.interpreter_name || '—'}</td>
                        <td className="px-3 py-2">
                          <div className="font-mono font-semibold">{fmtAmt(r.amount)}</div>
                          <div className="text-[10px] text-muted-foreground">{r.payment_method || '—'}</div>
                        </td>
                        <td className="px-3 py-2">
                          {ai ? (
                            <div>
                              <div className="text-xs font-medium">{ai.city}{ai.state ? `, ${ai.state}` : ''}</div>
                              <div className="text-[10px] text-muted-foreground">
                                {ai.source_language}{ai.target_language ? ` → ${ai.target_language}` : ''}
                              </div>
                              {ai.rate && (
                                <div className="text-[10px] text-muted-foreground font-mono">${parseFloat(ai.rate).toFixed(2)}/hr</div>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs">{fmt(r.scheduled_date)}</td>
                        <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
                        <td className="px-3 py-2">
                          <div className="flex gap-1 justify-end">
                            {r.status === 'PENDING' && (
                              <Button size="sm"
                                className="h-7 px-2 gap-1 text-[10px] bg-warning/90 hover:bg-warning text-white"
                                onClick={() => handleProcessPayment(r)}
                                disabled={!!actionLoading[`proc-${r.id}`]}>
                                {actionLoading[`proc-${r.id}`]
                                  ? <Loader2 className="w-3 h-3 animate-spin" />
                                  : <Check className="w-3 h-3" />}
                                Process
                              </Button>
                            )}
                            {r.status === 'PROCESSING' && (
                              <Button size="sm"
                                className="h-7 px-2 gap-1 text-[10px] bg-success hover:bg-success/90 text-white"
                                onClick={() => handleCompletePayment(r)}
                                disabled={!!actionLoading[`complete-${r.id}`]}>
                                {actionLoading[`complete-${r.id}`]
                                  ? <Loader2 className="w-3 h-3 animate-spin" />
                                  : <Check className="w-3 h-3" />}
                                Mark Complete
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <Pagination page={payPage} count={payCount} pageSize={PAGE_SIZE} onChange={setPayPage} />
          </div>
        )}
      </div>

      <PaymentStubModal
        isOpen={stubModal}
        onClose={() => setStubModal(false)}
        onSuccess={() => { setStubModal(false); fetchStubs(stubPage, stubSearch); refresh(); }}
      />
      <BatchStubModal
        isOpen={batchModal}
        onClose={() => setBatchModal(false)}
        onSuccess={() => { setBatchModal(false); fetchStubs(stubPage, stubSearch); refresh(); }}
      />
      <TaxSummaryModal
        isOpen={taxModal}
        onClose={() => setTaxModal(false)}
      />
      <ManualStubModal
        isOpen={manualModal}
        onClose={() => setManualModal(false)}
        onSuccess={() => { setManualModal(false); fetchStubs(stubPage, stubSearch); refresh(); }}
      />
    </>
  );
};

export default PayrollModule;
