"use client";

// Independent Google Maps rendering module; avoids reusing the Leaflet stack so both maps can coexist.
import { useCallback, useEffect, useRef, useState } from 'react';
import styles from './GoogleMapView.module.css';
import predefinedExtractionRoutes from './predefinedExtractionRoutes.json';

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

type SimulationMode = 'deposit' | 'extraction';

type SimulationRequest = {
  id: number;
  mode: SimulationMode;
};

type GoogleMapViewProps = {
  onSucursalSelect: (sucursal: SucursalRecord | null) => void;
  selectedSucursal?: SucursalRecord | null;
  simulationRequest?: SimulationRequest | null;
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

type SimulationStop = {
  position: LatLngLiteral;
  branchId?: string | null;
  type: 'branch' | 'vault';
};

type SimulationRoute = {
  id: string;
  color: string;
  stops: SimulationStop[];
  origin: LatLngLiteral;
  destination: LatLngLiteral;
  participantBranchIds: string[];
  startBranchId?: string | null;
  endBranchId?: string | null;
  marker?: any;
  polyline?: any;
  path?: LatLngLiteral[];
};

type DepositSummary = {
  endpointsByRoute: Map<string, string | null>;
};

type PreparedSimulation = {
  routes: SimulationRoute[];
  participantIds: Set<string>;
  nonParticipantIds: Set<string>;
  startBranchIds: Set<string>;
  depositSummary?: DepositSummary | null;
};

type MapSucursalRecord = SucursalRecord & {
  position: LatLngLiteral;
};

declare global {
  interface Window {
    google?: any;
  }
}

const GOOGLE_SCRIPT_ID = 'capi-google-maps-sdk';
const SIMULATION_TRUCK_COUNT = 5;
const SIMULATION_DURATION_MS = 10000;
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
const TRUCK_ICON_URL = '/Caudal.png';
const TRUCK_ICON_SIZE = 34;
const VAULT_COORDS: LatLngLiteral = { lat: -34.6073508, lng: -58.3722956 };
const EARTH_RADIUS_METERS = 6371000;
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

type MarkerRegistryEntry = {
  marker: any;
  defaultAppearance: MarkerAppearance;
  currentAppearance: MarkerAppearance;
};

const DEFICIT_MARKER_APPEARANCE: MarkerAppearance = {
  imageUrl: '/point-violeta.png',
  size: 36,
};

const SURPLUS_MARKER_APPEARANCE: MarkerAppearance = {
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

const DEFAULT_MARKER_APPEARANCE = NEUTRAL_MARKER_APPEARANCE;

const DEFICIT_COVERAGE_THRESHOLD = -0.4;
const EXCESS_TOLERANCE = 0.4;
const SURPLUS_EXTRACTION_THRESHOLD = 0.4;

const PREDEFINED_DEPOSIT_ROUTES: string[][] = [
  ['SUC-395', 'SUC-423', 'SUC-408', 'SUC-417'],
  ['SUC-406', 'SUC-405', 'SUC-407', 'SUC-402'],
  ['SUC-420', 'SUC-437', 'SUC-435', 'SUC-430'],
  ['SUC-398', 'SUC-377', 'SUC-432', 'SUC-382'],
  ['SUC-413', 'SUC-363', 'SUC-410', 'SUC-433'],
];

const PREDEFINED_EXTRACTION_ROUTES: string[][] = predefinedExtractionRoutes;

type AdvancedMarkerOptions = {
  map: any;
  position: LatLngLiteral;
  title: string;
  imageUrl: string;
  size: number;
  zIndex?: number;
};

function createAdvancedMarker(options: AdvancedMarkerOptions): any {
  const position = ensureValidLatLng(options.position);
  return new window.google.maps.Marker({
    map: options.map,
    position,
    title: options.title,
    zIndex: options.zIndex,
    icon: {
      url: options.imageUrl,
      scaledSize: new window.google.maps.Size(options.size, options.size),
    },
  });
}

async function createMirroredIconUrl(imageUrl: string): Promise<string | null> {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return null;
  }

  return new Promise((resolve) => {
    const image = new Image();
    image.crossOrigin = 'anonymous';
    image.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = image.naturalWidth || image.width;
      canvas.height = image.naturalHeight || image.height;
      const context = canvas.getContext('2d');
      if (!context) {
        resolve(null);
        return;
      }
      context.translate(canvas.width, 0);
      context.scale(-1, 1);
      context.drawImage(image, 0, 0);
      resolve(canvas.toDataURL('image/png'));
    };
    image.onerror = () => resolve(null);
    image.src = imageUrl;
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
  return (record.saldo_total_sucursal - record.caja_teorica_sucursal) / record.caja_teorica_sucursal;
}

function resolveMarkerAppearance(record: SucursalRecord): MarkerAppearance {
  const ratio = getCoverageRatio(record);

  if (ratio === null) {
    return DEFAULT_MARKER_APPEARANCE;
  }

  if (ratio <= DEFICIT_COVERAGE_THRESHOLD) {
    return DEFICIT_MARKER_APPEARANCE;
  }

  if (ratio >= EXCESS_TOLERANCE) {
    return SURPLUS_MARKER_APPEARANCE;
  }

  return NEUTRAL_MARKER_APPEARANCE;
}

function updateMarkerPosition(marker: any, position: LatLngLiteral): void {
  if (!marker) {
    return;
  }
  const nextPosition = ensureValidLatLng(position);
  if (typeof marker.setPosition === 'function') {
    marker.setPosition(nextPosition);
    return;
  }
  if ('position' in marker) {
    marker.position = nextPosition;
  }
}

function applyMarkerAppearance(marker: any, appearance: MarkerAppearance): void {
  if (!marker || !window.google?.maps?.Size) {
    return;
  }
  const icon = {
    url: appearance.imageUrl,
    scaledSize: new window.google.maps.Size(appearance.size, appearance.size),
  };

  if (typeof marker.setIcon === 'function') {
    marker.setIcon(icon);
    return;
  }
  if ('icon' in marker) {
    marker.icon = icon;
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

function ensureValidLatLng(point: LatLngLiteral, fallback: LatLngLiteral = VAULT_COORDS): LatLngLiteral {
  if (!point || typeof point !== 'object') {
    console.warn('ensureValidLatLng recibió un punto inválido, usando fallback.', point);
    return { lat: fallback.lat, lng: fallback.lng };
  }

  const latValue = Number((point as LatLngLiteral).lat);
  const lngValue = Number((point as LatLngLiteral).lng);
  const lat = Number.isFinite(latValue) ? Math.min(Math.max(latValue, -85), 85) : fallback.lat;
  const lng = Number.isFinite(lngValue) ? Math.min(Math.max(lngValue, -180), 180) : fallback.lng;
  if (!Number.isFinite(latValue) || !Number.isFinite(lngValue)) {
    console.warn('ensureValidLatLng: coordenadas no finitas, aplicando fallback', point);
  }
  return { lat, lng };
}

function getLatLngFromRecord(record: SucursalRecord): LatLngLiteral {
  if ((record as MapSucursalRecord).position) {
    return ensureValidLatLng((record as MapSucursalRecord).position);
  }
  const latValue = typeof record.latitud === 'number' ? record.latitud : Number(record.latitud);
  const lngValue = typeof record.longitud === 'number' ? record.longitud : Number(record.longitud);
  return ensureValidLatLng({
    lat: latValue,
    lng: lngValue,
  });
}

function getDistanceToVault(record: SucursalRecord): number {
  return getDistanceMeters(VAULT_COORDS, getLatLngFromRecord(record));
}

function hasValidCoordinates(record: SucursalRecord): boolean {
  const latRaw = record.latitud;
  const lngRaw = record.longitud;
  const lat =
    typeof latRaw === 'number'
      ? latRaw
      : typeof latRaw === 'string' && latRaw.trim().length
        ? Number(latRaw)
        : NaN;
  const lng =
    typeof lngRaw === 'number'
      ? lngRaw
      : typeof lngRaw === 'string' && lngRaw.trim().length
        ? Number(lngRaw)
        : NaN;

  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return false;
  }

  return Math.abs(lat) <= 90 && Math.abs(lng) <= 180;
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
    const lat = typeof record.latitud === 'number' ? record.latitud : Number(record.latitud);
    const lng = typeof record.longitud === 'number' ? record.longitud : Number(record.longitud);
    const key = `${lat.toFixed(6)}:${lng.toFixed(6)}`;
    if (!seen.has(key)) {
      seen.set(key, record);
    }
  });
  return Array.from(seen.values());
}

function normalizeSucursalRecord(record: SucursalRecord): MapSucursalRecord | null {
  const latRaw = record.latitud;
  const lngRaw = record.longitud;
  const lat =
    typeof latRaw === 'number'
      ? latRaw
      : typeof latRaw === 'string' && latRaw.trim().length
        ? Number(latRaw)
        : NaN;
  const lng =
    typeof lngRaw === 'number'
      ? lngRaw
      : typeof lngRaw === 'string' && lngRaw.trim().length
        ? Number(lngRaw)
        : NaN;

  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return null;
  }

  const position = ensureValidLatLng({ lat, lng });
  return {
    ...record,
    latitud: position.lat,
    longitud: position.lng,
    position,
  };
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
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=${libraries}&loading=async`;
    script.async = true;
    script.defer = true;
    script.setAttribute('loading', 'async');
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Google Maps script.'));
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

function buildDepositSimulation(records: SucursalRecord[]): PreparedSimulation {
  const validRecords = records.filter(hasValidCoordinates);
  if (validRecords.length < 2) {
    return {
      routes: [],
      participantIds: new Set(),
      nonParticipantIds: new Set(),
      startBranchIds: new Set(),
      depositSummary: { endpointsByRoute: new Map() },
    };
  }

  const uniqueRecords = dedupeByCoordinates(validRecords);
  if (uniqueRecords.length < 2) {
    return {
      routes: [],
      participantIds: new Set(),
      nonParticipantIds: new Set(),
      startBranchIds: new Set(),
      depositSummary: { endpointsByRoute: new Map() },
    };
  }

  const deficitRecords = uniqueRecords.filter((record) => {
    const ratio = getCoverageRatio(record);
    return ratio !== null && ratio <= DEFICIT_COVERAGE_THRESHOLD;
  });

  if (!deficitRecords.length) {
    return {
      routes: [],
      participantIds: new Set(),
      nonParticipantIds: new Set(uniqueRecords.map((record) => record.sucursal_id)),
      startBranchIds: new Set(),
      depositSummary: { endpointsByRoute: new Map() },
    };
  }

  const branchById = new Map(uniqueRecords.map((record) => [record.sucursal_id, record]));
  const deficitMap = new Map(deficitRecords.map((record) => [record.sucursal_id, record]));

  const truckPlans = PREDEFINED_DEPOSIT_ROUTES.map((routeIds, index) => {
    const branches: SucursalRecord[] = [];
    routeIds.forEach((id) => {
      const branch = deficitMap.get(id) ?? branchById.get(id);
      if (branch && deficitMap.has(branch.sucursal_id)) {
        branches.push(branch);
        deficitMap.delete(id);
      }
    });
    const currentPosition = branches.length
      ? getLatLngFromRecord(branches[branches.length - 1])
      : ensureValidLatLng(VAULT_COORDS);
    return {
      id: `truck-${index + 1}`,
      color: ROUTE_COLORS[index % ROUTE_COLORS.length],
      branches,
      currentPosition,
    };
  });

  const remainingDeficit = Array.from(deficitMap.values());

  remainingDeficit.forEach((branch) => {
    const branchPosition = getLatLngFromRecord(branch);
    let bestPlan = truckPlans[0];
    let bestDistance = getDistanceMeters(bestPlan.currentPosition, branchPosition);

    for (let index = 1; index < truckPlans.length; index += 1) {
      const candidate = truckPlans[index];
      if (!candidate.branches.length) {
        bestPlan = candidate;
        bestDistance = getDistanceMeters(ensureValidLatLng(VAULT_COORDS), branchPosition);
        continue;
      }
      const candidateDistance = getDistanceMeters(candidate.currentPosition, branchPosition);
      if (candidateDistance < bestDistance) {
        bestPlan = candidate;
        bestDistance = candidateDistance;
      }
    }

    bestPlan.branches.push(branch);
    bestPlan.currentPosition = branchPosition;
  });

  const routes: SimulationRoute[] = [];
  const participantIds = new Set<string>();
  const nonParticipantIds = new Set<string>(uniqueRecords.map((record) => record.sucursal_id));
  const endpointsByRoute = new Map<string, string | null>();

  truckPlans.forEach((plan) => {
    if (!plan.branches.length) {
      endpointsByRoute.set(plan.id, null);
      return;
    }

    const stops: SimulationStop[] = [
      { position: ensureValidLatLng(VAULT_COORDS), type: 'vault' },
      ...plan.branches.map((branch) => ({
        position: getLatLngFromRecord(branch),
        branchId: branch.sucursal_id,
        type: 'branch' as const,
      })),
    ];

    const participantList = plan.branches.map((branch) => branch.sucursal_id);
    participantList.forEach((id) => {
      participantIds.add(id);
      nonParticipantIds.delete(id);
    });

    const finalBranchId = participantList[participantList.length - 1] ?? null;

    routes.push({
      id: plan.id,
      color: plan.color,
      stops,
      origin: stops[0].position,
      destination: stops[stops.length - 1].position,
      participantBranchIds: participantList,
      startBranchId: null,
      endBranchId: finalBranchId,
    });

    endpointsByRoute.set(plan.id, finalBranchId);
  });

  const depositSummary: DepositSummary = { endpointsByRoute };

  return {
    routes,
    participantIds,
    nonParticipantIds,
    startBranchIds: new Set(),
    depositSummary,
  };
}

function buildExtractionSimulation(
  records: SucursalRecord[],
  depositSummary: DepositSummary | null
): PreparedSimulation {
  const validRecords = records.filter(hasValidCoordinates);
  if (validRecords.length < 2) {
    return {
      routes: [],
      participantIds: new Set(),
      nonParticipantIds: new Set(),
      startBranchIds: new Set(),
    };
  }

  const uniqueRecords = dedupeByCoordinates(validRecords);
  if (uniqueRecords.length < 2) {
    return {
      routes: [],
      participantIds: new Set(),
      nonParticipantIds: new Set(),
      startBranchIds: new Set(),
    };
  }

  const branchById = new Map(uniqueRecords.map((record) => [record.sucursal_id, record]));
  const targetRecords = uniqueRecords.filter((record) => {
    const coverage = getCoverageRatio(record);
    return coverage !== null && coverage > SURPLUS_EXTRACTION_THRESHOLD;
  });

  const targetIds = new Set(targetRecords.map((record) => record.sucursal_id));
  const participantIds = new Set<string>();
  const nonParticipantIds = new Set<string>(targetIds);
  const startBranchIds = new Set<string>();
  const routes: SimulationRoute[] = [];
  const vaultPosition = ensureValidLatLng(VAULT_COORDS);

  if (!targetRecords.length) {
    return {
      routes,
      participantIds,
      nonParticipantIds,
      startBranchIds,
    };
  }

  PREDEFINED_EXTRACTION_ROUTES.forEach((routeIds, index) => {
    const routeId = `truck-${index + 1}`;
    const branches: SucursalRecord[] = routeIds
      .map((id) => branchById.get(id))
      .filter((record): record is SucursalRecord => Boolean(record));

    if (!branches.length) {
      return;
    }

    const startBranch = branches[0] ?? null;
    if (startBranch) {
      startBranchIds.add(startBranch.sucursal_id);
    }

    const stops: SimulationStop[] = branches.map((branch) => ({
      position: getLatLngFromRecord(branch),
      branchId: branch.sucursal_id,
      type: 'branch' as const,
    }));
    stops.push({ position: vaultPosition, type: 'vault' });

    const participantBranchIds: string[] = [];
    branches.forEach((branch, branchIndex) => {
      const branchId = branch.sucursal_id;
      if (targetIds.has(branchId)) {
        participantIds.add(branchId);
        nonParticipantIds.delete(branchId);
        participantBranchIds.push(branchId);
      } else if (branchIndex === 0 && startBranch?.sucursal_id === branchId) {
        participantBranchIds.push(branchId);
      }
    });

    routes.push({
      id: routeId,
      color: ROUTE_COLORS[index % ROUTE_COLORS.length],
      stops,
      origin: stops[0].position,
      destination: stops[stops.length - 1].position,
      participantBranchIds,
      startBranchId: startBranch?.sucursal_id ?? null,
      endBranchId: null,
    });
  });

  return {
    routes,
    participantIds,
    nonParticipantIds,
    startBranchIds,
  };
}

function prepareSimulationForMode(
  records: SucursalRecord[],
  mode: SimulationMode,
  depositSummary: DepositSummary | null
): PreparedSimulation {
  if (mode === 'deposit') {
    return buildDepositSimulation(records);
  }
  return buildExtractionSimulation(records, depositSummary);
}

export default function GoogleMapView({
  onSucursalSelect,
  selectedSucursal,
  simulationRequest = null,
  onSimulationStateChange,
  onReadyStateChange,
  onSelectionPositionChange,
}: GoogleMapViewProps) {
  const simulationTrigger = simulationRequest?.id;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const vaultMarkerRef = useRef<any | null>(null);
  const overlayHelperRef = useRef<any | null>(null);
  const mapListenersRef = useRef<any[]>([]);
  const selectionPositionCallbackRef = useRef<((position: PixelPosition | null) => void) | null>(
    onSelectionPositionChange ?? null,
  );
  const selectedSucursalRef = useRef<MapSucursalRecord | null>(selectedSucursal ? normalizeSucursalRecord(selectedSucursal) : null);
  const resizeListenerRef = useRef<(() => void) | null>(null);
  const branchDataRef = useRef<MapSucursalRecord[]>([]);
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
  const truckIconAssetsRef = useRef<{ forward: string; return: string | null }>({
    forward: TRUCK_ICON_URL,
    return: null,
  });
  const markersByIdRef = useRef<Map<string, MarkerRegistryEntry>>(new Map());
  const persistentHighlightIdsRef = useRef<Set<string>>(new Set());
  const simulationContextRef = useRef<{
    mode: SimulationMode;
    participantIds: Set<string>;
    nonParticipantIds: Set<string>;
    startBranchIds: Set<string>;
  } | null>(null);
  const pendingDepositSummaryRef = useRef<DepositSummary | null>(null);
  const lastDepositSummaryRef = useRef<DepositSummary | null>(null);
  const simulationRequestRef = useRef<SimulationRequest | null>(simulationRequest);
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
    simulationRequestRef.current = simulationRequest ?? null;
  }, [simulationRequest]);

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

    const selectionPosition = getLatLngFromRecord(selection);
    const latLng = new window.google.maps.LatLng(selectionPosition.lat, selectionPosition.lng);
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
    const normalizedSelection = selectedSucursal ? normalizeSucursalRecord(selectedSucursal) : null;
    selectedSucursalRef.current = normalizedSelection;
    if (!normalizedSelection) {
      selectionPositionCallbackRef.current?.(null);
      return;
    }
    updateOverlayPosition();
  }, [selectedSucursal, updateOverlayPosition]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const setMarkersToAppearance = useCallback(
    (ids: Iterable<string>, appearance: MarkerAppearance) => {
      if (!window.google?.maps) {
        return;
      }
      for (const id of ids) {
        const entry = markersByIdRef.current.get(id);
        if (!entry) {
          continue;
        }
        applyMarkerAppearance(entry.marker, appearance);
        entry.currentAppearance = appearance;
      }
    },
    []
  );

  const restoreMarkerSet = useCallback(
    (ids: Iterable<string>) => {
      if (!window.google?.maps) {
        return;
      }
      for (const id of ids) {
        const entry = markersByIdRef.current.get(id);
        if (!entry) {
          continue;
        }
        applyMarkerAppearance(entry.marker, entry.defaultAppearance);
        entry.currentAppearance = entry.defaultAppearance;
      }
    },
    []
  );

  const restoreAllMarkers = useCallback(() => {
    if (!window.google?.maps) {
      return;
    }
    markersByIdRef.current.forEach((entry) => {
      applyMarkerAppearance(entry.marker, entry.defaultAppearance);
      entry.currentAppearance = entry.defaultAppearance;
    });
    persistentHighlightIdsRef.current.clear();
    if (vaultMarkerRef.current) {
      applyMarkerAppearance(vaultMarkerRef.current, {
        imageUrl: '/boveda.png',
        size: 42,
      });
    }
  }, []);

  const ensureReturnIcon = useCallback(async (): Promise<string> => {
    if (truckIconAssetsRef.current.return) {
      return truckIconAssetsRef.current.return;
    }
    const mirrored = await createMirroredIconUrl(TRUCK_ICON_URL);
    truckIconAssetsRef.current.return = mirrored ?? truckIconAssetsRef.current.forward;
    return truckIconAssetsRef.current.return;
  }, []);

  const cleanupSimulationElements = useCallback(() => {
    if (animationStateRef.current.frameId) {
      cancelAnimationFrame(animationStateRef.current.frameId);
      animationStateRef.current.frameId = 0;
    }
    animationStateRef.current.active = false;
    simulationContextRef.current = null;

    simulationActiveRoutesRef.current.forEach((route) => {
      detachMarker(route.marker);
      route.polyline?.setMap(null);
    });
    simulationActiveRoutesRef.current = [];
    onSimulationStateChangeRef.current?.(false);
  }, []);

  const getDirectionsPath = useCallback(
    (origin: LatLngLiteral, destination: LatLngLiteral, waypoints: LatLngLiteral[] = []): Promise<LatLngLiteral[]> =>
      new Promise((resolve, reject) => {
        const service = directionsServiceRef.current ?? new window.google.maps.DirectionsService();
        directionsServiceRef.current = service;
        const sanitizedOrigin = ensureValidLatLng(origin);
        const sanitizedDestination = ensureValidLatLng(destination);
        const sanitizedWaypoints = waypoints.map((point) => ensureValidLatLng(point));

        service.route(
          {
            origin: sanitizedOrigin,
            destination: sanitizedDestination,
            travelMode: window.google.maps.TravelMode.DRIVING,
            waypoints: sanitizedWaypoints.length
              ? sanitizedWaypoints.map((point) => ({ location: point }))
              : undefined,
            optimizeWaypoints: false,
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
                resolve([sanitizedOrigin, ...sanitizedWaypoints, sanitizedDestination]);
              }
            } else {
              reject(new Error(`Directions request failed: ${status}`));
            }
          }
        );
      }),
    []
  );

  const handleSimulationCompleted = useCallback(() => {
    const context = simulationContextRef.current;
    if (!context) {
      return;
    }

    if (context.mode === 'extraction' && context.nonParticipantIds.size) {
      restoreMarkerSet(context.nonParticipantIds);
    }

    if (context.participantIds.size) {
      setMarkersToAppearance(context.participantIds, NEUTRAL_MARKER_APPEARANCE);
      persistentHighlightIdsRef.current = new Set(context.participantIds);
    } else {
      persistentHighlightIdsRef.current.clear();
    }

    if (context.mode === 'deposit') {
      lastDepositSummaryRef.current = pendingDepositSummaryRef.current ?? null;
    }

    pendingDepositSummaryRef.current = null;
    simulationContextRef.current = null;
  }, [restoreMarkerSet, setMarkersToAppearance]);

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

    const request = simulationRequestRef.current;
    if (!request) {
      pendingSimulationRef.current = false;
      return;
    }

    if (!branchDataRef.current.length) {
      pendingSimulationRef.current = false;
      return;
    }

    pendingSimulationRef.current = false;
    restoreAllMarkers();
    cleanupSimulationElements();

      const mode = request.mode;

      const prepared = prepareSimulationForMode(
        branchDataRef.current,
        mode,
        lastDepositSummaryRef.current
      );

    if (!prepared.routes.length) {
      simulationContextRef.current = null;
      pendingDepositSummaryRef.current = null;
      onSimulationStateChangeRef.current?.(false);
      return;
    }

    simulationRoutesRef.current = prepared.routes;
    simulationContextRef.current = {
      mode,
      participantIds: prepared.participantIds,
      nonParticipantIds: prepared.nonParticipantIds,
      startBranchIds: prepared.startBranchIds,
    };
    pendingDepositSummaryRef.current = mode === 'deposit' ? prepared.depositSummary ?? null : null;

    if (mode === 'extraction') {
      const deficitIds = branchDataRef.current
        .filter((record) => {
          const ratio = getCoverageRatio(record);
          return ratio !== null && ratio <= DEFICIT_COVERAGE_THRESHOLD;
        })
        .map((record) => record.sucursal_id);

      if (deficitIds.length) {
        setMarkersToAppearance(deficitIds, DEFAULT_MARKER_APPEARANCE);
      }

      if (prepared.startBranchIds.size) {
        const neutralStartIds = Array.from(prepared.startBranchIds).filter((id) => {
          const entry = markersByIdRef.current.get(id);
          return entry?.defaultAppearance === NEUTRAL_MARKER_APPEARANCE;
        });
      if (neutralStartIds.length) {
        setMarkersToAppearance(neutralStartIds, DEFAULT_MARKER_APPEARANCE);
      }
    }
      if (prepared.nonParticipantIds.size) {
        setMarkersToAppearance(prepared.nonParticipantIds, NEUTRAL_MARKER_APPEARANCE);
      }
    }

      try {
        const requestedIconUrl =
          mode === 'deposit'
            ? truckIconAssetsRef.current.forward
            : await ensureReturnIcon();
        const resolvedTruckIconUrl = requestedIconUrl ?? truckIconAssetsRef.current.forward;
        const rawRoutes = simulationRoutesRef.current;
        const sanitizedRoutes = rawRoutes
          .map((route) => {
            const sanitizedOrigin = ensureValidLatLng(route.origin);
            const sanitizedDestination = ensureValidLatLng(route.destination);
            const sanitizedStops = route.stops
              .map((stop) => {
                if (!stop?.position) {
                  console.warn(`Ruta ${route.id} contiene un stop sin posición, se omitirá.`, stop);
                  return null;
                }
                const sanitizedPosition = ensureValidLatLng(stop.position);
                return { ...stop, position: sanitizedPosition };
              })
              .filter((stop): stop is SimulationStop => stop !== null);

            if (sanitizedStops.length < 2) {
              console.warn(`Ruta ${route.id} no cuenta con suficientes puntos luego de sanear coordenadas.`);
              return null;
            }

            return {
              ...route,
              origin: sanitizedOrigin,
              destination: sanitizedDestination,
              stops: sanitizedStops,
            };
          })
          .filter((route): route is SimulationRoute => route !== null);

        if (!sanitizedRoutes.length) {
          console.warn('No hay rutas válidas para animar la simulación.');
          onSimulationStateChangeRef.current?.(false);
          return;
        }

        simulationRoutesRef.current = sanitizedRoutes;

        const enrichedRoutes = await Promise.all(
          sanitizedRoutes.map(async (route, index) => {
            const intermediate = route.stops.slice(1, -1).map((stop) => stop.position);
            let pathPoints: LatLngLiteral[] = [];

          try {
            pathPoints = await getDirectionsPath(route.origin, route.destination, intermediate);
          } catch (directionsError) {
            console.warn(`Directions request failed for ${route.id}:`, directionsError);
            pathPoints = [route.origin, ...intermediate, route.destination];
          }

          if (pathPoints.length < 2) {
            pathPoints = [route.origin, route.destination];
          }

          pathPoints = pathPoints
            .map((point) => ensureValidLatLng(point))
            .filter((point, pointIndex, array) => {
              if (!Number.isFinite(point.lat) || !Number.isFinite(point.lng)) {
                return false;
              }
              const previous = array[pointIndex - 1];
              return !previous || previous.lat !== point.lat || previous.lng !== point.lng;
            });

          if (pathPoints.length < 2) {
            pathPoints = [ensureValidLatLng(route.origin), ensureValidLatLng(route.destination)];
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
            imageUrl: resolvedTruckIconUrl,
            size: TRUCK_ICON_SIZE,
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
          handleSimulationCompleted();
        }
      };

      animationStateRef.current.frameId = requestAnimationFrame(step);
    } catch (error) {
      console.error('Simulation error:', error);
      cleanupSimulationElements();
      onSimulationStateChangeRef.current?.(false);
      pendingDepositSummaryRef.current = null;
      simulationContextRef.current = null;
    }
  }, [
    cleanupSimulationElements,
    getDirectionsPath,
    handleSimulationCompleted,
    ensureReturnIcon,
    restoreAllMarkers,
    setMarkersToAppearance,
  ]);

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

        const normalizedRecords = payload
          .map(normalizeSucursalRecord)
          .filter((record): record is MapSucursalRecord => record !== null);
        if (!normalizedRecords.length) {
          throw new Error('No hay sucursales con coordenadas validas para mostrar en el mapa.');
        }

        if (payload.length !== normalizedRecords.length) {
          console.warn(
            `Se omitieron ${payload.length - normalizedRecords.length} sucursales sin coordenadas validas para la simulacion.`
          );
        }

        const mapCenter = { ...normalizedRecords[0].position };

        const mapOptions: google.maps.MapOptions = {
          center: mapCenter,
          zoom: 12,
          disableDefaultUI: true,
          clickableIcons: false,
          styles: MAP_STYLES,
          gestureHandling: 'greedy',
          scrollwheel: true,
        };

        const map = new window.google.maps.Map(containerRef.current, mapOptions);

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

        const vaultMarker = createAdvancedMarker({
          map,
          position: ensureValidLatLng(VAULT_COORDS),
          title: 'Bóveda Central',
          imageUrl: '/boveda.png',
          size: 42,
          zIndex: 2500,
        });
        vaultMarkerRef.current = vaultMarker;

        markersByIdRef.current.clear();
        persistentHighlightIdsRef.current.clear();
        lastDepositSummaryRef.current = null;

        markersRef.current = normalizedRecords.map((record) => {
          const appearance = resolveMarkerAppearance(record);
          const marker = createAdvancedMarker({
            map,
            position: record.position,
            title: record.sucursal_nombre,
            imageUrl: appearance.imageUrl || FALLBACK_MARKER_APPEARANCE.imageUrl,
            size: appearance.size || FALLBACK_MARKER_APPEARANCE.size,
          });

          markersByIdRef.current.set(record.sucursal_id, {
            marker,
            defaultAppearance: appearance,
            currentAppearance: appearance,
          });

          marker.addListener('click', () => {
            selectedSucursalRef.current = record;
            onSucursalSelectRef.current?.(record);
            updateOverlayPosition();
          });

          return marker;
        });

        const bounds = new window.google.maps.LatLngBounds();
        normalizedRecords.forEach(({ position }) => {
          bounds.extend(position);
        });
        if (!bounds.isEmpty()) {
          map.fitBounds(bounds, 80);
          if (map.getZoom() > 14) {
            map.setZoom(14);
          }
        }

        branchDataRef.current = normalizedRecords;
        const depositPreview = buildDepositSimulation(normalizedRecords);
        simulationRoutesRef.current = depositPreview.routes;
        setIsLoading(false);
        setError(null);
        onReadyStateChangeRef.current?.(depositPreview.routes.length > 0);

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
      if (vaultMarkerRef.current) {
        detachMarker(vaultMarkerRef.current);
        vaultMarkerRef.current = null;
      }
      markersRef.current.forEach((marker) => detachMarker(marker));
      markersRef.current = [];
      markersByIdRef.current.clear();
      persistentHighlightIdsRef.current.clear();
      simulationContextRef.current = null;
      pendingDepositSummaryRef.current = null;
      lastDepositSummaryRef.current = null;
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
    mapRef.current.panTo(getLatLngFromRecord(selectedSucursal));
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



