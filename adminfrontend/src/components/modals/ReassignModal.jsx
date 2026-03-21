// JHBridge — Reassign Interpreter Modal
import { useState, useEffect, useMemo } from 'react';
import { Modal } from '@/components/shared/Modal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { showToast } from '@/components/shared/Toast';
import { dispatchService } from '@/services/dispatchService';
import { Search, Loader2, Check, Star, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

export const ReassignModal = ({ isOpen, assignment, onClose, onSuccess }) => {
  const [interpreters, setInterpreters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    if (!isOpen || !assignment) return;
    setLoading(true);
    setSelectedId(null);
    setSearch('');
    const params = {};
    if (assignment.source_language?.id) params.source_language = assignment.source_language.id;
    if (assignment.target_language?.id) params.target_language = assignment.target_language.id;
    if (assignment.start_time) params.date = assignment.start_time.slice(0, 10);
    if (assignment.city) params.city = assignment.city;

    dispatchService.getAvailableInterpreters(params)
      .then(res => setInterpreters(res.data?.results || res.data || []))
      .catch(() => showToast.error('Failed to load interpreters'))
      .finally(() => setLoading(false));
  }, [isOpen, assignment]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return interpreters.filter(i => {
      const name = `${i.first_name || ''} ${i.last_name || ''}`.toLowerCase();
      return name.includes(q) || (i.city || '').toLowerCase().includes(q);
    });
  }, [interpreters, search]);

  const handleReassign = async () => {
    if (!selectedId) return;
    setSaving(true);
    try {
      await dispatchService.reassignInterpreter(assignment.id, selectedId);
      const selected = interpreters.find(i => i.id === selectedId);
      const name = `${selected?.first_name || ''} ${selected?.last_name || ''}`.trim();
      showToast.success(`Mission #${assignment.id} reassigned to ${name}`);
      onSuccess?.();
    } catch (err) {
      showToast.error(err?.response?.data?.detail || 'Failed to reassign');
    } finally {
      setSaving(false);
    }
  };

  const currentInterpId = assignment?.interpreter_detail?.id;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Reassign Mission #${assignment?.id}`}
      subtitle={`${assignment?.source_language?.name} → ${assignment?.target_language?.name} · ${assignment?.city || ''}`}
      size="md"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button
            className="bg-navy hover:bg-navy-light"
            onClick={handleReassign}
            disabled={saving || !selectedId || selectedId === currentInterpId}>
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />}
            {saving ? 'Reassigning…' : 'Confirm Reassignment'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {/* Current interpreter info */}
        {assignment?.interpreter_detail && (
          <div className="p-3 rounded-md bg-warning/5 border border-warning/20 text-sm">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0" />
              <span>
                Currently assigned: <strong>{assignment.interpreter_detail.first_name} {assignment.interpreter_detail.last_name}</strong>.
                They will be notified of the change.
              </span>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            placeholder="Search by name or city…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-8 h-8 text-sm"
          />
        </div>

        {/* List */}
        <div className="border border-border rounded-md overflow-hidden max-h-72 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading…
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-8 text-sm text-muted-foreground">
              No available interpreters found for these criteria.
            </div>
          ) : filtered.map(i => {
            const name = `${i.first_name || ''} ${i.last_name || ''}`.trim() || i.user_email;
            const isSelected = i.id === selectedId;
            const isCurrent = i.id === currentInterpId;
            const langs = i.languages?.map(l => l.name || l).join(', ') || '';

            return (
              <button key={i.id} type="button"
                onClick={() => !isCurrent && setSelectedId(i.id)}
                disabled={isCurrent}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2.5 border-b border-border/50 last:border-0 text-left transition-colors',
                  isCurrent ? 'opacity-50 cursor-not-allowed bg-muted/30' :
                  isSelected ? 'bg-primary/5 hover:bg-primary/10' : 'hover:bg-muted/40',
                )}>
                {/* Checkbox */}
                <div className={cn('w-4 h-4 rounded-full border flex items-center justify-center flex-shrink-0 transition-colors',
                  isSelected ? 'bg-primary border-primary' : isCurrent ? 'border-border' : 'border-border hover:border-primary/50')}>
                  {isSelected && <Check className="w-3 h-3 text-primary-foreground" />}
                </div>

                {/* Avatar */}
                <div className="w-9 h-9 rounded-full bg-navy text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
                  {name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm truncate">{name}</span>
                    {isCurrent && (
                      <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">Current</span>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground truncate">{langs}</div>
                  <div className="text-[11px] text-muted-foreground">
                    {i.city}{i.state ? `, ${i.state}` : ''}
                    {i.radius_of_service ? ` · ${i.radius_of_service}mi` : ''}
                  </div>
                </div>

                {/* Rating + rate */}
                <div className="text-right flex-shrink-0">
                  {i.avg_rating != null && (
                    <div className="flex items-center gap-0.5 text-gold justify-end">
                      <Star className="w-3 h-3 fill-gold" />
                      <span className="text-xs font-mono">{parseFloat(i.avg_rating).toFixed(1)}</span>
                    </div>
                  )}
                  {i.hourly_rate && (
                    <div className="text-[11px] text-muted-foreground font-mono">${i.hourly_rate}/hr</div>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {selectedId && selectedId !== currentInterpId && (
          <div className="text-xs text-muted-foreground text-center">
            The new interpreter will receive an email with accept/decline links.
          </div>
        )}
      </div>
    </Modal>
  );
};

export default ReassignModal;
