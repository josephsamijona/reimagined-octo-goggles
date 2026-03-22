// JHBridge — Mission Form Modal (Create / Edit)
// • Google Places autocomplete for street address (auto-fills city, state, zip)
// • State dropdown (50 states + DC)
// • Timezone-aware datetime: times are entered in the ASSIGNMENT'S local timezone,
//   automatically converted to/from UTC on save/load.
import { useState, useEffect, useCallback, useRef } from 'react';
import { useJsApiLoader } from '@react-google-maps/api';
import { Modal } from '@/components/shared/Modal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { showToast } from '@/components/shared/Toast';
import { dispatchService } from '@/services/dispatchService';
import {
  Calendar, Clock, MapPin, Building2, Languages,
  User, Star, Check, Loader2, AlertTriangle, RefreshCw, Globe,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const GMAPS_LIBS = ['places'];

const US_STATES = [
  { code: 'AL', name: 'Alabama' },       { code: 'AK', name: 'Alaska' },
  { code: 'AZ', name: 'Arizona' },       { code: 'AR', name: 'Arkansas' },
  { code: 'CA', name: 'California' },    { code: 'CO', name: 'Colorado' },
  { code: 'CT', name: 'Connecticut' },   { code: 'DE', name: 'Delaware' },
  { code: 'DC', name: 'Dist. of Columbia' },
  { code: 'FL', name: 'Florida' },       { code: 'GA', name: 'Georgia' },
  { code: 'HI', name: 'Hawaii' },        { code: 'ID', name: 'Idaho' },
  { code: 'IL', name: 'Illinois' },      { code: 'IN', name: 'Indiana' },
  { code: 'IA', name: 'Iowa' },          { code: 'KS', name: 'Kansas' },
  { code: 'KY', name: 'Kentucky' },      { code: 'LA', name: 'Louisiana' },
  { code: 'ME', name: 'Maine' },         { code: 'MD', name: 'Maryland' },
  { code: 'MA', name: 'Massachusetts' }, { code: 'MI', name: 'Michigan' },
  { code: 'MN', name: 'Minnesota' },     { code: 'MS', name: 'Mississippi' },
  { code: 'MO', name: 'Missouri' },      { code: 'MT', name: 'Montana' },
  { code: 'NE', name: 'Nebraska' },      { code: 'NV', name: 'Nevada' },
  { code: 'NH', name: 'New Hampshire' }, { code: 'NJ', name: 'New Jersey' },
  { code: 'NM', name: 'New Mexico' },    { code: 'NY', name: 'New York' },
  { code: 'NC', name: 'North Carolina' },{ code: 'ND', name: 'North Dakota' },
  { code: 'OH', name: 'Ohio' },          { code: 'OK', name: 'Oklahoma' },
  { code: 'OR', name: 'Oregon' },        { code: 'PA', name: 'Pennsylvania' },
  { code: 'RI', name: 'Rhode Island' },  { code: 'SC', name: 'South Carolina' },
  { code: 'SD', name: 'South Dakota' },  { code: 'TN', name: 'Tennessee' },
  { code: 'TX', name: 'Texas' },         { code: 'UT', name: 'Utah' },
  { code: 'VT', name: 'Vermont' },       { code: 'VA', name: 'Virginia' },
  { code: 'WA', name: 'Washington' },    { code: 'WV', name: 'West Virginia' },
  { code: 'WI', name: 'Wisconsin' },     { code: 'WY', name: 'Wyoming' },
  { code: 'PR', name: 'Puerto Rico' },   { code: 'GU', name: 'Guam' },
  { code: 'VI', name: 'U.S. Virgin Islands' },
];

// Primary IANA timezone per state — uses dominant timezone for split-tz states
const STATE_TIMEZONES = {
  AL: 'America/Chicago',       AK: 'America/Anchorage',
  AZ: 'America/Phoenix',       AR: 'America/Chicago',
  CA: 'America/Los_Angeles',   CO: 'America/Denver',
  CT: 'America/New_York',      DE: 'America/New_York',
  DC: 'America/New_York',      FL: 'America/New_York',
  GA: 'America/New_York',      HI: 'Pacific/Honolulu',
  ID: 'America/Boise',         IL: 'America/Chicago',
  IN: 'America/Indiana/Indianapolis',
  IA: 'America/Chicago',       KS: 'America/Chicago',
  KY: 'America/New_York',      LA: 'America/Chicago',
  ME: 'America/New_York',      MD: 'America/New_York',
  MA: 'America/New_York',      MI: 'America/Detroit',
  MN: 'America/Chicago',       MS: 'America/Chicago',
  MO: 'America/Chicago',       MT: 'America/Denver',
  NE: 'America/Chicago',       NV: 'America/Los_Angeles',
  NH: 'America/New_York',      NJ: 'America/New_York',
  NM: 'America/Denver',        NY: 'America/New_York',
  NC: 'America/New_York',      ND: 'America/Chicago',
  OH: 'America/New_York',      OK: 'America/Chicago',
  OR: 'America/Los_Angeles',   PA: 'America/New_York',
  RI: 'America/New_York',      SC: 'America/New_York',
  SD: 'America/Chicago',       TN: 'America/Chicago',
  TX: 'America/Chicago',       UT: 'America/Denver',
  VT: 'America/New_York',      VA: 'America/New_York',
  WA: 'America/Los_Angeles',   WV: 'America/New_York',
  WI: 'America/Chicago',       WY: 'America/Denver',
  PR: 'America/Puerto_Rico',   GU: 'Pacific/Guam',
  VI: 'America/St_Thomas',
};

// ---------------------------------------------------------------------------
// Timezone utilities
// ---------------------------------------------------------------------------

/** Offset in ms (local − UTC) for a given IANA timezone at a given Date. */
function tzOffsetMs(date, ianaTz) {
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: ianaTz,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  });
  const p = Object.fromEntries(fmt.formatToParts(date).map(x => [x.type, x.value]));
  const h = p.hour === '24' ? '0' : p.hour;
  const localMs = Date.UTC(+p.year, +p.month - 1, +p.day, +h, +p.minute, +p.second);
  return localMs - date.getTime();
}

/**
 * Interpret a datetime-local string ("2026-03-21T14:00") as wall-clock time
 * in `ianaTz` and return the corresponding UTC ISO string.
 * Falls back to browser-local interpretation if ianaTz is missing.
 */
export function localToUTC(dtlStr, ianaTz) {
  if (!dtlStr) return '';
  if (!ianaTz) return new Date(dtlStr).toISOString();

  const [datePart, timePart] = dtlStr.split('T');
  const [yr, mo, dy] = datePart.split('-').map(Number);
  const [hr, mn] = timePart.split(':').map(Number);

  // Treat the wall-clock components as UTC initially (approximate)
  const approxMs = Date.UTC(yr, mo - 1, dy, hr, mn, 0);
  const approx = new Date(approxMs);

  // Find the tz offset at this approximate UTC time
  const off1 = tzOffsetMs(approx, ianaTz);
  const corrected = new Date(approxMs - off1);

  // DST boundary correction: verify the local representation matches
  const off2 = tzOffsetMs(corrected, ianaTz);
  if (off2 !== off1) {
    return new Date(approxMs - off2).toISOString();
  }
  return corrected.toISOString();
}

/**
 * Convert a UTC ISO string to a datetime-local string ("2026-03-21T14:00")
 * displayed in the given IANA timezone.
 */
export function utcToLocal(isoStr, ianaTz) {
  if (!isoStr) return '';
  const date = new Date(isoStr);
  const tz = ianaTz || Intl.DateTimeFormat().resolvedOptions().timeZone;
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: tz,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
    hour12: false,
  });
  const p = Object.fromEntries(fmt.formatToParts(date).map(x => [x.type, x.value]));
  const h = p.hour === '24' ? '00' : p.hour;
  return `${p.year}-${p.month}-${p.day}T${h}:${p.minute}`;
}

/** Short timezone abbreviation (e.g. "EST", "PDT"). */
function tzAbbr(ianaTz) {
  if (!ianaTz) return '';
  return new Intl.DateTimeFormat('en-US', { timeZone: ianaTz, timeZoneName: 'short' })
    .formatToParts(new Date())
    .find(p => p.type === 'timeZoneName')?.value || ianaTz;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const fmtAmt = (v) => v != null ? `$${parseFloat(v).toFixed(2)}` : '—';

const EMPTY_FORM = {
  client: '', client_name: '', client_email: '', client_phone: '',
  service_type: '', source_language: '', target_language: '',
  location: '', city: '', state: '', zip_code: '',
  start_time: '', end_time: '',
  interpreter: '', interpreter_rate: '', minimum_hours: 2,
  notes: '', special_requirements: '',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
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

  // Google Maps / Places
  const { isLoaded: gmLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '',
    libraries: GMAPS_LIBS,
  });
  const addressInputRef = useRef(null);
  const autocompleteRef = useRef(null);

  // Derived timezone from selected state
  const assignmentTz = STATE_TIMEZONES[form.state] || 'America/New_York'; // default to ET (company HQ)
  const tzLabel = form.state ? `${tzAbbr(assignmentTz)} — ${assignmentTz}` : 'ET (default)';

  // Estimated total
  const estimatedTotal = (() => {
    const rate = parseFloat(form.interpreter_rate) || 0;
    const start = form.start_time ? new Date(localToUTC(form.start_time, assignmentTz)) : null;
    const end = form.end_time ? new Date(localToUTC(form.end_time, assignmentTz)) : null;
    if (!rate || !start || !end || end <= start) return null;
    const hours = (end - start) / 3600000;
    const billable = Math.max(hours, parseFloat(form.minimum_hours) || 2);
    return rate * billable;
  })();

  // ---- Google Places Autocomplete ----------------------------------------
  useEffect(() => {
    if (!isOpen || !gmLoaded || !addressInputRef.current) return;
    if (autocompleteRef.current) return; // already attached

    const ac = new window.google.maps.places.Autocomplete(addressInputRef.current, {
      types: ['address'],
      componentRestrictions: { country: 'us' },
      fields: ['address_components', 'formatted_address', 'geometry'],
    });

    ac.addListener('place_changed', () => {
      const place = ac.getPlace();
      if (!place?.address_components) return;

      let streetNumber = '', route = '', city = '', state = '', zip = '';
      for (const comp of place.address_components) {
        const types = comp.types;
        if (types.includes('street_number')) streetNumber = comp.long_name;
        else if (types.includes('route')) route = comp.long_name;
        else if (types.includes('locality')) city = comp.long_name;
        else if (types.includes('administrative_area_level_1')) state = comp.short_name;
        else if (types.includes('postal_code')) zip = comp.long_name;
      }

      const street = [streetNumber, route].filter(Boolean).join(' ');
      setForm(prev => ({
        ...prev,
        location: street || place.formatted_address || prev.location,
        city: city || prev.city,
        state: state || prev.state,
        zip_code: zip || prev.zip_code,
      }));
      setErrors(prev => ({ ...prev, city: null, location: null }));
    });

    autocompleteRef.current = ac;
  }, [isOpen, gmLoaded]);

  // Cleanup autocomplete on close
  useEffect(() => {
    if (!isOpen) {
      autocompleteRef.current = null;
    }
  }, [isOpen]);

  // ---- Load dropdowns on open --------------------------------------------
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

  // ---- Initialize form for edit or prefill --------------------------------
  useEffect(() => {
    if (!isOpen) return;
    if (mission) {
      const missionTz = STATE_TIMEZONES[mission.state] || 'America/New_York';
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
        // Convert UTC → assignment's local timezone for display
        start_time: utcToLocal(mission.start_time, missionTz),
        end_time: utcToLocal(mission.end_time, missionTz),
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

  // ---- Auto-fill rate from service type ----------------------------------
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

  // ---- Available interpreters --------------------------------------------
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

  // ---- Conflict detection -------------------------------------------------
  useEffect(() => {
    if (!form.interpreter || !form.start_time || !form.end_time) { setConflict(null); return; }
    dispatchService.checkConflict(
      form.interpreter,
      localToUTC(form.start_time, assignmentTz),
      localToUTC(form.end_time, assignmentTz),
      mission?.id || null,
    ).then(res => setConflict(res.data?.has_conflict ? res.data.conflicts : null))
      .catch(() => setConflict(null));
  }, [form.interpreter, form.start_time, form.end_time, mission?.id, assignmentTz]);

  const set = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: null }));
  };

  // ---- Validation ---------------------------------------------------------
  const validate = () => {
    const e = {};
    if (!useManualClient && !form.client) e.client = 'Client required';
    if (useManualClient && !form.client_name) e.client_name = 'Name required';
    if (!form.service_type) e.service_type = 'Service type required';
    if (!form.source_language) e.source_language = 'Required';
    if (!form.target_language) e.target_language = 'Required';
    if (!form.city) e.city = 'City required';
    if (!form.state) e.state = 'State required';
    if (!form.start_time) e.start_time = 'Required';
    if (!form.end_time) e.end_time = 'Required';
    if (form.start_time && form.end_time) {
      const s = new Date(localToUTC(form.start_time, assignmentTz));
      const en = new Date(localToUTC(form.end_time, assignmentTz));
      if (en <= s) e.end_time = 'End must be after start';
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  // ---- Submit -------------------------------------------------------------
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
        // Convert from assignment's local tz → UTC before sending to backend
        start_time: localToUTC(form.start_time, assignmentTz),
        end_time: localToUTC(form.end_time, assignmentTz),
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

  // ---- Render -------------------------------------------------------------
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

        {/* ── Client ──────────────────────────────────────────────────── */}
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
                {clients.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.company_name || c.user_name}{c.city ? ` — ${c.city}` : ''}
                  </option>
                ))}
              </select>
              {errors.client && <p className="text-xs text-danger mt-0.5">{errors.client}</p>}
            </>
          )}
        </div>

        {/* ── Service type ────────────────────────────────────────────── */}
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

        {/* ── Languages ───────────────────────────────────────────────── */}
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

        {/* ── Location ────────────────────────────────────────────────── */}
        <div>
          <Label className="flex items-center gap-1.5 mb-1.5">
            <MapPin className="w-3.5 h-3.5" /> Location *
            {gmLoaded && (
              <span className="text-[10px] text-muted-foreground font-normal ml-1">
                — start typing for address suggestions
              </span>
            )}
          </Label>

          {/* Smart address input — Places Autocomplete attaches here */}
          <div className="relative mb-2">
            <MapPin className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
            <input
              ref={addressInputRef}
              type="text"
              placeholder="Street address…"
              defaultValue={form.location}
              onBlur={e => set('location', e.target.value)}
              className="w-full pl-8 pr-3 py-2 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>

          {/* City / State / ZIP row */}
          <div className="grid grid-cols-5 gap-2">
            <div className="col-span-2">
              <Input
                placeholder="City *"
                value={form.city}
                onChange={e => set('city', e.target.value)}
                className={cn(errors.city && 'border-danger')}
              />
              {errors.city && <p className="text-xs text-danger mt-0.5">{errors.city}</p>}
            </div>
            <div>
              <select
                value={form.state}
                onChange={e => set('state', e.target.value)}
                className={cn(
                  'w-full h-10 px-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-ring',
                  errors.state ? 'border-danger' : 'border-input',
                )}>
                <option value="">State *</option>
                {US_STATES.map(s => (
                  <option key={s.code} value={s.code}>{s.code} — {s.name}</option>
                ))}
              </select>
              {errors.state && <p className="text-xs text-danger mt-0.5">{errors.state}</p>}
            </div>
            <div className="col-span-2">
              <Input
                placeholder="ZIP code"
                value={form.zip_code}
                onChange={e => set('zip_code', e.target.value)}
                maxLength={10}
              />
            </div>
          </div>
        </div>

        {/* ── Schedule ────────────────────────────────────────────────── */}
        <div>
          {/* Timezone banner */}
          <div className={cn(
            'flex items-center gap-1.5 mb-2 text-xs rounded-md px-2.5 py-1.5 border',
            form.state
              ? 'bg-blue-500/5 border-blue-500/20 text-blue-600 dark:text-blue-400'
              : 'bg-muted/50 border-border text-muted-foreground',
          )}>
            <Globe className="w-3.5 h-3.5 flex-shrink-0" />
            <span>
              {form.state
                ? <>Times are in <strong>{tzLabel}</strong> — the assignment's local timezone</>
                : 'Select a state to set the correct timezone for this mission'
              }
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="flex items-center gap-1.5 mb-1.5">
                <Calendar className="w-3.5 h-3.5" /> Start *
              </Label>
              <Input
                type="datetime-local"
                value={form.start_time}
                onChange={e => set('start_time', e.target.value)}
                className={cn(errors.start_time && 'border-danger')}
              />
              {errors.start_time && <p className="text-xs text-danger mt-0.5">{errors.start_time}</p>}
            </div>
            <div>
              <Label className="flex items-center gap-1.5 mb-1.5">
                <Clock className="w-3.5 h-3.5" /> End *
              </Label>
              <Input
                type="datetime-local"
                value={form.end_time}
                onChange={e => set('end_time', e.target.value)}
                className={cn(errors.end_time && 'border-danger')}
              />
              {errors.end_time && <p className="text-xs text-danger mt-0.5">{errors.end_time}</p>}
            </div>
          </div>
        </div>

        {/* ── Rate & min hours ─────────────────────────────────────────── */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label className="mb-1.5 block">Rate ($/hr)</Label>
            <Input type="number" min={0} step={0.5} placeholder="0.00"
              value={form.interpreter_rate}
              onChange={e => set('interpreter_rate', e.target.value)} />
          </div>
          <div>
            <Label className="mb-1.5 block">Min. Hours</Label>
            <Input type="number" min={1} max={24}
              value={form.minimum_hours}
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

        {/* ── Interpreter ─────────────────────────────────────────────── */}
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

          {conflict && (
            <div className="mb-2 p-2 rounded-md bg-warning/10 border border-warning/30 text-warning text-xs flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>This interpreter has a conflicting assignment during the selected time slot.</span>
            </div>
          )}

          <div className="border border-input rounded-md max-h-48 overflow-y-auto">
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
                    <div className="text-[10px] text-muted-foreground">
                      {interp.city}{interp.state ? `, ${interp.state}` : ''}
                      {interp.state && STATE_TIMEZONES[interp.state] && (
                        <span className="ml-1 text-blue-500">({tzAbbr(STATE_TIMEZONES[interp.state])})</span>
                      )}
                    </div>
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

        {/* ── Notes ───────────────────────────────────────────────────── */}
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
