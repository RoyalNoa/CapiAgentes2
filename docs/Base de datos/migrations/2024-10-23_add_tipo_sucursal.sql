ALTER TABLE public.saldos_sucursal
    ADD COLUMN IF NOT EXISTS tipo_sucursal TEXT NOT NULL DEFAULT 'sucursal';

-- Asegurar valor explícito en registros existentes
UPDATE public.saldos_sucursal
SET tipo_sucursal = COALESCE(NULLIF(TRIM(tipo_sucursal), ''), 'sucursal');

-- Registrar la bóveda central si aún no existe
INSERT INTO public.saldos_sucursal (
    sucursal_id,
    sucursal_numero,
    sucursal_nombre,
    tipo_sucursal,
    telefonos,
    calle,
    altura,
    barrio,
    comuna,
    codigo_postal,
    codigo_postal_argentino,
    saldo_total_sucursal,
    caja_teorica_sucursal,
    total_atm,
    total_ats,
    total_tesoro,
    total_cajas_ventanilla,
    total_buzon_depositos,
    total_recaudacion,
    total_caja_chica,
    total_otros,
    direccion_sucursal,
    latitud,
    longitud,
    observacion
) VALUES (
    'SUC-900',
    900,
    'Boveda Central',
    'boveda',
    '4310-0000',
    'RECONQUISTA',
    40,
    'San Nicolas',
    1,
    1003,
    'C1003AAA',
    1000000,
    1000000,
    0,
    0,
    1000000,
    0,
    0,
    0,
    0,
    0,
    'RECONQUISTA 40',
    -34.60254,
    -58.37302,
    'Bóveda central del banco'
) ON CONFLICT (sucursal_id) DO UPDATE
SET tipo_sucursal = EXCLUDED.tipo_sucursal,
    saldo_total_sucursal = EXCLUDED.saldo_total_sucursal,
    caja_teorica_sucursal = EXCLUDED.caja_teorica_sucursal,
    total_tesoro = EXCLUDED.total_tesoro,
    direccion_sucursal = EXCLUDED.direccion_sucursal,
    observacion = EXCLUDED.observacion;

-- Opcional: limpiar restricciones antiguas con valor por defecto
ALTER TABLE public.saldos_sucursal
    ALTER COLUMN tipo_sucursal SET DEFAULT 'sucursal';
