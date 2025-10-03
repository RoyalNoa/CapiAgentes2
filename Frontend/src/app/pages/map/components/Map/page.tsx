"use client";
import dynamicImport from 'next/dynamic';
import { useCallback, useState, useEffect } from 'react';
import { banks } from '@/app/mocks/banks';
import FullScreenPopup from './FullScreenPopup';

interface IBank {
  id: number;
  lat: string;
  long: string;
  sucursal_numero: number;
  sucursal_nombre: string;
  telefonos: string;
  calle: string;
  altura: number;
  barrio: string;
  comuna: number;
  codigo_postal: number;
  codigo_postal_argentino: string;
}
// Cargamos componentes react-leaflet de forma dinámica (sin SSR)
const MapContainer = dynamicImport(() => import('react-leaflet').then(m => m.MapContainer), { ssr: false });
const TileLayer = dynamicImport(() => import('react-leaflet').then(m => m.TileLayer), { ssr: false });
const Marker = dynamicImport(() => import('react-leaflet').then(m => m.Marker), { ssr: false });
const Popup = dynamicImport(() => import('react-leaflet').then(m => m.Popup), { ssr: false });

import iconMarker from '@/app/resources/images/iconCash.png';
import "./styles.css";

// Evitar acceso a leaflet en build SSR: se inicializa tras mount
let leafletRef: typeof import('leaflet') | null = null;

export const dynamicMode = 'force-dynamic'; // evita prerender estático problemático

export default function Map({ onSucursalSelect }: { onSucursalSelect: (sucursal: IBank) => void }) {
  const [expandedBank, setExpandedBank] = useState<IBank | null>(null);
  const [ready, setReady] = useState(false);
  const [customIcon, setCustomIcon] = useState<any>(null);

  const handleMarkerClick = useCallback((bank: IBank) => {
    onSucursalSelect(bank);
  }, [onSucursalSelect]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      if (typeof window === 'undefined') return;
      
      try {
        if (!leafletRef) {
          leafletRef = await import('leaflet');
          // Importar CSS de leaflet solo en cliente
          // @ts-ignore: hoja de estilos sin tipos
          await import('leaflet/dist/leaflet.css');
        }
        
        if (mounted && leafletRef) {
          const L = leafletRef;
          
          // Crear icono personalizado
          const icon = L.icon({
            iconUrl: iconMarker.src,
            iconSize: [70, 70],
            iconAnchor: [35, 70],
            popupAnchor: [0, -70],
            shadowSize: [41, 41],
            shadowAnchor: [12, 41]
          });
          
          setCustomIcon(icon);
          setReady(true);
        }
      } catch (error) {
        console.error('Error loading leaflet:', error);
        // Fallback: mostrar mapa sin icono personalizado
        setReady(true);
      }
    })();
    return () => { mounted = false; };
  }, []);

  if (!ready) {
    return <div style={{padding: 16, fontSize: 12, opacity: .7}}>Cargando mapa...</div>;
  }

  return (
    <>
      <MapContainer className='margin24 border-radius16 mapContainer' center={[-34.616667, -58.383333]} zoom={13} scrollWheelZoom>
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a> | &copy; <a href="https://openstreetmap.org/copyright">OSM</a>'
        />
        {banks.map((bank, index) => (
          <Marker 
            key={index} 
            position={[Number(bank.lat), Number(bank.long)]} 
            icon={customIcon || undefined}
            eventHandlers={{ click: () => handleMarkerClick(bank) }}
          >
            <Popup>
              <p><strong>{bank.sucursal_nombre}</strong></p>
              <p>{bank.calle} {bank.altura}</p>
              <p>{bank.barrio}</p>
              <button className="expand-btn" onClick={() => setExpandedBank(bank)}>
                Ver Detalles
              </button>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      {expandedBank && (
        <FullScreenPopup bank={expandedBank} onClose={() => setExpandedBank(null)} />
      )}
    </>
  );
}