"use client";

// Independent Google Maps rendering module; avoids reusing the Leaflet stack so both maps can coexist.
import { useCallback, useEffect, useRef, useState } from 'react';
import styles from './GoogleMapView.module.css';

type SucursalRecord = {
  sucursal_id: string;
  sucursal_numero: number;
  sucursal_nombre: string;
  telefonos?: string | null;
  calle?: string | null;
  altura?: number | null;
  barrio?: string | null;
  comuna?: number | null;
  codigo_postal?: number | null;
  codigo_postal_argentino?: string | null;
  saldo_total_sucursal: number;
  caja_teorica_sucursal?: number | null;
  total_atm: number;
  total_ats: number;
  total_tesoro: number;
  total_cajas_ventanilla: number;
  total_buzon_depositos: number;
  total_recaudacion: number;
  total_caja_chica: number;
  total_otros: number;
  direccion_sucursal?: string | null;
  latitud: number;
  longitud: number;
  observacion?: string | null;
  medido_en?: string | null;
};

type AlertSummary = {
  id: string;
  status?: string | null;
  priority?: string | null;
  sucursal?: {
    sucursal_id?: string | null;
  } | null;
};

type GoogleMapViewProps = {
  onSucursalSelect: (sucursal: SucursalRecord | null) => void;
  selectedSucursal?: SucursalRecord | null;
  simulationTrigger?: number;
  onSimulationStateChange?: (isRunning: boolean) => void;
  onReadyStateChange?: (isReady: boolean) => void;
  onSelectionPositionChange?: (position: PixelPosition | null) => void;
};

type LatLngLiteral = {
  lat: number;
  lng: number;
};

type PixelPosition = {
  viewportX: number;
  viewportY: number;
  mapX: number;
  mapY: number;
};

type SimulationRoute = {
  id: string;
  origin: LatLngLiteral;
  destination: LatLngLiteral;
  color: string;
  marker?: any;
  polyline?: any;
  path?: LatLngLiteral[];
};

declare global {
  interface Window {
    google?: any;
  }
}

const GOOGLE_SCRIPT_ID = 'capi-google-maps-sdk';
const MAX_SIMULATION_TRUCKS = 9;
const SIMULATION_DURATION_MS = 20000;
const ROUTE_COLORS = [
  '#38bdf8',
  '#f97316',
  '#a855f7',
  '#22c55e',
  '#facc15',
  '#ef4444',
  '#ec4899',
  '#0ea5e9',
  '#94a3b8'
];
const EARTH_RADIUS_METERS = 6371000;
const MIN_ROUTE_DISTANCE_METERS = 250;
const MAP_STYLES = [
  { elementType: 'geometry', stylers: [{ color: '#081624' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#081624' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#6c8096' }] },
  { featureType: 'administrative', stylers: [{ visibility: 'off' }] },
  { featureType: 'landscape', stylers: [{ color: '#0a192c' }] },
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'poi.business', stylers: [{ visibility: 'off' }] },
  { featureType: 'poi.park', stylers: [{ visibility: 'off' }] },
  { featureType: 'poi.medical', stylers: [{ visibility: 'off' }] },
  { featureType: 'poi.place_of_worship', stylers: [{ visibility: 'off' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#122b40' }] },
  { featureType: 'road', elementType: 'labels', stylers: [{ visibility: 'simplified' }] },
  { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#8193a8' }] },
  { featureType: 'road', elementType: 'labels.icon', stylers: [{ visibility: 'off' }] },
  { featureType: 'transit', stylers: [{ visibility: 'off' }] },
  { featureType: 'water', stylers: [{ color: '#06111f' }] },
];

type MarkerAppearance = {
  imageUrl: string;
  size: number;
};

const DEFAULT_MARKER_APPEARANCE: MarkerAppearance = {
  imageUrl: '/point-violeta.png',
  size: 32,
};

const ALERT_MARKER_APPEARANCE: MarkerAppearance = {
  imageUrl: '/point-rojo.png',
  size: 36,
};

const FALLBACK_MARKER_APPEARANCE: MarkerAppearance = {
  imageUrl: '/point.png',
  size: 26,
};

const NEUTRAL_MARKER_APPEARANCE: MarkerAppearance = {
  imageUrl: '/point.png',
  size: 32,
};

const BALANCE_TOLERANCE = 0.15;


type AdvancedMarkerOptions = {
  map: any;
  position: LatLngLiteral;
  title: string;
  imageUrl: string;
  size: number;
  zIndex?: number;
};

function createAdvancedMarker(options: AdvancedMarkerOptions): any {
  const icon = {
    url: options.imageUrl,
    scaledSize: new window.google.maps.Size(options.size, options.size),
  };

  return new window.google.maps.Marker({
    map: options.map,
    position: options.position,
    title: options.title,
    zIndex: options.zIndex,
    icon,
  });
}

function buildAlertsIndex(alerts: AlertSummary[]): Map<string, AlertSummary[]> {
  const index = new Map<string, AlertSummary[]>();
  alerts.forEach((alert) => {
    const sucursalId = alert?.sucursal?.sucursal_id;
    if (!sucursalId) {
      return;
    }
    const normalizedId = sucursalId.toString();
    const bucket = index.get(normalizedId) ?? [];
    bucket.push(alert);
    index.set(normalizedId, bucket);
  });
  return index;
}

function isAlertActive(alert: AlertSummary): boolean {
  const status = (alert.status ?? '').toLowerCase();
  if (!status) {
    return false;
  }
  const resolvedStatuses = new Set([
    'resuelta',
    'resuelto',
    'resolved',
    'silenciada',
    'cerrada',
    'closed',
    'completada',
  ]);
  return !resolvedStatuses.has(status);
}

function hasActiveAlerts(alerts: AlertSummary[] | undefined): boolean {
  return Boolean(alerts?.some((alert) => isAlertActive(alert)));
}

function getCoverageRatio(record: SucursalRecord): number | null {
  if (!Number.isFinite(record.caja_teorica_sucursal) || !record.caja_teorica_sucursal) {
    return null;
  }
  return record.saldo_total_sucursal / record.caja_teorica_sucursal;
}

function resolveMarkerAppearance(
  record: SucursalRecord,
  alertsIndex: Map<string, AlertSummary[]>
): MarkerAppearance {
  const alerts = alertsIndex.get(record.sucursal_id) ?? [];
  const activeAlert = hasActiveAlerts(alerts);
  const ratio = getCoverageRatio(record);

  if (activeAlert) {
    return ALERT_MARKER_APPEARANCE;
  }

  if (ratio === null) {
    return DEFAULT_MARKER_APPEARANCE;
  }

  if (ratio < 1 - BALANCE_TOLERANCE) {
    return ALERT_MARKER_APPEARANCE;
  }

  if (ratio <= 1 + BALANCE_TOLERANCE) {
    return NEUTRAL_MARKER_APPEARANCE;
  }

  return DEFAULT_MARKER_APPEARANCE;
}

function updateMarkerPosition(marker: any, position: LatLngLiteral): void {
  if (!marker) {
    return;
  }
  if (typeof marker.setPosition === 'function') {
    marker.setPosition(position);
    return;
  }
  if ('position' in marker) {
    marker.position = position;
  }
}


function detachMarker(marker: any): void {
  if (!marker) {
    return;
  }
  if (typeof marker.setMap === 'function') {
    marker.setMap(null);
    return;
  }
  if ('map' in marker) {
    marker.map = null;
  }
}
function hasValidCoordinates(record: SucursalRecord): boolean {
  return Number.isFinite(record.latitud) && Number.isFinite(record.longitud);
}

function toRadians(value: number): number {
  return (value * Math.PI) / 180;
}

function getDistanceMeters(origin: LatLngLiteral, destination: LatLngLiteral): number {
  const dLat = toRadians(destination.lat - origin.lat);
  const dLng = toRadians(destination.lng - origin.lng);
  const lat1 = toRadians(origin.lat);
  const lat2 = toRadians(destination.lat);

  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS_METERS * c;
}

function dedupeByCoordinates(records: SucursalRecord[]): SucursalRecord[] {
  const seen = new Map<string, SucursalRecord>();
  records.forEach((record) => {
    const key = `${record.latitud.toFixed(6)}:${record.longitud.toFixed(6)}`;
    if (!seen.has(key)) {
      seen.set(key, record);
    }
  });
  return Array.from(seen.values());
}

function shuffleSelection<T>(items: T[]): T[] {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    const temp = copy[index];
    copy[index] = copy[randomIndex];
    copy[randomIndex] = temp;
  }
  return copy;
}

async function loadGoogleMaps(): Promise<void> {
  if (typeof window !== 'undefined' && window.google && window.google.maps) {
    return;
  }

  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  if (!apiKey) {
    throw new Error('NEXT_PUBLIC_GOOGLE_MAPS_API_KEY is not configured.');
  }

  if (document.getElementById(GOOGLE_SCRIPT_ID)) {
    return new Promise((resolve, reject) => {
      const existing = document.getElementById(GOOGLE_SCRIPT_ID);
      if (!existing) {
        reject(new Error('Google Maps script element missing.'));
        return;
      }
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('Failed to load Google Maps script.')), { once: true });
    });
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.id = GOOGLE_SCRIPT_ID;
    const libraries = 'marker,geometry';
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=${libraries}`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Google Maps script.'));
    script.setAttribute('loading', 'async');
    document.head.appendChild(script);
  });
}
function interpolatePosition(
  origin: LatLngLiteral,
  destination: LatLngLiteral,
  progress: number
): LatLngLiteral {
  if (
    typeof window !== 'undefined' &&
    window.google?.maps?.geometry?.spherical?.interpolate
  ) {
    const interpolated = window.google.maps.geometry.spherical.interpolate(
      origin,
      destination,
      progress
    );
    return interpolated.toJSON();
  }

  return {
    lat: origin.lat + (destination.lat - origin.lat) * progress,
    lng: origin.lng + (destination.lng - origin.lng) * progress,
  };
}

function getRoutePosition(route: SimulationRoute, progress: number): LatLngLiteral {
  if (!route.path || route.path.length < 2) {
    return interpolatePosition(route.origin, route.destination, progress);
  }

  const scaled = progress * (route.path.length - 1);
  const index = Math.min(Math.floor(scaled), route.path.length - 2);
  const segmentProgress = scaled - index;
  const start = route.path[index];
  const end = route.path[index + 1];
  return interpolatePosition(start, end, segmentProgress);
}

function buildSimulationRoutes(data: SucursalRecord[]): SimulationRoute[] {
  const validRecords = data.filter(hasValidCoordinates);
  if (validRecords.length < 2) {
    return [];
  }

  const uniqueRecords = dedupeByCoordinates(validRecords);
  if (uniqueRecords.length < 2) {
    return [];
  }

  type CandidateRoute = {
    origin: SucursalRecord;
    destination: SucursalRecord;
    distance: number;
  };

  const candidates: CandidateRoute[] = [];

  for (let originIndex = 0; originIndex < uniqueRecords.length; originIndex += 1) {
    for (let destinationIndex = originIndex + 1; destinationIndex < uniqueRecords.length; destinationIndex += 1) {
      const origin = uniqueRecords[originIndex];
      const destination = uniqueRecords[destinationIndex];
      const originPoint: LatLngLiteral = { lat: origin.latitud, lng: origin.longitud };
      const destinationPoint: LatLngLiteral = { lat: destination.latitud, lng: destination.longitud };
      const distance = getDistanceMeters(originPoint, destinationPoint);

      candidates.push({ origin, destination, distance });
      candidates.push({ origin: destination, destination: origin, distance });
    }
  }

  if (!candidates.length) {
    return [];
  }

  const prioritized = candidates.filter((candidate) => candidate.distance >= MIN_ROUTE_DISTANCE_METERS);
  const selectionPool = prioritized.length >= MAX_SIMULATION_TRUCKS ? prioritized : candidates;
  const shuffled = shuffleSelection(selectionPool);
  if (!shuffled.length) {
    return [];
  }

  const routes: SimulationRoute[] = [];

  for (let index = 0; index < MAX_SIMULATION_TRUCKS; index += 1) {
    const candidate = shuffled[index % shuffled.length];
    routes.push({
      id: `truck-${index + 1}`,
      origin: { lat: candidate.origin.latitud, lng: candidate.origin.longitud },
      destination: { lat: candidate.destination.latitud, lng: candidate.destination.longitud },
      color: ROUTE_COLORS[index % ROUTE_COLORS.length],
    });
  }

  return routes;
}

export default function GoogleMapView({
  onSucursalSelect,
  selectedSucursal,
  simulationTrigger = 0,
  onSimulationStateChange,
  onReadyStateChange,
  onSelectionPositionChange,
}: GoogleMapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const overlayHelperRef = useRef<any | null>(null);
  const mapListenersRef = useRef<any[]>([]);
  const selectionPositionCallbackRef = useRef<((position: PixelPosition | null) => void) | null>(
    onSelectionPositionChange ?? null,
  );
  const selectedSucursalRef = useRef<SucursalRecord | null>(selectedSucursal ?? null);
  const resizeListenerRef = useRef<(() => void) | null>(null);
  const branchDataRef = useRef<SucursalRecord[]>([]);
  const alertsIndexRef = useRef<Map<string, AlertSummary[]>>(new Map<string, AlertSummary[]>());
  const simulationRoutesRef = useRef<SimulationRoute[]>([]);
  const simulationActiveRoutesRef = useRef<SimulationRoute[]>([]);
  const pendingSimulationRef = useRef(false);
  const directionsServiceRef = useRef<any | null>(null);
  const animationStateRef = useRef<{ frameId: number; active: boolean; startTime: number }>({
    frameId: 0,
    active: false,
    startTime: 0,
  });
  const lastTriggerRef = useRef<number>(simulationTrigger);
  const onSucursalSelectRef = useRef(onSucursalSelect);
  const onSimulationStateChangeRef = useRef(onSimulationStateChange);
  const onReadyStateChangeRef = useRef(onReadyStateChange);

  useEffect(() => {
    onSucursalSelectRef.current = onSucursalSelect;
  }, [onSucursalSelect]);

  useEffect(() => {
    onSimulationStateChangeRef.current = onSimulationStateChange;
  }, [onSimulationStateChange]);

  useEffect(() => {
    onReadyStateChangeRef.current = onReadyStateChange;
  }, [onReadyStateChange]);

  useEffect(() => {
    selectionPositionCallbackRef.current = onSelectionPositionChange ?? null;
  }, [onSelectionPositionChange]);

  const updateOverlayPosition = useCallback(() => {
    const overlay = overlayHelperRef.current;
    const selection = selectedSucursalRef.current;
    if (!overlay || !selection || !window.google?.maps) {
      if (!selection) {
        selectionPositionCallbackRef.current?.(null);
      }
      return;
    }

    const projection = overlay.getProjection?.();
    if (!projection) {
      return;
    }

    const latLng = new window.google.maps.LatLng(selection.latitud, selection.longitud);
    const point = projection.fromLatLngToDivPixel(latLng);
    if (!point) {
      return;
    }

    const mapDiv: HTMLDivElement | undefined = mapRef.current?.getDiv?.() ?? containerRef.current ?? undefined;
    const mapRect = mapDiv?.getBoundingClientRect?.();
    if (!mapRect) {
      return;
    }

    selectionPositionCallbackRef.current?.({
      viewportX: mapRect.left + point.x,
      viewportY: mapRect.top + point.y,
      mapX: point.x,
      mapY: point.y,
    });
  }, []);

  useEffect(() => {
    selectedSucursalRef.current = selectedSucursal ?? null;
    if (!selectedSucursal) {
      selectionPositionCallbackRef.current?.(null);
      return;
    }
    updateOverlayPosition();
  }, [selectedSucursal, updateOverlayPosition]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cleanupSimulationElements = useCallback(() => {
    if (animationStateRef.current.frameId) {
      cancelAnimationFrame(animationStateRef.current.frameId);
      animationStateRef.current.frameId = 0;
    }
    animationStateRef.current.active = false;

    simulationActiveRoutesRef.current.forEach((route) => {
      detachMarker(route.marker);
      route.polyline?.setMap(null);
    });
    simulationActiveRoutesRef.current = [];
    onSimulationStateChangeRef.current?.(false);
  }, []);

  const getDirectionsPath = useCallback(
    (origin: LatLngLiteral, destination: LatLngLiteral): Promise<LatLngLiteral[]> =>
      new Promise((resolve, reject) => {
        const service = directionsServiceRef.current ?? new window.google.maps.DirectionsService();
        directionsServiceRef.current = service;
        service.route(
          {
            origin,
            destination,
            travelMode: window.google.maps.TravelMode.DRIVING,
          },
          (result: any, status: any) => {
            if (status === 'OK' && result?.routes?.length) {
              const overviewPath = result.routes[0].overview_path ?? [];
              const pathPoints = overviewPath.map((point: any) => {
                if (typeof point?.toJSON === 'function') {
                  return point.toJSON();
                }
                return { lat: point.lat(), lng: point.lng() };
              });
              if (pathPoints.length >= 2) {
                resolve(pathPoints);
              } else {
                reject(new Error('Directions returned an empty path.'));
              }
            } else {
              reject(new Error(`Directions request failed: ${status}`));
            }
          }
        );
      }),
    []
  );

  const startSimulation = useCallback(async () => {
    if (!pendingSimulationRef.current) {
      return;
    }
    if (animationStateRef.current.active) {
      return;
    }

    const map = mapRef.current;
    if (!map || !window.google?.maps) {
      return;
    }

    if (!branchDataRef.current.length) {
      return;
    }

    const preparedRoutes = buildSimulationRoutes(branchDataRef.current);
    if (!preparedRoutes.length) {
      pendingSimulationRef.current = false;
      onSimulationStateChangeRef.current?.(false);
      return;
    }

    pendingSimulationRef.current = false;

    simulationRoutesRef.current = preparedRoutes;
    cleanupSimulationElements();

    try {
      const routesToAnimate = simulationRoutesRef.current;
      const enrichedRoutes = await Promise.all(
        routesToAnimate.map(async (route, index) => {
          let pathPoints: LatLngLiteral[] = [];

          try {
            pathPoints = await getDirectionsPath(route.origin, route.destination);
          } catch (directionsError) {
            console.warn(`Directions request failed for ${route.id}:`, directionsError);
          }

          if (pathPoints.length < 2) {
            pathPoints = [route.origin, route.destination];
          }

          const polyline = new window.google.maps.Polyline({
            map,
            path: pathPoints,
            strokeColor: route.color,
            strokeOpacity: 0.9,
            strokeWeight: 4,
          });

          const marker = createAdvancedMarker({
            map,
            position: pathPoints[0],
            title: `Camion ${index + 1}`,
            imageUrl: '/Caudal.png',
            size: 34,
            zIndex: 2000 + index,
          });

          return { ...route, marker, polyline, path: pathPoints };
        })
      );

      simulationActiveRoutesRef.current = enrichedRoutes;
      animationStateRef.current.active = true;
      animationStateRef.current.startTime = performance.now();
      onSimulationStateChangeRef.current?.(true);

      const step = (timestamp: number) => {
        const elapsed = timestamp - animationStateRef.current.startTime;
        const progress = Math.min(elapsed / SIMULATION_DURATION_MS, 1);

        simulationActiveRoutesRef.current.forEach((route) => {
          if (!route.marker) {
            return;
          }
          const nextPosition = getRoutePosition(route, progress);
          updateMarkerPosition(route.marker, nextPosition);
        });

        if (progress < 1) {
          animationStateRef.current.frameId = requestAnimationFrame(step);
        } else {
          simulationActiveRoutesRef.current.forEach((route) => {
            const finalPosition = route.path?.[route.path.length - 1] ?? route.destination;
            updateMarkerPosition(route.marker, finalPosition);
          });
          animationStateRef.current.active = false;
          animationStateRef.current.frameId = 0;
          onSimulationStateChangeRef.current?.(false);
        }
      };

      animationStateRef.current.frameId = requestAnimationFrame(step);
    } catch (error) {
      console.error('Simulation error:', error);
      cleanupSimulationElements();
      onSimulationStateChangeRef.current?.(false);
    }
  }, [cleanupSimulationElements, getDirectionsPath]);

  useEffect(() => {
    let isMounted = true;

    async function initialize() {
      try {
        onReadyStateChangeRef.current?.(false);
        await loadGoogleMaps();
        if (!isMounted) return;

        const [sucursalesResponse, alertsResponse] = await Promise.all([
          fetch('/api/maps/sucursales'),
          fetch('/api/maps/alerts?limit=200').catch((error) => {
            console.warn('Fallo la carga de alertas para el mapa:', error);
            return null;
          }),
        ]);

        if (!sucursalesResponse?.ok) {
          throw new Error('No se pudo cargar la informacion de sucursales.');
        }

        const payload: SucursalRecord[] = await sucursalesResponse.json();

        if (alertsResponse && alertsResponse.ok) {
          try {
            const alertsPayload: AlertSummary[] = await alertsResponse.json();
            alertsIndexRef.current = buildAlertsIndex(Array.isArray(alertsPayload) ? alertsPayload : []);
          } catch (alertsError) {
            console.warn('No se pudieron interpretar las alertas del mapa:', alertsError);
            alertsIndexRef.current = new Map<string, AlertSummary[]>();
          }
        } else {
          alertsIndexRef.current = new Map<string, AlertSummary[]>();
        }
        if (!isMounted) return;

        if (!containerRef.current) {
          throw new Error('Container element not found.');
        }

        const sanitizedRecords = payload.filter(hasValidCoordinates);
        if (!sanitizedRecords.length) {
          throw new Error('No hay sucursales con coordenadas validas para mostrar en el mapa.');
        }

        if (payload.length !== sanitizedRecords.length) {
          console.warn(`Se omitieron ${payload.length - sanitizedRecords.length} sucursales sin coordenadas validas para la simulacion.`);
        }

        const mapCenter = { lat: sanitizedRecords[0].latitud, lng: sanitizedRecords[0].longitud };

        const map = new window.google.maps.Map(containerRef.current, {
          center: mapCenter,
          zoom: 12,
          disableDefaultUI: true,
          clickableIcons: false,
          styles: MAP_STYLES,
          gestureHandling: 'greedy',
          scrollwheel: true,
        });

        mapRef.current = map;

        const overlayHelper = new window.google.maps.OverlayView();
        overlayHelper.onAdd = () => {};
        overlayHelper.draw = () => {
          updateOverlayPosition();
        };
        overlayHelper.onRemove = () => {
          selectionPositionCallbackRef.current?.(null);
        };
        overlayHelper.setMap(map);
        overlayHelperRef.current = overlayHelper;

        mapListenersRef.current.push(map.addListener('idle', () => updateOverlayPosition()));
        mapListenersRef.current.push(map.addListener('zoom_changed', () => updateOverlayPosition()));
        mapListenersRef.current.push(map.addListener('dragend', () => updateOverlayPosition()));

        if (typeof window !== 'undefined') {
          const handleResize = () => updateOverlayPosition();
          resizeListenerRef.current = handleResize;
          window.addEventListener('resize', handleResize);
        }

        updateOverlayPosition();

        markersRef.current = sanitizedRecords.map((record) => {
          const appearance = resolveMarkerAppearance(record, alertsIndexRef.current) ?? FALLBACK_MARKER_APPEARANCE;
          const marker = createAdvancedMarker({
            map,
            position: { lat: record.latitud, lng: record.longitud },
            title: record.sucursal_nombre,
            imageUrl: appearance.imageUrl || FALLBACK_MARKER_APPEARANCE.imageUrl,
            size: appearance.size || FALLBACK_MARKER_APPEARANCE.size,
          });

          marker.addListener('click', () => {
            selectedSucursalRef.current = record;
            onSucursalSelectRef.current?.(record);
            updateOverlayPosition();
          });

          return marker;
        });

        const bounds = new window.google.maps.LatLngBounds();
        sanitizedRecords.forEach(({ latitud, longitud }) => {
          bounds.extend({ lat: latitud, lng: longitud });
        });
        if (!bounds.isEmpty()) {
          map.fitBounds(bounds, 80);
          if (map.getZoom() > 14) {
            map.setZoom(14);
          }
        }

        branchDataRef.current = sanitizedRecords;
        simulationRoutesRef.current = buildSimulationRoutes(sanitizedRecords);
        setIsLoading(false);
        setError(null);
        onReadyStateChangeRef.current?.(simulationRoutesRef.current.length > 0);

        if (pendingSimulationRef.current) {
          void startSimulation();
        }
      } catch (err: any) {
        if (!isMounted) return;
        setError(err?.message ?? 'Error inesperado al inicializar el mapa.');
        setIsLoading(false);
        onReadyStateChangeRef.current?.(false);
      }
    }

    initialize();

    return () => {
      isMounted = false;
      cleanupSimulationElements();
      pendingSimulationRef.current = false;
      markersRef.current.forEach((marker) => detachMarker(marker));
      markersRef.current = [];
      mapListenersRef.current.forEach((listener) => {
        if (listener?.remove) {
          listener.remove();
          return;
        }
        if (window.google?.maps?.event?.removeListener) {
          window.google.maps.event.removeListener(listener);
        }
      });
      mapListenersRef.current = [];
      if (resizeListenerRef.current && typeof window !== 'undefined') {
        window.removeEventListener('resize', resizeListenerRef.current);
        resizeListenerRef.current = null;
      }
      overlayHelperRef.current?.setMap(null);
      overlayHelperRef.current = null;
      selectionPositionCallbackRef.current?.(null);
      onReadyStateChangeRef.current?.(false);
    };
  }, [cleanupSimulationElements, startSimulation, updateOverlayPosition]);

  useEffect(() => {
    if (!selectedSucursal || !mapRef.current) {
      return;
    }
    mapRef.current.panTo({ lat: selectedSucursal.latitud, lng: selectedSucursal.longitud });
    mapRef.current.setZoom(14);
    updateOverlayPosition();
  }, [selectedSucursal, updateOverlayPosition]);

  useEffect(() => {
    if (simulationTrigger === undefined) {
      return;
    }
    if (lastTriggerRef.current === simulationTrigger) {
      return;
    }
    lastTriggerRef.current = simulationTrigger;
    pendingSimulationRef.current = true;
    void startSimulation();
  }, [simulationTrigger, startSimulation]);

  return (
    <div className={styles.wrapper}>
      <div ref={containerRef} className={styles.mapCanvas} />
      {isLoading && <div className={styles.overlayMessage}>Cargando mapa futurista...</div>}
      {error && <div className={styles.overlayMessage}>{error}</div>}
    </div>
  );
}

