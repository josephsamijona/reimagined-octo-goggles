// JHBridge — Payment Stub Generation Modal (single interpreter)
import { useState, useEffect } from 'react';
import { Modal } from '@/components/shared/Modal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { showToast } from '@/components/shared/Toast';
import { interpreterService } from '@/services/interpreterService';
import { payrollService } from '@/services/payrollService';
import { User, Calendar, Loader2, Check, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

const today        = () => new Date().toISOString().slice(0, 10);
const firstOfMonth = () => { const d = new Date(); d.setDate(1); return d.toISOString().slice(0, 10); };
const firstOfYear  = () => `${new Date().getFullYear()}-01-01`;

export const PaymentStubModal = ({ isOpen, onClose, onSuccess }) => {
  const [interpreters, setInterpreters]     = useState([]);
  const [loadingInterp, setLoadingInterp]   = useState(false);
  const [selectedId, setSelectedId]         = useState('');
  const [periodStart, setPeriodStart]       = useState(firstOfMonth());
  const [periodEnd, setPeriodEnd]           = useState(today());
  const [preview, setPreview]               = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError]     = useState(null);
  const [generating, setGenerating]         = useState(false);
  const [sendAfter, setSendAfter]           = useState(false);

  // Load interpreter list on open
  useEffect(() => {
    if (!isOpen) return;
    setLoadingInterp(true);
    interpreterService.getInterpreters({ page_size: 200, ordering: 'user__last_name' })
      .then(data => setInterpreters(data.results || []))
      .catch(() => showToast.error('Failed to load interpreters'))
      .finally(() => setLoadingInterp(false));
  }, [isOpen]);

  // Preview: fetch assignment count whenever interpreter + dates change
  useEffect(() => {
    if (!isOpen || !selectedId || !periodStart || !periodEnd) { setPreview(null); return; }
    let cancelled = false;
    setLoadingPreview(true);
    setPreviewError(null);
    payrollService.getEarningsSummary({ interpreter_id: selectedId, period_start: periodStart, period_end: periodEnd })
      .then(res => { if (!cancelled) setPreview(res.data); })
      .catch(() => { if (!cancelled) setPreviewError('Could not load assignment preview'); })
      .finally(() => { if (!cancelled) setLoadingPreview(false); });
    return () => { cancelled = true; };
  }, [isOpen, selectedId, periodStart, periodEnd]);

  const handleGenerate = async () => {
    if (!selectedId) { showToast.error('Please select an interpreter'); return; }
    if (!periodStart || !periodEnd) { showToast.error('Please set a period'); return; }
    setGenerating(true);
    try {
      const res = await payrollService.batchStubs({
        interpreter_ids: [parseInt(selectedId)],
        period_start: periodStart,
        period_end: periodEnd,
      });
      const created = res.data?.[0];
      showToast.success(`Stub ${created?.document_number || ''} generated`);
      if (sendAfter && created?.id) {
        await payrollService.sendStub(created.id).catch(() => {});
        showToast.success('Stub sent to interpreter');
      }
      onSuccess?.();
    } catch {
      showToast.error('Failed to generate stub');
    } finally {
      setGenerating(false);
    }
  };

  const handleClose = () => {
    if (generating) return;
    setSelectedId(''); setPeriodStart(firstOfMonth()); setPeriodEnd(today());
    setPreview(null); setSendAfter(false);
    onClose();
  };

  const fmtAmt = (v) => v ? `$${parseFloat(v).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="New Payment Stub"
      subtitle="Generate a pay stub from completed assignments" size="md">
      <div className="space-y-5">

        {/* Interpreter selector */}
        <div>
          <Label className="flex items-center gap-1.5 mb-1.5">
            <User className="w-3.5 h-3.5" /> Interpreter *
          </Label>
          {loadingInterp ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading interpreters…
            </div>
          ) : (
            <select value={selectedId}
              onChange={e => { setSelectedId(e.target.value); setPreview(null); }}
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

        {/* Period */}
        <div>
          <Label className="flex items-center gap-1.5 mb-1.5">
            <Calendar className="w-3.5 h-3.5" /> Period *
          </Label>
          <div className="flex gap-2 items-center mb-2">
            <Input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} className="flex-1" />
            <span className="text-muted-foreground text-xs">to</span>
            <Input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} className="flex-1" />
          </div>
          <div className="flex gap-1.5">
            {[
              { label: 'This month', start: firstOfMonth(), end: today() },
              { label: 'This year',  start: firstOfYear(),  end: today() },
            ].map(({ label, start, end }) => (
              <button key={label} type="button"
                onClick={() => { setPeriodStart(start); setPeriodEnd(end); }}
                className="text-[11px] px-2 py-1 rounded border border-border text-muted-foreground hover:bg-muted transition-colors">
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Assignments preview */}
        {selectedId && (
          <div className="rounded-md border border-border bg-muted/30 p-3 min-h-[60px]">
            {loadingPreview && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Checking assignments…
              </div>
            )}
            {previewError && !loadingPreview && (
              <div className="flex items-center gap-2 text-sm text-danger">
                <AlertCircle className="w-3.5 h-3.5" /> {previewError}
              </div>
            )}
            {preview && !loadingPreview && (
              <div className="text-sm space-y-1">
                <div className="font-medium">{preview.interpreter_name}</div>
                <div className="text-muted-foreground">
                  {preview.total_assignments === 0
                    ? 'No completed assignments in this period'
                    : `${preview.total_assignments} completed assignment${preview.total_assignments !== 1 ? 's' : ''}`}
                </div>
                {preview.total_assignments > 0 && (
                  <div className="text-lg font-bold font-mono mt-1">{fmtAmt(preview.total_earnings)}</div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Send after generating */}
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <div onClick={() => setSendAfter(v => !v)}
            className={cn('w-4 h-4 rounded border flex items-center justify-center transition-colors cursor-pointer',
              sendAfter ? 'bg-primary border-primary' : 'border-border')}>
            {sendAfter && <Check className="w-3 h-3 text-primary-foreground" />}
          </div>
          <span className="text-sm">Send stub to interpreter after generating</span>
        </label>

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          <Button variant="outline" className="flex-1" onClick={handleClose} disabled={generating}>Cancel</Button>
          <Button
            className="flex-1 bg-navy hover:bg-navy-light text-white gap-1.5"
            onClick={handleGenerate}
            disabled={generating || !selectedId || !periodStart || !periodEnd || preview?.total_assignments === 0}>
            {generating && <Loader2 className="w-4 h-4 animate-spin" />}
            {generating ? 'Generating…' : 'Generate Stub'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default PaymentStubModal;
