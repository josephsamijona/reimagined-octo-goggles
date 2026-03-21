// JHBridge Command Center — Dispatch Module
import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { SectionHeader, StatusBadge } from '@/components/shared/UIComponents';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { showToast } from '@/components/shared/Toast';
import { useAssignments } from '@/hooks/useAssignments';
import { dispatchService } from '@/services/dispatchService';
import { MissionFormModal } from '@/components/modals/MissionFormModal';
import { MissionDetailModal } from '@/components/modals/MissionDetailModal';
import { DispatchMapView } from '@/components/modules/DispatchMapView';
import {
  Plus, Check, X, MapPin, RefreshCw, Loader2, AlertCircle,
  ChevronLeft, ChevronRight, Search, Filter, Download,
  LayoutList, Columns, Calendar as CalendarIcon, AlertTriangle,
  CheckCircle, XCircle, Play, Eye, Bell, Ban, Copy, Map as MapIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 15;
const VIEWS = ['table', 'kanban', 'calendar', 'map'];

const fmt = (v) => v
  ? new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  : '—';
const fmtTime = (v) => v
  ? new Date(v).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  : '—';
const fmtAmt = (v) => (v != null) ? `$${parseFloat(v).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—';

function duration(start, end) {
  if (!start || !end) return '—';
  const h = (new Date(end) - new Date(start)) / 3600000;
  return `${h.toFixed(1)}h`;
}

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------
const Pagination = ({ page, count, pageSize, onChange }) => {
  const total = Math.ceil((count || 0) / pageSize);
  if (total <= 1) return null;
  const pages = [];
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else if (page <= 4) {
    pages.push(1, 2, 3, 4, 5, '…', total);
  } else if (page >= total - 3) {
    pages.push(1, '…', total - 4, total - 3, total - 2, total - 1, total);
  } else {
    pages.push(1, '…', page - 1, page, page + 1, '…', total);
  }
  return (
    <div className="flex items-center justify-between px-1 pt-2 text-xs text-muted-foreground">
      <span>{Math.min((page - 1) * pageSize + 1, count || 0)}–{Math.min(page * pageSize, count || 0)} of {count || 0}</span>
      <div className="flex gap-1">
        <button disabled={page <= 1} onClick={() => onChange(page - 1)}
          className="h-7 w-7 flex items-center justify-center rounded border border-border disabled:opacity-30 hover:bg-muted transition-colors">
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>
        {pages.map((p, i) =>
          p === '…'
            ? <span key={`e${i}`} className="h-7 w-7 flex items-center justify-center text-muted-foreground">…</span>
            : <button key={p} onClick={() => onChange(p)}
                className={cn('h-7 w-7 flex items-center justify-center rounded border text-[11px] transition-colors',
                  p === page ? 'bg-primary text-primary-foreground border-primary' : 'border-border hover:bg-muted')}>
                {p}
              </button>
        )}
        <button disabled={page >= total} onClick={() => onChange(page + 1)}
          className="h-7 w-7 flex items-center justify-center rounded border border-border disabled:opacity-30 hover:bg-muted transition-colors">
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Status color helpers
// ---------------------------------------------------------------------------
const STATUS_COLORS = {
  PENDING: '#FFA500',
  CONFIRMED: '#3B82F6',
  IN_PROGRESS: '#8B5CF6',
  COMPLETED: '#10B981',
  CANCELLED: '#EF4444',
  NO_SHOW: '#6B7280',
};

// ---------------------------------------------------------------------------
// KPI Bar
// ---------------------------------------------------------------------------
const KpiBar = ({ stats, statsLoading, onFilter, activeStatus }) => {
  const statuses = [
    { key: 'PENDING',     label: 'Pending',     color: 'text-warning'         },
    { key: 'CONFIRMED',   label: 'Confirmed',   color: 'text-blue-500'        },
    { key: 'IN_PROGRESS', label: 'In Progress', color: 'text-purple-500'      },
    { key: 'COMPLETED',   label: 'Completed',   color: 'text-success'         },
    { key: 'CANCELLED',   label: 'Cancelled',   color: 'text-danger'          },
    { key: 'NO_SHOW',     label: 'No Show',     color: 'text-muted-foreground'},
  ];
  const byStatus = stats?.by_status || {};
  const unassigned = stats?.unassigned_count ?? 0;
  const today = stats?.today_count ?? 0;

  return (
    <div className="space-y-2">
      {/* Row 1: status tiles */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
        {statuses.map(({ key, label, color }) => (
          <button key={key} onClick={() => onFilter(activeStatus === key ? '' : key)}
            className={cn(
              'rounded-lg border p-2.5 text-left transition-all hover:shadow-sm',
              activeStatus === key
                ? 'bg-primary/10 border-primary/40'
                : 'bg-card border-border hover:border-primary/30',
            )}>
            <div className={cn('text-xl font-bold font-mono', color)}>
              {statsLoading ? '…' : (byStatus[key] ?? 0)}
            </div>
            <div className="text-[11px] text-muted-foreground mt-0.5">{label}</div>
          </button>
        ))}
      </div>
      {/* Row 2: unassigned alert + today */}
      <div className="grid grid-cols-2 gap-2">
        <button onClick={() => onFilter('unassigned')}
          className={cn(
            'rounded-lg border p-2.5 text-left transition-all hover:shadow-sm',
            activeStatus === 'unassigned'
              ? 'bg-danger/10 border-danger/40'
              : unassigned > 0 ? 'bg-danger/5 border-danger/20 hover:border-danger/40' : 'bg-card border-border',
          )}>
          <div className={cn('text-xl font-bold font-mono', unassigned > 0 ? 'text-danger' : 'text-muted-foreground')}>
            {statsLoading ? '…' : unassigned}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-1">
            {unassigned > 0 && <AlertTriangle className="w-3 h-3 text-danger" />}
            Unassigned (needs interpreter)
          </div>
        </button>
        <div className="rounded-lg border bg-card border-border p-2.5">
          <div className="text-xl font-bold font-mono text-navy dark:text-gold">
            {statsLoading ? '…' : today}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">Today's missions</div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Table View
// ---------------------------------------------------------------------------
const TableView = ({
  assignments, count, isLoading,
  params, setParams,
  selectedIds, toggleSelect, toggleAll, allSelected,
  onRowClick, onAction, actionLoading,
}) => {
  const searchTimer = useRef(null);
  const [searchInput, setSearchInput] = useState(params.search || '');

  const onSearch = (val) => {
    setSearchInput(val);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => setParams({ search: val }), 400);
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Filter bar */}
      <div className="flex gap-2 flex-wrap items-center">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input placeholder="Search client, interpreter, city…" value={searchInput}
            onChange={e => onSearch(e.target.value)} className="pl-8 h-8 text-sm" />
        </div>
        <div className="flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-muted-foreground" />
          <select value={params.status || ''}
            onChange={e => setParams({ status: e.target.value })}
            className="h-8 text-sm rounded-md border border-border bg-background px-2 pr-7 focus:outline-none">
            <option value="">All statuses</option>
            {['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'].map(s => (
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            ))}
          </select>
        </div>
        <input type="date" value={params.date_from || ''} onChange={e => setParams({ date_from: e.target.value })}
          className="h-8 text-sm rounded-md border border-border bg-background px-2 focus:outline-none" />
        <span className="text-xs text-muted-foreground">→</span>
        <input type="date" value={params.date_to || ''} onChange={e => setParams({ date_to: e.target.value })}
          className="h-8 text-sm rounded-md border border-border bg-background px-2 focus:outline-none" />
        <span className="text-xs text-muted-foreground ml-auto">{count} mission{count !== 1 ? 's' : ''}</span>
      </div>

      {/* Bulk bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-2 flex-wrap px-3 py-2 rounded-md bg-primary/5 border border-primary/20 text-sm">
          <span className="font-medium text-primary">{selectedIds.size} selected</span>
          <Button size="sm" className="h-7 px-3 gap-1 text-xs bg-blue-500 hover:bg-blue-600 text-white"
            onClick={() => onAction('bulk_confirm')} disabled={!!actionLoading.bulk}>
            <CheckCircle className="w-3 h-3" /> Confirm
          </Button>
          <Button size="sm" className="h-7 px-3 gap-1 text-xs bg-success hover:bg-success/90 text-white"
            onClick={() => onAction('bulk_complete')} disabled={!!actionLoading.bulk}>
            <Check className="w-3 h-3" /> Complete
          </Button>
          <Button size="sm" className="h-7 px-3 gap-1 text-xs bg-danger hover:bg-danger/90 text-white"
            onClick={() => onAction('bulk_cancel')} disabled={!!actionLoading.bulk}>
            <XCircle className="w-3 h-3" /> Cancel
          </Button>
          {actionLoading.bulk && <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />}
          <button className="ml-auto text-xs text-muted-foreground hover:text-foreground"
            onClick={() => toggleAll(false)}>Clear</button>
        </div>
      )}

      {/* Table */}
      <div className="rounded-md border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50 border-b border-border text-xs text-muted-foreground">
              <th className="px-3 py-2 w-8">
                <div onClick={() => toggleAll(!allSelected)}
                  className={cn('w-4 h-4 rounded border flex items-center justify-center cursor-pointer transition-colors',
                    allSelected ? 'bg-primary border-primary' : 'border-border hover:border-primary/50')}>
                  {allSelected && <Check className="w-3 h-3 text-primary-foreground" />}
                </div>
              </th>
              <th className="text-left px-3 py-2 font-medium">ID</th>
              <th className="text-left px-3 py-2 font-medium">Client</th>
              <th className="text-left px-3 py-2 font-medium">Interpreter</th>
              <th className="text-left px-3 py-2 font-medium">Languages</th>
              <th className="text-left px-3 py-2 font-medium">Type</th>
              <th className="text-left px-3 py-2 font-medium">Start</th>
              <th className="text-left px-3 py-2 font-medium">Dur.</th>
              <th className="text-left px-3 py-2 font-medium">Location</th>
              <th className="text-left px-3 py-2 font-medium">Total</th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={12} className="text-center py-12 text-muted-foreground">
                <Loader2 className="w-5 h-5 animate-spin inline mr-2" />Loading…
              </td></tr>
            ) : assignments.length === 0 ? (
              <tr><td colSpan={12} className="text-center py-12 text-muted-foreground">
                <MapPin className="w-10 h-10 mx-auto mb-2 opacity-20" />
                No missions found.
              </td></tr>
            ) : assignments.map((r, i) => {
              const sel = selectedIds.has(r.id);
              return (
                <tr key={r.id} onClick={() => onRowClick(r)}
                  className={cn('border-b border-border/50 last:border-0 cursor-pointer transition-colors hover:bg-muted/30',
                    sel && 'bg-primary/5', i % 2 !== 0 && 'bg-muted/10')}>
                  <td className="px-3 py-2" onClick={e => { e.stopPropagation(); toggleSelect(r.id); }}>
                    <div className={cn('w-4 h-4 rounded border flex items-center justify-center cursor-pointer transition-colors',
                      sel ? 'bg-primary border-primary' : 'border-border hover:border-primary/50')}>
                      {sel && <Check className="w-3 h-3 text-primary-foreground" />}
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <span className="font-mono font-semibold text-navy dark:text-gold text-xs">#{r.id}</span>
                  </td>
                  <td className="px-3 py-2 font-medium text-sm max-w-[120px] truncate">{r.client_display}</td>
                  <td className="px-3 py-2">
                    {r.interpreter_name
                      ? <span className="text-sm">{r.interpreter_name}</span>
                      : <span className="flex items-center gap-1 text-danger text-xs font-semibold">
                          <AlertTriangle className="w-3 h-3" /> Unassigned
                        </span>}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {r.source_language_name && r.target_language_name
                      ? `${r.source_language_name.substring(0,2).toUpperCase()} → ${r.target_language_name.substring(0,2).toUpperCase()}`
                      : '—'}
                  </td>
                  <td className="px-3 py-2 text-xs">{r.service_type_name || '—'}</td>
                  <td className="px-3 py-2">
                    <div className="font-mono text-xs">{fmt(r.start_time_local || r.start_time)}</div>
                    <div className="text-[10px] text-muted-foreground">{fmtTime(r.start_time_local || r.start_time)}</div>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{duration(r.start_time, r.end_time)}</td>
                  <td className="px-3 py-2 text-xs">{r.city}{r.state ? `, ${r.state}` : ''}</td>
                  <td className="px-3 py-2 font-mono text-xs font-semibold">{fmtAmt(r.total_interpreter_payment)}</td>
                  <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
                  <td className="px-3 py-2" onClick={e => e.stopPropagation()}>
                    <div className="flex gap-1 justify-end">
                      {/* PENDING actions */}
                      {r.status === 'PENDING' && (
                        <>
                          <button onClick={() => onAction('confirm', r)}
                            disabled={!!actionLoading[`confirm-${r.id}`]}
                            className="h-7 w-7 flex items-center justify-center rounded text-success hover:bg-success/10 transition-colors disabled:opacity-40"
                            title="Confirm">
                            {actionLoading[`confirm-${r.id}`]
                              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              : <CheckCircle className="w-3.5 h-3.5" />}
                          </button>
                          <button onClick={() => onAction('cancel_prompt', r)}
                            className="h-7 w-7 flex items-center justify-center rounded text-danger hover:bg-danger/10 transition-colors"
                            title="Cancel">
                            <XCircle className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                      {/* CONFIRMED actions */}
                      {r.status === 'CONFIRMED' && (
                        <>
                          <button onClick={() => onAction('start', r)}
                            disabled={!!actionLoading[`start-${r.id}`]}
                            className="h-7 w-7 flex items-center justify-center rounded text-purple-500 hover:bg-purple-500/10 transition-colors disabled:opacity-40"
                            title="Start mission">
                            {actionLoading[`start-${r.id}`]
                              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              : <Play className="w-3.5 h-3.5" />}
                          </button>
                          <button onClick={() => onAction('reminder', r)}
                            disabled={!!actionLoading[`reminder-${r.id}`]}
                            className="h-7 w-7 flex items-center justify-center rounded text-blue-500 hover:bg-blue-500/10 transition-colors disabled:opacity-40"
                            title="Send reminder">
                            {actionLoading[`reminder-${r.id}`]
                              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              : <Bell className="w-3.5 h-3.5" />}
                          </button>
                        </>
                      )}
                      {/* CONFIRMED + IN_PROGRESS: complete, no-show, cancel */}
                      {(r.status === 'CONFIRMED' || r.status === 'IN_PROGRESS') && (
                        <>
                          <button onClick={() => onAction('complete_prompt', r)}
                            className="h-7 w-7 flex items-center justify-center rounded text-success hover:bg-success/10 transition-colors"
                            title="Mark complete">
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => onAction('noshow_prompt', r)}
                            className="h-7 w-7 flex items-center justify-center rounded text-orange-500 hover:bg-orange-500/10 transition-colors"
                            title="Mark no-show">
                            <Ban className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => onAction('cancel_prompt', r)}
                            className="h-7 w-7 flex items-center justify-center rounded text-danger hover:bg-danger/10 transition-colors"
                            title="Cancel">
                            <XCircle className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                      {/* Duplicate (always available) */}
                      <button onClick={() => onAction('duplicate', r)}
                        disabled={!!actionLoading[`dup-${r.id}`]}
                        className="h-7 w-7 flex items-center justify-center rounded text-muted-foreground hover:bg-muted transition-colors disabled:opacity-40"
                        title="Duplicate mission">
                        {actionLoading[`dup-${r.id}`]
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Copy className="w-3.5 h-3.5" />}
                      </button>
                      {/* View details */}
                      <button onClick={() => onRowClick(r)}
                        className="h-7 w-7 flex items-center justify-center rounded text-muted-foreground hover:bg-muted transition-colors"
                        title="View details">
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Pagination page={params.page} count={count} pageSize={PAGE_SIZE}
        onChange={p => setParams({ page: p })} />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Kanban View
// ---------------------------------------------------------------------------
const KANBAN_COLS = [
  { key: 'PENDING', label: 'Pending', color: 'border-t-[#FFA500]' },
  { key: 'CONFIRMED', label: 'Confirmed', color: 'border-t-[#3B82F6]' },
  { key: 'IN_PROGRESS', label: 'In Progress', color: 'border-t-[#8B5CF6]' },
  { key: 'COMPLETED', label: 'Completed', color: 'border-t-[#10B981]' },
  { key: 'CANCELLED', label: 'Cancelled', color: 'border-t-[#EF4444]' },
];

const KanbanView = ({ onRowClick, onAction, actionLoading, refresh }) => {
  const [kanban, setKanban] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    dispatchService.getKanban()
      .then(res => setKanban(res.data || {}))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [refresh]);

  if (loading) return (
    <div className="flex items-center justify-center py-16 text-muted-foreground">
      <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading kanban…
    </div>
  );

  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {KANBAN_COLS.map(({ key, label, color }) => {
        const cards = kanban[key] || [];
        return (
          <div key={key} className="flex-shrink-0 w-64">
            <div className={cn('rounded-lg border-t-2 bg-muted/30 border border-border', color)}>
              <div className="px-3 py-2 flex items-center justify-between border-b border-border">
                <span className="text-xs font-semibold">{label}</span>
                <span className="text-xs bg-muted rounded-full px-2 py-0.5 font-mono">{cards.length}</span>
              </div>
              <div className="p-2 space-y-2 max-h-[60vh] overflow-y-auto">
                {cards.length === 0 ? (
                  <div className="text-xs text-muted-foreground text-center py-4">Empty</div>
                ) : cards.map(r => (
                  <div key={r.id} onClick={() => onRowClick(r)}
                    className="bg-card rounded-md border border-border p-2.5 cursor-pointer hover:shadow-sm hover:border-primary/30 transition-all">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[10px] text-muted-foreground">#{r.id}</span>
                      <span className="text-[10px] font-mono font-semibold text-success">{fmtAmt(r.total_interpreter_payment)}</span>
                    </div>
                    <div className="font-medium text-xs truncate mb-0.5">{r.client_display}</div>
                    <div className="text-[11px] text-muted-foreground truncate">
                      {r.interpreter_name
                        ? r.interpreter_name
                        : <span className="text-danger">⚠ Unassigned</span>}
                    </div>
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-muted-foreground">
                      <MapPin className="w-3 h-3" />
                      <span>{r.city}{r.state ? `, ${r.state}` : ''}</span>
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-0.5 font-mono">
                      {fmt(r.start_time_local || r.start_time)}
                    </div>
                    {/* Quick actions */}
                    <div className="flex gap-1 mt-2" onClick={e => e.stopPropagation()}>
                      {key === 'PENDING' && (
                        <button onClick={() => onAction('confirm', r)}
                          disabled={!!actionLoading[`confirm-${r.id}`]}
                          className="flex-1 h-6 text-[10px] rounded border border-success/30 text-success hover:bg-success/10 transition-colors disabled:opacity-40">
                          {actionLoading[`confirm-${r.id}`] ? '…' : '✓ Confirm'}
                        </button>
                      )}
                      {key === 'CONFIRMED' && (
                        <button onClick={() => onAction('start', r)}
                          disabled={!!actionLoading[`start-${r.id}`]}
                          className="flex-1 h-6 text-[10px] rounded border border-purple-500/30 text-purple-500 hover:bg-purple-500/10 transition-colors disabled:opacity-40">
                          {actionLoading[`start-${r.id}`] ? '…' : '▶ Start'}
                        </button>
                      )}
                      {(key === 'CONFIRMED' || key === 'IN_PROGRESS') && (
                        <button onClick={() => onAction('complete_prompt', r)}
                          className="flex-1 h-6 text-[10px] rounded border border-success/30 text-success hover:bg-success/10 transition-colors">
                          ✓ Complete
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Calendar View
// ---------------------------------------------------------------------------
const CalendarView = ({ onRowClick }) => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const monthStart = new Date(year, month, 1);
  const monthEnd = new Date(year, month + 1, 0);

  useEffect(() => {
    setLoading(true);
    dispatchService.getCalendar(monthStart.toISOString(), monthEnd.toISOString())
      .then(res => setEvents(res.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [year, month]); // eslint-disable-line

  const daysInMonth = monthEnd.getDate();
  const firstDayOfWeek = monthStart.getDay();

  const eventsByDay = useMemo(() => {
    const map = {};
    events.forEach(ev => {
      const d = new Date(ev.start).getDate();
      if (!map[d]) map[d] = [];
      map[d].push(ev);
    });
    return map;
  }, [events]);

  const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));
  const today = new Date();
  const isToday = (d) => today.getFullYear() === year && today.getMonth() === month && today.getDate() === d;

  const monthLabel = currentDate.toLocaleString('en-US', { month: 'long', year: 'numeric' });

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <button onClick={prevMonth} className="h-7 w-7 rounded border border-border flex items-center justify-center hover:bg-muted">
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="text-sm font-semibold">{monthLabel}</span>
          <button onClick={nextMonth} className="h-7 w-7 rounded border border-border flex items-center justify-center hover:bg-muted">
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
        <button onClick={() => setCurrentDate(new Date())}
          className="text-xs px-2 py-1 rounded border border-border hover:bg-muted transition-colors">Today</button>
      </div>
      {loading && <div className="flex items-center justify-center py-10 text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading…</div>}
      {!loading && (
        <div className="rounded-lg border border-border overflow-hidden">
          {/* Day labels */}
          <div className="grid grid-cols-7 bg-muted/50 border-b border-border">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
              <div key={d} className="py-1.5 text-center text-[11px] font-medium text-muted-foreground">{d}</div>
            ))}
          </div>
          {/* Days grid */}
          <div className="grid grid-cols-7">
            {Array.from({ length: firstDayOfWeek }, (_, i) => (
              <div key={`e${i}`} className="min-h-[80px] border-b border-r border-border/50 bg-muted/20" />
            ))}
            {Array.from({ length: daysInMonth }, (_, i) => {
              const day = i + 1;
              const dayEvents = eventsByDay[day] || [];
              return (
                <div key={day} className={cn('min-h-[80px] border-b border-r border-border/50 p-1',
                  isToday(day) && 'bg-primary/5')}>
                  <div className={cn('text-xs font-medium mb-1 w-6 h-6 flex items-center justify-center rounded-full',
                    isToday(day) ? 'bg-primary text-primary-foreground' : 'text-muted-foreground')}>
                    {day}
                  </div>
                  <div className="space-y-0.5">
                    {dayEvents.slice(0, 3).map(ev => (
                      <button key={ev.id} onClick={() => onRowClick({ id: ev.id })}
                        className="w-full text-left text-[10px] rounded px-1 py-0.5 truncate font-medium text-white"
                        style={{ backgroundColor: ev.color || STATUS_COLORS[ev.status] || '#6b7280' }}>
                        {ev.title}
                      </button>
                    ))}
                    {dayEvents.length > 3 && (
                      <div className="text-[10px] text-muted-foreground pl-1">+{dayEvents.length - 3} more</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      {/* Legend */}
      <div className="flex gap-3 mt-2 flex-wrap">
        {Object.entries(STATUS_COLORS).map(([s, c]) => (
          <span key={s} className="flex items-center gap-1 text-[10px] text-muted-foreground">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: c }} />
            {s.replace('_', ' ')}
          </span>
        ))}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Module
// ---------------------------------------------------------------------------
export const DispatchModule = () => {
  const { assignments, count, stats, isLoading, statsLoading, error, params, setParams, refresh } = useAssignments();
  const [view, setView] = useState('table');

  // Modals
  const [formModal, setFormModal] = useState({ open: false, mission: null });
  const [detailModal, setDetailModal] = useState({ open: false, id: null });

  // Confirm dialogs
  const [confirmDialog, setConfirmDialog] = useState({ open: false, type: null, mission: null });
  const [confirmLoading, setConfirmLoading] = useState(false);

  // Action loading per row
  const [actionLoading, setActionLoading] = useState({});
  const setAL = (key, val) => setActionLoading(prev => ({ ...prev, [key]: val }));

  // Selection
  const [selectedIds, setSelectedIds] = useState(new Set());
  const allSelected = assignments.length > 0 && assignments.every(a => selectedIds.has(a.id));

  const toggleSelect = useCallback((id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const toggleAll = useCallback((select) => {
    if (select) {
      setSelectedIds(prev => {
        const next = new Set(prev);
        assignments.forEach(a => next.add(a.id));
        return next;
      });
    } else {
      setSelectedIds(new Set());
    }
  }, [assignments]);

  // KPI filter click
  const handleKpiFilter = (statusKey) => {
    if (statusKey === 'unassigned') {
      setParams({ unassigned: params.unassigned === 'true' ? '' : 'true', status: '' });
    } else {
      setParams({ status: statusKey, unassigned: '' });
    }
  };
  const activeKpiStatus = params.unassigned === 'true' ? 'unassigned' : (params.status || '');

  // Row click → open detail modal
  const handleRowClick = useCallback((r) => {
    setDetailModal({ open: true, id: r.id });
  }, []);

  // Single-row quick actions
  const handleAction = useCallback(async (type, mission) => {
    if (type === 'confirm') {
      const key = `confirm-${mission.id}`;
      setAL(key, true);
      try {
        await dispatchService.confirmAssignment(mission.id);
        showToast.success(`Mission #${mission.id} confirmed`);
        refresh();
      } catch { showToast.error('Failed to confirm mission'); }
      finally { setAL(key, false); }

    } else if (type === 'start') {
      const key = `start-${mission.id}`;
      setAL(key, true);
      try {
        await dispatchService.startAssignment(mission.id);
        showToast.success(`Mission #${mission.id} started`);
        refresh();
      } catch { showToast.error('Failed to start mission'); }
      finally { setAL(key, false); }

    } else if (type === 'reminder') {
      const key = `reminder-${mission.id}`;
      setAL(key, true);
      try {
        await dispatchService.sendReminder(mission.id);
        showToast.success(`Reminder sent for mission #${mission.id}`);
      } catch (err) {
        showToast.error(err?.response?.data?.detail || 'Failed to send reminder');
      } finally { setAL(key, false); }

    } else if (type === 'duplicate') {
      const key = `dup-${mission.id}`;
      setAL(key, true);
      try {
        const res = await dispatchService.duplicateAssignment(mission.id);
        showToast.success(`Mission #${res.data?.id} created as duplicate`);
        refresh();
      } catch { showToast.error('Failed to duplicate mission'); }
      finally { setAL(key, false); }

    } else if (type === 'cancel_prompt') {
      setConfirmDialog({ open: true, type: 'cancel', mission });
    } else if (type === 'complete_prompt') {
      setConfirmDialog({ open: true, type: 'complete', mission });
    } else if (type === 'noshow_prompt') {
      setConfirmDialog({ open: true, type: 'noshow', mission });

    } else if (type === 'bulk_confirm') {
      setAL('bulk', true);
      try {
        const res = await dispatchService.bulkAction('confirm', [...selectedIds]);
        const { succeeded, failed } = res.data;
        showToast.success(`${succeeded.length} confirmed${failed.length ? `, ${failed.length} skipped` : ''}`);
        setSelectedIds(new Set());
        refresh();
      } catch { showToast.error('Bulk confirm failed'); }
      finally { setAL('bulk', false); }

    } else if (type === 'bulk_complete') {
      setAL('bulk', true);
      try {
        const res = await dispatchService.bulkAction('complete', [...selectedIds]);
        const { succeeded, failed } = res.data;
        showToast.success(`${succeeded.length} completed${failed.length ? `, ${failed.length} skipped` : ''}`);
        setSelectedIds(new Set());
        refresh();
      } catch { showToast.error('Bulk complete failed'); }
      finally { setAL('bulk', false); }

    } else if (type === 'bulk_cancel') {
      setAL('bulk', true);
      try {
        const res = await dispatchService.bulkAction('cancel', [...selectedIds]);
        const { succeeded, failed } = res.data;
        showToast.success(`${succeeded.length} cancelled${failed.length ? `, ${failed.length} skipped` : ''}`);
        setSelectedIds(new Set());
        refresh();
      } catch { showToast.error('Bulk cancel failed'); }
      finally { setAL('bulk', false); }
    }
  }, [selectedIds, refresh]);

  // Confirm dialog submit
  const handleConfirmSubmit = async () => {
    if (!confirmDialog.mission) return;
    setConfirmLoading(true);
    try {
      if (confirmDialog.type === 'cancel') {
        await dispatchService.cancelAssignment(confirmDialog.mission.id);
        showToast.warning(`Mission #${confirmDialog.mission.id} cancelled`);
      } else if (confirmDialog.type === 'complete') {
        await dispatchService.completeAssignment(confirmDialog.mission.id);
        showToast.success(`Mission #${confirmDialog.mission.id} completed`);
      } else if (confirmDialog.type === 'noshow') {
        await dispatchService.noShowAssignment(confirmDialog.mission.id);
        showToast.warning(`Mission #${confirmDialog.mission.id} marked as no-show`);
      }
      refresh();
    } catch {
      showToast.error(`Failed to ${confirmDialog.type} mission`);
    } finally {
      setConfirmLoading(false);
      setConfirmDialog({ open: false, type: null, mission: null });
    }
  };

  const viewIcons = { table: LayoutList, kanban: Columns, calendar: CalendarIcon, map: MapIcon };

  return (
    <div className="flex flex-col gap-4" data-testid="dispatch-module">
      <SectionHeader
        title="Dispatch Center"
        subtitle="Mission control & interpreter assignment"
        action={
          <div className="flex gap-2 flex-wrap">
            {/* View toggle */}
            <div className="flex rounded-md border border-border overflow-hidden">
              {VIEWS.map(v => {
                const Icon = viewIcons[v];
                return (
                  <button key={v} onClick={() => setView(v)}
                    className={cn('h-8 px-2.5 flex items-center gap-1.5 text-xs transition-colors',
                      v === view ? 'bg-primary text-primary-foreground' : 'hover:bg-muted text-muted-foreground')}>
                    <Icon className="w-3.5 h-3.5" />
                    <span className="capitalize hidden sm:inline">{v}</span>
                  </button>
                );
              })}
            </div>
            <Button variant="outline" size="sm" className="gap-1.5"
              onClick={() => dispatchService.exportCsv({
                ...(params.status && { status: params.status }),
                ...(params.search && { search: params.search }),
                ...(params.date_from && { date_from: params.date_from }),
                ...(params.date_to && { date_to: params.date_to }),
              })}>
              <Download className="w-3.5 h-3.5" /> Export
            </Button>
            <Button size="sm" className="gap-1.5 bg-navy hover:bg-navy-light"
              onClick={() => setFormModal({ open: true, mission: null })}>
              <Plus className="w-3.5 h-3.5" /> New Mission
            </Button>
            <Button variant="ghost" size="sm" className="h-8 px-2" onClick={refresh}
              disabled={isLoading}>
              <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
            </Button>
          </div>
        }
      />

      {/* KPI Bar */}
      <KpiBar stats={stats} statsLoading={statsLoading} onFilter={handleKpiFilter} activeStatus={activeKpiStatus} />

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-md bg-danger/10 border border-danger/20 text-danger text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          Failed to load missions.
          <button className="underline ml-1" onClick={refresh}>Retry</button>
        </div>
      )}

      {/* Active filter chips */}
      {(params.status || params.unassigned || params.date_from || params.date_to || params.search) && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground">Filters:</span>
          {params.status && (
            <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded flex items-center gap-1">
              {params.status} <button onClick={() => setParams({ status: '' })}><X className="w-3 h-3" /></button>
            </span>
          )}
          {params.unassigned === 'true' && (
            <span className="px-2 py-0.5 bg-danger/10 text-danger text-xs rounded flex items-center gap-1">
              Unassigned only <button onClick={() => setParams({ unassigned: '' })}><X className="w-3 h-3" /></button>
            </span>
          )}
          {params.search && (
            <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded flex items-center gap-1">
              "{params.search}" <button onClick={() => { setParams({ search: '' }); }}><X className="w-3 h-3" /></button>
            </span>
          )}
          {(params.date_from || params.date_to) && (
            <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded flex items-center gap-1">
              {params.date_from || '…'} → {params.date_to || '…'}
              <button onClick={() => setParams({ date_from: '', date_to: '' })}><X className="w-3 h-3" /></button>
            </span>
          )}
          <button onClick={() => setParams({ status: '', unassigned: '', search: '', date_from: '', date_to: '' })}
            className="text-xs text-muted-foreground hover:text-foreground underline">Clear all</button>
        </div>
      )}

      {/* Views */}
      {view === 'table' && (
        <TableView
          assignments={assignments} count={count} isLoading={isLoading}
          params={params} setParams={setParams}
          selectedIds={selectedIds} toggleSelect={toggleSelect}
          toggleAll={toggleAll} allSelected={allSelected}
          onRowClick={handleRowClick} onAction={handleAction}
          actionLoading={actionLoading}
        />
      )}
      {view === 'kanban' && (
        <KanbanView onRowClick={handleRowClick} onAction={handleAction}
          actionLoading={actionLoading} refresh={refresh} />
      )}
      {view === 'calendar' && (
        <CalendarView onRowClick={handleRowClick} />
      )}
      {view === 'map' && (
        <DispatchMapView onAssignmentClick={handleRowClick} />
      )}

      {/* Modals */}
      <MissionFormModal
        isOpen={formModal.open}
        onClose={() => setFormModal({ open: false, mission: null })}
        mission={formModal.mission}
        onSuccess={() => { setFormModal({ open: false, mission: null }); refresh(); }}
      />

      <MissionDetailModal
        isOpen={detailModal.open}
        assignmentId={detailModal.id}
        onClose={() => setDetailModal({ open: false, id: null })}
        onEdit={(mission) => {
          setDetailModal({ open: false, id: null });
          setFormModal({ open: true, mission });
        }}
        onRefresh={refresh}
      />

      {/* Confirm dialogs */}
      <ConfirmDialog
        isOpen={confirmDialog.open && confirmDialog.type === 'cancel'}
        onConfirm={handleConfirmSubmit}
        onCancel={() => setConfirmDialog({ open: false, type: null, mission: null })}
        title="Cancel Mission?"
        message={`Cancel mission #${confirmDialog.mission?.id}? The interpreter and client will be notified.`}
        confirmText="Cancel Mission"
        variant="danger"
        loading={confirmLoading}
      />
      <ConfirmDialog
        isOpen={confirmDialog.open && confirmDialog.type === 'complete'}
        onConfirm={handleConfirmSubmit}
        onCancel={() => setConfirmDialog({ open: false, type: null, mission: null })}
        title="Mark Complete?"
        message={`Mark mission #${confirmDialog.mission?.id} as completed? The client will be notified.`}
        confirmText="Mark Complete"
        variant="info"
        loading={confirmLoading}
      />
      <ConfirmDialog
        isOpen={confirmDialog.open && confirmDialog.type === 'noshow'}
        onConfirm={handleConfirmSubmit}
        onCancel={() => setConfirmDialog({ open: false, type: null, mission: null })}
        title="Mark No-Show?"
        message={`Mark mission #${confirmDialog.mission?.id} as no-show? The interpreter's payment will be cancelled.`}
        confirmText="Mark No-Show"
        variant="danger"
        loading={confirmLoading}
      />
    </div>
  );
};

export default DispatchModule;
