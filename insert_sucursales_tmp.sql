-- Script temporal para insertar sucursales y dispositivos desde docs/Base de datos/InsertSucursales.sql
-- Recomendación: hacer idempotente con ON CONFLICT en futuras migraciones

\echo 'Insertando saldos_sucursal...'
INSERT INTO public.saldos_sucursal (sucursal_id, sucursal_numero, sucursal_nombre, telefonos, calle, altura, barrio, comuna, codigo_postal, codigo_postal_argentino, saldo_total_sucursal, caja_teorica_sucursal, total_atm, total_ats, total_tesoro, total_cajas_ventanilla, total_buzon_depositos, total_recaudacion, total_caja_chica, total_otros, direccion_sucursal, latitud, longitud, observacion)
VALUES
  ('SUC-384', 328, 'Mataderos', '4686-1395/4687-2064/4687-2164/4687-2364', 'ALBERDI JUAN B', 6401, 'Mataderos', 9, 1440, 'C1440ABC', 148000, 100000, 70400, 15900, 20600, 12000, 6000, 5200, 3100, 14800, 'ALBERDI JUAN B 6401', -34.655595183244, -58.507384893964, NULL);
-- Truncado: copiar el resto si se necesita todo el dataset completo.
\echo 'Fin parcial (dataset completo está en docs/Base de datos/InsertSucursales.sql)';
