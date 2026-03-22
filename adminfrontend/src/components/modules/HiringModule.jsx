// JHBridge Command Center — Hiring & Onboarding Module (live API)
import { useState, useCallback, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { SectionHeader } from '@/components/shared/UIComponents';
import { showToast } from '@/components/shared/Toast';
import { hiringService } from '@/services/hiringService';
import { cn } from '@/lib/utils';
import {
  Plus, Send, X, RefreshCw, Loader2,
  Mail, Phone, Clock, Ban, Calendar, ArrowRight, Search,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Phase metadata
// ---------------------------------------------------------------------------

const PHASE_META = {
  INVITED:           { label: 'Invited',           color: 'muted-foreground', step: 1 },
  EMAIL_OPENED:      { label: 'Email Opened',       color: 'warning',          step: 2 },
  WELCOME_VIEWED:    { label: 'Welcome Viewed',     color: 'info',             step: 3 },
  ACCOUNT_CREATED:   { label: 'Account Created',    color: 'gold',             step: 4 },
  PROFILE_COMPLETED: { label: 'Profile Completed',  color: 'navy',             step: 5 },
  CONTRACT_STARTED:  { label: 'Contract Started',   color: 'navy',             step: 6 },
  COMPLETED:         { label: 'Completed',          color: 'success',          step: 7 },
  VOIDED:            { label: 'Voided',             color: 'danger',           step: 0 },
  EXPIRED:           { label: 'Expired',            color: 'muted-foreground', step: 0 },
};

const BORDER = {
  'muted-foreground': 'border-t-muted-foreground',
  warning: 'border-t-warning', info: 'border-t-info', gold: 'border-t-gold',
  navy: 'border-t-navy', success: 'border-t-success', danger: 'border-t-red-500',
};
const TXT = {
  'muted-foreground': 'text-muted-foreground',
  warning: 'text-warning', info: 'text-info', gold: 'text-gold',
  navy: 'text-navy dark:text-gold', success: 'text-success', danger: 'text-red-500',
};
const BG = {
  'muted-foreground': 'bg-muted-foreground',
  warning: 'bg-warning', info: 'bg-info', gold: 'bg-gold',
  navy: 'bg-navy', success: 'bg-success', danger: 'bg-red-500',
};

const PIPELINE_PHASES = [
  'INVITED', 'EMAIL_OPENED', 'WELCOME_VIEWED',
  'ACCOUNT_CREATED', 'PROFILE_COMPLETED', 'CONTRACT_STARTED',
];

const TERMINAL = new Set(['COMPLETED', 'VOIDED', 'EXPIRED']);

const fmt = (v) =>
  v ? new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';

// ---------------------------------------------------------------------------
// New Invitation Modal
// ---------------------------------------------------------------------------

const NewInvitationModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', phone: '' });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const validate = () => {
    const err = {};
    if (!form.first_name.trim()) err.first_name = 'Required';
    if (!form.last_name.trim()) err.last_name = 'Required';
    if (!form.email.trim()) err.email = 'Required';
    else if (!/\S+@\S+\.\S+/.test(form.email)) err.email = 'Invalid email';
    setErrors(err);
    return Object.keys(err).length === 0;
  };

  const submit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      await hiringService.createInvitation(form);
      showToast.success('Invitation sent to ' + form.email);
      onCreated();
      onClose();
    } catch (err) {
      const msg = err?.response?.data?.email?.[0]
        || err?.response?.data?.detail
        || 'Failed to create invitation';
      showToast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-background border border-border rounded-lg shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold">New Interpreter Invitation</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            {['first_name', 'last_name'].map((k) => (
              <div key={k}>
                <label className="text-xs font-medium text-muted-foreground">
                  {k === 'first_name' ? 'First Name' : 'Last Name'}
                </label>
                <Input
                  value={form[k]}
                  onChange={set(k)}
                  className={cn('mt-1 h-8 text-sm', errors[k] && 'border-red-500')}
                  placeholder={k === 'first_name' ? 'Jane' : 'Doe'}
                />
                {errors[k] && <p className="text-[11px] text-red-500 mt-0.5">{errors[k]}</p>}
              </div>
            ))}
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Email</label>
            <Input
              type="email"
              value={form.email}
              onChange={set('email')}
              className={cn('mt-1 h-8 text-sm', errors.email && 'border-red-500')}
              placeholder="jane.doe@example.com"
            />
            {errors.email && <p className="text-[11px] text-red-500 mt-0.5">{errors.email}</p>}
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">
              Phone <span className="text-muted-foreground/60">(optional)</span>
            </label>
            <Input value={form.phone} onChange={set('phone')} className="mt-1 h-8 text-sm" placeholder="+1 (555) 000-0000" />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" size="sm" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button size="sm" onClick={submit} disabled={loading} className="bg-navy hover:bg-navy-light gap-1.5">
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
            Send Invitation
          </Button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Detail Drawer
// ---------------------------------------------------------------------------

const TIMELINE_FIELDS = [
  { label: 'Invited',           key: 'email_sent_at' },
  { label: 'Email Opened',      key: 'email_opened_at' },
  { label: 'Welcome Viewed',    key: 'welcome_viewed_at' },
  { label: 'Account Created',   key: 'account_created_at' },
  { label: 'Profile Completed', key: 'profile_completed_at' },
  { label: 'Contract Started',  key: 'contract_started_at' },
  { label: 'Completed',         key: 'completed_at' },
];

const DetailDrawer = ({ invitation, onClose, onRefresh }) => {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState('');
  const [voidReason, setVoidReason] = useState('');
  const [showVoidInput, setShowVoidInput] = useState(false);

  const fetch = useCallback(async () => {
    try {
      const r = await hiringService.getInvitation(invitation.id);
      setDetail(r.data);
    } catch {
      showToast.error('Failed to load invitation details');
    } finally {
      setLoading(false);
    }
  }, [invitation.id]);

  useEffect(() => { fetch(); }, [fetch]);

  const doAction = async (action) => {
    setActionLoading(action);
    try {
      if (action === 'resend')  await hiringService.resend(invitation.id);
      if (action === 'void')    await hiringService.void(invitation.id, voidReason);
      if (action === 'advance') await hiringService.advance(invitation.id);
      if (action === 'extend')  await hiringService.extend(invitation.id, 14);
      const msgs = { resend: 'Resent', void: 'Voided', advance: 'Advanced', extend: 'Extended +14d' };
      showToast.success(msgs[action]);
      if (action === 'void') setShowVoidInput(false);
      onRefresh();
      await fetch();
    } catch (err) {
      showToast.error(err?.response?.data?.detail || 'Failed to ' + action);
    } finally {
      setActionLoading('');
    }
  };

  const phase = PHASE_META[detail?.current_phase || invitation.current_phase] || PHASE_META.INVITED;
  const isTerminal = TERMINAL.has(detail?.current_phase || invitation.current_phase);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
      <div className="w-full max-w-lg bg-background border-l border-border shadow-xl flex flex-col h-full overflow-y-auto">
        {/* Header */}
        <div className="flex items-start justify-between p-4 border-b border-border sticky top-0 bg-background z-10">
          <div>
            <div className="font-mono text-xs text-muted-foreground">{invitation.invitation_number}</div>
            <h2 className="text-sm font-semibold mt-0.5">{invitation.first_name} {invitation.last_name}</h2>
            <span className={cn('text-[11px] font-semibold', TXT[phase.color])}>{phase.label}</span>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground mt-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : detail && (
          <div className="flex-1 p-4 space-y-5">
            {/* Contact */}
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Contact</p>
              <div className="flex items-center gap-2 text-xs">
                <Mail className="w-3.5 h-3.5 text-muted-foreground" />{detail.email}
              </div>
              {detail.phone && (
                <div className="flex items-center gap-2 text-xs">
                  <Phone className="w-3.5 h-3.5 text-muted-foreground" />{detail.phone}
                </div>
              )}
              {detail.languages?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {detail.languages.map((l) => (
                    <span key={l} className="text-[10px] bg-muted px-1.5 py-0.5 rounded font-medium">{l}</span>
                  ))}
                </div>
              )}
            </div>

            {/* Progress */}
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Progress</p>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5, 6, 7].map((s) => (
                  <div key={s} className={cn('flex-1 h-1.5 rounded-sm', s <= phase.step ? BG[phase.color] : 'bg-muted')} />
                ))}
              </div>
            </div>

            {/* Timeline */}
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Timeline</p>
              <div className="space-y-1">
                {TIMELINE_FIELDS.map(({ label, key }) => (
                  <div key={key} className="flex items-center justify-between text-xs">
                    <span className={cn('text-muted-foreground', detail[key] && 'text-foreground font-medium')}>{label}</span>
                    <span className={cn('font-mono text-[11px]', detail[key] ? 'text-success' : 'text-muted-foreground/50')}>
                      {detail[key] ? fmt(detail[key]) : '—'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Expiry */}
            <div className="flex items-center gap-2 text-xs p-2 rounded bg-muted/50 border border-border">
              <Clock className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">Expires:</span>
              <span className={cn('font-medium', detail.is_expired && 'text-red-500')}>{fmt(detail.expires_at)}</span>
            </div>

            {detail.void_reason && (
              <div className="p-2 rounded bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 text-xs">
                <span className="font-semibold text-red-600">Voided:</span> {detail.void_reason}
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        {!isTerminal && (
          <div className="p-4 border-t border-border space-y-2">
            <div className="grid grid-cols-2 gap-2">
              {[
                { action: 'resend',  label: 'Resend',      Icon: Send },
                { action: 'extend',  label: 'Extend +14d', Icon: Calendar },
                { action: 'advance', label: 'Advance',     Icon: ArrowRight },
              ].map(({ action, label, Icon }) => (
                <Button key={action} variant="outline" size="sm" className="gap-1.5 text-xs"
                  disabled={!!actionLoading} onClick={() => doAction(action)}>
                  {actionLoading === action
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <Icon className="w-3.5 h-3.5" />}
                  {label}
                </Button>
              ))}
              <Button variant="outline" size="sm" className="gap-1.5 text-xs text-red-500 border-red-200 hover:text-red-600"
                disabled={!!actionLoading} onClick={() => setShowVoidInput((v) => !v)}>
                <Ban className="w-3.5 h-3.5" /> Void
              </Button>
            </div>
            {showVoidInput && (
              <div className="space-y-2">
                <Input value={voidReason} onChange={(e) => setVoidReason(e.target.value)}
                  placeholder="Reason for voiding (optional)" className="h-8 text-xs" />
                <Button variant="destructive" size="sm" className="w-full text-xs"
                  disabled={!!actionLoading} onClick={() => doAction('void')}>
                  {actionLoading === 'void' && <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />}
                  Confirm Void
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Phase badge
// ---------------------------------------------------------------------------

const PhaseBadge = ({ phase }) => {
  const p = PHASE_META[phase] || PHASE_META.INVITED;
  return <span className={cn('text-[11px] font-semibold', TXT[p.color])}>{p.label}</span>;
};

// ---------------------------------------------------------------------------
// HiringModule
// ---------------------------------------------------------------------------

export const HiringModule = () => {
  const [pipeline, setPipeline] = useState({});
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const PAGE_SIZE = 20;

  const loadPipeline = useCallback(async () => {
    try {
      const r = await hiringService.getPipeline();
      setPipeline(r.data);
    } catch {
      showToast.error('Failed to load pipeline');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTable = useCallback(async () => {
    setTableLoading(true);
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (search) params.search = search;
      const r = await hiringService.getInvitations(params);
      const data = r.data.results ?? r.data;
      setInvitations(data);
      setTotalCount(r.data.count ?? data.length);
    } catch {
      showToast.error('Failed to load invitations');
    } finally {
      setTableLoading(false);
    }
  }, [page, search]);

  useEffect(() => { loadPipeline(); }, [loadPipeline]);
  useEffect(() => { loadTable(); }, [loadTable]);

  const refresh = () => { loadPipeline(); loadTable(); };

  const totalActive = PIPELINE_PHASES.reduce((s, ph) => s + (pipeline[ph]?.length ?? 0), 0);
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <div className="flex flex-col gap-4" data-testid="hiring-module">
      <SectionHeader
        title="Hiring & Onboarding"
        subtitle={loading ? 'Loading…' : `${totalActive} active · ${pipeline['COMPLETED']?.length ?? 0} completed`}
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={refresh}>
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
            <Button size="sm" onClick={() => setShowCreate(true)} className="gap-1.5 bg-navy hover:bg-navy-light" data-testid="new-invitation-btn">
              <Plus className="w-3.5 h-3.5" /> New Invitation
            </Button>
          </div>
        }
      />

      {/* ── Pipeline Kanban ─────────────────────────────────── */}
      {loading ? (
        <div className="flex items-center justify-center h-28 text-muted-foreground text-sm">
          <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading pipeline…
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
          {PIPELINE_PHASES.map((phase) => {
            const p = PHASE_META[phase];
            const items = pipeline[phase] ?? [];
            return (
              <Card key={phase} className={cn('shadow-sm border-t-2', BORDER[p.color])}>
                <div className="px-3 py-2 border-b border-border flex justify-between items-center">
                  <span className="text-[10px] font-semibold uppercase tracking-wider truncate">{p.label}</span>
                  <span className={cn('text-[10px] font-semibold font-mono px-1.5 py-0.5 rounded', TXT[p.color])}>
                    {items.length}
                  </span>
                </div>
                <CardContent className="p-2 flex flex-col gap-1.5 min-h-[80px]">
                  {items.map((o) => (
                    <button key={o.id} onClick={() => setSelected(o)}
                      className="w-full text-left p-2 bg-muted/50 rounded-sm border border-border hover:border-gold transition-colors">
                      <div className="text-xs font-semibold truncate">{o.first_name} {o.last_name}</div>
                      <div className="text-[10px] text-muted-foreground font-mono truncate">{o.invitation_number}</div>
                      {o.days_remaining > 0 && (
                        <div className={cn('text-[10px] mt-0.5', o.days_remaining <= 3 ? 'text-warning' : 'text-muted-foreground')}>
                          {o.days_remaining}d left
                        </div>
                      )}
                    </button>
                  ))}
                  {items.length === 0 && (
                    <div className="p-3 text-center text-[10px] text-muted-foreground">Empty</div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* ── Search ─────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search name, email, #…"
            className="h-8 pl-8 text-sm"
          />
        </div>
      </div>

      {/* ── Table ──────────────────────────────────────────── */}
      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50 border-b border-border text-xs text-muted-foreground">
              <th className="text-left px-3 py-2 font-medium">Invitation #</th>
              <th className="text-left px-3 py-2 font-medium">Name</th>
              <th className="text-left px-3 py-2 font-medium">Email</th>
              <th className="text-left px-3 py-2 font-medium">Phase</th>
              <th className="text-left px-3 py-2 font-medium">Progress</th>
              <th className="text-left px-3 py-2 font-medium">Expires</th>
              <th className="text-left px-3 py-2 font-medium">Created</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {tableLoading ? (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-muted-foreground text-xs">
                  <Loader2 className="w-4 h-4 animate-spin inline mr-2" />Loading…
                </td>
              </tr>
            ) : invitations.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-muted-foreground text-xs">
                  No invitations found.
                </td>
              </tr>
            ) : invitations.map((r) => {
              const p = PHASE_META[r.current_phase] || PHASE_META.INVITED;
              return (
                <tr key={r.id} onClick={() => setSelected(r)}
                  className="border-b border-border hover:bg-muted/40 cursor-pointer transition-colors">
                  <td className="px-3 py-2">
                    <span className="font-mono font-semibold text-navy dark:text-gold text-xs">
                      {r.invitation_number}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-medium text-xs">{r.first_name} {r.last_name}</td>
                  <td className="px-3 py-2">
                    <span className="font-mono text-[11px] text-muted-foreground">{r.email}</span>
                  </td>
                  <td className="px-3 py-2"><PhaseBadge phase={r.current_phase} /></td>
                  <td className="px-3 py-2">
                    <div className="flex gap-0.5">
                      {[1, 2, 3, 4, 5, 6, 7].map((s) => (
                        <div key={s} className={cn('w-4 h-1 rounded-sm', s <= p.step ? BG[p.color] : 'bg-muted')} />
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-xs">
                    <span className={cn(
                      r.is_expired ? 'text-red-500 font-medium' :
                      r.days_remaining <= 3 && r.days_remaining > 0 ? 'text-warning' : ''
                    )}>
                      {fmt(r.expires_at)}
                      {r.is_expired && <span className="text-[10px] ml-1">EXPIRED</span>}
                      {!r.is_expired && r.days_remaining > 0 && (
                        <span className="text-[10px] text-muted-foreground ml-1">({r.days_remaining}d)</span>
                      )}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">{fmt(r.created_at)}</td>
                  <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost" size="sm" className="h-7 px-2 gap-1 text-[10px]"
                      disabled={TERMINAL.has(r.current_phase)}
                      onClick={async () => {
                        try {
                          await hiringService.resend(r.id);
                          showToast.success('Resent to ' + r.email);
                          refresh();
                        } catch (err) {
                          showToast.error(err?.response?.data?.detail || 'Failed to resend');
                        }
                      }}
                    >
                      <Send className="w-3 h-3" /> Resend
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-3 py-2 border-t border-border text-xs text-muted-foreground">
            <span>{totalCount} total</span>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="sm" className="h-7 px-2"
                onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
                Prev
              </Button>
              <span className="px-2">{page} / {totalPages}</span>
              <Button variant="outline" size="sm" className="h-7 px-2"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {showCreate && (
        <NewInvitationModal onClose={() => setShowCreate(false)} onCreated={refresh} />
      )}
      {selected && (
        <DetailDrawer invitation={selected} onClose={() => setSelected(null)} onRefresh={refresh} />
      )}
    </div>
  );
};

export default HiringModule;
