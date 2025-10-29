# Optimizacion de rutas

## Resumen

Documento paso a paso para calcular rutas de camiones de caudales que cubren sucursales deficitarias minimizando la suma de kilometros recorridos. Sirve como guia para que otra IA replique el proceso.

## Objetivo

Datos necesarios:
- Endpoint `/api/maps/sucursales`.
- Filtro: sucursales con saldo total <= 60 % de la caja teorica (equivalente a deficit del 40 % o mas).
- Punto de partida de todos los camiones: boveda central (`lat = -34.6073508`, `lon = -58.3722956`).
- Flota disponible: entre 5 y 9 camiones.
- Restriccion operativa: maximo 4 paradas por camion.

Meta: asignar cada sucursal deficitaria a exactamente un camion y determinar el orden de visita de manera que la distancia total recorrida sea minima (no se impone retorno a la boveda).

## Herramientas utilizadas

- Node.js (version 16 o superior) con soporte nativo de `fetch`.
- Distancia aproximada mediante formula de Haversine.
- Programacion dinamica para componer los grupos de sucursales.

## Procedimiento

1. **Descargar datos**
   ```bash
   curl -s http://localhost:3000/api/maps/sucursales > tmp_sucursales.json
   ```

2. **Filtrar sucursales deficitarias**
   ```js
   const data = require('./tmp_sucursales.json');
   const fixEncoding = value => Buffer.from(value, 'latin1').toString('utf8');

   const deficit = data
     .map(item => {
       const caja = Number(item.caja_teorica_sucursal);
       const saldo = Number(item.saldo_total_sucursal);
       const ratio = (saldo - caja) / Math.abs(caja);
       return {
         id: item.sucursal_id,
         name: fixEncoding(item.sucursal_nombre),
         lat: item.latitud,
         lon: item.longitud,
         ratio,
       };
     })
     .filter(branch =>
       Number.isFinite(branch.ratio) &&
       branch.ratio <= -0.4
     );
   ```

3. **Orden angular respecto de la boveda**
   ```js
   const vault = { lat: -34.6073508, lon: -58.3722956 };
   const toRadians = deg => (deg * Math.PI) / 180;
   const toDegrees = rad => (rad * 180) / Math.PI;

   const enriched = deficit
     .map(branch => {
       const angle = Math.atan2(branch.lat - vault.lat, branch.lon - vault.lon);
       return { ...branch, angleDeg: (toDegrees(angle) + 360) % 360 };
     })
     .sort((a, b) => a.angleDeg - b.angleDeg);
   ```

4. **Rotar la lista para evitar cortes**
   ```js
   let maxGap = -1;
   let pivot = 0;
   for (let i = 0; i < enriched.length; i++) {
     const current = enriched[i];
     const next = enriched[(i + 1) % enriched.length];
     const gap = (next.angleDeg - current.angleDeg + 360) % 360;
     if (gap > maxGap) {
       maxGap = gap;
       pivot = (i + 1) % enriched.length;
     }
   }
   const ordered = [...enriched.slice(pivot), ...enriched.slice(0, pivot)];
   ```

5. **Distancias Haversine**
   ```js
   const haversine = (lat1, lon1, lat2, lon2) => {
     const R = 6371; // kilometros
     const dLat = toRadians(lat2 - lat1);
     const dLon = toRadians(lon2 - lon1);
     const a = Math.sin(dLat / 2) ** 2 +
               Math.cos(toRadians(lat1)) *
               Math.cos(toRadians(lat2)) *
               Math.sin(dLon / 2) ** 2;
     const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
     return R * c;
   };
   const distanceBetween = (a, b) => haversine(a.lat, a.lon, b.lat, b.lon);
   ```

6. **Matrices de costo**
   - Para cada bloque continuo `ordered[i..j]` con longitud <= 4:
     1. Enumerar todas las permutaciones posible.
     2. Calcular el costo de iniciar en la boveda y recorrer las sucursales en ese orden (no se agrega retorno).
     3. Guardar el minimo costo y el orden asociado.
   - Resultado:
     - `costMatrix[i][j]`: costo minimo.
     - `orderMatrix[i][j]`: arreglo con el orden optimo de sucursales.

7. **Programacion dinamica para asignar camiones**
   - Sea `N = ordered.length`.
   - Para cada cantidad de camiones `K` (entre 5 y 9) calcular `dp[i][k]`, costo minimo para cubrir sucursales desde `i` hasta `N-1` con `k` camiones.
   - Recurrencia:
     ```
     dp[i][k] = min_{end = i .. N-k} ( costMatrix[i][end] + dp[end+1][k-1] )
     ```
     con caso base `dp[i][1] = costMatrix[i][N-1]`.
   - Guardar la decision (`end`) que minimiza el costo para reconstruir la particion.
   - Comparar los resultados para todos los `K`; elegir el menor costo total (en el escenario actual: 5 camiones, 60.75 km).

8. **Reconstruir rutas optimas**
   - Comenzar en `i = 0` con `k = K`.
   - Recuperar el segmento `ordered[i..end]` y el orden optimo `orderMatrix[i][end]`.
   - Calcular:
     - Lista de tramos desde la boveda y entre cada parada.
     - Acumulado de kilometros.
     - Porcentaje de deficit (`ratio * 100`).
   - Avanzar `i = end + 1` y reducir `k` hasta cubrir todas las sucursales.

9. **Eliminar archivos temporales**
   ```bash
   rm tmp_sucursales.json
   ```

## Consejos operativos

- Las distancias Haversine aproximan la realidad; validar rutas en Google Maps o Waze antes de emitir el plan final.
- Si un camion debe volver a la boveda, sumar ese tramo al final del recorrido.
- Ajustar `MAX_GROUP_SIZE` si se acepta mas de 4 paradas. Mayor tamano incrementa factorialmente las permutaciones.
- Modificar el filtro del paso 2 si cambia el umbral de deficit.

## Ejecucion rapida de ejemplo (5 camiones)

```powershell
$script = @'
// Implementar aqui las funciones de los pasos 6, 7 y 8
'@
Set-Content -Path tmp_routes5.js -Value $script -Encoding UTF8
node tmp_routes5.js
Remove-Item tmp_routes5.js
```

## Ideas a futuro

- Integrar Google Directions API para obtener kilometros y tiempos reales.
- Incorporar restriccion de capacidad (peso o valor) por camion.
- Manejar ventanas horarias o prioridades por sucursal.
- Publicar esta logica como servicio interno o integrarla al mapa con controles interactivos.
