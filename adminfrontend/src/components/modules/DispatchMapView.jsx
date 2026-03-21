// JHBridge — Dispatch Map View
// Shows active assignment pins + interpreter location pins on a shared Google Map.
import { useState, useEffect, useCallback, useMemo } from 'react';
import { GoogleMap, useJsApiLoader, Marker, InfoWindow } from '@react-google-maps/api';
import { Loader2, MapPin, User, AlertTriangle } from 'lucide-react';
import { dispatchService } from '@/services/dispatchService';
import { cn } from '@/lib/utils';

const GMAPS_LIBRARIES = ['places'];
const MAP_CONTAINER = { width: '100%', height: '560px', borderRadius: '0.5rem' };
const US_CENTER = { lat: 39.8283, lng: -98.5795 };

const STATUS_COLORS = {
  PENDING:     '#FFA500',
  CONFIRMED:   '#3B82F6',
  IN_PROGRESS: '#8B5CF6',
  COMPLETED:   '#10B981',
  CANCELLED:   '#EF4444',
  NO_SHOW:     '#6B7280',
};

const INTERP_COLORS = {
  available:  '#10b981',
  on_mission: '#eab308',
  blocked:    '#ef4444',
};

const darkMapStyle = [
  { elementType: 'geometry', stylers: [{ color: '#242f3e' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#242f3e' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#746855' }] },
  { featureType: 'administrative.locality', elementType: 'labels.text.fill', stylers: [{ color: '#d59563' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#38414e' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#746855' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#17263c' }] },
];

// ---------------------------------------------------------------------------
// localStorage geocoding cache — 7-day TTL
// ---------------------------------------------------------------------------
const GEO_CACHE_KEY = 'jh_dispatch_geo_v1';
const GEO_TTL = 7 * 24 * 60 * 60 * 1000;

const loadGeoCache = () => {
  try {
    const raw = localStorage.getItem(GEO_CACHE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    const now = Date.now();
    const valid = {};
    for (const [k, v] of Object.entries(parsed)) {
      if (v.exp > now) valid[k] = v;
    }
    return valid;
  } catch { return {}; }
};

const saveGeoCache = (c) => {
  try { localStorage.setItem(GEO_CACHE_KEY, JSON.stringify(c)); } catch {}
};

const geocodeAddress = (geocoder, address) =>
  new Promise((resolve) => {
    geocoder.geocode({ address }, (results, status) => {
      if (status === 'OK' && results[0]) {
        const loc = results[0].geometry.location;
        resolve({ lat: loc.lat(), lng: loc.lng() });
      } else {
        resolve(null);
      }
    });
  });

const geocodeBatch = async (geocoder, items, geoCache) => {
  const results = {};
  const now = Date.now();
  const BATCH = 5;
  for (let i = 0; i < items.length; i += BATCH) {
    const chunk = items.slice(i, i + BATCH);
    const resolved = await Promise.all(
      chunk.map(async ({ key, address }) => {
        if (geoCache[address]) return { key, pos: geoCache[address].pos };
        const pos = await geocodeAddress(geocoder, address);
        if (pos) geoCache[address] = { pos, exp: now + GEO_TTL };
        return { key, pos };
      })
    );
    for (const { key, pos } of resolved) {
      if (pos) results[key] = pos;
    }
    if (i + BATCH < items.length) await new Promise(r => setTimeout(r, 200));
  }
  saveGeoCache(geoCache);
  return results;
};

// ---------------------------------------------------------------------------
// Build a colored SVG marker icon string
// ---------------------------------------------------------------------------
const buildSvgIcon = (color, shape = 'circle') => {
  if (shape === 'pin') {
    // Drop-pin for assignments
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='24' height='32' viewBox='0 0 24 32'>
      <path d='M12 0C5.37 0 0 5.37 0 12c0 9 12 20 12 20s12-11 12-20C24 5.37 18.63 0 12 0z' fill='${color}' stroke='#fff' stroke-width='2'/>
      <circle cx='12' cy='12' r='5' fill='#fff'/>
    </svg>`;
    return { url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`, anchor: { x: 12, y: 32 } };
  }
  // Circle for interpreters
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='22' height='22' viewBox='0 0 22 22'>
    <circle cx='11' cy='11' r='9' fill='${color}' stroke='#fff' stroke-width='2.5'/>
    <circle cx='11' cy='11' r='4' fill='#fff'/>
  </svg>`;
  return { url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`, anchor: { x: 11, y: 11 } };
};

// ---------------------------------------------------------------------------
// Layer legend
// ---------------------------------------------------------------------------
const Legend = ({ showAssignments, showInterpreters }) => (
  <div className="absolute bottom-4 left-4 z-10 bg-background/95 border border-border rounded-lg px-3 py-2.5 text-xs space-y-1 shadow-lg min-w-[160px]">
    {showAssignments && (
      <>
        <div className="font-semibold text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">Missions</div>
        {Object.entries(STATUS_COLORS).map(([s, c]) => (
          <div key={s} className="flex items-center gap-2">
            <svg width="12" height="16" viewBox="0 0 12 16">
              <path d="M6 0C2.69 0 0 2.69 0 6c0 4.5 6 10 6 10s6-5.5 6-10C12 2.69 9.31 0 6 0z" fill={c}/>
            </svg>
            <span>{s.replace('_', ' ')}</span>
          </div>
        ))}
      </>
    )}
    {showAssignments && showInterpreters && <div className="border-t border-border my-1" />}
    {showInterpreters && (
      <>
        <div className="font-semibold text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">Interpreters</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#10b981] inline-block" /> Available</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#eab308] inline-block" /> On Mission</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#ef4444] inline-block" /> Blocked</div>
      </>
    )}
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export const DispatchMapView = ({ onAssignmentClick }) => {
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '',
    libraries: GMAPS_LIBRARIES,
  });

  const [assignments, setAssignments] = useState([]);
  const [interpreters, setInterpreters] = useState([]);
  const [assignmentPositions, setAssignmentPositions] = useState({});
  const [activeMarker, setActiveMarker] = useState(null); // { type: 'assignment'|'interpreter', id }
  const [loading, setLoading] = useState(true);
  const [geocoding, setGeocoding] = useState(false);

  // Layer toggles
  const [showAssignments, setShowAssignments] = useState(true);
  const [showInterpreters, setShowInterpreters] = useState(true);
  const [statusFilter, setStatusFilter] = useState(''); // '' = all active

  // Fetch data: assignments + active interpreters (InterpreterListSerializer includes lat/lng)
  useEffect(() => {
    setLoading(true);
    Promise.all([
      dispatchService.getAssignments({ page_size: 200, ordering: '-start_time' }),
      dispatchService.getInterpretersForMap(),
    ]).then(([assRes, interpRes]) => {
      setAssignments(assRes.data?.results || assRes.data || []);
      const list = interpRes.data?.results || interpRes.data || [];
      // Only include interpreters with actual GPS coordinates from their last location ping
      setInterpreters(Array.isArray(list) ? list.filter(i => i.lat && i.lng) : []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  // Geocode assignments that only have city/state
  const geocodeAssignments = useCallback(async () => {
    if (!isLoaded || !window.google || assignments.length === 0) return;
    const geocoder = new window.google.maps.Geocoder();
    const geoCache = loadGeoCache();

    const cacheHits = {};
    const toFetch = [];

    for (const a of assignments) {
      const address = [a.location, a.city, a.state].filter(Boolean).join(', ');
      if (!address) continue;
      const key = `asgn-${a.id}`;
      if (geoCache[address]) {
        cacheHits[key] = geoCache[address].pos;
      } else {
        toFetch.push({ key, address });
      }
    }

    if (Object.keys(cacheHits).length > 0) {
      setAssignmentPositions(prev => ({ ...prev, ...cacheHits }));
    }

    if (toFetch.length === 0) return;

    setGeocoding(true);
    const fresh = await geocodeBatch(geocoder, toFetch, geoCache);
    setAssignmentPositions(prev => ({ ...prev, ...fresh }));
    setGeocoding(false);
  }, [isLoaded, assignments]);

  useEffect(() => { geocodeAssignments(); }, [geocodeAssignments]);

  // Filtered assignments for map display
  const visibleAssignments = useMemo(() => {
    const active = ['PENDING', 'CONFIRMED', 'IN_PROGRESS'];
    return assignments.filter(a => {
      const matchStatus = statusFilter ? a.status === statusFilter : active.includes(a.status);
      const pos = assignmentPositions[`asgn-${a.id}`];
      return matchStatus && pos;
    });
  }, [assignments, assignmentPositions, statusFilter]);

  // Interpreters with valid lat/lng
  const visibleInterpreters = useMemo(() =>
    interpreters.filter(i => i.lat && i.lng),
  [interpreters]);

  const activeAssignment = useMemo(() => {
    if (activeMarker?.type !== 'assignment') return null;
    return assignments.find(a => a.id === activeMarker.id) || null;
  }, [activeMarker, assignments]);

  const activeInterpreter = useMemo(() => {
    if (activeMarker?.type !== 'interpreter') return null;
    return interpreters.find(i => i.id === activeMarker.id) || null;
  }, [activeMarker, interpreters]);

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-danger border border-danger/20 rounded-lg bg-danger/5 gap-2">
        <AlertTriangle className="w-8 h-8" />
        <span className="text-sm font-medium">Failed to load Google Maps</span>
        <span className="text-xs text-muted-foreground">Please verify VITE_GOOGLE_MAPS_API_KEY is set</span>
      </div>
    );
  }

  if (!isLoaded || loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground border border-border rounded-lg bg-card/50">
        <Loader2 className="w-6 h-6 animate-spin mr-2" />
        {!isLoaded ? 'Loading map…' : 'Fetching mission data…'}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="checkbox" checked={showAssignments} onChange={e => setShowAssignments(e.target.checked)}
              className="accent-primary w-3.5 h-3.5" />
            <MapPin className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-xs">Missions</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="checkbox" checked={showInterpreters} onChange={e => setShowInterpreters(e.target.checked)}
              className="accent-primary w-3.5 h-3.5" />
            <User className="w-3.5 h-3.5 text-emerald-500" />
            <span className="text-xs">Interpreters</span>
          </label>
        </div>
        {showAssignments && (
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="h-7 text-xs rounded-md border border-border bg-background px-2 pr-6 focus:outline-none">
            <option value="">Active missions</option>
            {['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'].map(s => (
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            ))}
          </select>
        )}
        <span className="text-xs text-muted-foreground ml-auto">
          {visibleAssignments.length} mission{visibleAssignments.length !== 1 ? 's' : ''}
          {showInterpreters && ` · ${visibleInterpreters.length} interpreter${visibleInterpreters.length !== 1 ? 's' : ''}`}
          {geocoding && <> · <Loader2 className="w-3 h-3 animate-spin inline ml-1" /> Geocoding…</>}
        </span>
      </div>

      {/* Map */}
      <div className="relative rounded-lg overflow-hidden border border-border shadow-sm">
        <GoogleMap
          mapContainerStyle={MAP_CONTAINER}
          zoom={4}
          center={US_CENTER}
          options={{ disableDefaultUI: false, zoomControl: true, styles: darkMapStyle }}
          onClick={() => setActiveMarker(null)}
        >
          {/* Assignment pins */}
          {showAssignments && visibleAssignments.map(a => {
            const pos = assignmentPositions[`asgn-${a.id}`];
            if (!pos) return null;
            const color = STATUS_COLORS[a.status] || '#6B7280';
            const icon = buildSvgIcon(color, 'pin');
            return (
              <Marker
                key={`a-${a.id}`}
                position={pos}
                icon={{ url: icon.url, anchor: isLoaded && window.google ? new window.google.maps.Point(icon.anchor.x, icon.anchor.y) : undefined }}
                zIndex={20}
                onClick={() => setActiveMarker({ type: 'assignment', id: a.id })}
                title={`#${a.id} — ${a.client_display || ''}`}
              >
                {activeMarker?.type === 'assignment' && activeMarker.id === a.id && (
                  <InfoWindow onCloseClick={() => setActiveMarker(null)}>
                    <div className="p-1 min-w-[200px] font-sans text-gray-900">
                      <div className="font-bold text-sm mb-0.5">Mission #{a.id}</div>
                      <div className="text-xs text-gray-500 mb-1">{a.city}{a.state ? `, ${a.state}` : ''}</div>
                      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs mb-2">
                        <span className="text-gray-500">Status</span>
                        <span className="font-semibold" style={{ color }}>{a.status.replace('_', ' ')}</span>
                        <span className="text-gray-500">Client</span>
                        <span className="truncate">{a.client_display || '—'}</span>
                        <span className="text-gray-500">Interpreter</span>
                        <span className="truncate">{a.interpreter_name || <span className="text-orange-500">Unassigned</span>}</span>
                        {a.source_language_name && (
                          <>
                            <span className="text-gray-500">Lang</span>
                            <span>{a.source_language_name} → {a.target_language_name}</span>
                          </>
                        )}
                        {a.start_time && (
                          <>
                            <span className="text-gray-500">Start</span>
                            <span>{new Date(a.start_time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                          </>
                        )}
                      </div>
                      <button
                        className="w-full text-xs py-1 rounded bg-navy text-white hover:bg-navy-light transition-colors"
                        onClick={() => { onAssignmentClick(a); setActiveMarker(null); }}>
                        View Details →
                      </button>
                    </div>
                  </InfoWindow>
                )}
              </Marker>
            );
          })}

          {/* Interpreter pins */}
          {showInterpreters && visibleInterpreters.map(interp => {
            const interpStatus = interp.is_on_mission ? 'on_mission' : (interp.is_manually_blocked ? 'blocked' : 'available');
            const color = INTERP_COLORS[interpStatus] || INTERP_COLORS.available;
            const icon = buildSvgIcon(color, 'circle');
            const name = `${interp.first_name || ''} ${interp.last_name || ''}`.trim() || interp.user_email;
            return (
              <Marker
                key={`i-${interp.id}`}
                position={{ lat: parseFloat(interp.lat), lng: parseFloat(interp.lng) }}
                icon={{ url: icon.url, anchor: isLoaded && window.google ? new window.google.maps.Point(icon.anchor.x, icon.anchor.y) : undefined }}
                zIndex={10}
                onClick={() => setActiveMarker({ type: 'interpreter', id: interp.id })}
                title={name}
              >
                {activeMarker?.type === 'interpreter' && activeMarker.id === interp.id && (
                  <InfoWindow onCloseClick={() => setActiveMarker(null)}>
                    <div className="p-1 min-w-[180px] font-sans text-gray-900">
                      <div className="font-bold text-sm mb-0.5">{name}</div>
                      <div className="text-xs text-gray-500 mb-1.5">{interp.city}{interp.state ? `, ${interp.state}` : ''}</div>
                      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs mb-1.5">
                        <span className="text-gray-500">Status</span>
                        <span className="font-semibold capitalize" style={{ color }}>{interpStatus.replace('_', ' ')}</span>
                        {interp.hourly_rate && (
                          <>
                            <span className="text-gray-500">Rate</span>
                            <span>${interp.hourly_rate}/hr</span>
                          </>
                        )}
                        {interp.radius_of_service && (
                          <>
                            <span className="text-gray-500">Radius</span>
                            <span>{interp.radius_of_service} mi</span>
                          </>
                        )}
                      </div>
                      {interp.languages?.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {interp.languages.slice(0, 4).map((l, i) => (
                            <span key={i} className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px] text-gray-700">
                              {l.name || l}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </InfoWindow>
                )}
              </Marker>
            );
          })}
        </GoogleMap>

        <Legend showAssignments={showAssignments} showInterpreters={showInterpreters} />
      </div>

      {/* Empty state */}
      {visibleAssignments.length === 0 && visibleInterpreters.length === 0 && (
        <div className="text-center text-sm text-muted-foreground py-4">
          No geocodable locations found. Ensure missions have a city and state.
        </div>
      )}
    </div>
  );
};

export default DispatchMapView;
