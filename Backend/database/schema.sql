-- CapiAgentes PostgreSQL schema
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS alerts;

-- Catalog of platform users/teams for alerts workflow
CREATE TABLE IF NOT EXISTS alerts.users (
  id UUID PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  email TEXT,
  full_name TEXT,
  team TEXT,
  role TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts.teams (
  id UUID PRIMARY KEY,
  team_name TEXT NOT NULL UNIQUE,
  department TEXT,
  manager_id UUID REFERENCES alerts.users(id),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Agent catalog
CREATE TABLE IF NOT EXISTS public.agentes (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre           TEXT NOT NULL UNIQUE,
  rol              TEXT NOT NULL,
  descripcion      TEXT,
  herramientas     TEXT[] NOT NULL DEFAULT '{}',
  nivel_privilegio TEXT NOT NULL DEFAULT 'standard'
                     CHECK (nivel_privilegio IN ('restricted','standard','elevated','privileged','admin')),
  activo           BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Financial snapshot per sucursal
CREATE TABLE IF NOT EXISTS public.saldos_sucursal (
  id                        BIGSERIAL PRIMARY KEY,
  sucursal_id               TEXT NOT NULL UNIQUE,
  sucursal_numero           INTEGER NOT NULL,
  sucursal_nombre           TEXT NOT NULL,
  telefonos                 TEXT,
  calle                     TEXT,
  altura                    INTEGER,
  barrio                    TEXT,
  comuna                    INTEGER,
  codigo_postal             INTEGER,
  codigo_postal_argentino   TEXT,
  saldo_total_sucursal      NUMERIC(20,2) NOT NULL,
  caja_teorica_sucursal     NUMERIC(20,2),
  total_atm                 NUMERIC(20,2) DEFAULT 0,
  total_ats                 NUMERIC(20,2) DEFAULT 0,
  total_tesoro              NUMERIC(20,2) DEFAULT 0,
  total_cajas_ventanilla    NUMERIC(20,2) DEFAULT 0,
  total_buzon_depositos     NUMERIC(20,2) DEFAULT 0,
  total_recaudacion         NUMERIC(20,2) DEFAULT 0,
  total_caja_chica          NUMERIC(20,2) DEFAULT 0,
  total_otros               NUMERIC(20,2) DEFAULT 0,
  direccion_sucursal        TEXT,
  latitud                   DOUBLE PRECISION,
  longitud                  DOUBLE PRECISION,
  observacion               TEXT,
  medido_en                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_saldo_sucursal_medido_en
  ON public.saldos_sucursal (medido_en DESC);

CREATE TABLE IF NOT EXISTS public.saldos_dispositivo (
  id               BIGSERIAL PRIMARY KEY,
  sucursal_id      TEXT NOT NULL,
  dispositivo_id   TEXT NOT NULL,
  tipo_dispositivo TEXT NOT NULL CHECK (tipo_dispositivo IN ('ATM','ATS','TESORO')),
  saldo_total      NUMERIC(20,2) NOT NULL,
  caja_teorica     NUMERIC(20,2),
  cant_d1          INTEGER NOT NULL DEFAULT 0,
  cant_d2          INTEGER NOT NULL DEFAULT 0,
  cant_d3          INTEGER NOT NULL DEFAULT 0,
  cant_d4          INTEGER NOT NULL DEFAULT 0,
  direccion        TEXT,
  latitud          NUMERIC(9,6),
  longitud         NUMERIC(9,6),
  observacion      TEXT,
  medido_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT fk_saldos_dispositivo_sucursal
    FOREIGN KEY (sucursal_id)
    REFERENCES public.saldos_sucursal (sucursal_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_saldo_dispositivo_tiempo
  ON public.saldos_dispositivo (sucursal_id, dispositivo_id, medido_en);

CREATE INDEX IF NOT EXISTS ix_saldo_dispositivo_latest
  ON public.saldos_dispositivo (sucursal_id, dispositivo_id, medido_en DESC);

CREATE OR REPLACE VIEW public.saldos_actuales_sucursal_oficial AS
SELECT DISTINCT ON (sucursal_id)
  sucursal_id,
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
  medido_en,
  observacion
FROM public.saldos_sucursal
ORDER BY sucursal_id, medido_en DESC;

CREATE OR REPLACE VIEW public.saldos_actuales_dispositivo AS
SELECT *
FROM (
  SELECT
    s.*,
    ROW_NUMBER() OVER (
      PARTITION BY s.sucursal_id, s.dispositivo_id
      ORDER BY s.medido_en DESC
    ) AS rn
  FROM public.saldos_dispositivo s
) t
WHERE t.rn = 1;

CREATE OR REPLACE VIEW public.saldos_actuales_sucursal_dispositivos AS
SELECT
  sucursal_id,
  SUM(saldo_total) AS saldo_total_dispositivos,
  SUM(caja_teorica) AS caja_teorica_dispositivos,
  SUM(cant_d1) AS cant_d1,
  SUM(cant_d2) AS cant_d2,
  SUM(cant_d3) AS cant_d3,
  SUM(cant_d4) AS cant_d4,
  MAX(medido_en) AS medido_en_ultimo
FROM public.saldos_actuales_dispositivo
GROUP BY sucursal_id;

CREATE OR REPLACE VIEW public.saldos_conciliacion_sucursal AS
SELECT
  o.sucursal_id,
  o.saldo_total_sucursal,
  d.saldo_total_dispositivos,
  (o.saldo_total_sucursal - COALESCE(d.saldo_total_dispositivos, 0)) AS desfase_oficial_vs_dispositivos,
  o.caja_teorica_sucursal,
  d.caja_teorica_dispositivos,
  o.total_tesoro,
  o.total_cajas_ventanilla,
  o.total_buzon_depositos,
  o.total_recaudacion,
  o.medido_en AS medido_en_oficial,
  d.medido_en_ultimo AS medido_en_dispositivos
FROM public.saldos_actuales_sucursal_oficial o
LEFT JOIN public.saldos_actuales_sucursal_dispositivos d
  ON d.sucursal_id = o.sucursal_id;

-- Operational events
CREATE TABLE IF NOT EXISTS public.eventos (
  id           BIGSERIAL PRIMARY KEY,
  ocurrido_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
  agente_id    UUID NOT NULL REFERENCES public.agentes(id),
  tipo_evento  TEXT NOT NULL,
  ejecucion_id TEXT,
  estado       TEXT NOT NULL,
  duracion_ms  INTEGER,
  tokens_total INTEGER,
  costo_usd    NUMERIC(10,4),
  mensaje      TEXT,
  sucursal_id  TEXT REFERENCES public.saldos_sucursal(sucursal_id) ON DELETE SET NULL,
  dispositivo_id TEXT
);

CREATE INDEX IF NOT EXISTS ix_eventos_tiempo        ON public.eventos (ocurrido_en DESC);
CREATE INDEX IF NOT EXISTS ix_eventos_agente_tiempo ON public.eventos (agente_id, ocurrido_en DESC);
CREATE INDEX IF NOT EXISTS ix_eventos_ejecucion     ON public.eventos (ejecucion_id);
CREATE INDEX IF NOT EXISTS ix_eventos_sucursal      ON public.eventos (sucursal_id);
CREATE INDEX IF NOT EXISTS ix_eventos_dispositivo   ON public.eventos (dispositivo_id);

-- Alerts domain
CREATE TABLE IF NOT EXISTS alerts.historical_alerts (
  id UUID PRIMARY KEY,
  alert_code TEXT NOT NULL UNIQUE,
  "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now(),
  alert_type TEXT,
  priority TEXT,
  agent_source TEXT,
  title TEXT NOT NULL,
  description TEXT,
  financial_impact NUMERIC(20,2),
  currency TEXT NOT NULL DEFAULT 'USD',
  confidence_score NUMERIC(6,3),
  status TEXT NOT NULL,
  resolved_at TIMESTAMPTZ,
  resolved_by UUID REFERENCES alerts.users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts.affected_entities (
  alert_id UUID REFERENCES alerts.historical_alerts(id) ON DELETE CASCADE,
  entity_type TEXT NOT NULL,
  entity_name TEXT,
  entity_id TEXT NOT NULL,
  impact_level TEXT,
  affected_value NUMERIC(20,2),
  currency TEXT DEFAULT 'USD',
  risk_notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ,
  PRIMARY KEY (alert_id, entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS public.alertas (
  id          BIGSERIAL PRIMARY KEY,
  creada_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
  agente_id   UUID REFERENCES public.agentes(id),
  prioridad   TEXT NOT NULL CHECK (prioridad IN ('baja','media','alta','critica')),
  estado      TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta','resuelta','silenciada')),
  problema    TEXT NOT NULL,
  hipotesis   TEXT,
  impacto     TEXT,
  datos_clave JSONB NOT NULL DEFAULT '[]'::jsonb,
  acciones    TEXT,
  sucursal_id TEXT REFERENCES public.saldos_sucursal(sucursal_id) ON DELETE SET NULL,
  dispositivo_id TEXT,
  evento_id   BIGINT REFERENCES public.eventos(id),
  dedupe_clave TEXT
);

CREATE INDEX IF NOT EXISTS ix_alertas_estado_tiempo ON public.alertas (estado, creada_en DESC);
CREATE INDEX IF NOT EXISTS ix_alertas_agente        ON public.alertas (agente_id, creada_en DESC);
CREATE INDEX IF NOT EXISTS ix_alertas_evento        ON public.alertas (evento_id);
CREATE INDEX IF NOT EXISTS ix_alertas_sucursal      ON public.alertas (sucursal_id);
CREATE INDEX IF NOT EXISTS ix_alertas_dispositivo   ON public.alertas (dispositivo_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_alertas_dedupe_abiertas
  ON public.alertas (dedupe_clave)
  WHERE dedupe_clave IS NOT NULL AND estado = 'abierta';

CREATE OR REPLACE VIEW public.alertas_para_llm AS
SELECT
  a.id,
  a.creada_en,
  a.agente_id,
  a.prioridad,
  a.estado,
  CONCAT(
    'Problema: ', a.problema, ' | ',
    'Hipotesis: ', COALESCE(a.hipotesis, 'N/D'), ' | ',
    'Impacto: ', COALESCE(a.impacto, 'N/D'), ' | ',
    'Datos clave: ', COALESCE((
      SELECT string_agg(elem, '; ')
      FROM jsonb_array_elements_text(a.datos_clave) AS t(elem)
    ), 'N/D'),
    ' | Acciones: ', COALESCE(a.acciones, 'N/D')
  ) AS contexto_llm
FROM public.alertas a;

CREATE TABLE IF NOT EXISTS alerts.ai_analysis (
  id SERIAL PRIMARY KEY,
  alert_id UUID REFERENCES alerts.historical_alerts(id) ON DELETE CASCADE,
  root_cause TEXT,
  probability_fraud NUMERIC(6,3),
  probability_system_error NUMERIC(6,3),
  similar_incidents_count INTEGER,
  trend_analysis TEXT,
  risk_assessment TEXT,
  confidence_level NUMERIC(6,3),
  model_version TEXT,
  analysis_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts.recommended_actions (
  id SERIAL PRIMARY KEY,
  alert_id UUID REFERENCES alerts.historical_alerts(id) ON DELETE CASCADE,
  priority INTEGER,
  action_type TEXT,
  action_description TEXT,
  estimated_time_minutes INTEGER,
  responsible_team TEXT,
  status TEXT,
  assigned_to UUID REFERENCES alerts.users(id)
);

CREATE TABLE IF NOT EXISTS alerts.cash_policies (
  id SERIAL PRIMARY KEY,
  channel TEXT NOT NULL UNIQUE,
  max_surplus_pct NUMERIC(6,3) NOT NULL DEFAULT 0.10,
  max_deficit_pct NUMERIC(6,3) NOT NULL DEFAULT 0.05,
  min_buffer_amount NUMERIC(20,2) NOT NULL DEFAULT 0,
  daily_withdrawal_limit NUMERIC(20,2),
  daily_deposit_limit NUMERIC(20,2),
  reload_lead_hours INTEGER NOT NULL DEFAULT 12,
  sla_hours INTEGER NOT NULL DEFAULT 24,
  truck_fixed_cost NUMERIC(20,2) NOT NULL DEFAULT 0,
  truck_variable_cost_per_kg NUMERIC(20,2) NOT NULL DEFAULT 0,
  notes TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts.human_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id UUID REFERENCES alerts.historical_alerts(id) ON DELETE CASCADE,
  recommended_action_id INTEGER REFERENCES alerts.recommended_actions(id) ON DELETE SET NULL,
  task_title TEXT,
  task_description TEXT,
  priority INTEGER DEFAULT 1,
  status TEXT DEFAULT 'pending',
  assigned_to_user UUID REFERENCES alerts.users(id),
  assigned_to_team TEXT,
  due_date TIMESTAMPTZ,
  estimated_effort_hours NUMERIC(10,2),
  actual_effort_hours NUMERIC(10,2),
  progress_percentage INTEGER DEFAULT 0,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  completion_notes TEXT,
  blockers TEXT,
  dependencies TEXT[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts.ai_context (
  alert_id UUID PRIMARY KEY REFERENCES alerts.historical_alerts(id) ON DELETE CASCADE,
  context_type TEXT,
  business_context TEXT,
  operational_context TEXT,
  historical_context TEXT,
  stakeholder_impact TEXT,
  regulatory_implications TEXT,
  technical_details TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts.resolution_log (
  id SERIAL PRIMARY KEY,
  alert_id UUID REFERENCES alerts.historical_alerts(id) ON DELETE CASCADE,
  resolution_step TEXT,
  action_taken TEXT,
  performed_by UUID REFERENCES alerts.users(id),
  performed_by_team TEXT,
  performed_at TIMESTAMPTZ,
  effectiveness_score NUMERIC(6,3),
  follow_up_required BOOLEAN DEFAULT FALSE,
  follow_up_due_date TIMESTAMPTZ,
  lessons_learned TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts.alert_metrics (
  id SERIAL PRIMARY KEY,
  alert_id UUID REFERENCES alerts.historical_alerts(id) ON DELETE CASCADE,
  metric_type TEXT,
  metric_name TEXT,
  metric_value NUMERIC(20,4),
  metric_unit TEXT,
  metadata JSONB,
  trend TEXT,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
