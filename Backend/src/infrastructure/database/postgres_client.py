"""
PostgreSQL Database Client for CapiAgentes Historical Alerts
Professional database layer with connection pooling and advanced features
Author: Claude Code Expert
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
import asyncpg
from asyncpg import Connection, Pool
from contextlib import asynccontextmanager
import json
from dataclasses import dataclass, asdict
from enum import Enum
from decimal import Decimal

from ...core.config import get_settings
from ...core.exceptions import DatabaseError, ConfigurationError

def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

# Configure logging
logger = logging.getLogger(__name__)

class AlertPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    SILENCED = "silenced"

@dataclass
class HistoricalAlert:
    id: Optional[str] = None
    alert_code: Optional[str] = None
    timestamp: Optional[datetime] = None
    alert_type: Optional[str] = None
    priority: Optional[AlertPriority] = None
    agent_source: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    financial_impact: Optional[float] = None
    currency: str = "USD"
    confidence_score: Optional[float] = None
    status: AlertStatus = AlertStatus.ACTIVE
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class AIAnalysis:
    id: Optional[str] = None
    alert_id: Optional[str] = None
    root_cause: Optional[str] = None
    probability_fraud: Optional[float] = None
    probability_system_error: Optional[float] = None
    similar_incidents_count: int = 0
    trend_analysis: Optional[str] = None
    risk_assessment: Optional[str] = None
    confidence_level: Optional[float] = None
    model_version: Optional[str] = None
    analysis_timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None

@dataclass
class HumanTask:
    id: Optional[str] = None
    alert_id: Optional[str] = None
    recommended_action_id: Optional[str] = None
    task_title: Optional[str] = None
    task_description: Optional[str] = None
    priority: int = 1
    status: str = "pending"
    assigned_to_user: Optional[str] = None
    assigned_to_team: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_effort_hours: Optional[float] = None
    actual_effort_hours: Optional[float] = None
    progress_percentage: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    blockers: Optional[str] = None
    dependencies: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PostgreSQLClient:
    """Professional PostgreSQL client with connection pooling and advanced features"""

    _SUCURSAL_SELECT_FIELDS = [
        "sucursal_id",
        "sucursal_numero",
        "sucursal_nombre",
        "telefonos",
        "calle",
        "altura",
        "barrio",
        "comuna",
        "codigo_postal",
        "codigo_postal_argentino",
        "saldo_total_sucursal",
        "caja_teorica_sucursal",
        "total_atm",
        "total_ats",
        "total_tesoro",
        "total_cajas_ventanilla",
        "total_buzon_depositos",
        "total_recaudacion",
        "total_caja_chica",
        "total_otros",
        "direccion_sucursal",
        "latitud",
        "longitud",
        "observacion",
        "medido_en",
    ]

    _SUCURSAL_WRITABLE_FIELDS = [
        "sucursal_id",
        "sucursal_numero",
        "sucursal_nombre",
        "telefonos",
        "calle",
        "altura",
        "barrio",
        "comuna",
        "codigo_postal",
        "codigo_postal_argentino",
        "saldo_total_sucursal",
        "caja_teorica_sucursal",
        "total_atm",
        "total_ats",
        "total_tesoro",
        "total_cajas_ventanilla",
        "total_buzon_depositos",
        "total_recaudacion",
        "total_caja_chica",
        "total_otros",
        "direccion_sucursal",
        "latitud",
        "longitud",
        "observacion",
        "medido_en",
    ]

    _SUCURSAL_FLOAT_FIELDS = [
        "saldo_total_sucursal",
        "caja_teorica_sucursal",
        "total_atm",
        "total_ats",
        "total_tesoro",
        "total_cajas_ventanilla",
        "total_buzon_depositos",
        "total_recaudacion",
        "total_caja_chica",
        "total_otros",
        "latitud",
        "longitud",
    ]

    _DISPOSITIVO_SELECT_FIELDS = [
        "id",
        "sucursal_id",
        "dispositivo_id",
        "tipo_dispositivo",
        "saldo_total",
        "caja_teorica",
        "cant_d1",
        "cant_d2",
        "cant_d3",
        "cant_d4",
        "direccion",
        "latitud",
        "longitud",
        "observacion",
        "medido_en",
    ]

    _DISPOSITIVO_WRITABLE_FIELDS = [
        "sucursal_id",
        "dispositivo_id",
        "tipo_dispositivo",
        "saldo_total",
        "caja_teorica",
        "cant_d1",
        "cant_d2",
        "cant_d3",
        "cant_d4",
        "direccion",
        "latitud",
        "longitud",
        "observacion",
        "medido_en",
    ]

    _DISPOSITIVO_FLOAT_FIELDS = [
        "saldo_total",
        "caja_teorica",
        "latitud",
        "longitud",
    ]

    _CASH_POLICY_COLUMNS = [
        "channel",
        "max_surplus_pct",
        "max_deficit_pct",
        "min_buffer_amount",
        "daily_withdrawal_limit",
        "daily_deposit_limit",
        "reload_lead_hours",
        "sla_hours",
        "truck_fixed_cost",
        "truck_variable_cost_per_kg",
        "notes",
    ]

    _CASH_POLICY_NUMERIC_FIELDS = [
        "max_surplus_pct",
        "max_deficit_pct",
        "min_buffer_amount",
        "daily_withdrawal_limit",
        "daily_deposit_limit",
        "reload_lead_hours",
        "sla_hours",
        "truck_fixed_cost",
        "truck_variable_cost_per_kg",
    ]

    def __init__(self):
        self.settings = get_settings()
        self._pool: Optional[Pool] = None
        self._initialized = False

    @classmethod
    def _normalize_sucursal_record(cls, record: Any) -> Dict[str, Any]:
        data = dict(record)
        for field in cls._SUCURSAL_FLOAT_FIELDS:
            value = data.get(field)
            if value is not None:
                data[field] = float(value)
        return data

    @classmethod
    def _normalize_dispositivo_record(cls, record: Any) -> Dict[str, Any]:
        data = dict(record)
        for field in cls._DISPOSITIVO_FLOAT_FIELDS:
            value = data.get(field)
            if value is not None:
                data[field] = float(value)
        for field in ("cant_d1", "cant_d2", "cant_d3", "cant_d4"):
            value = data.get(field)
            if value is not None:
                data[field] = int(value)
        return data

    @staticmethod
    def _record_to_cash_policy(record: Any) -> Dict[str, Any]:
        data = dict(record)
        decimal_fields = {
            "max_surplus_pct",
            "max_deficit_pct",
            "min_buffer_amount",
            "daily_withdrawal_limit",
            "daily_deposit_limit",
            "truck_fixed_cost",
            "truck_variable_cost_per_kg",
        }
        int_fields = {"reload_lead_hours", "sla_hours"}
        for field in decimal_fields:
            value = data.get(field)
            if value is not None:
                data[field] = float(value)
        for field in int_fields:
            value = data.get(field)
            if value is not None:
                data[field] = int(value)
        timestamp = data.get("updated_at")
        if hasattr(timestamp, "isoformat"):
            data["updated_at"] = timestamp.isoformat()
        return data
    async def initialize(self) -> None:
        """Initialize the database connection pool"""
        if self._initialized:
            return

        try:
            database_url = self._get_database_url()

            self._pool = await asyncpg.create_pool(
                database_url,
                min_size=2,
                max_size=10,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=60,
                server_settings={
                    'jit': 'off',  # Disable JIT for faster connection times
                    'application_name': 'capi_alerts_system'
                }
            )

            # Test connection
            async with self._pool.acquire() as conn:
                await conn.execute('SELECT 1')

            self._initialized = True
            logger.info("PostgreSQL connection pool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")

    def _get_database_url(self) -> str:
        """Build database URL from settings"""
        # Try environment variables first
        import os
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url

        # Build from components
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'capi_alerts')
        username = os.getenv('POSTGRES_USER', 'capi_user')
        password = os.getenv('POSTGRES_PASSWORD', 'capi_secure_2024')

        return f"postgresql://{username}:{password}@{host}:{port}/{database}"

    async def close(self) -> None:
        """Close the database connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._initialized = False
            logger.info("PostgreSQL connection pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool"""
        if not self._initialized:
            await self.initialize()

        async with self._pool.acquire() as conn:
            try:
                yield conn
            except Exception as e:
                logger.error(f"Database operation failed: {e}")
                raise DatabaseError(f"Database operation failed: {e}")


    async def get_historical_alerts(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        agent_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get historical alerts from the public.alertas catalog"""

        query = """
        SELECT
            a.id::text        AS id,
            a.creada_en       AS created_at,
            a.prioridad       AS priority,
            a.estado          AS status,
            a.problema        AS title,
            a.hipotesis       AS hypothesis,
            a.datos_clave     AS datos_clave,
            a.acciones        AS acciones,
            a.dedupe_clave    AS dedupe,
            a.agente_id::text AS agent_id,
            ev.tipo_evento    AS event_type,
            ev.mensaje        AS event_message,
            a.sucursal_id     AS sucursal_id,
            suc.sucursal_nombre AS sucursal_nombre,
            suc.saldo_total_sucursal AS sucursal_saldo_total,
            suc.caja_teorica_sucursal AS sucursal_caja_teorica,
            CASE
              WHEN suc.caja_teorica_sucursal IS NULL OR suc.caja_teorica_sucursal = 0
                THEN NULL
              ELSE ROUND((suc.saldo_total_sucursal / suc.caja_teorica_sucursal) * 100, 2)
            END AS sucursal_saldo_pct,
            a.dispositivo_id  AS dispositivo_id,
            sad.tipo_dispositivo AS dispositivo_tipo,
            sad.saldo_total   AS dispositivo_saldo_total,
            sad.caja_teorica  AS dispositivo_caja_teorica,
            CASE
              WHEN sad.caja_teorica IS NULL OR sad.caja_teorica = 0
                THEN NULL
              ELSE ROUND((sad.saldo_total / sad.caja_teorica) * 100, 2)
            END AS dispositivo_saldo_pct,
            sad.latitud       AS dispositivo_latitud,
            sad.longitud      AS dispositivo_longitud
        FROM public.alertas a
        LEFT JOIN public.agentes ag ON ag.id = a.agente_id
        LEFT JOIN public.eventos ev ON ev.id = a.evento_id
        LEFT JOIN public.saldos_sucursal suc ON suc.sucursal_id = a.sucursal_id
        LEFT JOIN public.saldos_actuales_dispositivo sad
          ON sad.sucursal_id = a.sucursal_id
         AND sad.dispositivo_id = a.dispositivo_id
        WHERE ($3::text IS NULL OR a.estado = $3)
          AND ($4::text IS NULL OR a.prioridad = $4)
          AND ($5::text IS NULL OR a.agente_id::text = $5)
        ORDER BY a.creada_en DESC
        LIMIT $1 OFFSET $2
        """

        agent_param = agent_filter if agent_filter and len(agent_filter) == 36 else None

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, limit, offset, status_filter, priority_filter, agent_param)

        alerts: List[Dict[str, Any]] = []
        for row in rows:
            datos_clave = row.get('datos_clave')
            if isinstance(datos_clave, list):
                claves = datos_clave
            elif datos_clave:
                try:
                    claves = json.loads(datos_clave)
                except Exception:
                    claves = []
            else:
                claves = []

            affected_entities = [
                {
                    'entity_type': 'dato_clave',
                    'entity_name': str(item),
                    'impact_level': None
                }
                for item in claves
            ]

            priority_value = (row['priority'] or '').capitalize() if row['priority'] else 'N/D'
            status_value = (row['status'] or '').capitalize() if row['status'] else 'N/D'

            sucursal_info = None
            if row['sucursal_id']:
                sucursal_info = {
                    'sucursal_id': row['sucursal_id'],
                    'nombre': row.get('sucursal_nombre'),
                    'saldo_total': _to_float(row.get('sucursal_saldo_total')),
                    'caja_teorica': _to_float(row.get('sucursal_caja_teorica')),
                    'saldo_cobertura_pct': _to_float(row.get('sucursal_saldo_pct')),
                }

            dispositivo_info = None
            if row['dispositivo_id']:
                dispositivo_info = {
                    'dispositivo_id': row['dispositivo_id'],
                    'tipo': row.get('dispositivo_tipo'),
                    'saldo_total': _to_float(row.get('dispositivo_saldo_total')),
                    'caja_teorica': _to_float(row.get('dispositivo_caja_teorica')),
                    'saldo_cobertura_pct': _to_float(row.get('dispositivo_saldo_pct')),
                    'latitud': _to_float(row.get('dispositivo_latitud')),
                    'longitud': _to_float(row.get('dispositivo_longitud')),
                }

            alerts.append({
                'id': row['id'],
                'alert_code': row['dedupe'] or f"alert_{row['id']}",
                'timestamp': row['created_at'],
                'title': row['title'] or 'Alerta sin titulo',
                'priority': priority_value,
                'status': status_value,
                'financial_impact': None,
                'currency': 'USD',
                'confidence_score': None,
                'pending_tasks': 0,
                'affected_entities': affected_entities,
                'sucursal': sucursal_info,
                'dispositivo': dispositivo_info,
            })

        return alerts

    async def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific alert by ID with enriched data from public.alertas"""

        try:
            alert_pk = int(alert_id)
        except (TypeError, ValueError):
            return None

        query = """
        SELECT
            a.id::text        AS id,
            a.creada_en       AS created_at,
            a.prioridad       AS priority,
            a.estado          AS status,
            a.problema        AS title,
            a.hipotesis       AS hypothesis,
            a.impacto         AS impacto,
            a.datos_clave     AS datos_clave,
            a.acciones        AS acciones,
            a.dedupe_clave    AS dedupe,
            a.agente_id::text AS agent_id,
            ag.nombre        AS agent_name,
            ev.id::text       AS event_id,
            ev.tipo_evento    AS event_type,
            ev.ocurrido_en    AS event_timestamp,
            ev.estado         AS event_status,
            ev.mensaje        AS event_message,
            ev.duracion_ms    AS event_duration,
            ev.tokens_total   AS event_tokens,
            ev.costo_usd      AS event_cost,
            a.sucursal_id     AS sucursal_id,
            suc.sucursal_nombre AS sucursal_nombre,
            suc.saldo_total_sucursal AS sucursal_saldo_total,
            suc.caja_teorica_sucursal AS sucursal_caja_teorica,
            CASE
              WHEN suc.caja_teorica_sucursal IS NULL OR suc.caja_teorica_sucursal = 0
                THEN NULL
              ELSE ROUND((suc.saldo_total_sucursal / suc.caja_teorica_sucursal) * 100, 2)
            END AS sucursal_saldo_pct,
            a.dispositivo_id  AS dispositivo_id,
            sad.tipo_dispositivo AS dispositivo_tipo,
            sad.saldo_total   AS dispositivo_saldo_total,
            sad.caja_teorica  AS dispositivo_caja_teorica,
            CASE
              WHEN sad.caja_teorica IS NULL OR sad.caja_teorica = 0
                THEN NULL
              ELSE ROUND((sad.saldo_total / sad.caja_teorica) * 100, 2)
            END AS dispositivo_saldo_pct,
            sad.latitud       AS dispositivo_latitud,
            sad.longitud      AS dispositivo_longitud
        FROM public.alertas a
        LEFT JOIN public.agentes ag ON ag.id = a.agente_id
        LEFT JOIN public.eventos ev ON ev.id = a.evento_id
        LEFT JOIN public.saldos_sucursal suc ON suc.sucursal_id = a.sucursal_id
        LEFT JOIN public.saldos_actuales_dispositivo sad
          ON sad.sucursal_id = a.sucursal_id
         AND sad.dispositivo_id = a.dispositivo_id
        WHERE a.id = $1::bigint
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, alert_pk)

        if not row:
            return None

        datos_clave = row.get('datos_clave')
        if isinstance(datos_clave, list):
            claves = datos_clave
        elif datos_clave:
            try:
                claves = json.loads(datos_clave)
            except Exception:
                claves = []
        else:
            claves = []

        affected_entities = [
            {
                'entity_type': 'dato_clave',
                'entity_name': str(item),
                'impact_level': None
            }
            for item in claves
        ]

        priority_value = (row['priority'] or '').capitalize() if row['priority'] else 'N/D'
        status_value = (row['status'] or '').capitalize() if row['status'] else 'N/D'

        sucursal_info = None
        if row['sucursal_id']:
            sucursal_info = {
                'sucursal_id': row['sucursal_id'],
                'nombre': row.get('sucursal_nombre'),
                'saldo_total': _to_float(row.get('sucursal_saldo_total')),
                'caja_teorica': _to_float(row.get('sucursal_caja_teorica')),
                'saldo_cobertura_pct': _to_float(row.get('sucursal_saldo_pct')),
            }

        dispositivo_info = None
        if row['dispositivo_id']:
            dispositivo_info = {
                'dispositivo_id': row['dispositivo_id'],
                'tipo': row.get('dispositivo_tipo'),
                'saldo_total': _to_float(row.get('dispositivo_saldo_total')),
                'caja_teorica': _to_float(row.get('dispositivo_caja_teorica')),
                'saldo_cobertura_pct': _to_float(row.get('dispositivo_saldo_pct')),
                'latitud': _to_float(row.get('dispositivo_latitud')),
                'longitud': _to_float(row.get('dispositivo_longitud')),
            }

        detail = {
            'id': row['id'],
            'alert_code': row['dedupe'] or f"alert_{row['id']}",
            'timestamp': row['created_at'],
            'alert_type': row['event_type'] or 'alerta_manual',
            'priority': priority_value,
            'agent_source': row['agent_name'] or row['agent_id'] or 'desconocido',
            'title': row['title'] or 'Alerta',
            'description': row['hypothesis'],
            'financial_impact': None,
            'currency': 'USD',
            'confidence_score': None,
            'status': status_value,
            'resolved_at': None,
            'resolved_by': None,
            'created_at': row['created_at'],
            'updated_at': row['created_at'],
            'root_cause': row['hypothesis'],
            'probability_fraud': None,
            'probability_system_error': None,
            'similar_incidents_count': None,
            'trend_analysis': row['event_message'],
            'risk_assessment': row['impacto'],
            'confidence_level': None,
            'model_version': None,
            'affected_entities': affected_entities,
            'human_tasks': [],
            'acciones': row['acciones'],
            'datos_clave': claves,
            'evento': {
                'id': row['event_id'],
                'estado': row['event_status'],
                'timestamp': row['event_timestamp'],
                'duracion_ms': row['event_duration'],
                'tokens_total': row['event_tokens'],
                'costo_usd': row['event_cost'],
                'mensaje': row['event_message'],
            },
            'sucursal': sucursal_info,
            'dispositivo': dispositivo_info,
        }

        return detail
    async def update_alert_status(
        self,
        alert_id: str,
        new_status: str,
        *,
        actor: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update status field in public.alertas table."""

        if not alert_id or not new_status:
            logger.warning("update_alert_status called with missing parameters", extra={"alert_id": alert_id, "new_status": new_status})
            return False

        try:
            alert_pk = int(alert_id)
        except (TypeError, ValueError):
            logger.warning("update_alert_status received non-numeric alert_id", extra={"alert_id": alert_id})
            return False

        normalized_status = new_status.strip().lower()

        query = """
        UPDATE public.alertas
           SET estado = $2
         WHERE id = $1::bigint
        """

        try:
            async with self.get_connection() as conn:
                result = await conn.execute(query, alert_pk, normalized_status)
        except asyncpg.PostgresError as exc:
            logger.error("Database error updating alert status", extra={"alert_id": alert_id, "status": normalized_status, "actor": actor, "reason": reason, "metadata": metadata})
            raise DatabaseError(f"Failed to update alert {alert_id} status") from exc

        updated = bool(result and result.split()[-1].isdigit() and int(result.split()[-1]) > 0)
        if updated:
            logger.info("Alert status updated", extra={"alert_id": alert_id, "status": normalized_status, "actor": actor, "reason": reason})
        else:
            logger.warning("Alert status update affected no rows", extra={"alert_id": alert_id, "status": normalized_status})

        return updated


    async def get_sucursales(self) -> List[Dict[str, Any]]:
        """Return sucursal records for mapping layers."""

        query = """
        SELECT
            sucursal_id,
            sucursal_numero,
            sucursal_nombre,
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
            observacion,
            medido_en
        FROM public.saldos_sucursal
        ORDER BY sucursal_numero;
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
            return [self._normalize_sucursal_record(row) for row in rows]

    async def get_sucursal_by_id(self, sucursal_id: str) -> Dict[str, Any]:
        select_fields = ", ".join(self._SUCURSAL_SELECT_FIELDS)
        query = f"""
        SELECT
            {select_fields}
        FROM public.saldos_sucursal
        WHERE sucursal_id = $1
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, sucursal_id)

        if not row:
            raise DatabaseError(f"Sucursal {sucursal_id} no encontrada")

        return self._normalize_sucursal_record(row)

    async def create_sucursal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = ["sucursal_id", "sucursal_numero", "sucursal_nombre", "saldo_total_sucursal"]
        for field in required_fields:
            if payload.get(field) in (None, ""):
                raise DatabaseError(f"El campo {field} es obligatorio")

        data = {key: payload.get(key) for key in self._SUCURSAL_WRITABLE_FIELDS if key in payload and payload.get(key) is not None}
        columns = list(data.keys())
        placeholders = ", ".join(f"${idx}" for idx in range(1, len(columns) + 1))
        insert_query = f"""
        INSERT INTO public.saldos_sucursal ({', '.join(columns)})
        VALUES ({placeholders})
        RETURNING sucursal_id
        """

        async with self.get_connection() as conn:
            await conn.fetchrow(insert_query, *[data[col] for col in columns])

        return await self.get_sucursal_by_id(payload["sucursal_id"])

    async def update_sucursal(self, sucursal_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = {key: payload.get(key) for key in self._SUCURSAL_WRITABLE_FIELDS if key != "sucursal_id" and key in payload}
        if not data:
            raise DatabaseError("No se recibieron campos para actualizar")

        set_clause = ", ".join(f"{field} = ${idx}" for idx, field in enumerate(data.keys(), start=1))
        update_query = f"""
        UPDATE public.saldos_sucursal
        SET {set_clause}
        WHERE sucursal_id = ${len(data) + 1}
        RETURNING sucursal_id
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(update_query, *list(data.values()), sucursal_id)

        if not row:
            raise DatabaseError(f"Sucursal {sucursal_id} no encontrada")

        return await self.get_sucursal_by_id(sucursal_id)

    async def delete_sucursal(self, sucursal_id: str) -> bool:
        query = "DELETE FROM public.saldos_sucursal WHERE sucursal_id = $1"
        async with self.get_connection() as conn:
            result = await conn.execute(query, sucursal_id)
        return result.endswith(' 1')

    async def get_dispositivos(self) -> List[Dict[str, Any]]:
        select_fields = ", ".join(self._DISPOSITIVO_SELECT_FIELDS)
        query = f"""
        SELECT
            {select_fields}
        FROM public.saldos_dispositivo
        ORDER BY sucursal_id, dispositivo_id, medido_en DESC
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
            return [self._normalize_dispositivo_record(row) for row in rows]

    async def get_dispositivo_by_id(self, record_id: int) -> Dict[str, Any]:
        select_fields = ", ".join(self._DISPOSITIVO_SELECT_FIELDS)
        query = f"""
        SELECT
            {select_fields}
        FROM public.saldos_dispositivo
        WHERE id = $1
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, record_id)

        if not row:
            raise DatabaseError(f"Dispositivo {record_id} no encontrado")

        return self._normalize_dispositivo_record(row)

    async def create_dispositivo(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = ["sucursal_id", "dispositivo_id", "tipo_dispositivo", "saldo_total"]
        for field in required_fields:
            if payload.get(field) in (None, ""):
                raise DatabaseError(f"El campo {field} es obligatorio")

        data = {key: payload.get(key) for key in self._DISPOSITIVO_WRITABLE_FIELDS if key in payload and payload.get(key) is not None}
        if "tipo_dispositivo" in data and isinstance(data["tipo_dispositivo"], str):
            tipo = data["tipo_dispositivo"].upper()
            if tipo not in {"ATM", "ATS", "TESORO"}:
                raise DatabaseError("Tipo de dispositivo invalido")
            data["tipo_dispositivo"] = tipo

        columns = list(data.keys())
        placeholders = ", ".join(f"${idx}" for idx in range(1, len(columns) + 1))
        insert_query = f"""
        INSERT INTO public.saldos_dispositivo ({', '.join(columns)})
        VALUES ({placeholders})
        RETURNING id
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(insert_query, *[data[col] for col in columns])

        record_id = int(row['id'])
        return await self.get_dispositivo_by_id(record_id)

    async def update_dispositivo(self, record_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = {key: payload.get(key) for key in self._DISPOSITIVO_WRITABLE_FIELDS if key != 'sucursal_id' and key != 'dispositivo_id' and key != 'tipo_dispositivo' and key in payload}
        # Allow changing tipo_dispositivo if provided
        if 'tipo_dispositivo' in payload and payload['tipo_dispositivo'] is not None:
            tipo_val = payload['tipo_dispositivo']
            if isinstance(tipo_val, str):
                tipo_upper = tipo_val.upper()
                if tipo_upper not in {"ATM", "ATS", "TESORO"}:
                    raise DatabaseError("Tipo de dispositivo invalido")
                data['tipo_dispositivo'] = tipo_upper
            else:
                data['tipo_dispositivo'] = tipo_val
        if 'sucursal_id' in payload:
            data['sucursal_id'] = payload['sucursal_id']
        if 'dispositivo_id' in payload:
            data['dispositivo_id'] = payload['dispositivo_id']

        if not data:
            raise DatabaseError('No se recibieron campos para actualizar')

        set_clause = ', '.join(f"{field} = ${idx}" for idx, field in enumerate(data.keys(), start=1))
        update_query = f"""
        UPDATE public.saldos_dispositivo
        SET {set_clause}
        WHERE id = ${len(data) + 1}
        RETURNING id
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(update_query, *list(data.values()), record_id)

        if not row:
            raise DatabaseError(f"Dispositivo {record_id} no encontrado")

        return await self.get_dispositivo_by_id(record_id)

    async def delete_dispositivo(self, record_id: int) -> bool:
        query = "DELETE FROM public.saldos_dispositivo WHERE id = $1"
        async with self.get_connection() as conn:
            result = await conn.execute(query, record_id)
        return result.endswith(' 1')

    async def get_cash_policies(self) -> List[Dict[str, Any]]:
        query = """
        SELECT
            channel,
            max_surplus_pct,
            max_deficit_pct,
            min_buffer_amount,
            daily_withdrawal_limit,
            daily_deposit_limit,
            reload_lead_hours,
            sla_hours,
            truck_fixed_cost,
            truck_variable_cost_per_kg,
            notes,
            updated_at
        FROM alerts.cash_policies
        ORDER BY channel
        """
        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
        return [self._record_to_cash_policy(row) for row in rows]

    async def upsert_cash_policy(self, channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(payload or {})
        insert_columns = [
            "channel",
            "max_surplus_pct",
            "max_deficit_pct",
            "min_buffer_amount",
            "daily_withdrawal_limit",
            "daily_deposit_limit",
            "reload_lead_hours",
            "sla_hours",
            "truck_fixed_cost",
            "truck_variable_cost_per_kg",
            "notes",
        ]
        values = [channel]
        for column in insert_columns[1:]:
            values.append(payload.get(column))
        placeholders = ", ".join(f"${idx}" for idx in range(1, len(insert_columns) + 1))
        query = f"""
        INSERT INTO alerts.cash_policies ({', '.join(insert_columns)})
        VALUES ({placeholders})
        ON CONFLICT (channel) DO UPDATE SET
            max_surplus_pct = EXCLUDED.max_surplus_pct,
            max_deficit_pct = EXCLUDED.max_deficit_pct,
            min_buffer_amount = EXCLUDED.min_buffer_amount,
            daily_withdrawal_limit = EXCLUDED.daily_withdrawal_limit,
            daily_deposit_limit = EXCLUDED.daily_deposit_limit,
            reload_lead_hours = EXCLUDED.reload_lead_hours,
            sla_hours = EXCLUDED.sla_hours,
            truck_fixed_cost = EXCLUDED.truck_fixed_cost,
            truck_variable_cost_per_kg = EXCLUDED.truck_variable_cost_per_kg,
            notes = EXCLUDED.notes,
            updated_at = now()
        RETURNING
            channel,
            max_surplus_pct,
            max_deficit_pct,
            min_buffer_amount,
            daily_withdrawal_limit,
            daily_deposit_limit,
            reload_lead_hours,
            sla_hours,
            truck_fixed_cost,
            truck_variable_cost_per_kg,
            notes,
            updated_at
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *values)
        if row is None:
            raise DatabaseError("No se pudo guardar la política de efectivo")
        return self._record_to_cash_policy(row)
    async def create_historical_alert(self, alert: HistoricalAlert) -> str:
        """Create a new historical alert"""

        query = """
        INSERT INTO alerts.historical_alerts (
            alert_code, timestamp, alert_type, priority, agent_source,
            title, description, financial_impact, currency, confidence_score, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING id
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(
                query,
                alert.alert_code,
                alert.timestamp or datetime.now(timezone.utc),
                alert.alert_type,
                alert.priority.value if alert.priority else None,
                alert.agent_source,
                alert.title,
                alert.description,
                alert.financial_impact,
                alert.currency,
                alert.confidence_score,
                alert.status.value if alert.status else AlertStatus.ACTIVE.value
            )
            return str(row['id'])

    async def update_task_progress(
        self,
        task_id: str,
        progress_percentage: int,
        status: Optional[str] = None,
        completion_notes: Optional[str] = None
    ) -> bool:
        """Update task progress and status"""

        query = """
        UPDATE alerts.human_tasks
        SET progress_percentage = $2,
            status = COALESCE($3, status),
            completion_notes = COALESCE($4, completion_notes),
            completed_at = CASE WHEN $3 = 'completed' THEN NOW() ELSE completed_at END,
            updated_at = NOW()
        WHERE id = $1
        """

        async with self.get_connection() as conn:
            result = await conn.execute(query, task_id, progress_percentage, status, completion_notes)
            return result.split()[-1] == '1'  # Check if one row was updated

    async def get_team_workload(self) -> List[Dict[str, Any]]:
        """Get current workload by team"""

        query = """
        SELECT
            t.team_name,
            COUNT(ht.id) as total_tasks,
            COUNT(CASE WHEN ht.status = 'pending' THEN 1 END) as pending_tasks,
            COUNT(CASE WHEN ht.status = 'in_progress' THEN 1 END) as in_progress_tasks,
            COUNT(CASE WHEN ht.status = 'completed' THEN 1 END) as completed_tasks,
            COALESCE(AVG(ht.progress_percentage), 0) as avg_progress
        FROM alerts.teams t
        LEFT JOIN alerts.human_tasks ht ON t.team_name = ht.assigned_to_team
        WHERE t.active = true
        GROUP BY t.id, t.team_name
        ORDER BY pending_tasks DESC
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    async def get_critical_alerts_summary(self) -> Dict[str, Any]:
        """Get summary of critical active alerts"""

        query = """
        SELECT
            COUNT(*) as total_critical,
            COALESCE(SUM(financial_impact), 0) as total_financial_impact,
            COALESCE(AVG(confidence_score), 0) as avg_confidence,
            COUNT(CASE WHEN aa.probability_fraud > 0.7 THEN 1 END) as high_fraud_risk
        FROM alerts.historical_alerts ha
        LEFT JOIN alerts.ai_analysis aa ON ha.id = aa.alert_id
        WHERE ha.priority = 'critical' AND ha.status = 'active'
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query)
            return dict(row)

    async def search_alerts(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Full-text search in alerts"""

        query = """
        SELECT
            ha.id,
            ha.alert_code,
            ha.title,
            ha.description,
            ha.priority,
            ha.status,
            ha.timestamp,
            ha.financial_impact,
            ts_rank(
                to_tsvector('english', ha.title || ' ' || ha.description),
                plainto_tsquery('english', $1)
            ) as relevance_score
        FROM alerts.historical_alerts ha
        WHERE to_tsvector('english', ha.title || ' ' || ha.description) @@ plainto_tsquery('english', $1)
        ORDER BY relevance_score DESC, ha.timestamp DESC
        LIMIT $2
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, search_term, limit)
            return [dict(row) for row in rows]

# Global instance
_postgres_client: Optional[PostgreSQLClient] = None

def get_postgres_client() -> PostgreSQLClient:
    """Get the global PostgreSQL client instance"""
    global _postgres_client
    if _postgres_client is None:
        _postgres_client = PostgreSQLClient()
    return _postgres_client

async def initialize_database():
    """Initialize the database connection"""
    client = get_postgres_client()
    await client.initialize()

async def close_database():
    """Close the database connection"""
    client = get_postgres_client()
    await client.close()


