# Esquema mínimo de base de datos (CapiAgentes)

Objetivo: modelo simple, legible por humanos y útil para IA. Tres tablas:
- `agentes`: catálogo con ID único, nombre, rol y herramientas.
- `eventos`: histórico compacto (10 campos) para trazabilidad.
- `alertas`: diseñada para que humanos y LLM entiendan rápido el problema, con 12 campos.

Notas generales
- Motor sugerido: PostgreSQL.
- Tiempos en `TIMESTAMPTZ` (UTC) con `DEFAULT now()` donde aplique.
- Textos breves y claros; detalles extensos en `detalle`/`datos_clave`.

---

## 1) Catálogo de agentes

Propósito: identificar de forma única cada agente y qué hace.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS agentes (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre        TEXT NOT NULL UNIQUE,           -- p.ej.: CapiBuscadorNoticias
  rol           TEXT NOT NULL,                  -- p.ej.: buscador_noticias
  descripcion   TEXT,                           -- 1-2 frases sobre su propósito
  herramientas  TEXT[] NOT NULL DEFAULT '{}',   -- p.ej.: ['busqueda_web','rss','scraping','resumen']
  nivel_privilegio TEXT NOT NULL DEFAULT 'standard'
                  CHECK (nivel_privilegio IN ('restricted','standard','elevated','privileged','admin')),
  activo        BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices sugeridos
-- UNIQUE(nombre) ya impide duplicados
```

Campos clave
- `nombre`: humano-amigable; único.
- `rol`: etiqueta simple para clasificar (p.ej., `buscador_noticias`).
- `herramientas`: lista breve de capabilities del agente.
- `nivel_privilegio`: integra con el módulo de autorización (valores: `restricted | standard | elevated | privileged | admin`). Permite ajustar desde BD sin tocar archivos.

Notas rápidas (autorización)
- Para cambiar el nivel del Capi Desktop: `UPDATE agentes SET nivel_privilegio = 'elevated' WHERE nombre = 'capi_desktop';`
- Recomendación: mantener por defecto `standard` y elevar temporalmente solo cuando sea necesario.

Nota de implementación (importante)
- Al implementar esta tabla en entornos productivos, agregar un endpoint REST/GQL en el backend para:
  - listar y actualizar `nivel_privilegio` por `nombre`/`id` de agente;
  - auditar cambios (quién/cuándo/por qué).
- Reemplazar cualquier hardcode o fallback temporal en el módulo de autorización para que el valor efectivo provenga de BD cuando `DATABASE_URL` esté disponible.

---

## 2) Eventos (10 campos esenciales)

Propósito: trazabilidad y diagnósticos rápidos sin complejidad.

```sql
CREATE TABLE IF NOT EXISTS eventos (
  id            BIGSERIAL PRIMARY KEY,               -- 1
  ocurrido_en   TIMESTAMPTZ NOT NULL DEFAULT now(),  -- 2
  agente_id     UUID NOT NULL REFERENCES agentes(id),-- 3
  tipo_evento   TEXT NOT NULL,                        -- 4 (p.ej.: 'busqueda_iniciada','fuente_parseada','error')
  ejecucion_id  TEXT,                                 -- 5 (run para agrupar)
  estado        TEXT NOT NULL,                        -- 6 ('ok'|'error'|'info')
  duracion_ms   INTEGER,                              -- 7
  tokens_total  INTEGER,                              -- 8 (opcional, métrica IA)
  costo_usd     NUMERIC(10,4),                        -- 9 (opcional)
  mensaje       TEXT                                  -- 10 (nota breve, query/fuente o error)
);

-- Índices útiles
CREATE INDEX IF NOT EXISTS idx_eventos_tiempo       ON eventos (ocurrido_en DESC);
CREATE INDEX IF NOT EXISTS idx_eventos_agente_tiempo ON eventos (agente_id, ocurrido_en DESC);
CREATE INDEX IF NOT EXISTS idx_eventos_ejecucion    ON eventos (ejecucion_id);
```

Campos clave
- `tipo_evento`: nombre simple y consistente.
- `mensaje`: texto corto con lo más relevante (query/fuente/error).

---

## 3) Alertas (12 campos, orientada a humanos y LLM)

Propósito: que en una lectura rápida una persona entienda el problema, y que el LLM pueda usarlo como contexto para resolver.

```sql
CREATE TABLE IF NOT EXISTS alertas (
  id           BIGSERIAL PRIMARY KEY,                                            -- 1
  creada_en    TIMESTAMPTZ NOT NULL DEFAULT now(),                               -- 2
  agente_id    UUID REFERENCES agentes(id),                                       -- 3
  prioridad    TEXT NOT NULL CHECK (prioridad IN ('baja','media','alta','critica')), -- 4
  estado       TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta','resuelta','silenciada')), -- 5
  problema     TEXT NOT NULL,                                                     -- 6: síntoma en 1 frase
  hipotesis    TEXT,                                                              -- 7: causa raíz probable (1–2 frases)
  impacto      TEXT,                                                              -- 8: a quién/qué afecta y magnitud
  datos_clave  JSONB NOT NULL DEFAULT '[]'::jsonb,                                -- 9: 3–5 hechos/medidas (strings)
  acciones     TEXT,                                                              -- 10: próximos pasos sugeridos
  evento_id    BIGINT REFERENCES eventos(id),                                     -- 11: vínculo con el evento disparador
  dedupe_clave TEXT                                                               -- 12: hash estable para evitar duplicados
);

-- Índices prácticos
CREATE INDEX IF NOT EXISTS ix_alertas_estado_tiempo ON alertas (estado, creada_en DESC);
CREATE INDEX IF NOT EXISTS ix_alertas_agente        ON alertas (agente_id, creada_en DESC);
CREATE INDEX IF NOT EXISTS ix_alertas_evento        ON alertas (evento_id);

-- Evitar duplicados de alertas "abiertas" por misma causa
CREATE UNIQUE INDEX IF NOT EXISTS uq_alertas_dedupe_abiertas
  ON alertas (dedupe_clave)
  WHERE dedupe_clave IS NOT NULL AND estado = 'abierta';
```

Guía de llenado (alertas)
- `problema`: “No llegan artículos nuevos de X desde hace 2h”.
- `hipotesis`: “API de X aplica rate-limiting por exceso de requests”.
- `impacto`: “Panel sin actualizaciones; backlog creciente”.
- `datos_clave`: ["429 desde 12:10","80 req/min > límite 60","fuente=newsapi","ventana=2h"].
- `acciones`: “Reducir QPS a 50; habilitar backoff exponencial; reintentar backlog”.
- `dedupe_clave`: sha256(prioridad + agente_id + tipo/causa normalizada).

Vista recomendada (texto listo para LLM)
```sql
CREATE OR REPLACE VIEW alertas_para_llm AS
SELECT
  a.id,
  a.creada_en,
  a.agente_id,
  a.prioridad,
  a.estado,
  CONCAT(
    'Problema: ', a.problema, ' | ',
    'Hipótesis: ', COALESCE(a.hipotesis,'N/D'), ' | ',
    'Impacto: ', COALESCE(a.impacto,'N/D'), ' | ',
    'Datos clave: ', COALESCE((
      SELECT string_agg(elem, '; ')
      FROM jsonb_array_elements_text(a.datos_clave) AS t(elem)
    ), 'N/D'),
    ' | Acciones: ', COALESCE(a.acciones,'N/D')
  ) AS contexto_llm
FROM alertas a;
```

Evoluciones futuras (sin romper el modelo)
- Añadir `resumen_llm` si querés curar el texto manualmente.
- Tabla opcional `alertas_envios` si más adelante notificás por email/Slack.
- Si necesitás semántica, incorporar `pgvector` y embeddings con otra tabla.

---

## 4) Saldos en tiempo real (Sucursal vs Dispositivos)

Objetivo: conocer el 100% del efectivo por sucursal (oficial) y, en paralelo, el detalle por cada ATM/ATS/TESORO con conteos por denominación. Timestamp al final. Dirección y coordenadas incluidas.

### 4.1 Snapshot oficial por sucursal (100% del cash)

```sql
CREATE TABLE IF NOT EXISTS saldos_sucursal (
  id                      BIGSERIAL PRIMARY KEY,
  sucursal_id             TEXT NOT NULL UNIQUE,                                  -- S001

  -- Importes principales (primero)
  saldo_total_sucursal    NUMERIC(20,2) NOT NULL,                         -- 100% del efectivo de la sucursal
  caja_teorica_sucursal   NUMERIC(20,2),                                  -- esperado por sistema

  -- Desgloses opcionales (si se relevan)
  total_atm               NUMERIC(20,2),
  total_ats               NUMERIC(20,2),
  total_tesoro            NUMERIC(20,2),                                  -- bóveda/tesoro
  total_cajas_ventanilla  NUMERIC(20,2),                                  -- cajas de atención
  total_buzon_depositos   NUMERIC(20,2),                                  -- buzón/depósito nocturno
  total_recaudacion       NUMERIC(20,2),                                  -- backoffice/recuento temporal
  total_caja_chica        NUMERIC(20,2),
  total_otros             NUMERIC(20,2),                                  -- cualquier otro efectivo local

  -- Ubicación de la sucursal
  direccion_sucursal      TEXT,
  latitud                 NUMERIC(9,6),
  longitud                NUMERIC(9,6),

  observacion             TEXT,
  medido_en               TIMESTAMPTZ NOT NULL DEFAULT now()              -- timestamp al final
);

-- Índices: ordenar por última medición
CREATE INDEX IF NOT EXISTS ix_saldo_sucursal_medido_en
  ON saldos_sucursal (medido_en DESC);

-- Vista: último snapshot oficial por sucursal
CREATE OR REPLACE VIEW saldos_actuales_sucursal_oficial AS
SELECT DISTINCT ON (sucursal_id)
  sucursal_id,
  saldo_total_sucursal,
  caja_teorica_sucursal,
  total_atm, total_ats, total_tesoro, total_cajas_ventanilla, total_buzon_depositos,
  total_recaudacion, total_caja_chica, total_otros,
  direccion_sucursal, latitud, longitud,
  medido_en,
  observacion
FROM saldos_sucursal
ORDER BY sucursal_id, medido_en DESC;
```

### 4.2 Snapshots por dispositivo (ATM/ATS/TESORO)

```sql
CREATE TABLE IF NOT EXISTS saldos_dispositivo (
  id               BIGSERIAL PRIMARY KEY,
  sucursal_id      TEXT NOT NULL,                                        -- S001
  dispositivo_id   TEXT NOT NULL,                                        -- ATM-12 | ATS-04 | TESORO-S001
  tipo_dispositivo TEXT NOT NULL CHECK (tipo_dispositivo IN ('ATM','ATS','TESORO')),

  -- Importes principales (primero)
  saldo_total      NUMERIC(20,2) NOT NULL,                               -- total del dispositivo (todas las denom.)
  caja_teorica     NUMERIC(20,2),                                        -- esperado por sistema

  -- Conteo por 4 denominaciones (D1..D4 -> mapear a valores nominales en tu ETL)
  cant_d1          INTEGER NOT NULL DEFAULT 0,
  cant_d2          INTEGER NOT NULL DEFAULT 0,
  cant_d3          INTEGER NOT NULL DEFAULT 0,
  cant_d4          INTEGER NOT NULL DEFAULT 0,

  -- Ubicación del dispositivo (si aplica)
  direccion        TEXT,
  latitud          NUMERIC(9,6),
  longitud         NUMERIC(9,6),

  observacion      TEXT,
  medido_en        TIMESTAMPTZ NOT NULL DEFAULT now(),                   -- timestamp al final
  CONSTRAINT fk_saldos_dispositivo_sucursal
    FOREIGN KEY (sucursal_id)
    REFERENCES saldos_sucursal (sucursal_id)
);

-- Índices para “último por dispositivo”
CREATE UNIQUE INDEX IF NOT EXISTS uq_saldo_dispositivo_tiempo
  ON saldos_dispositivo (sucursal_id, dispositivo_id, medido_en);

CREATE INDEX IF NOT EXISTS ix_saldo_dispositivo_latest
  ON saldos_dispositivo (sucursal_id, dispositivo_id, medido_en DESC);

-- Vista: último snapshot por dispositivo
CREATE OR REPLACE VIEW saldos_actuales_dispositivo AS
SELECT *
FROM (
  SELECT
    s.*,
    ROW_NUMBER() OVER (PARTITION BY s.sucursal_id, s.dispositivo_id ORDER BY s.medido_en DESC) AS rn
  FROM saldos_dispositivo s
) t
WHERE t.rn = 1;
```

### 4.3 Conciliación (oficial vs dispositivos)

```sql
-- Agregado actual por sucursal derivado de dispositivos (ATM+ATS+TESORO)
CREATE OR REPLACE VIEW saldos_actuales_sucursal_dispositivos AS
SELECT
  sucursal_id,
  SUM(saldo_total)                          AS saldo_total_dispositivos,
  SUM(caja_teorica)                         AS caja_teorica_dispositivos,
  SUM(cant_d1) AS cant_d1,
  SUM(cant_d2) AS cant_d2,
  SUM(cant_d3) AS cant_d3,
  SUM(cant_d4) AS cant_d4,
  MAX(medido_en)                            AS medido_en_ultimo
FROM saldos_actuales_dispositivo
GROUP BY sucursal_id;

-- Vista de conciliación: total oficial vs suma de dispositivos
CREATE OR REPLACE VIEW saldos_conciliacion_sucursal AS
SELECT
  o.sucursal_id,
  o.saldo_total_sucursal,
  d.saldo_total_dispositivos,
  (o.saldo_total_sucursal - COALESCE(d.saldo_total_dispositivos,0)) AS desfase_oficial_vs_dispositivos,
  o.caja_teorica_sucursal,
  d.caja_teorica_dispositivos,
  o.total_tesoro, o.total_cajas_ventanilla, o.total_buzon_depositos, o.total_recaudacion,
  o.medido_en   AS medido_en_oficial,
  d.medido_en_ultimo AS medido_en_dispositivos
FROM saldos_actuales_sucursal_oficial o
LEFT JOIN saldos_actuales_sucursal_dispositivos d
  ON d.sucursal_id = o.sucursal_id;
```

Consultas rápidas (SQL)
- Último saldo oficial por sucursal:
```sql
SELECT * FROM saldos_actuales_sucursal_oficial ORDER BY sucursal_id;
```
- Suma actual por dispositivos (ATM+ATS+TESORO) por sucursal:
```sql
SELECT * FROM saldos_actuales_sucursal_dispositivos ORDER BY sucursal_id;
```
- Conciliación (oficial vs dispositivos) con desfase:
```sql
SELECT sucursal_id, saldo_total_sucursal, saldo_total_dispositivos, desfase_oficial_vs_dispositivos,
       medido_en_oficial, medido_en_dispositivos
FROM saldos_conciliacion_sucursal
ORDER BY sucursal_id;
```



