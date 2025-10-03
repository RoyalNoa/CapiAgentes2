"use client";
import React, { useEffect, useState } from 'react';

/**
 * error.tsx (App Router) – Renderiza cuando ocurre una excepción en el cliente/servidor
 * Provee detalles básicos en desarrollo y un ID de incidente para producción.
 */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const [extra, setExtra] = useState<string | null>(null);

  useEffect(() => {
    // Log interno
    console.error('[GlobalError]', error);
    // Captura última entrada de consola si existe stack
    setExtra(error.stack || null);
  }, [error]);

  return (
    <html lang="es">
      <body style={{ fontFamily: 'system-ui, sans-serif', margin: 0 }}>
        <div style={{maxWidth: 680, margin: '40px auto', padding: '24px', background: 'rgba(255,255,255,0.85)', borderRadius: 12, boxShadow: '0 4px 16px rgba(0,0,0,0.08)'}}>
          <h1 style={{marginTop:0,fontSize:28}}>Se produjo un error en la aplicación</h1>
          <p style={{color:'#444'}}>Ha ocurrido una excepción en el cliente o durante la hidratación.</p>
          <div style={{background:'#111',color:'#fafafa',padding:'12px 14px',borderRadius:8, fontSize:12, overflowX:'auto'}}>
            <strong>Mensaje:</strong> {error.message || 'Error desconocido'}<br/>
            {error.digest && (<><strong>Digest:</strong> {error.digest}<br/></>)}
            {extra && (
              <details style={{marginTop:8}} open>
                <summary style={{cursor:'pointer'}}>Stack trace</summary>
                <pre style={{whiteSpace:'pre-wrap'}}>{extra}</pre>
              </details>
            )}
          </div>
          <div style={{display:'flex',gap:12,marginTop:24,flexWrap:'wrap'}}>
            <button onClick={() => reset()} style={btnStyle}>Reintentar</button>
            <button onClick={() => window.location.reload()} style={btnStyleAlt}>Recargar página</button>
            <button onClick={() => history.back()} style={btnStyleAlt}>Volver</button>
          </div>
          <p style={{marginTop:32,fontSize:12,color:'#666'}}>Si el error persiste, copia el contenido y compártelo para analizar la causa raíz.</p>
        </div>
      </body>
    </html>
  );
}

const btnStyle: React.CSSProperties = {
  background:'#2563eb',color:'#fff',border:'none',padding:'10px 16px',borderRadius:8,cursor:'pointer',fontSize:14
};
const btnStyleAlt: React.CSSProperties = {
  background:'#e2e8f0',color:'#111',border:'none',padding:'10px 16px',borderRadius:8,cursor:'pointer',fontSize:14
};
