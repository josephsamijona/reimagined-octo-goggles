// JHBridge — Earnings / Tax Summary Modal
import { useState, useEffect } from 'react';
import { Modal } from '@/components/shared/Modal';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { showToast } from '@/components/shared/Toast';
import { interpreterService } from '@/services/interpreterService';
import { payrollService } from '@/services/payrollService';
import {
  User, Calendar, Loader2, AlertCircle, Download, Send, FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = [currentYear, currentYear - 1, currentYear - 2];

export const TaxSummaryModal = ({ isOpen, onClose }) => {
  const [interpreters, setInterpreters]     = useState([]);
  const [loadingInterp, setLoadingInterp]   = useState(false);
  const [selectedId, setSelectedId]         = useState('');
  const [mode, setMode]                     = useState('year');   // 'year' | 'custom'
  const [year, setYear]                     = useState(String(currentYear));
  const [periodStart, setPeriodStart]       = useState('');
  const [periodEnd, setPeriodEnd]           = useState('');
  const [summary, setSummary]               = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [summaryError, setSummaryError]     = useState(null);
  const [downloading, setDownloading]       = useState(false);
  const [sending, setSending]               = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setLoadingInterp(true);
    interpreterService.getInterpreters({ page_size: 200, ordering: 'user__last_name' })
      .then(data => setInterpreters(data.results || []))
      .catch(() => showToast.error('Failed to load interpreters'))
      .finally(() => setLoadingInterp(false));
  }, [isOpen]);

  // Fetch summary whenever params change
  useEffect(() => {
    if (!isOpen || !selectedId) { setSummary(null); return; }
    if (mode === 'custom' && (!periodStart || !periodEnd)) { setSummary(null); return; }
    let cancelled = false;
    setLoadingSummary(true);
    setSummaryError(null);
    const params = mode === 'year'
      ? { interpreter_id: selectedId, year }
      : { interpreter_id: selectedId, period_start: periodStart, period_end: periodEnd };
    payrollService.getEarningsSummary(params)
      .then(res => { if (!cancelled) setSummary(res.data); })
      .catch(() => { if (!cancelled) setSummaryError('Failed to load earnings data'); })
      .finally(() => { if (!cancelled) setLoadingSummary(false); });
    return () => { cancelled = true; };
  }, [isOpen, selectedId, mode, year, periodStart, periodEnd]);

  const getParams = () => mode === 'year'
    ? { interpreter_id: selectedId, year }
    : { interpreter_id: selectedId, period_start: periodStart, period_end: periodEnd };

  const handleDownload = async () => {
    if (!selectedId) return;
    setDownloading(true);
    try {
      await payrollService.downloadEarningsSummaryPdf(getParams());
    } catch {
      showToast.error('Failed to download PDF');
    } finally {
      setDownloading(false);
    }
  };

  const handleSend = async () => {
    if (!selectedId) return;
    setSending(true);
    try {
      await payrollService.sendEarningsSummary(getParams());
      showToast.success(`Earnings summary sent to ${summary?.interpreter_email}`);
    } catch {
      showToast.error('Failed to send earnings summary');
    } finally {
      setSending(false);
    }
  };

  const handleClose = () => {
    if (downloading || sending) return;
    setSelectedId(''); setSummary(null); setMode('year'); setYear(String(currentYear));
    setPeriodStart(''); setPeriodEnd('');
    onClose();
  };

  const fmtAmt = (v) => v ? `$${parseFloat(v).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Earnings Summary"
      subtitle="Generate annual earnings report for tax purposes" size="lg">
      <div className="space-y-5">

        {/* Interpreter */}
        <div>
          <Label className="flex items-center gap-1.5 mb-1.5">
            <User className="w-3.5 h-3.5" /> Interpreter *
          </Label>
          {loadingInterp ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading…
            </div>
          ) : (
            <select value={selectedId} onChange={e => { setSelectedId(e.target.value); setSummary(null); }}
              className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm">
              <option value="">Select interpreter…</option>
              {interpreters.map(i => (
                <option key={i.id} value={i.id}>
                  {`${i.first_name || ''} ${i.last_name || ''}`.trim() || i.user_email} — {i.city}, {i.state}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Period mode toggle */}
        <div>
          <Label className="flex items-center gap-1.5 mb-2">
            <Calendar className="w-3.5 h-3.5" /> Period
          </Label>
          <div className="flex gap-1 mb-3">
            {['year', 'custom'].map(m => (
              <button key={m} type="button" onClick={() => setMode(m)}
                className={cn('px-3 py-1.5 text-xs rounded border transition-colors',
                  mode === m ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:bg-muted')}>
                {m === 'year' ? 'Full Year' : 'Custom Range'}
              </button>
            ))}
          </div>

          {mode === 'year' && (
            <div className="flex gap-2">
              {YEAR_OPTIONS.map(y => (
                <button key={y} type="button" onClick={() => setYear(String(y))}
                  className={cn('flex-1 py-2 text-sm rounded border font-mono transition-colors',
                    year === String(y) ? 'bg-navy text-white border-navy' : 'border-border text-muted-foreground hover:bg-muted')}>
                  {y}
                </button>
              ))}
            </div>
          )}

          {mode === 'custom' && (
            <div className="flex gap-2 items-center">
              <Input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} className="flex-1" />
              <span className="text-muted-foreground text-xs">to</span>
              <Input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} className="flex-1" />
            </div>
          )}
        </div>

        {/* Summary preview */}
        {selectedId && (
          <div className="rounded-md border border-border bg-muted/20 overflow-hidden">
            {loadingSummary && (
              <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading earnings data…
              </div>
            )}
            {summaryError && !loadingSummary && (
              <div className="flex items-center gap-2 p-4 text-sm text-danger">
                <AlertCircle className="w-4 h-4" /> {summaryError}
              </div>
            )}
            {summary && !loadingSummary && (
              <>
                {/* Header */}
                <div className="bg-navy/5 border-b border-border px-4 py-3 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-sm">{summary.interpreter_name}</div>
                    <div className="text-xs text-muted-foreground">{summary.interpreter_email}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-muted-foreground">{summary.period_label}</div>
                    <div className="text-xs">{summary.total_assignments} assignment{summary.total_assignments !== 1 ? 's' : ''}</div>
                  </div>
                </div>

                {/* Assignment table */}
                {summary.assignments?.length > 0 ? (
                  <div className="max-h-48 overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-border bg-muted/40">
                          <th className="text-left px-3 py-1.5 font-medium text-muted-foreground">Date</th>
                          <th className="text-left px-3 py-1.5 font-medium text-muted-foreground">Client</th>
                          <th className="text-left px-3 py-1.5 font-medium text-muted-foreground">Languages</th>
                          <th className="text-right px-3 py-1.5 font-medium text-muted-foreground">Hrs</th>
                          <th className="text-right px-3 py-1.5 font-medium text-muted-foreground">Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {summary.assignments.map(a => (
                          <tr key={a.id} className="border-b border-border/50 hover:bg-muted/20">
                            <td className="px-3 py-1.5 font-mono">{a.date}</td>
                            <td className="px-3 py-1.5 max-w-[120px] truncate">{a.client}</td>
                            <td className="px-3 py-1.5 text-muted-foreground">
                              {a.source_language} → {a.target_language}
                            </td>
                            <td className="px-3 py-1.5 text-right font-mono">{parseFloat(a.duration).toFixed(1)}</td>
                            <td className="px-3 py-1.5 text-right font-mono font-medium">{fmtAmt(a.amount)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-4 text-sm text-muted-foreground text-center">
                    No completed assignments found for this period.
                  </div>
                )}

                {/* Total */}
                {summary.assignments?.length > 0 && (
                  <div className="flex justify-between items-center px-4 py-3 border-t border-border bg-navy/5">
                    <span className="text-sm font-semibold">Total Earnings</span>
                    <span className="text-xl font-bold font-mono">{fmtAmt(summary.total_earnings)}</span>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          <Button variant="outline" className="flex-1" onClick={handleClose} disabled={downloading || sending}>
            Close
          </Button>
          <Button
            variant="outline"
            className="flex-1 gap-1.5"
            onClick={handleDownload}
            disabled={downloading || !summary || summary.total_assignments === 0}>
            {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Download PDF
          </Button>
          <Button
            className="flex-1 gap-1.5 bg-navy hover:bg-navy-light text-white"
            onClick={handleSend}
            disabled={sending || !summary || summary.total_assignments === 0}>
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Send to Interpreter
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default TaxSummaryModal;
