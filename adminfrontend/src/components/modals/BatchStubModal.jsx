// JHBridge — Batch Pay Stub Generation Modal (multiple interpreters)
import { useState, useEffect, useMemo } from 'react';
import { Modal } from '@/components/shared/Modal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { showToast } from '@/components/shared/Toast';
import { interpreterService } from '@/services/interpreterService';
import { payrollService } from '@/services/payrollService';
import { Calendar, Search, Loader2, Check, CheckSquare, Square } from 'lucide-react';
import { cn } from '@/lib/utils';

const today        = () => new Date().toISOString().slice(0, 10);
const firstOfMonth = () => { const d = new Date(); d.setDate(1); return d.toISOString().slice(0, 10); };
const firstOfYear  = () => `${new Date().getFullYear()}-01-01`;

export const BatchStubModal = ({ isOpen, onClose, onSuccess }) => {
  const [interpreters, setInterpreters]   = useState([]);
  const [loadingInterp, setLoadingInterp] = useState(false);
  const [search, setSearch]               = useState('');
  const [selectedIds, setSelectedIds]     = useState(new Set());
  const [periodStart, setPeriodStart]     = useState(firstOfMonth());
  const [periodEnd, setPeriodEnd]         = useState(today());
  const [sendAfter, setSendAfter]         = useState(false);
  const [generating, setGenerating]       = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setLoadingInterp(true);
    interpreterService.getInterpreters({ page_size: 200, ordering: 'user__last_name', active: true })
      .then(data => setInterpreters(data.results || []))
      .catch(() => showToast.error('Failed to load interpreters'))
      .finally(() => setLoadingInterp(false));
  }, [isOpen]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return interpreters.filter(i => {
      const name = `${i.user?.first_name || ''} ${i.user?.last_name || ''}`.toLowerCase();
      return name.includes(q) || (i.city || '').toLowerCase().includes(q);
    });
  }, [interpreters, search]);

  const toggleOne = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === filtered.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filtered.map(i => i.id)));
    }
  };

  const handleGenerate = async () => {
    if (selectedIds.size === 0) { showToast.error('Select at least one interpreter'); return; }
    if (!periodStart || !periodEnd) { showToast.error('Please set a period'); return; }
    setGenerating(true);
    try {
      const res = await payrollService.batchStubs({
        interpreter_ids: [...selectedIds],
        period_start: periodStart,
        period_end: periodEnd,
      });
      const created = res.data || [];
      showToast.success(`${created.length} stub${created.length !== 1 ? 's' : ''} generated`);
      if (sendAfter && created.length > 0) {
        await Promise.allSettled(created.map(s => payrollService.sendStub(s.id)));
        showToast.success('Stubs sent to interpreters');
      }
      onSuccess?.();
    } catch {
      showToast.error('Failed to generate stubs');
    } finally {
      setGenerating(false);
    }
  };

  const handleClose = () => {
    if (generating) return;
    setSelectedIds(new Set()); setSearch('');
    setPeriodStart(firstOfMonth()); setPeriodEnd(today());
    setSendAfter(false);
    onClose();
  };

  const allSelected = filtered.length > 0 && selectedIds.size === filtered.length;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Batch Generate Pay Stubs"
      subtitle="Generate pay stubs for multiple interpreters at once" size="lg">
      <div className="space-y-5">

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

        {/* Interpreter multi-select */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label>Interpreters *</Label>
            {selectedIds.size > 0 && (
              <span className="text-xs text-primary font-medium">{selectedIds.size} selected</span>
            )}
          </div>

          {/* Search */}
          <div className="relative mb-2">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              placeholder="Search by name or city…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-8 h-8 text-sm"
            />
          </div>

          {loadingInterp ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading interpreters…
            </div>
          ) : (
            <div className="border border-border rounded-md overflow-hidden">
              {/* Select all header */}
              <button type="button" onClick={toggleAll}
                className="w-full flex items-center gap-2.5 px-3 py-2 bg-muted/40 hover:bg-muted/60 border-b border-border text-xs font-medium transition-colors text-left">
                <div className={cn('w-4 h-4 rounded border flex items-center justify-center',
                  allSelected ? 'bg-primary border-primary' : 'border-border bg-background')}>
                  {allSelected && <Check className="w-3 h-3 text-primary-foreground" />}
                </div>
                {allSelected ? 'Deselect all' : `Select all (${filtered.length})`}
              </button>

              {/* Interpreter list */}
              <div className="max-h-52 overflow-y-auto">
                {filtered.length === 0 ? (
                  <div className="px-3 py-4 text-sm text-muted-foreground text-center">No interpreters found</div>
                ) : filtered.map(i => {
                  const selected = selectedIds.has(i.id);
                  const name = `${i.first_name || ''} ${i.last_name || ''}`.trim() || i.user_email;
                  return (
                    <button key={i.id} type="button" onClick={() => toggleOne(i.id)}
                      className={cn('w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-muted/40 border-b border-border/50 last:border-0 text-left transition-colors',
                        selected && 'bg-primary/5')}>
                      <div className={cn('w-4 h-4 rounded border flex items-center justify-center flex-shrink-0',
                        selected ? 'bg-primary border-primary' : 'border-border')}>
                        {selected && <Check className="w-3 h-3 text-primary-foreground" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">{name}</div>
                        <div className="text-[11px] text-muted-foreground">{i.city}, {i.state}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Send after */}
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <div onClick={() => setSendAfter(v => !v)}
            className={cn('w-4 h-4 rounded border flex items-center justify-center transition-colors cursor-pointer',
              sendAfter ? 'bg-primary border-primary' : 'border-border')}>
            {sendAfter && <Check className="w-3 h-3 text-primary-foreground" />}
          </div>
          <span className="text-sm">Send each stub to interpreter after generating</span>
        </label>

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          <Button variant="outline" className="flex-1" onClick={handleClose} disabled={generating}>Cancel</Button>
          <Button
            className="flex-1 bg-navy hover:bg-navy-light text-white gap-1.5"
            onClick={handleGenerate}
            disabled={generating || selectedIds.size === 0 || !periodStart || !periodEnd}>
            {generating && <Loader2 className="w-4 h-4 animate-spin" />}
            {generating
              ? 'Generating…'
              : `Generate ${selectedIds.size > 0 ? selectedIds.size : ''} Stub${selectedIds.size !== 1 ? 's' : ''}`}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default BatchStubModal;
