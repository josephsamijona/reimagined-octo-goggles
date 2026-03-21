// JHBridge — Mission Detail Modal — Real API
import { useState, useEffect } from 'react';
import { Modal } from '@/components/shared/Modal';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { StatusBadge } from '@/components/shared/UIComponents';
import { showToast } from '@/components/shared/Toast';
import { dispatchService } from '@/services/dispatchService';
import { ReassignModal } from '@/components/modals/ReassignModal';
import {
  Edit, CheckCircle, XCircle, Bell, MapPin, Clock,
  Calendar, Phone, Mail, Star, Building2, User,
  RefreshCw, FileText, Play, AlertTriangle, Copy,
  MessageSquare, ChevronRight, Loader2, DollarSign,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const fmt = (v) => v ? new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
const fmtDt = (v) => v ? new Date(v).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
const fmtAmt = (v) => v != null ? `$${parseFloat(v).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—';

// Status flow pill navigator
const StatusFlow = ({ status }) => {
  const FLOW = ['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED'];
  const COLORS = {
    PENDING: 'bg-[#FFA500]',
    CONFIRMED: 'bg-[#3B82F6]',
    IN_PROGRESS: 'bg-[#8B5CF6]',
    COMPLETED: 'bg-[#10B981]',
    CANCELLED: 'bg-[#EF4444]',
    NO_SHOW: 'bg-[#6B7280]',
  };
  if (status === 'CANCELLED' || status === 'NO_SHOW') {
    return (
      <span className={cn('inline-flex items-center px-3 py-1 rounded-full text-white text-xs font-semibold', COLORS[status])}>
        {status.replace('_', ' ')}
      </span>
    );
  }
  const idx = FLOW.indexOf(status);
  return (
    <div className="flex items-center gap-0">
      {FLOW.map((s, i) => (
        <div key={s} className="flex items-center">
          <div className={cn('flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold',
            i <= idx ? `${COLORS[s]} text-white` : 'bg-muted text-muted-foreground')}>
            {i < idx && <CheckCircle className="w-3 h-3" />}
            {s.replace('_', ' ')}
          </div>
          {i < FLOW.length - 1 && (
            <ChevronRight className={cn('w-3.5 h-3.5 mx-0.5', i < idx ? 'text-muted-foreground' : 'text-muted-foreground/40')} />
          )}
        </div>
      ))}
    </div>
  );
};

export const MissionDetailModal = ({ isOpen, assignmentId, onClose, onEdit, onRefresh }) => {
  const [assignment, setAssignment] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [loadingData, setLoadingData] = useState(false);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [confirmDialog, setConfirmDialog] = useState({ open: false, type: null });
  const [noteText, setNoteText] = useState('');
  const [addingNote, setAddingNote] = useState(false);
  const [showNoteInput, setShowNoteInput] = useState(false);
  const [reassignOpen, setReassignOpen] = useState(false);

  const setAL = (key, val) => setActionLoading(prev => ({ ...prev, [key]: val }));

  // Load assignment details
  useEffect(() => {
    if (!isOpen || !assignmentId) return;
    setLoadingData(true);
    setAssignment(null);
    dispatchService.getAssignment(assignmentId)
      .then(res => setAssignment(res.data))
      .catch(() => showToast.error('Failed to load mission details'))
      .finally(() => setLoadingData(false));
  }, [isOpen, assignmentId]);

  // Load timeline
  useEffect(() => {
    if (!isOpen || !assignmentId) return;
    setLoadingTimeline(true);
    dispatchService.getTimeline(assignmentId)
      .then(res => setTimeline(res.data || []))
      .catch(() => setTimeline([]))
      .finally(() => setLoadingTimeline(false));
  }, [isOpen, assignmentId]);

  if (!isOpen) return null;

  const a = assignment;
  const interp = a?.interpreter_detail;
  const client = a?.client_detail;

  // Lifecycle permissions
  const canConfirm = a?.status === 'PENDING';
  const canStart = a?.status === 'CONFIRMED';
  const canComplete = ['CONFIRMED', 'IN_PROGRESS'].includes(a?.status);
  const canCancel = ['PENDING', 'CONFIRMED'].includes(a?.status);
  const canNoShow = ['CONFIRMED', 'IN_PROGRESS'].includes(a?.status);
  const isDone = ['COMPLETED', 'CANCELLED', 'NO_SHOW'].includes(a?.status);

  const doAction = async (type) => {
    setAL(type, true);
    try {
      if (type === 'confirm') {
        await dispatchService.confirmAssignment(a.id);
        showToast.success('Mission confirmed');
      } else if (type === 'start') {
        await dispatchService.startAssignment(a.id);
        showToast.success('Mission started');
      } else if (type === 'complete') {
        await dispatchService.completeAssignment(a.id);
        showToast.success('Mission completed');
      } else if (type === 'cancel') {
        await dispatchService.cancelAssignment(a.id);
        showToast.warning('Mission cancelled');
      } else if (type === 'no_show') {
        await dispatchService.noShowAssignment(a.id);
        showToast.warning('Marked as no-show');
      } else if (type === 'reminder') {
        await dispatchService.sendReminder(a.id);
        showToast.success('Reminder sent');
      } else if (type === 'duplicate') {
        const res = await dispatchService.duplicateAssignment(a.id);
        showToast.success(`Mission duplicated → #${res.data.id}`);
        onRefresh?.();
        onClose();
        return;
      }
      // Reload
      const res = await dispatchService.getAssignment(a.id);
      setAssignment(res.data);
      onRefresh?.();
    } catch (err) {
      showToast.error(err?.response?.data?.detail || `Failed to ${type} mission`);
    } finally {
      setAL(type, false);
      setConfirmDialog({ open: false, type: null });
    }
  };

  const handleAddNote = async () => {
    if (!noteText.trim()) return;
    setAddingNote(true);
    try {
      await dispatchService.addNote(a.id, noteText);
      setNoteText('');
      setShowNoteInput(false);
      // Reload timeline
      const [newA, newT] = await Promise.all([
        dispatchService.getAssignment(a.id),
        dispatchService.getTimeline(a.id),
      ]);
      setAssignment(newA.data);
      setTimeline(newT.data || []);
    } catch {
      showToast.error('Failed to add note');
    } finally {
      setAddingNote(false);
    }
  };

  const durationHours = a?.start_time && a?.end_time
    ? ((new Date(a.end_time) - new Date(a.start_time)) / 3600000).toFixed(1)
    : null;

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title={a ? `Mission #${a.id}` : 'Loading…'}
        size="lg"
        footer={
          a && (
            <div className="flex items-center justify-between w-full flex-wrap gap-2">
              <div className="flex gap-2 flex-wrap">
                {canConfirm && (
                  <Button variant="outline" size="sm" className="gap-1.5 text-success border-success/30 hover:bg-success/10"
                    onClick={() => setConfirmDialog({ open: true, type: 'confirm' })}
                    disabled={!!actionLoading.confirm}>
                    {actionLoading.confirm ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                    Confirm
                  </Button>
                )}
                {canStart && (
                  <Button variant="outline" size="sm" className="gap-1.5 text-purple-500 border-purple-500/30 hover:bg-purple-500/10"
                    onClick={() => doAction('start')} disabled={!!actionLoading.start}>
                    {actionLoading.start ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    Start
                  </Button>
                )}
                {canComplete && (
                  <Button variant="outline" size="sm" className="gap-1.5 text-success border-success/30 hover:bg-success/10"
                    onClick={() => setConfirmDialog({ open: true, type: 'complete' })}
                    disabled={!!actionLoading.complete}>
                    <CheckCircle className="w-4 h-4" /> Complete
                  </Button>
                )}
                {canCancel && (
                  <Button variant="outline" size="sm" className="gap-1.5 text-danger border-danger/30 hover:bg-danger/10"
                    onClick={() => setConfirmDialog({ open: true, type: 'cancel' })}
                    disabled={!!actionLoading.cancel}>
                    <XCircle className="w-4 h-4" /> Cancel
                  </Button>
                )}
                {canNoShow && (
                  <Button variant="outline" size="sm" className="gap-1.5 text-warning border-warning/30 hover:bg-warning/10"
                    onClick={() => setConfirmDialog({ open: true, type: 'no_show' })}
                    disabled={!!actionLoading.no_show}>
                    <AlertTriangle className="w-4 h-4" /> No-Show
                  </Button>
                )}
              </div>
              <div className="flex gap-2 flex-wrap">
                {interp && (
                  <Button variant="outline" size="sm" className="gap-1.5"
                    onClick={() => doAction('reminder')} disabled={!!actionLoading.reminder || isDone}>
                    {actionLoading.reminder ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bell className="w-4 h-4" />}
                    Reminder
                  </Button>
                )}
                {isDone && (
                  <Button variant="outline" size="sm" className="gap-1.5"
                    onClick={() => doAction('duplicate')} disabled={!!actionLoading.duplicate}>
                    {actionLoading.duplicate ? <Loader2 className="w-4 h-4 animate-spin" /> : <Copy className="w-4 h-4" />}
                    Duplicate
                  </Button>
                )}
                <Button size="sm" className="gap-1.5 bg-navy hover:bg-navy-light"
                  onClick={() => onEdit?.(a)}>
                  <Edit className="w-4 h-4" /> Edit
                </Button>
              </div>
            </div>
          )
        }
      >
        {/* Loading state */}
        {loadingData && (
          <div className="flex items-center justify-center py-16 text-muted-foreground">
            <Loader2 className="w-6 h-6 animate-spin mr-2" /> Loading mission…
          </div>
        )}

        {a && (
          <div className="space-y-5">
            {/* Status flow */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <StatusFlow status={a.status} />
              <span className="text-xs text-muted-foreground font-mono">
                Created {fmt(a.created_at)}
              </span>
            </div>

            {/* Core details */}
            <div className="bg-muted/30 rounded-lg p-4">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Mission Details</h4>
              <div className="grid grid-cols-2 gap-x-6 gap-y-2.5 text-sm">
                <div className="flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                  <span className="text-muted-foreground">Type:</span>
                  <span className="font-medium">{a.service_type?.name || '—'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Languages:</span>
                  <span className="font-mono font-medium text-xs">
                    {a.source_language?.name} → {a.target_language?.name}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                  <span className="text-muted-foreground">Start:</span>
                  <span className="font-medium font-mono text-xs">{fmtDt(a.start_time_local || a.start_time)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                  <span className="text-muted-foreground">End:</span>
                  <span className="font-medium font-mono text-xs">{fmtDt(a.end_time_local || a.end_time)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                  <span className="text-muted-foreground">Location:</span>
                  <span className="font-medium">{a.location || a.city}{a.state ? `, ${a.state}` : ''} {a.zip_code || ''}</span>
                </div>
                {durationHours && (
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Duration:</span>
                    <span className="font-mono font-medium">{durationHours}h</span>
                  </div>
                )}
                {a.special_requirements && (
                  <div className="col-span-2 flex items-start gap-2">
                    <span className="text-muted-foreground flex-shrink-0">Requirements:</span>
                    <span className="text-sm">{a.special_requirements}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Interpreter */}
            <div className="bg-muted/30 rounded-lg p-4">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Interpreter</h4>
              {interp ? (
                <div className="flex items-start gap-4">
                  <div className="w-11 h-11 rounded-full bg-navy text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                    {`${interp.first_name?.[0] || ''}${interp.last_name?.[0] || ''}`.toUpperCase() || '?'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold">{interp.first_name} {interp.last_name}</span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {interp.city}{interp.state ? `, ${interp.state}` : ''}
                      {interp.radius_of_service ? ` · ${interp.radius_of_service}mi radius` : ''}
                    </div>
                    {interp.languages?.length > 0 && (
                      <div className="text-xs text-muted-foreground mt-0.5">{interp.languages.join(', ')}</div>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-sm">
                      {interp.phone && (
                        <a href={`tel:${interp.phone}`} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
                          <Phone className="w-3.5 h-3.5" />{interp.phone}
                        </a>
                      )}
                      {interp.email && (
                        <a href={`mailto:${interp.email}`} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
                          <Mail className="w-3.5 h-3.5" />Email
                        </a>
                      )}
                    </div>
                  </div>
                  {!isDone && (
                    <Button variant="outline" size="sm" className="flex-shrink-0 gap-1"
                      onClick={() => setReassignOpen(true)}>
                      <RefreshCw className="w-3.5 h-3.5" /> Reassign
                    </Button>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-between p-3 bg-danger/10 rounded border border-danger/30">
                  <div className="flex items-center gap-2 text-danger">
                    <User className="w-4 h-4" />
                    <span className="font-medium text-sm">No interpreter assigned</span>
                  </div>
                  <Button size="sm" variant="outline" className="text-danger border-danger/30 gap-1"
                    onClick={() => onEdit?.(a)}>
                    <User className="w-3.5 h-3.5" /> Assign Now
                  </Button>
                </div>
              )}
            </div>

            {/* Client */}
            <div className="bg-muted/30 rounded-lg p-4">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Client</h4>
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-gold/20 text-gold flex items-center justify-center flex-shrink-0">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="font-medium">
                    {client?.company_name || a.client_name || '—'}
                  </div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground mt-0.5">
                    {(client?.email || a.client_email) && (
                      <a href={`mailto:${client?.email || a.client_email}`}
                        className="flex items-center gap-1 hover:text-foreground">
                        <Mail className="w-3.5 h-3.5" />{client?.email || a.client_email}
                      </a>
                    )}
                    {(client?.phone || a.client_phone) && (
                      <a href={`tel:${client?.phone || a.client_phone}`}
                        className="flex items-center gap-1 hover:text-foreground">
                        <Phone className="w-3.5 h-3.5" />{client?.phone || a.client_phone}
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Financials */}
            <div className="bg-muted/30 rounded-lg p-4">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                <DollarSign className="w-3.5 h-3.5 inline mr-1" />Financials
              </h4>
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <div className="text-xs text-muted-foreground">Rate</div>
                  <div className="font-mono font-semibold">{fmtAmt(a.interpreter_rate)}/hr</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Min. Hours</div>
                  <div className="font-mono font-semibold">{a.minimum_hours || 2}h</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Total Payment</div>
                  <div className="font-mono font-semibold text-navy dark:text-gold">
                    {fmtAmt(a.total_interpreter_payment)}
                  </div>
                </div>
              </div>
              {a.interpreter_payment && (
                <div className="mt-3 pt-3 border-t border-border flex items-center justify-between text-sm">
                  <div>
                    <span className="text-muted-foreground">Payment: </span>
                    <span className="font-mono text-xs">#{a.interpreter_payment.reference_number}</span>
                  </div>
                  <StatusBadge status={a.interpreter_payment.status} />
                </div>
              )}
              {a.is_paid && (
                <div className="mt-2 text-xs text-success flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" /> Marked as paid
                </div>
              )}
            </div>

            {/* Feedback (if completed) */}
            {a.status === 'COMPLETED' && (
              <div className="bg-muted/30 rounded-lg p-4">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                  Client Feedback
                </h4>
                {a.feedback ? (
                  <div>
                    <div className="flex items-center gap-1 text-gold mb-1">
                      {Array.from({ length: 5 }, (_, i) => (
                        <Star key={i} className={cn('w-4 h-4', i < a.feedback.rating ? 'fill-gold' : 'text-border')} />
                      ))}
                      <span className="text-xs text-muted-foreground ml-1">{fmt(a.feedback.created_at)}</span>
                    </div>
                    {a.feedback.comments && <p className="text-sm">{a.feedback.comments}</p>}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No feedback recorded yet.</p>
                )}
              </div>
            )}

            {/* Internal notes */}
            {a.notes && (
              <div className="bg-muted/30 rounded-lg p-4">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Internal Notes</h4>
                <p className="text-sm whitespace-pre-line">{a.notes}</p>
              </div>
            )}

            {/* Timeline */}
            <div className="bg-muted/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Timeline</h4>
                <button onClick={() => setShowNoteInput(v => !v)}
                  className="text-xs text-primary flex items-center gap-1 hover:underline">
                  <MessageSquare className="w-3 h-3" /> Add note
                </button>
              </div>

              {showNoteInput && (
                <div className="mb-3 flex gap-2">
                  <Input placeholder="Enter note…" value={noteText}
                    onChange={e => setNoteText(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleAddNote()}
                    className="text-sm h-8" />
                  <Button size="sm" className="h-8 px-3 bg-navy hover:bg-navy-light"
                    onClick={handleAddNote} disabled={addingNote || !noteText.trim()}>
                    {addingNote ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Add'}
                  </Button>
                </div>
              )}

              {loadingTimeline ? (
                <div className="text-xs text-muted-foreground flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin" /> Loading…
                </div>
              ) : (
                <div className="space-y-2">
                  {timeline.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No timeline entries.</p>
                  ) : timeline.map((item, idx) => (
                    <div key={idx} className="flex items-start gap-3 text-sm">
                      <div className="w-2 h-2 rounded-full bg-navy dark:bg-gold flex-shrink-0 mt-1.5" />
                      <div>
                        <span className="text-muted-foreground font-mono text-xs">
                          {new Date(item.time).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <span className="mx-2 text-muted-foreground">·</span>
                        <span>{item.action}</span>
                        {item.actor && <span className="text-muted-foreground text-xs"> by {item.actor}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* Confirm dialogs */}
      {['confirm', 'complete', 'cancel', 'no_show'].map(type => (
        <ConfirmDialog key={type}
          isOpen={confirmDialog.open && confirmDialog.type === type}
          onConfirm={() => doAction(type)}
          onCancel={() => setConfirmDialog({ open: false, type: null })}
          title={
            type === 'confirm' ? 'Confirm Mission?' :
            type === 'complete' ? 'Mark Complete?' :
            type === 'cancel' ? 'Cancel Mission?' : 'Record No-Show?'
          }
          message={
            type === 'confirm' ? `Confirm mission #${a?.id}? The interpreter will be notified.` :
            type === 'complete' ? `Mark mission #${a?.id} as completed?` :
            type === 'cancel' ? `Cancel mission #${a?.id}? This will notify all parties.` :
            `Record no-show for mission #${a?.id}? The interpreter's payment will be voided.`
          }
          confirmText={
            type === 'confirm' ? 'Confirm' :
            type === 'complete' ? 'Mark Complete' :
            type === 'cancel' ? 'Cancel Mission' : 'Record No-Show'
          }
          variant={type === 'cancel' || type === 'no_show' ? 'danger' : 'info'}
          loading={!!actionLoading[type]}
        />
      ))}

      {/* Reassign modal */}
      <ReassignModal
        isOpen={reassignOpen}
        assignment={a}
        onClose={() => setReassignOpen(false)}
        onSuccess={async () => {
          setReassignOpen(false);
          const res = await dispatchService.getAssignment(a.id);
          setAssignment(res.data);
          onRefresh?.();
        }}
      />
    </>
  );
};

export default MissionDetailModal;
