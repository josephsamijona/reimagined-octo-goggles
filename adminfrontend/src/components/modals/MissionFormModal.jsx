// JHBridge — Mission Form Modal (Create / Edit) — Real API
import { useState, useEffect, useCallback } from 'react';
import { Modal } from '@/components/shared/Modal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { showToast } from '@/components/shared/Toast';
import { dispatchService } from '@/services/dispatchService';
import {
  Calendar, Clock, MapPin, Building2, Languages,
  User, Star, Check, Loader2, AlertTriangle, RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const fmtAmt = (v) => v != null ? `$${parseFloat(v).toFixed(2)}` : '—';

const toDatetimeLocal = (iso) => {
  if (!iso) return '';
  return new Date(iso).toISOString().slice(0, 16);
};

const EMPTY_FORM = {
  client: '',
  client_name: '',
  client_email: '',
  client_phone: '',
  service_type: '',
  source_language: '',
  target_language: '',
  location: '',
  city: '',
  state: '',
  zip_code: '',
  start_time: '',
  end_time: '',
  interpreter: '',
  interpreter_rate: '',
  minimum_hours: 2,
  notes: '',
  special_requirements: '',
};

export const MissionFormModal = ({ isOpen, onClose, mission = null, prefillData = null, onSuccess }) => {
  const isEdit = !!mission;
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  // Remote data
  const [clients, setClients] = useState([]);
  const [serviceTypes, setServiceTypes] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [availableInterps, setAvailableInterps] = useState([]);
  const [loadingInterps, setLoadingInterps] = useState(false);
  const [conflict, setConflict] = useState(null);
  const [useManualClient, setUseManualClient] = useState(false);

  // Computed totals
  const estimatedTotal = (() => {
    const rate = parseFloat(form.interpreter_rate) || 0;
    const start = form.start_time ? new Date(form.start_time) : null;
    const end = form.end_time ? new Date(form.end_time) : null;
    if (!rate || !start || !end || end <= start) return null;
    const hours = (end - start) / 3600000;
    const billable = Math.max(hours, parseFloat(form.minimum_hours) || 2);
    return rate * billable;
  })();

  // Load dropdowns on open
  useEffect(() => {
    if (!isOpen) return;
    Promise.all([
      dispatchService.getClients({ page_size: 200 }),
      dispatchService.getServiceTypes(),
      dispatchService.getLanguages(),
    ]).then(([c, st, l]) => {
      setClients(c.data?.results || c.data || []);
      setServiceTypes(st.data?.results || st.data || []);
      setLanguages(l.data?.results || l.data || []);
    }).catch(() => showToast.error('Failed to load form data'));
  }, [isOpen]);

  // Initialize form for edit or prefill
  useEffect(() => {
    if (!isOpen) return;
    if (mission) {
      setForm({
        client: mission.client || '',
        client_name: mission.client_name || '',
        client_email: mission.client_email || '',
        client_phone: mission.client_phone || '',
        service_type: mission.service_type?.id || '',
        source_language: mission.source_language?.id || '',
        target_language: mission.target_language?.id || '',
        location: mission.location || '',
        city: mission.city || '',
        state: mission.state || '',
        zip_code: mission.zip_code || '',
        start_time: toDatetimeLocal(mission.start_time),
        end_time: toDatetimeLocal(mission.end_time),
        interpreter: mission.interpreter_id || '',
        interpreter_rate: mission.interpreter_rate || '',
        minimum_hours: mission.minimum_hours || 2,
        notes: mission.notes || '',
        special_requirements: mission.special_requirements || '',
      });
      setUseManualClient(!mission.client);
    } else if (prefillData) {
      setForm(prev => ({ ...prev, ...prefillData }));
    } else {
      setForm(EMPTY_FORM);
      setUseManualClient(false);
    }
    setErrors({});
    setConflict(null);
    setAvailableInterps([]);
  }, [isOpen, mission, prefillData]);

  // Auto-fill rate from service type
  useEffect(() => {
    if (!form.service_type) return;
    const st = serviceTypes.find(s => String(s.id) === String(form.service_type));
    if (st?.base_rate && !form.interpreter_rate) {
      setForm(prev => ({
        ...prev,
        interpreter_rate: st.base_rate,
        minimum_hours: st.minimum_hours || prev.minimum_hours,
      }));
    }
  }, [form.service_type, serviceTypes]); // eslint-disable-line

  // Fetch available interpreters when languages / start_time change
  const fetchAvailableInterps = useCallback(async () => {
    if (!form.source_language && !form.target_language) return;
    setLoadingInterps(true);
    try {
      const params = {};
      if (form.source_language) params.source_language = form.source_language;
      if (form.target_language) params.target_language = form.target_language;
      if (form.start_time) params.date = form.start_time.slice(0, 10);
      if (form.city) params.city = form.city;
      const res = await dispatchService.getAvailableInterpreters(params);
      setAvailableInterps(res.data?.results || res.data || []);
    } catch {
      setAvailableInterps([]);
    } finally {
      setLoadingInterps(false);
    }
  }, [form.source_language, form.target_language, form.start_time, form.city]);

  useEffect(() => { fetchAvailableInterps(); }, [fetchAvailableInterps]);

  // Check conflict when interpreter + times are set
  useEffect(() => {
    if (!form.interpreter || !form.start_time || !form.end_time) { setConflict(null); return; }
    dispatchService.checkConflict(
      form.interpreter,
      new Date(form.start_time).toISOString(),
      new Date(form.end_time).toISOString(),
      mission?.id || null,
    ).then(res => setConflict(res.data?.has_conflict ? res.data.conflicts : null))
      .catch(() => setConflict(null));
  }, [form.interpreter, form.start_time, form.end_time, mission?.id]);

  const set = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: null }));
  };

  const validate = () => {
    const e = {};
    if (!useManualClient && !form.client) e.client = 'Client required';
    if (useManualClient && !form.client_name) e.client_name = 'Name required';
    if (!form.service_type) e.service_type = 'Service type required';
    if (!form.source_language) e.source_language = 'Required';
    if (!form.target_language) e.target_language = 'Required';
    if (!form.city) e.city = 'City required';
    if (!form.start_time) e.start_time = 'Required';
    if (!form.end_time) e.end_time = 'Required';
    if (form.start_time && form.end_time && new Date(form.end_time) <= new Date(form.start_time)) {
      e.end_time = 'End must be after start';
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const payload = {
        service_type: form.service_type,
        source_language: form.source_language,
        target_language: form.target_language,
        location: form.location,
        city: form.city,
        state: form.state,
        zip_code: form.zip_code,
        start_time: new Date(form.start_time).toISOString(),
        end_time: new Date(form.end_time).toISOString(),
        interpreter_rate: form.interpreter_rate || null,
        minimum_hours: form.minimum_hours,
        notes: form.notes,
        special_requirements: form.special_requirements,
        ...(form.interpreter ? { interpreter: form.interpreter } : {}),
      };
      if (useManualClient) {
        payload.client_name = form.client_name;
        payload.client_email = form.client_email;
        payload.client_phone = form.client_phone;
      } else {
        payload.client = form.client;
      }

      if (isEdit) {
        await dispatchService.updateAssignment(mission.id, payload);
        showToast.success(`Mission #${mission.id} updated`);
      } else {
        const res = await dispatchService.createAssignment(payload);
        showToast.success(`Mission #${res.data.id} created`);
      }
      onSuccess?.();
      onClose();
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to save mission';
      showToast.error(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Mission #${mission?.id}` : 'New Mission'}
      subtitle={isEdit ? 'Update mission details' : 'Create a new interpreter assignment'}
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={loading} className="bg-navy hover:bg-navy-light">
            {loading && <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />}
            {loading ? 'Saving…' : isEdit ? 'Update Mission' : 'Create Mission'}
          </Button>
        </>
      }
    >
      <div className="space-y-5">

        {/* Client */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <Label className="flex items-center gap-1.5"><Building2 className="w-3.5 h-3.5" /> Client *</Label>
            <button type="button" onClick={() => setUseManualClient(v => !v)}
              className="text-[11px] text-primary underline">
              {useManualClient ? 'Select existing client' : 'Enter manually'}
            </button>
          </div>
          {useManualClient ? (
            <div className="grid grid-cols-2 gap-2">
              <div className="col-span-2">
                <Input placeholder="Contact / Company name *" value={form.client_name}
                  onChange={e => set('client_name', e.target.value)}
                  className={cn(errors.client_name && 'border-danger')} />
                {errors.client_name && <p className="text-xs text-danger mt-0.5">{errors.client_name}</p>}
              </div>
              <Input placeholder="Email" type="email" value={form.client_email} onChange={e => set('client_email', e.target.value)} />
              <Input placeholder="Phone" value={form.client_phone} onChange={e => set('client_phone', e.target.value)} />
            </div>
          ) : (
            <>
              <select value={form.client} onChange={e => set('client', e.target.value)}
                className={cn('w-full px-3 py-2 rounded-md border bg-background text-sm',
                  errors.client ? 'border-danger' : 'border-input')}>
                <option value="">Select client…</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.company_name}</option>)}
              </select>
              {errors.client && <p className="text-xs text-danger mt-0.5">{errors.client}</p>}
            </>
          )}
        </div>

        {/* Service type */}
        <div>
          <Label className="mb-1.5 block">Service Type *</Label>
          <select value={form.service_type} onChange={e => set('service_type', e.target.value)}
            className={cn('w-full px-3 py-2 rounded-md border bg-background text-sm',
              errors.service_type ? 'border-danger' : 'border-input')}>
            <option value="">Select service type…</option>
            {serviceTypes.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          {errors.service_type && <p className="text-xs text-danger mt-0.5">{errors.service_type}</p>}
        </div>

        {/* Languages */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="flex items-center gap-1.5 mb-1.5"><Languages className="w-3.5 h-3.5" /> Source Language *</Label>
            <select value={form.source_language} onChange={e => set('source_language', e.target.value)}
              className={cn('w-full px-3 py-2 rounded-md border bg-background text-sm',
                errors.source_language ? 'border-danger' : 'border-input')}>
              <option value="">Select…</option>
              {languages.filter(l => String(l.id) !== String(form.target_language)).map(l => (
                <option key={l.id} value={l.id}>{l.name}</option>
              ))}
            </select>
            {errors.source_language && <p className="text-xs text-danger mt-0.5">{errors.source_language}</p>}
          </div>
          <div>
            <Label className="flex items-center gap-1.5 mb-1.5"><Languages className="w-3.5 h-3.5" /> Target Language *</Label>
            <select value={form.target_language} onChange={e => set('target_language', e.target.value)}
              className={cn('w-full px-3 py-2 rounded-md border bg-background text-sm',
                errors.target_language ? 'border-danger' : 'border-input')}>
              <option value="">Select…</option>
              {languages.filter(l => String(l.id) !== String(form.source_language)).map(l => (
                <option key={l.id} value={l.id}>{l.name}</option>
              ))}
            </select>
            {errors.target_language && <p className="text-xs text-danger mt-0.5">{errors.target_language}</p>}
          </div>
        </div>

        {/* Location */}
        <div>
          <Label className="flex items-center gap-1.5 mb-1.5"><MapPin className="w-3.5 h-3.5" /> Location *</Label>
          <Input placeholder="Street address" value={form.location} onChange={e => set('location', e.target.value)} className="mb-2" />
          <div className="grid grid-cols-3 gap-2">
            <Input placeholder="City *" value={form.city} onChange={e => set('city', e.target.value)}
              className={cn(errors.city && 'border-danger')} />
            <Input placeholder="State" value={form.state} onChange={e => set('state', e.target.value)} maxLength={2} />
            <Input placeholder="ZIP" value={form.zip_code} onChange={e => set('zip_code', e.target.value)} maxLength={10} />
          </div>
          {errors.city && <p className="text-xs text-danger mt-0.5">{errors.city}</p>}
        </div>

        {/* Schedule */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="flex items-center gap-1.5 mb-1.5"><Calendar className="w-3.5 h-3.5" /> Start *</Label>
            <Input type="datetime-local" value={form.start_time} onChange={e => set('start_time', e.target.value)}
              className={cn(errors.start_time && 'border-danger')} />
            {errors.start_time && <p className="text-xs text-danger mt-0.5">{errors.start_time}</p>}
          </div>
          <div>
            <Label className="flex items-center gap-1.5 mb-1.5"><Clock className="w-3.5 h-3.5" /> End *</Label>
            <Input type="datetime-local" value={form.end_time} onChange={e => set('end_time', e.target.value)}
              className={cn(errors.end_time && 'border-danger')} />
            {errors.end_time && <p className="text-xs text-danger mt-0.5">{errors.end_time}</p>}
          </div>
        </div>

        {/* Rate & min hours */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label className="mb-1.5 block">Rate ($/hr)</Label>
            <Input type="number" min={0} step={0.5} placeholder="0.00" value={form.interpreter_rate}
              onChange={e => set('interpreter_rate', e.target.value)} />
          </div>
          <div>
            <Label className="mb-1.5 block">Min. Hours</Label>
            <Input type="number" min={1} max={24} value={form.minimum_hours}
              onChange={e => set('minimum_hours', e.target.value)} />
          </div>
          <div className="flex items-end">
            {estimatedTotal != null ? (
              <div className="w-full bg-muted/50 border border-border rounded-md px-3 py-2">
                <div className="text-[10px] text-muted-foreground">Estimated Total</div>
                <div className="text-base font-bold font-mono">{fmtAmt(estimatedTotal)}</div>
              </div>
            ) : (
              <div className="w-full bg-muted/20 border border-border rounded-md px-3 py-2 text-xs text-muted-foreground">
                Fill rate + times
              </div>
            )}
          </div>
        </div>

        {/* Interpreter */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <Label className="flex items-center gap-1.5"><User className="w-3.5 h-3.5" /> Interpreter (optional)</Label>
            {loadingInterps && <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />}
            {!loadingInterps && (form.source_language || form.target_language) && (
              <button type="button" onClick={fetchAvailableInterps}
                className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1">
                <RefreshCw className="w-3 h-3" /> Refresh
              </button>
            )}
          </div>

          {/* Conflict warning */}
          {conflict && (
            <div className="mb-2 p-2 rounded-md bg-warning/10 border border-warning/30 text-warning text-xs flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>This interpreter has a conflicting assignment during the selected time slot.</span>
            </div>
          )}

          <div className="border border-input rounded-md max-h-48 overflow-y-auto">
            {/* Unassigned option */}
            <button type="button" onClick={() => set('interpreter', '')}
              className={cn('w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-muted transition-colors border-b border-border',
                !form.interpreter && 'bg-muted/50')}>
              <div className={cn('w-4 h-4 rounded-full border flex items-center justify-center',
                !form.interpreter ? 'bg-primary border-primary' : 'border-border')}>
                {!form.interpreter && <Check className="w-3 h-3 text-primary-foreground" />}
              </div>
              <span className="text-muted-foreground text-sm">Leave unassigned</span>
            </button>

            {availableInterps.length === 0 && !loadingInterps ? (
              <div className="px-3 py-4 text-sm text-muted-foreground text-center">
                {(form.source_language || form.target_language)
                  ? 'No available interpreters for selected criteria'
                  : 'Select languages to see available interpreters'}
              </div>
            ) : availableInterps.map(interp => {
              const name = `${interp.first_name || ''} ${interp.last_name || ''}`.trim() || interp.user_email;
              const selected = String(form.interpreter) === String(interp.id);
              const langs = interp.languages?.map(l => l.name || l).join(', ') || '';
              return (
                <button key={interp.id} type="button" onClick={() => set('interpreter', interp.id)}
                  className={cn('w-full px-3 py-2.5 text-left text-sm flex items-center gap-3 hover:bg-muted transition-colors border-b border-border/50 last:border-0',
                    selected && 'bg-primary/5')}>
                  <div className={cn('w-4 h-4 rounded-full border flex-shrink-0 flex items-center justify-center',
                    selected ? 'bg-primary border-primary' : 'border-border')}>
                    {selected && <Check className="w-3 h-3 text-primary-foreground" />}
                  </div>
                  <div className="w-9 h-9 rounded-full bg-navy text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
                    {name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{name}</div>
                    <div className="text-xs text-muted-foreground truncate">{langs}</div>
                    <div className="text-[10px] text-muted-foreground">{interp.city}{interp.state ? `, ${interp.state}` : ''}</div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    {interp.avg_rating != null && (
                      <div className="flex items-center gap-0.5 text-gold justify-end">
                        <Star className="w-3 h-3 fill-gold" />
                        <span className="text-xs font-mono">{parseFloat(interp.avg_rating).toFixed(1)}</span>
                      </div>
                    )}
                    {interp.hourly_rate && (
                      <div className="text-xs text-muted-foreground font-mono">${interp.hourly_rate}/hr</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Notes */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="mb-1.5 block">Internal Notes</Label>
            <Textarea placeholder="Internal notes…" value={form.notes}
              onChange={e => set('notes', e.target.value)} rows={3} />
          </div>
          <div>
            <Label className="mb-1.5 block">Special Requirements</Label>
            <Textarea placeholder="Special requirements for the client or interpreter…"
              value={form.special_requirements}
              onChange={e => set('special_requirements', e.target.value)} rows={3} />
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default MissionFormModal;
