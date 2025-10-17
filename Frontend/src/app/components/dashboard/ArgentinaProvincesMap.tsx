"use client";

import React, {
  CSSProperties,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type {
  Feature,
  FeatureCollection,
  GeoJsonProperties,
  MultiPolygon,
  Polygon,
} from 'geojson';
import { geoMercator, geoPath } from 'd3-geo';
import { scaleQuantize } from 'd3-scale';
import styles from './ArgentinaProvincesMap.module.css';

type ProvinceGeometry = Polygon | MultiPolygon;
type ProvinceFeature = Feature<ProvinceGeometry, GeoJsonProperties>;

export type ChoroplethDatum = {
  provincia: string;
  value: number;
};

export type ArgentinaProvincesMapProps = {
  geojson: FeatureCollection<ProvinceGeometry> | null;
  data: ChoroplethDatum[];
  width?: number;
  height?: number;
  palette?: string[];
  onSelect?: (provincia: string | null) => void;
};

type TooltipState = {
  visible: boolean;
  x: number;
  y: number;
  name: string;
  value: number | null;
  hasData: boolean;
};

type DrawableFeature = {
  feature: ProvinceFeature;
  name: string;
  path: string;
  centroid: [number, number];
  value: number | null;
};

const DEFAULT_WIDTH = 920;
const DEFAULT_HEIGHT = 620;
const DEFAULT_PALETTE = [
  '#0f172a',
  '#0b5ed7',
  '#2563eb',
  '#38bdf8',
  '#60efff',
  '#c4f1ff',
];

const PROVINCE_NAME_KEYS = [
  'provincia',
  'province',
  'name',
  'NAME',
  'NAME_1',
  'NOMBRE',
  'nombre',
];

const numberFormatter = new Intl.NumberFormat('es-AR', {
  maximumFractionDigits: 0,
});

function normalizeProvince(value?: string | null): string {
  return (value ?? '').trim().toLowerCase();
}

function resolveFeatureName(feature: ProvinceFeature): string {
  const props = feature.properties ?? {};
  for (const key of PROVINCE_NAME_KEYS) {
    const candidate = props[key];
    if (typeof candidate === 'string' && candidate.trim().length > 0) {
      return candidate.trim();
    }
  }
  if (typeof feature.id === 'string') return feature.id;
  if (typeof feature.id === 'number') return `${feature.id}`;
  return 'Provincia';
}

function formatBucket(min?: number, max?: number): string {
  if (min === undefined || max === undefined) {
    return 'Sin datos';
  }
  return `${numberFormatter.format(min)} – ${numberFormatter.format(max)}`;
}

const ArgentinaProvincesMap: React.FC<ArgentinaProvincesMapProps> = ({
  geojson,
  data,
  width,
  height,
  palette,
  onSelect,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const mapWidth = width ?? DEFAULT_WIDTH;
  const mapHeight = height ?? DEFAULT_HEIGHT;
  const colorPalette = palette && palette.length > 0 ? palette : DEFAULT_PALETTE;

  const [selectedProvince, setSelectedProvince] = useState<string | null>(null);
  const [hoveredProvince, setHoveredProvince] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    name: '',
    value: null,
    hasData: false,
  });

  const features = useMemo(() => {
    if (!geojson?.features) return [];
    return geojson.features.filter(
      (feature): feature is ProvinceFeature =>
        feature.geometry != null &&
        (feature.geometry.type === 'Polygon' || feature.geometry.type === 'MultiPolygon'),
    );
  }, [geojson]);

  const valueByProvince = useMemo(() => {
    const map = new Map<string, number>();
    data.forEach(({ provincia, value }) => {
      if (Number.isFinite(value)) {
        map.set(normalizeProvince(provincia), value);
      }
    });
    return map;
  }, [data]);

  const numericValues = useMemo(() => Array.from(valueByProvince.values()), [valueByProvince]);

  const colorScale = useMemo(() => {
    if (numericValues.length === 0) return null;
    let min = Math.min(...numericValues);
    let max = Math.max(...numericValues);
    if (min === max) {
      max = min + 1;
    }
    return scaleQuantize<string>().domain([min, max]).range(colorPalette);
  }, [numericValues, colorPalette]);

  const projection = useMemo(() => {
    return geojson ? geoMercator().fitSize([mapWidth, mapHeight], geojson) : null;
  }, [geojson, mapWidth, mapHeight]);

  const pathGenerator = useMemo(() => {
    return projection ? geoPath(projection) : null;
  }, [projection]);

  const drawableFeatures = useMemo<DrawableFeature[]>(() => {
    if (!pathGenerator) return [];
    return features.map((feature) => {
      const name = resolveFeatureName(feature);
      const normalized = normalizeProvince(name);
      const value = valueByProvince.has(normalized)
        ? valueByProvince.get(normalized) ?? null
        : null;
      return {
        feature,
        name,
        path: pathGenerator(feature) ?? '',
        centroid: pathGenerator.centroid(feature),
        value,
      };
    });
  }, [features, pathGenerator, valueByProvince]);

  const featureNameSet = useMemo(() => new Set(drawableFeatures.map((item) => item.name)), [drawableFeatures]);

  useEffect(() => {
    if (selectedProvince && !featureNameSet.has(selectedProvince)) {
      setSelectedProvince(null);
      onSelect?.(null);
    }
  }, [selectedProvince, featureNameSet, onSelect]);

  const resetSelection = useCallback(() => {
    setSelectedProvince(null);
    onSelect?.(null);
    setTooltip((state) => ({ ...state, visible: false }));
    setHoveredProvince(null);
  }, [onSelect]);

  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target as Node)) {
        resetSelection();
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [resetSelection]);

  const updateTooltip = useCallback(
    (x: number, y: number, name: string, value: number | null) => {
      setTooltip({
        visible: true,
        x,
        y,
        name,
        value,
        hasData: value !== null,
      });
    },
    [],
  );

  const updateTooltipFromPointer = useCallback(
    (event: React.PointerEvent<SVGPathElement>, name: string, value: number | null) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      updateTooltip(event.clientX - rect.left, event.clientY - rect.top, name, value);
    },
    [updateTooltip],
  );

  const showTooltipFromCentroid = useCallback(
    (centroid: [number, number], name: string, value: number | null) => {
      if (!containerRef.current || !svgRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      const svgRect = svgRef.current.getBoundingClientRect();
      const scaleX = svgRect.width / mapWidth;
      const scaleY = svgRect.height / mapHeight;
      updateTooltip(
        svgRect.left - containerRect.left + centroid[0] * scaleX,
        svgRect.top - containerRect.top + centroid[1] * scaleY,
        name,
        value,
      );
    },
    [mapWidth, mapHeight, updateTooltip],
  );

  const handleProvinceClick = useCallback(
    (name: string) => {
      setSelectedProvince((current) => {
        const next = current === name ? null : name;
        onSelect?.(next);
        return next;
      });
    },
    [onSelect],
  );

  const legendItems = useMemo(() => {
    if (!colorScale) return [];
    return colorScale.range().map((color) => {
      const [min, max] = colorScale.invertExtent(color);
      return {
        color,
        label: formatBucket(min ?? undefined, max ?? undefined),
      };
    });
  }, [colorScale]);

  const svgStyle = useMemo<CSSProperties>(() => ({
    maxWidth: mapWidth,
    maxHeight: mapHeight,
  }), [mapWidth, mapHeight]);

  return (
    <div
      ref={containerRef}
      className={styles.container}
      style={{
        '--map-width': `${mapWidth}px`,
        '--map-height': `${mapHeight}px`,
      } as CSSProperties}
    >
      <div className={styles.header}>
        <div className={styles.titleBlock}>
          <span className={styles.eyebrow}>Mapa regional</span>
          <h3 className={styles.title}>Heatmap de provincias argentinas</h3>
          <p className={styles.subtitle}>
            Colores cuantizados en tonos celestes. Hacé click o utilizá el teclado para
            resaltar una provincia y sincronizar las acciones del dashboard.
          </p>
        </div>
        <button type="button" className={styles.resetButton} onClick={resetSelection}>
          Reset
        </button>
      </div>

      <div className={styles.chartSurface}>
        {geojson ? (
          <svg
            ref={svgRef}
            className={styles.mapCanvas}
            viewBox={`0 0 ${mapWidth} ${mapHeight}`}
            role="img"
            aria-label="Mapa coroplético de provincias de Argentina"
            style={svgStyle}
          >
            <title>Mapa coroplético de provincias argentinas</title>
            {drawableFeatures.map((item) => {
              const isSelected = selectedProvince === item.name;
              const isHovered = hoveredProvince === item.name;
              const fillColor = item.value !== null && colorScale
                ? colorScale(item.value)
                : 'rgba(30, 41, 59, 0.8)';

              return (
                <path
                  key={item.name}
                  d={item.path}
                  role="button"
                  tabIndex={0}
                  aria-pressed={isSelected}
                  aria-label={
                    item.value !== null
                      ? `${item.name}: ${numberFormatter.format(item.value)}`
                      : `${item.name}: sin datos`
                  }
                  className={[
                    styles.province,
                    item.value !== null ? styles.provinceWithData : '',
                    isSelected ? styles.provinceSelected : '',
                    isHovered ? styles.provinceHovered : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  style={{ fill: fillColor }}
                  onPointerEnter={(event) => {
                    setHoveredProvince(item.name);
                    updateTooltipFromPointer(event, item.name, item.value);
                  }}
                  onPointerMove={(event) => updateTooltipFromPointer(event, item.name, item.value)}
                  onPointerLeave={() => {
                    setHoveredProvince((current) => (current === item.name ? null : current));
                    setTooltip((state) => ({ ...state, visible: false }));
                  }}
                  onPointerDown={(event) => {
                    if (event.pointerType === 'touch') {
                      updateTooltipFromPointer(event, item.name, item.value);
                    }
                  }}
                  onClick={() => handleProvinceClick(item.name)}
                  onFocus={() => {
                    setHoveredProvince(item.name);
                    showTooltipFromCentroid(item.centroid, item.name, item.value);
                  }}
                  onBlur={() => {
                    setHoveredProvince((current) => (current === item.name ? null : current));
                    setTooltip((state) => ({ ...state, visible: false }));
                  }}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      handleProvinceClick(item.name);
                    }
                  }}
                />
              );
            })}
          </svg>
        ) : (
          <div className={styles.selectionBanner}>
            Cargando límites provinciales...
          </div>
        )}

        {tooltip.visible ? (
          <div
            className={styles.tooltip}
            style={{
              left: tooltip.x,
              top: tooltip.y,
            }}
            role="status"
          >
            <strong>{tooltip.name}</strong>
            <span>
              {tooltip.hasData
                ? numberFormatter.format(tooltip.value ?? 0)
                : 'Sin datos'}
            </span>
            {selectedProvince === tooltip.name ? (
              <span className={styles.tooltipSelected}>Seleccionada</span>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className={styles.legend} aria-hidden={legendItems.length === 0}>
        <span className={styles.legendTitle}>Leyenda</span>
        <div className={styles.legendItems}>
          {legendItems.length === 0 ? (
            <span className={styles.legendItem}>Sin valores numéricos</span>
          ) : (
            legendItems.map((item) => (
              <span key={item.color} className={styles.legendItem}>
                <span className={styles.legendSwatch} style={{ background: item.color }} aria-hidden />
                <span>{item.label}</span>
              </span>
            ))
          )}
          <span className={styles.legendItemMuted}>
            <span className={styles.legendSwatchMuted} aria-hidden />
            <span>Sin datos</span>
          </span>
        </div>
      </div>

      <div className={styles.selectionBanner}>
        <span>Provincia seleccionada:</span>
        <span className={styles.selectionValue}>{selectedProvince ?? 'Ninguna'}</span>
      </div>
    </div>
  );
};

export default ArgentinaProvincesMap;