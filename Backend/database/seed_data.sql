-- CapiAgentes PostgreSQL Seed Data
-- Professional seed data for Historical Alerts System
-- Author: Claude Code Expert

INSERT INTO alerts.users (id, username, email, full_name, team, role) VALUES
('550e8400-e29b-41d4-a716-446655440000', 'admin', 'admin@capi.com', 'System Administrator', 'IT', 'admin'),
('550e8400-e29b-41d4-a716-446655440001', 'security_lead', 'security@capi.com', 'Maria Rodriguez', 'Security', 'lead'),
('550e8400-e29b-41d4-a716-446655440002', 'analyst_1', 'analyst1@capi.com', 'Carlos Mendoza', 'Analysis', 'analyst'),
('550e8400-e29b-41d4-a716-446655440003', 'ops_manager', 'ops@capi.com', 'Ana Silva', 'Operations', 'manager'),
('550e8400-e29b-41d4-a716-446655440004', 'cs_lead', 'cs@capi.com', 'Pedro Gomez', 'Customer Service', 'lead');

-- Seed Agents used by LangGraph nodes (idempotent)
INSERT INTO public.agentes (id, nombre, rol, descripcion, herramientas, nivel_privilegio) VALUES
('b37d1f90-6b35-4fb3-866e-2f88c9b29850', 'capi_elcajas', 'cash_diagnostics', 'Agente especializado en diagnostico de caja y generacion de alertas.', ARRAY['diagnostico', 'alertas', 'recomendaciones'], 'elevated')
ON CONFLICT (id) DO NOTHING;

-- Seed Teams
INSERT INTO alerts.teams (id, team_name, department, manager_id) VALUES
('660e8400-e29b-41d4-a716-446655440000', 'Security', 'IT Security', '550e8400-e29b-41d4-a716-446655440001'),
('660e8400-e29b-41d4-a716-446655440001', 'Analysis', 'Financial Analysis', '550e8400-e29b-41d4-a716-446655440002'),
('660e8400-e29b-41d4-a716-446655440002', 'Operations', 'Business Operations', '550e8400-e29b-41d4-a716-446655440003'),
('660e8400-e29b-41d4-a716-446655440003', 'Customer Service', 'Support', '550e8400-e29b-41d4-a716-446655440004');

-- Seed Historical Alerts
INSERT INTO alerts.historical_alerts (
    id, alert_code, timestamp, alert_type, priority, agent_source, title, description,
    financial_impact, currency, confidence_score, status
) VALUES
(
    '770e8400-e29b-41d4-a716-446655440000',
    'CAPI_2025_001',
    NOW() - INTERVAL '2 hours',
    'critical_anomaly',
    'critical',
    'anomaly',
    'Massive Transaction Pattern Deviation',
    'Detected 45 high-value transactions exceeding 400% of normal patterns across multiple branches',
    850000.00,
    'USD',
    0.92,
    'active'
),
(
    '770e8400-e29b-41d4-a716-446655440001',
    'CAPI_2025_002',
    NOW() - INTERVAL '1 day',
    'system_performance',
    'high',
    'branch',
    'Branch Sistema Norte Performance Degradation',
    'Branch Norte showing 65% slower response times and increased error rates',
    25000.00,
    'USD',
    0.87,
    'in_progress'
),
(
    '770e8400-e29b-41d4-a716-446655440002',
    'CAPI_2025_003',
    NOW() - INTERVAL '3 days',
    'customer_service',
    'medium',
    'summary',
    'Customer Satisfaction Score Drop',
    'Customer satisfaction dropped 15% in the last week across all service channels',
    12000.00,
    'USD',
    0.78,
    'resolved'
);

-- Seed Affected Entities
INSERT INTO alerts.affected_entities (alert_id, entity_type, entity_name, entity_id, impact_level) VALUES
('770e8400-e29b-41d4-a716-446655440000', 'branch', 'Branch Norte', 'BRN001', 'high'),
('770e8400-e29b-41d4-a716-446655440000', 'branch', 'Branch Centro', 'BRC001', 'high'),
('770e8400-e29b-41d4-a716-446655440000', 'branch', 'Branch Sur', 'BRS001', 'medium'),
('770e8400-e29b-41d4-a716-446655440001', 'branch', 'Branch Norte', 'BRN001', 'critical'),
('770e8400-e29b-41d4-a716-446655440002', 'system', 'Customer Service Platform', 'CSP001', 'medium'),
('770e8400-e29b-41d4-a716-446655440002', 'system', 'Mobile App', 'APP001', 'low');

-- Seed AI Analysis
INSERT INTO alerts.ai_analysis (
    alert_id, root_cause, probability_fraud, probability_system_error,
    similar_incidents_count, trend_analysis, risk_assessment, confidence_level, model_version
) VALUES
(
    '770e8400-e29b-41d4-a716-446655440000',
    'Coordinated transaction pattern suggests either sophisticated fraud scheme or system malfunction in payment processing',
    0.78,
    0.22,
    2,
    'Escalating pattern over 72 hours with exponential growth in transaction volumes',
    'HIGH RISK: Pattern matches known fraud signatures with 78% probability. Immediate containment required.',
    0.92,
    'fraud_detection_v2.1'
),
(
    '770e8400-e29b-41d4-a716-446655440001',
    'Database connection pool exhaustion combined with memory leak in transaction processing module',
    0.05,
    0.95,
    5,
    'Progressive degradation over 48 hours, pattern consistent with resource leak',
    'MEDIUM RISK: System performance impact affecting customer experience. Technical resolution needed.',
    0.87,
    'performance_analysis_v1.8'
),
(
    '770e8400-e29b-41d4-a716-446655440002',
    'Service quality issues stemming from new staff training gaps and system interface changes',
    0.10,
    0.30,
    8,
    'Declining trend over 7 days, correlates with recent system updates and staff changes',
    'LOW RISK: Operational issue with clear remediation path. Training and process improvements needed.',
    0.78,
    'customer_analysis_v1.3'
);

-- Seed Recommended Actions
INSERT INTO alerts.recommended_actions (
    alert_id, priority, action_type, action_description, estimated_time_minutes,
    responsible_team, status, assigned_to
) VALUES
(
    '770e8400-e29b-41d4-a716-446655440000',
    1,
    'immediate_terminal_lockdown',
    'Lock all affected terminals immediately to prevent further unauthorized transactions',
    5,
    'Security',
    'completed',
    '550e8400-e29b-41d4-a716-446655440001'
),
(
    '770e8400-e29b-41d4-a716-446655440000',
    2,
    'customer_verification',
    'Contact customers associated with flagged transactions for verification',
    120,
    'Customer Service',
    'in_progress',
    '550e8400-e29b-41d4-a716-446655440004'
),
(
    '770e8400-e29b-41d4-a716-446655440000',
    3,
    'forensic_analysis',
    'Deep forensic analysis of transaction logs and system access patterns',
    240,
    'Security',
    'pending',
    '550e8400-e29b-41d4-a716-446655440001'
),
(
    '770e8400-e29b-41d4-a716-446655440001',
    1,
    'system_restart',
    'Restart affected services to clear memory leaks and reset connection pools',
    30,
    'Operations',
    'completed',
    '550e8400-e29b-41d4-a716-446655440003'
),
(
    '770e8400-e29b-41d4-a716-446655440001',
    2,
    'performance_monitoring',
    'Implement enhanced monitoring for early detection of similar issues',
    180,
    'Operations',
    'in_progress',
    '550e8400-e29b-41d4-a716-446655440003'
);

-- Seed Human Tasks
INSERT INTO alerts.human_tasks (
    alert_id, recommended_action_id, task_title, task_description, priority, status,
    assigned_to_user, assigned_to_team, due_date, estimated_effort_hours, progress_percentage
) VALUES
(
    '770e8400-e29b-41d4-a716-446655440000',
    (SELECT id FROM alerts.recommended_actions WHERE action_type = 'customer_verification' AND alert_id = '770e8400-e29b-41d4-a716-446655440000'),
    'Verify High-Value Transactions',
    'Contact all customers involved in transactions above $50k to verify legitimacy',
    1,
    'in_progress',
    '550e8400-e29b-41d4-a716-446655440004',
    'Customer Service',
    NOW() + INTERVAL '4 hours',
    3.0,
    65
),
(
    '770e8400-e29b-41d4-a716-446655440000',
    (SELECT id FROM alerts.recommended_actions WHERE action_type = 'forensic_analysis' AND alert_id = '770e8400-e29b-41d4-a716-446655440000'),
    'Complete Security Forensics',
    'Analyze all system logs, access patterns, and transaction flows for evidence of compromise',
    2,
    'pending',
    '550e8400-e29b-41d4-a716-446655440001',
    'Security',
    NOW() + INTERVAL '8 hours',
    6.0,
    0
),
(
    '770e8400-e29b-41d4-a716-446655440001',
    (SELECT id FROM alerts.recommended_actions WHERE action_type = 'performance_monitoring' AND alert_id = '770e8400-e29b-41d4-a716-446655440001'),
    'Implement Advanced Monitoring',
    'Deploy APM tools and set up alerting for performance degradation patterns',
    1,
    'in_progress',
    '550e8400-e29b-41d4-a716-446655440003',
    'Operations',
    NOW() + INTERVAL '1 day',
    4.5,
    30
);

-- Seed AI Context
INSERT INTO alerts.ai_context (
    alert_id, context_type, business_context, operational_context,
    historical_context, stakeholder_impact, regulatory_implications, technical_details
) VALUES
(
    '770e8400-e29b-41d4-a716-446655440000',
    'comprehensive_analysis',
    'Critical fraud detection event during peak business hours affecting three major branches. Potential revenue loss of $850K with reputation risk.',
    'Operations suspended at affected terminals. Customer service team handling inquiries. Security protocols activated.',
    'Similar pattern detected 6 months ago resolved through system patches. Previous incidents linked to API vulnerabilities.',
    'High impact on customer trust. Board notification required. Media attention possible.',
    'Must comply with PCI-DSS incident reporting. Regulatory notification within 24 hours required.',
    '{"affected_systems": ["payment_gateway", "transaction_processor", "audit_log"], "api_versions": ["v2.1", "v2.3"], "ip_ranges": ["192.168.1.0/24", "10.0.0.0/16"]}'::jsonb
),
(
    '770e8400-e29b-41d4-a716-446655440001',
    'technical_analysis',
    'Performance degradation affecting customer experience and potentially impacting revenue through transaction delays.',
    'Branch Norte operating at reduced capacity. Staff manually processing some transactions.',
    'Third performance issue this quarter. Previous issues resolved through infrastructure scaling.',
    'Moderate customer impact. Branch staff frustrated. Regional manager concerned.',
    'No immediate regulatory implications. May affect SLA compliance.',
    '{"memory_usage": "95%", "connection_pool_size": "exhausted", "error_rates": "15%", "response_times": "3.2s avg"}'::jsonb
),
(
    '770e8400-e29b-41d4-a716-446655440002',
    'customer_service_analysis',
    'Customer satisfaction decline affecting brand reputation and customer retention. Potential revenue impact through churn.',
    'Customer service team morale low. Increased complaint volume. Response times elevated.',
    'Satisfaction scores typically stable. Recent system changes may be contributing factor.',
    'Customer retention risk. Marketing concerned about NPS scores. Senior management monitoring.',
    'Consumer protection compliance requires service quality maintenance.',
    '{"satisfaction_score": 6.8, "previous_score": 8.1, "complaint_volume": "+35%", "avg_resolution_time": "48h"}'::jsonb
);

-- Seed Resolution Log
INSERT INTO alerts.resolution_log (
    alert_id, resolution_step, action_taken, performed_by,
    performed_by_team, effectiveness_score, notes
) VALUES
(
    '770e8400-e29b-41d4-a716-446655440000',
    1,
    'Activated emergency security protocols and locked affected terminals',
    '550e8400-e29b-41d4-a716-446655440001',
    'Security',
    9,
    'Immediate containment successful. No further unauthorized transactions detected after lockdown.'
),
(
    '770e8400-e29b-41d4-a716-446655440001',
    1,
    'Restarted application services and cleared connection pools',
    '550e8400-e29b-41d4-a716-446655440003',
    'Operations',
    8,
    'Performance improved significantly. Response times back to normal levels within 15 minutes.'
),
(
    '770e8400-e29b-41d4-a716-446655440002',
    1,
    'Implemented additional staff training and updated service procedures',
    '550e8400-e29b-41d4-a716-446655440004',
    'Customer Service',
    7,
    'Initial improvement in response quality. Monitoring satisfaction scores for sustained improvement.'
);

-- Seed Alert Metrics
INSERT INTO alerts.alert_metrics (
    alert_id, metric_type, metric_name, metric_value, metric_unit, metadata
) VALUES
(
    '770e8400-e29b-41d4-a716-446655440000',
    'financial',
    'potential_loss',
    850000.00,
    'USD',
    '{"calculation_method": "transaction_volume_analysis", "confidence": 0.92}'::jsonb
),
(
    '770e8400-e29b-41d4-a716-446655440000',
    'security',
    'risk_score',
    9.2,
    'score',
    '{"scale": "1-10", "factors": ["transaction_pattern", "fraud_probability", "financial_impact"]}'::jsonb
),
(
    '770e8400-e29b-41d4-a716-446655440001',
    'performance',
    'response_time_degradation',
    65.0,
    'percent',
    '{"baseline_ms": 500, "current_ms": 825, "measurement_period": "1h"}'::jsonb
),
(
    '770e8400-e29b-41d4-a716-446655440002',
    'satisfaction',
    'customer_satisfaction_drop',
    15.0,
    'percent',
    '{"previous_score": 8.1, "current_score": 6.8, "scale": "1-10"}'::jsonb
);-- Seed public events for operational alerting
WITH agent_ref AS (
    SELECT id FROM public.agentes WHERE nombre = 'capi_desktop' LIMIT 1
)
INSERT INTO public.eventos (agente_id, tipo_evento, ejecucion_id, estado, duracion_ms, tokens_total, costo_usd, mensaje)
SELECT agent_ref.id, data.tipo_evento, data.ejecucion_id, data.estado, data.duracion_ms, data.tokens_total, data.costo_usd, data.mensaje
FROM agent_ref,
     (VALUES
        ('monitoreo', 'evt_monitoreo_news', 'info', 1450, 1200, 0.08, 'Monitoreo completado con retrasos intermitentes'),
        ('ingesta', 'evt_ingesta_riesgo', 'warning', 2980, 2100, 0.32, 'Ingesta parcial: 2 fuentes con errores 429')
     ) AS data(tipo_evento, ejecucion_id, estado, duracion_ms, tokens_total, costo_usd, mensaje);

-- Seed public alerts catalog
WITH agent_ref AS (
    SELECT id FROM public.agentes WHERE nombre = 'capi_desktop' LIMIT 1
)
INSERT INTO public.alertas (
    creada_en,
    agente_id,
    prioridad,
    estado,
    problema,
    hipotesis,
    impacto,
    datos_clave,
    acciones,
    evento_id,
    dedupe_clave
)
SELECT
    NOW() - INTERVAL '15 minutes',
    agent_ref.id,
    'alta',
    'abierta',
    'Fuentes de noticias sin actualización',
    'El proveedor NewsAPI está aplicando rate limit por exceso de requests',
    'Sin novedades en panel financiero durante 20 minutos',
    '["429 desde 10:05","fuentes=NewsAPI,Reuters","backoff=30s"]'::jsonb,
    'Reducir frecuencia de requests a 30 segundos; habilitar cache local; notificar a operaciones',
    (SELECT id FROM public.eventos WHERE ejecucion_id = 'evt_monitoreo_news'),
    'alert_newsapi_rate_limit'
FROM agent_ref
UNION ALL
SELECT
    NOW() - INTERVAL '45 minutes',
    agent_ref.id,
    'media',
    'abierta',
    'Ingesta de riesgos incompleta',
    'Dos fuentes devuelven errores 429 tras actualización nocturna',
    'Reportes de riesgo sin consolidar para mesa de operación',
    '["429 en proveedor RiesgoMX","429 en proveedor RiskNow","Ejecución=evt_ingesta_riesgo"]'::jsonb,
    'Habilitar reintentos con backoff exponencial; coordinar con proveedores para elevar límite temporal',
    (SELECT id FROM public.eventos WHERE ejecucion_id = 'evt_ingesta_riesgo'),
    'alert_ingesta_riesgo_parcial'
FROM agent_ref;
-- Additional operational events (avisos) and alerts for testing
WITH agent_ref AS (
    SELECT id FROM public.agentes WHERE nombre = 'capi_desktop' LIMIT 1
)
INSERT INTO public.eventos (agente_id, tipo_evento, ejecucion_id, estado, duracion_ms, tokens_total, costo_usd, mensaje)
SELECT agent_ref.id, data.tipo_evento, data.ejecucion_id, data.estado, data.duracion_ms, data.tokens_total, data.costo_usd, data.mensaje
FROM agent_ref,
     (VALUES
        ('monitoreo', 'evt_monitor_fuentes', 'info', 1750, 980, 0.050, 'Fuentes revisadas con retrasos leves'),
        ('auditoria', 'evt_auditoria_logs', 'warning', 3250, 1620, 0.120, 'Auditoria detecta inconsistencias en logs'),
        ('resumen', 'evt_resumen_finanzas', 'info', 2140, 1310, 0.085, 'Resumen financiero sin datos de unidad 04')
     ) AS data(tipo_evento, ejecucion_id, estado, duracion_ms, tokens_total, costo_usd, mensaje);

WITH agent_ref AS (
    SELECT id FROM public.agentes WHERE nombre = 'capi_desktop' LIMIT 1
)
INSERT INTO public.alertas (
    creada_en,
    agente_id,
    prioridad,
    estado,
    problema,
    hipotesis,
    impacto,
    datos_clave,
    acciones,
    evento_id,
    dedupe_clave
)
SELECT
    NOW() - INTERVAL '5 minutes',
    agent_ref.id,
    'critica',
    'abierta',
    'Logs de acceso con inconsistencias',
    'Desfase en replicacion de auditoria produce registros duplicados',
    'Equipo de ciberseguridad sin visibilidad completa de accesos',
    '["logs duplicados","replicacion retrasada 12m","fuente=SIEM"]'::jsonb,
    'Forzar resincronizacion de cluster SIEM; validar integridad en lotes; alertar al SOC',
    (SELECT id FROM public.eventos WHERE ejecucion_id = 'evt_auditoria_logs'),
    'alert_logs_si_mismatch'
FROM agent_ref
UNION ALL
SELECT
    NOW() - INTERVAL '25 minutes',
    agent_ref.id,
    'alta',
    'abierta',
    'Panel financiero incompleto',
    'Una de las unidades no envio consolidado diario',
    'Reportes ejecutivos muestran huecos en unidad 04',
    '["unidad_04 sin datos","ultimo update=07:10","fuente=evt_resumen_finanzas"]'::jsonb,
    'Escalar a operaciones unidad 04; forzar reingesta desde backup; notificar PMO',
    (SELECT id FROM public.eventos WHERE ejecucion_id = 'evt_resumen_finanzas'),
    'alert_finanzas_unidad04_incompleta'
FROM agent_ref
UNION ALL
SELECT
    NOW() - INTERVAL '40 minutes',
    agent_ref.id,
    'media',
    'abierta',
    'Retrasos en fuentes externas',
    'Proveedor secundario responde con latencias > 4s',
    'Usuarios de monitoreo ven datos con 6 minutos de retraso',
    '["latencia 4.2s","fuente=ExternalNews","timeout=8s"]'::jsonb,
    'Aplicar throttling inteligente; activar cache caliente; coordinar con proveedor para ampliar limite',
    (SELECT id FROM public.eventos WHERE ejecucion_id = 'evt_monitor_fuentes'),
    'alert_fuentes_latencia_4s'
FROM agent_ref;
-- Seed cash policies for cash management
INSERT INTO alerts.cash_policies (channel, max_surplus_pct, max_deficit_pct, min_buffer_amount, daily_withdrawal_limit, daily_deposit_limit, reload_lead_hours, sla_hours, truck_fixed_cost, truck_variable_cost_per_kg, notes) VALUES
    ('Saldo Total', 0.080, 0.050, 600000.00, 2500000.00, 2500000.00, 6, 12, 150000.00, 3800.00, 'Tolerancia global de sucursal'),
    ('ATM', 0.120, 0.060, 500000.00, 1500000.00, 1200000.00, 6, 12, 120000.00, 3500.00, 'Prioridad alta: buffer robusto para ATM'),
    ('ATS', 0.100, 0.050, 300000.00, 900000.00, 600000.00, 8, 16, 110000.00, 3200.00, 'ATS balance moderado'),
    ('Tesoro', 0.150, 0.080, 750000.00, NULL, NULL, 12, 24, 90000.00, 2800.00, 'Tesoro actúa como pulmón de la sucursal'),
    ('Ventanilla', 0.080, 0.040, 150000.00, 400000.00, 350000.00, 4, 8, 85000.00, 2600.00, 'Caja operativa al cliente'),
    ('Buzón', 0.050, 0.030, 50000.00, NULL, 250000.00, 12, 24, 95000.00, 3000.00, 'Depósitos no inmediatos'),
    ('Recaudación', 0.090, 0.050, 200000.00, 600000.00, 650000.00, 10, 20, 130000.00, 3600.00, 'Grandes volúmenes corporativos'),
    ('Caja Chica', 0.040, 0.030, 30000.00, 100000.00, 80000.00, 24, 48, 70000.00, 2200.00, 'Gastos operativos menores'),
    ('Otros', 0.070, 0.040, 50000.00, 200000.00, 180000.00, 12, 36, 100000.00, 3100.00, 'Reservas varias')
ON CONFLICT (channel) DO NOTHING;
