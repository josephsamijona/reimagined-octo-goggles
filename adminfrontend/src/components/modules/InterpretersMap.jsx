import { useState, useEffect, useCallback } from "react";
import { GoogleMap, useJsApiLoader, Marker, InfoWindow, Circle } from "@react-google-maps/api";
import { Loader2, Star } from "lucide-react";
import { Avatar } from "@/components/shared/UIComponents";
import { Button } from "@/components/ui/button";
import { interpreterService } from "@/services/interpreterService";

const GMAPS_LIBRARIES = ["places"];

const mapContainerStyle = { width: "100%", height: "100%", borderRadius: "0.5rem" };
const US_CENTER = { lat: 39.8283, lng: -98.5795 };
const MILES_TO_METERS = 1609.34;

const STATUS_COLORS = {
  available: { marker: "#10b981", circle: "#10b981" },
  on_mission: { marker: "#eab308", circle: "#eab308" },
  blocked: { marker: "#ef4444", circle: "#ef4444" },
};

const COVERAGE_CITY_COLOR = "#6366f1";

// ------------------------------------------------------------------
// localStorage geocoding cache — 7-day TTL, keyed by address string
// ------------------------------------------------------------------
const GEO_CACHE_KEY = "jh_geocode_v1";
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

// ------------------------------------------------------------------
// Geocode a single address
// ------------------------------------------------------------------
const geocodeAddress = (geocoder, address) =>
  new Promise((resolve) => {
    geocoder.geocode({ address }, (results, s) => {
      if (s === "OK" && results[0]) {
        const loc = results[0].geometry.location;
        resolve({ lat: loc.lat(), lng: loc.lng() });
      } else {
        resolve(null);
      }
    });
  });

// Geocode in parallel batches of 5, with 200ms pause between batches.
// Returns { [key]: { lat, lng } }. Mutates geoCache in place and persists it.
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

const darkMapStyle = [
  { elementType: "geometry", stylers: [{ color: "#242f3e" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#242f3e" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#746855" }] },
  { featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{ color: "#d59563" }] },
  { featureType: "poi", elementType: "labels.text.fill", stylers: [{ color: "#d59563" }] },
  { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#263c3f" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#38414e" }] },
  { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#212a37" }] },
  { featureType: "road", elementType: "labels.text.fill", stylers: [{ color: "#9ca5b3" }] },
  { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#746855" }] },
  { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#1f2835" }] },
  { featureType: "road.highway", elementType: "labels.text.fill", stylers: [{ color: "#f3d19c" }] },
  { featureType: "transit", elementType: "geometry", stylers: [{ color: "#2f3948" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#17263c" }] },
  { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#515c6d" }] },
];

export const InterpretersMap = ({ interpreters, onInterpreterClick }) => {
  const { isLoaded, loadError } = useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "",
    libraries: GMAPS_LIBRARIES,
  });

  const [mapData, setMapData] = useState([]);
  const [geocoded, setGeocoded] = useState({});
  const [coverageCities, setCoverageCities] = useState({});
  const [activeMarker, setActiveMarker] = useState(null);
  const [loadingGeo, setLoadingGeo] = useState(false);

  useEffect(() => {
    interpreterService.getMapData?.()
      .then(data => setMapData(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, []);

  // Geocode interpreter home addresses — cache hits applied immediately, new addresses fetched in parallel
  const geocodeAll = useCallback(async () => {
    if (!isLoaded || !window.google || interpreters.length === 0) return;
    const geocoder = new window.google.maps.Geocoder();
    const geoCache = loadGeoCache();

    const cacheHits = {};
    const toFetch = [];

    for (const interp of interpreters) {
      if (interp.lat && interp.lng) continue;
      const address = [interp.address, interp.city, interp.state].filter(Boolean).join(", ");
      if (!address) continue;
      if (geoCache[address]) {
        cacheHits[interp.id] = geoCache[address].pos;
      } else {
        toFetch.push({ key: interp.id, address });
      }
    }

    // Apply cache hits immediately (no spinner)
    if (Object.keys(cacheHits).length > 0) {
      setGeocoded(prev => ({ ...prev, ...cacheHits }));
    }

    if (toFetch.length === 0) return;

    setLoadingGeo(true);
    const fresh = await geocodeBatch(geocoder, toFetch, geoCache);
    setGeocoded(prev => ({ ...prev, ...fresh }));
    setLoadingGeo(false);
  }, [isLoaded, interpreters]);

  useEffect(() => { geocodeAll(); }, [geocodeAll]);

  // Geocode cities willing to cover
  const geocodeCoverageCities = useCallback(async () => {
    if (!isLoaded || !window.google || mapData.length === 0) return;
    const geocoder = new window.google.maps.Geocoder();
    const geoCache = loadGeoCache();

    const allItems = [];
    for (const mapInterp of mapData) {
      const cities = mapInterp.cities_willing_to_cover;
      if (!Array.isArray(cities) || cities.length === 0) continue;
      for (const cityName of cities) {
        const address = `${cityName}, ${mapInterp.state || "US"}`;
        allItems.push({ key: `${mapInterp.id}__${cityName}`, address, interpId: mapInterp.id, cityName });
      }
    }

    if (allItems.length === 0) return;

    const results = await geocodeBatch(geocoder, allItems, geoCache);

    const byInterp = {};
    for (const item of allItems) {
      const pos = results[item.key];
      if (!pos) continue;
      if (!byInterp[item.interpId]) byInterp[item.interpId] = [];
      byInterp[item.interpId].push({ lat: pos.lat, lng: pos.lng, name: item.cityName });
    }
    setCoverageCities(byInterp);
  }, [isLoaded, mapData]);

  useEffect(() => { geocodeCoverageCities(); }, [geocodeCoverageCities]);

  const getMarkerIcon = (status) => {
    const color = STATUS_COLORS[status]?.marker || STATUS_COLORS.available.marker;
    return {
      path: window.google.maps.SymbolPath.CIRCLE,
      fillColor: color,
      fillOpacity: 0.95,
      scale: 9,
      strokeColor: "#ffffff",
      strokeWeight: 2,
    };
  };

  const getCoverageCityIcon = () => ({
    path: window.google.maps.SymbolPath.CIRCLE,
    fillColor: COVERAGE_CITY_COLOR,
    fillOpacity: 0.6,
    scale: 5,
    strokeColor: "#ffffff",
    strokeWeight: 1.5,
  });

  if (loadError) {
    return (
      <div className="w-full h-[600px] flex items-center justify-center p-8 text-center text-danger border border-danger/20 rounded-lg bg-danger/5">
        Failed to load Google Maps. Please verify your API key.
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div className="w-full h-[600px] flex items-center justify-center text-muted-foreground border border-border rounded-lg bg-card/50">
        <Loader2 className="w-8 h-8 animate-spin text-gold" />
      </div>
    );
  }

  const plottable = interpreters.map(interp => {
    const lat = interp.lat ?? geocoded[interp.id]?.lat ?? null;
    const lng = interp.lng ?? geocoded[interp.id]?.lng ?? null;
    const mapExtra = mapData.find(m => m.id === interp.id) || {};
    return { ...interp, lat, lng, _map: mapExtra };
  }).filter(i => i.lat && i.lng);

  return (
    <div className="relative w-full h-[600px] rounded-lg overflow-hidden border border-border bg-card shadow-sm">
      {loadingGeo && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 bg-background/90 border border-border rounded-full px-3 py-1 flex items-center gap-2 text-xs text-muted-foreground shadow">
          <Loader2 className="w-3 h-3 animate-spin" /> Geocoding new addresses…
        </div>
      )}
      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-10 bg-background/90 border border-border rounded-lg px-3 py-2 text-xs space-y-1 shadow">
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#10b981] inline-block" /> Available</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#eab308] inline-block" /> On Mission</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#ef4444] inline-block" /> Blocked</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#6366f1] inline-block" /> City covered</div>
      </div>

      <GoogleMap
        mapContainerStyle={mapContainerStyle}
        zoom={4}
        center={US_CENTER}
        options={{ disableDefaultUI: false, zoomControl: true, styles: darkMapStyle }}
      >
        {plottable.map((interp) => {
          const colors = STATUS_COLORS[interp.status] || STATUS_COLORS.available;
          const radiusMeters = interp._map?.radius_of_service
            ? interp._map.radius_of_service * MILES_TO_METERS
            : interp.radius ? interp.radius * MILES_TO_METERS : null;
          const citiesForInterp = coverageCities[interp.id] || [];

          return (
            <span key={interp.id}>
              {radiusMeters && (
                <Circle
                  center={{ lat: interp.lat, lng: interp.lng }}
                  radius={radiusMeters}
                  options={{
                    strokeColor: colors.circle,
                    strokeOpacity: 0.5,
                    strokeWeight: 1.5,
                    fillColor: colors.circle,
                    fillOpacity: 0.07,
                  }}
                />
              )}

              {citiesForInterp.map((city, ci) => (
                <span key={`city-${interp.id}-${ci}`}>
                  <Marker position={{ lat: city.lat, lng: city.lng }} icon={getCoverageCityIcon()} title={city.name} />
                  <Circle
                    center={{ lat: city.lat, lng: city.lng }}
                    radius={20 * MILES_TO_METERS}
                    options={{
                      strokeColor: COVERAGE_CITY_COLOR,
                      strokeOpacity: 0.3,
                      strokeWeight: 1,
                      fillColor: COVERAGE_CITY_COLOR,
                      fillOpacity: 0.05,
                    }}
                  />
                </span>
              ))}

              <Marker
                position={{ lat: interp.lat, lng: interp.lng }}
                icon={getMarkerIcon(interp.status)}
                onClick={() => setActiveMarker(activeMarker === interp.id ? null : interp.id)}
                zIndex={10}
              >
                {activeMarker === interp.id && (
                  <InfoWindow onCloseClick={() => setActiveMarker(null)}>
                    <div className="p-1 min-w-[210px] max-w-[260px] font-sans">
                      <div className="flex items-center gap-2 mb-2">
                        <Avatar name={interp.name} src={interp._raw?.profile_image_url} size="sm" />
                        <div>
                          <div className="font-semibold text-[13px] leading-tight text-gray-900">{interp.name}</div>
                          <div className="text-[10px] text-gray-500">{interp.city}, {interp.state}</div>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] mb-2 text-gray-700">
                        <span>Missions: <b>{interp.missions}</b></span>
                        <span className="flex items-center gap-0.5">
                          <Star className="w-2.5 h-2.5 text-yellow-500 fill-yellow-500" />
                          <b>{interp.rating}</b>
                        </span>
                        {(interp._map?.radius_of_service || interp.radius) && (
                          <span className="col-span-2 text-gray-500">
                            Radius: <b className="text-gray-700">{interp._map?.radius_of_service || interp.radius} mi</b>
                          </span>
                        )}
                        {citiesForInterp.length > 0 && (
                          <span className="col-span-2 text-indigo-600 text-[10px]">
                            Covers: {citiesForInterp.map(c => c.name).join(", ")}
                          </span>
                        )}
                        <span className="col-span-2 capitalize font-bold" style={{ color: colors.marker }}>
                          {interp.status.replace("_", " ")}
                        </span>
                      </div>
                      {interp.langs?.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-2">
                          {interp.langs.slice(0, 4).map((l, i) => (
                            <span key={i} className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px] font-medium text-gray-700">{l}</span>
                          ))}
                        </div>
                      )}
                      <Button
                        size="sm"
                        className="w-full text-xs h-7 bg-navy hover:bg-navy-light text-white rounded-sm"
                        onClick={() => onInterpreterClick(interp)}
                      >
                        View Profile
                      </Button>
                    </div>
                  </InfoWindow>
                )}
              </Marker>
            </span>
          );
        })}
      </GoogleMap>
    </div>
  );
};
