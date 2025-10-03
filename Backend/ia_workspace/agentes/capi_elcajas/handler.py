"""El Cajas agent: diagnose cash deviations and recommend actions."""
from __future__ import annotations
import re
import json
import hashlib

import math
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.domain.agents.agent_protocol import BaseAgent
from src.domain.agents.agent_models import AgentResult, AgentTask, IntentType, TaskStatus
from src.application.services.cash_policy_service import CashPolicyService
from src.application.services.calendar_service import CalendarService
from src.infrastructure.workspace.session_storage import SessionStorage, resolve_workspace_root
logger = get_logger(__name__)

AVERAGE_BILL_VALUE = 1000.0  # ARS por billete asumido para estimar peso transportado
CHANNEL_FIELDS = {
    "ATM": "total_atm",
    "ATS": "total_ats",
    "Tesoro": "total_tesoro",
    "Ventanilla": "total_cajas_ventanilla",
    "Buzon": "total_buzon_depositos",
    "Recaudacion": "total_recaudacion",
    "Caja Chica": "total_caja_chica",
    "Otros": "total_otros",
}

EL_CAJAS_AGENT_UUID = uuid.UUID("b37d1f90-6b35-4fb3-866e-2f88c9b29850")


@dataclass
class ChannelRecommendation:
    channel: str
    action: str  # "withdraw" | "deposit"
    amount: float
    reason: str
    urgency: str
    estimated_cost: float
    weight_kg: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "action": self.action,
            "amount": round(self.amount, 2),
            "reason": self.reason,
            "urgency": self.urgency,
            "estimated_cost": round(self.estimated_cost, 2),
            "weight_kg": round(self.weight_kg, 3),
        }


class ElCajasAgent(BaseAgent):
    """Agent specialized in cash deviation diagnostics."""

    AGENT_NAME = "capi_elcajas"

    def __init__(
        self,
        *,
        policy_service: Optional[CashPolicyService] = None,
        calendar_service: Optional[CalendarService] = None,
        db_client: Optional[object] = None,
    ) -> None:
        super().__init__(self.AGENT_NAME)
        self._policy_service = policy_service
        self._calendar = calendar_service or CalendarService()
        self._db_client = db_client
        self._session_storage = SessionStorage()
        self._workspace_root = resolve_workspace_root()

    @property
    def supported_intents(self) -> List[IntentType]:
        return [IntentType.BRANCH, IntentType.BRANCH_QUERY, IntentType.DB_OPERATION, IntentType.QUERY]

    async def process(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        branch_rows = self._extract_branch_rows(task)

        if not branch_rows:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.agent_name,
                status=TaskStatus.COMPLETED,
                data={'analysis': [], 'alerts_created': 0, 'alert_operations': [], 'recommendation_files': []},
                message='Sin datos de sucursales para analizar',
                processing_time=time.time() - start_time,
            )

        policies = None
        if isinstance(task.context, dict):
            candidate = task.context.get('policies')
            if isinstance(candidate, list):
                policies = [dict(policy) for policy in candidate if isinstance(policy, dict)]
        if policies is None:
            if self._policy_service is None:
                policies = []
            else:
                policies = await self._policy_service.list_policies()
        policies = policies or []
        normalized_policies = [
            self._normalize_policy(policy)
            for policy in policies
            if isinstance(policy, dict)
        ]
        policy_map = {
            policy.get('channel', '').lower(): policy
            for policy in normalized_policies
            if isinstance(policy.get('channel'), str)
        }
        now = datetime.now(timezone.utc)
        calendar_descriptor = self._calendar.describe(now.astimezone())

        analysis: List[Dict[str, Any]] = []
        alerts_created = 0
        global_messages: List[str] = []
        alert_operations: List[Dict[str, Any]] = []
        recommendation_files: List[Dict[str, Any]] = []

        for row in branch_rows:
            branch_result = await self._analyze_branch(row, policy_map, now, task.session_id)
            analysis.append(branch_result)
            if branch_result.get('status') != 'ok':
                headline = branch_result.get('headline')
                if isinstance(headline, str):
                    global_messages.append(headline)
            alerts_created += int(branch_result.get('alerts_created', 0) or 0)

            operation_payload = branch_result.get('alert_operation')
            if isinstance(operation_payload, dict):
                alert_operations.append(operation_payload)

            artifact_payload = branch_result.get('recommendation_artifact')
            if isinstance(artifact_payload, dict):
                recommendation_files.append(artifact_payload)

        if global_messages:
            message = '; '.join(global_messages)
        else:
            message = 'Sucursales OK: caja real dentro de tolerancias'

        data_payload = {
            'analysis': analysis,
            'calendar': calendar_descriptor,
            'policies_loaded': len(policies),
            'alerts_created': alerts_created,
            'alert_operations': alert_operations,
            'recommendation_files': recommendation_files,
        }

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.agent_name,
            status=TaskStatus.COMPLETED,
            data=data_payload,
            message=message,
            processing_time=time.time() - start_time,
        )

    def _extract_branch_rows(self, task: AgentTask) -> List[Dict[str, Any]]:
        context = task.context or {}
        rows = context.get("branch_rows")
        if isinstance(rows, list):
            return [dict(item) for item in rows if isinstance(item, dict)]
        shared = context.get("shared") or {}
        shared_rows = shared.get("rows") if isinstance(shared, dict) else None
        if isinstance(shared_rows, list):
            return [dict(item) for item in shared_rows if isinstance(item, dict)]
        return []

    async def _analyze_branch(
        self,
        row: Dict[str, Any],
        policy_map: Dict[str, Dict[str, Any]],
        now: datetime,
        session_id: str,
    ) -> Dict[str, Any]:
        branch_id = row.get('sucursal_id') or str(row.get('sucursal_numero') or 'desconocida')
        branch_name = row.get('sucursal_nombre') or f'Sucursal {branch_id}'
        measured_total = self._to_float(row.get('saldo_total_sucursal'))
        theoretical_total = self._to_float(row.get('caja_teorica_sucursal'))
        diff_total = measured_total - theoretical_total
        deviation_pct = self._safe_ratio(diff_total, theoretical_total)
        total_policy = policy_map.get('saldo total') or {
            'max_surplus_pct': 0.08,
            'max_deficit_pct': 0.05,
            'min_buffer_amount': 0.0,
            'truck_fixed_cost': 0.0,
            'truck_variable_cost_per_kg': 0.0,
        }

        recommendations: List[ChannelRecommendation] = []
        severity = 'ok'
        alerts_created = 0

        if theoretical_total > 0:
            allowed_positive = theoretical_total * self._to_float(total_policy.get('max_surplus_pct'))
            allowed_negative = theoretical_total * self._to_float(total_policy.get('max_deficit_pct'))
            if diff_total > allowed_positive:
                severity = 'alert'
                recommendations.append(
                    self._build_recommendation(
                        channel='Saldo Total',
                        action='withdraw',
                        amount=diff_total - allowed_positive,
                        policy=total_policy,
                        reason='Exceso vs caja teorica',
                        now=now,
                    )
                )
            elif diff_total < -allowed_negative:
                severity = 'alert'
                recommendations.append(
                    self._build_recommendation(
                        channel='Saldo Total',
                        action='deposit',
                        amount=abs(diff_total) - allowed_negative,
                        policy=total_policy,
                        reason='Deficit vs caja teorica',
                        now=now,
                    )
                )

        channel_details: List[Dict[str, Any]] = []
        for channel, field in CHANNEL_FIELDS.items():
            amount = self._to_float(row.get(field))
            share = self._safe_ratio(amount, measured_total)
            theoretical_estimate = theoretical_total * share if theoretical_total else amount
            channel_policy = policy_map.get(channel.lower())
            channel_info = {
                'channel': channel,
                'amount': amount,
                'estimated_teorica': theoretical_estimate,
                'share': share,
            }
            if channel_policy:
                deviation = amount - theoretical_estimate
                deviation_pct = self._safe_ratio(deviation, theoretical_estimate)
                channel_info['deviation_pct'] = deviation_pct
                threshold_pos = self._to_float(channel_policy.get('max_surplus_pct'))
                threshold_neg = self._to_float(channel_policy.get('max_deficit_pct'))

                if theoretical_estimate > 0 and deviation_pct > threshold_pos:
                    severity = self._update_severity(severity, 'warning')
                    rec = self._build_recommendation(
                        channel=channel,
                        action='withdraw',
                        amount=deviation - (theoretical_estimate * threshold_pos),
                        policy=channel_policy,
                        reason='Exceso canal vs distribucion esperada',
                        now=now,
                    )
                    recommendations.append(rec)
                elif theoretical_estimate > 0 and deviation_pct < -threshold_neg:
                    severity = self._update_severity(severity, 'warning')
                    rec = self._build_recommendation(
                        channel=channel,
                        action='deposit',
                        amount=abs(deviation) - (theoretical_estimate * threshold_neg),
                        policy=channel_policy,
                        reason='Deficit canal vs distribucion esperada',
                        now=now,
                    )
                    recommendations.append(rec)

                min_buffer = self._to_float(channel_policy.get('min_buffer_amount'))
                if amount < min_buffer:
                    severity = self._update_severity(severity, 'alert')
                    rec = self._build_recommendation(
                        channel=channel,
                        action='deposit',
                        amount=min_buffer - amount,
                        policy=channel_policy,
                        reason='Monto por debajo del colchon minimo',
                        now=now,
                    )
                    recommendations.append(rec)
            channel_details.append(channel_info)

        headline = self._build_headline(branch_name, diff_total, deviation_pct, severity)

        alerts_to_persist: List[Dict[str, Any]] = []
        alert_operation: Optional[Dict[str, Any]] = None
        alert_priority: Optional[str] = None
        alert_escalated = False

        if severity != 'ok':
            alert_payload = self._build_alert_payload(
                branch_id=branch_id,
                branch_name=branch_name,
                diff_total=diff_total,
                deviation_pct=deviation_pct,
                recommendations=recommendations,
                severity=severity,
                headline=headline,
                now=now,
            )
            if alert_payload is not None:
                alert_priority = str(alert_payload.get('priority') or '') or None
                normalized_priority = (alert_priority or '').lower()
                persist_alert = normalized_priority == 'critical' or severity in {'alert', 'critical'}
                if persist_alert:
                    alert_payload.setdefault('status', 'active')
                    alerts_to_persist.append(alert_payload)
                    alert_operation = self._compose_alert_operation(
                        alert_payload,
                        branch_id=branch_id,
                        branch_name=branch_name,
                    )
                    alerts_created = 1
                    alert_escalated = True

        recommendation_dicts = [rec.to_dict() for rec in recommendations]
        recommendation_artifact: Optional[Dict[str, Any]] = None
        if recommendation_dicts:
            recommendation_artifact = self._persist_recommendation_artifact(
                session_id=session_id,
                branch_id=branch_id,
                branch_name=branch_name,
                severity=severity,
                diff_total=diff_total,
                deviation_pct=deviation_pct,
                recommendations=recommendation_dicts,
                generated_at=now,
            )

        return {
            'branch_id': branch_id,
            'branch_name': branch_name,
            'status': severity,
            'headline': headline,
            'measured_total': measured_total,
            'theoretical_total': theoretical_total,
            'difference': diff_total,
            'deviation_pct': deviation_pct,
            'recommendations': recommendation_dicts,
            'channels': channel_details,
            'alerts_created': alerts_created,
            'alerts_to_persist': alerts_to_persist,
            'alert_priority': alert_priority,
            'alert_escalated': alert_escalated,
            'alert_operation': alert_operation,
            'recommendation_artifact': recommendation_artifact,
        }

    def _normalize_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = dict(policy or {})
        numeric_keys = {
            "max_surplus_pct",
            "max_deficit_pct",
            "min_buffer_amount",
            "daily_withdrawal_limit",
            "daily_deposit_limit",
            "reload_lead_hours",
            "sla_hours",
            "truck_fixed_cost",
            "truck_variable_cost_per_kg",
        }
        for key in numeric_keys:
            if key not in sanitized:
                continue
            value = sanitized.get(key)
            if value is None:
                continue
            if key in {"reload_lead_hours", "sla_hours"}:
                sanitized[key] = int(self._to_float(value))
            else:
                sanitized[key] = self._to_float(value)
        return sanitized

    def _build_headline(self, branch_name: str, diff_total: float, deviation_pct: float, severity: str) -> str:
        if severity == "ok":
            return f"{branch_name}: dentro de tolerancias"
        direction = "exceso" if diff_total > 0 else "deficit"
        return f"{branch_name}: {direction} de {abs(diff_total):,.0f} ARS ({deviation_pct:.1%})"

    def _update_severity(self, current: str, new_value: str) -> str:
        levels = {"ok": 0, "warning": 1, "alert": 2, "critical": 3}
        return new_value if levels.get(new_value, 0) > levels.get(current, 0) else current

    def _build_recommendation(
        self,
        *,
        channel: str,
        action: str,
        amount: float,
        policy: Dict[str, Any],
        reason: str,
        now: datetime,
    ) -> ChannelRecommendation:
        effective_amount = max(amount, 0)
        fixed_cost = self._to_float(policy.get("truck_fixed_cost"))
        variable_cost = self._to_float(policy.get("truck_variable_cost_per_kg"))
        kilograms = self._estimate_weight(effective_amount)
        logger.info({"event": "el_cajas_recommendation_costs", "channel": channel, "fixed_cost_type": type(fixed_cost).__name__, "variable_cost_type": type(variable_cost).__name__, "kilograms": kilograms})
        estimated_cost = fixed_cost + variable_cost * kilograms
        urgency = "inmediato" if channel == "ATM" else ("programar" if action == "withdraw" else "proximo turno")
        return ChannelRecommendation(
            channel=channel,
            action=action,
            amount=effective_amount,
            reason=reason,
            urgency=urgency,
            estimated_cost=estimated_cost,
            weight_kg=kilograms,
        )

    def _build_alert_payload(
        self,
        *,
        branch_id: str,
        branch_name: str,
        diff_total: float,
        deviation_pct: float,
        recommendations: List[ChannelRecommendation],
        severity: str,
        headline: str,
        now: datetime,
    ) -> Optional[Dict[str, Any]]:
        try:
            priority_code = self._priority_from_deviation(deviation_pct, recommendations)
            priority_label = self._priority_to_spanish(priority_code)
            summary_text = self._render_recommendation_summary(branch_name, diff_total, deviation_pct, severity)
            hypothesis_text = f"Desvio detectado en {branch_name}"
            impact_text = f"Diferencia de {abs(diff_total):,.0f} ARS ({deviation_pct:.1%})"
            action_lines: List[str] = []
            for rec in recommendations:
                if isinstance(rec, ChannelRecommendation):
                    amount_text = self._format_amount(rec.amount)
                    line = f"{rec.channel}: {rec.action} {amount_text} ARS - {rec.reason}"
                    if rec.urgency and rec.urgency not in line:
                        line = f"{line} [{rec.urgency}]"
                    action_lines.append(line)
                elif isinstance(rec, dict):
                    channel = rec.get('channel')
                    action = rec.get('action')
                    amount = rec.get('amount')
                    reason = rec.get('reason')
                    fragments = []
                    if channel:
                        fragments.append(str(channel))
                    if action:
                        fragments.append(str(action))
                    if amount is not None:
                        fragments.append(f"{self._format_amount(amount)} ARS")
                    if reason:
                        fragments.append(str(reason))
                    action_lines.append(': '.join(fragments) if fragments else json.dumps(rec, ensure_ascii=False))
            timestamp_iso = now.astimezone(timezone.utc).isoformat()
            datos_clave = [
                f"Diferencia total: {self._format_amount(diff_total)} ARS",
                f"Desvio porcentual: {deviation_pct:.1%}",
                f"Sucursal: {branch_name} ({branch_id})",
            ]
            if action_lines:
                datos_clave.append(action_lines[0])
            datos_clave.append(f"Medicion: {timestamp_iso}")
            dedupe_seed = f"{branch_id or branch_name}|{priority_label}|{round(diff_total)}|{round(deviation_pct, 4)}|{timestamp_iso}"
            dedupe_clave = hashlib.sha256(dedupe_seed.encode('utf-8')).hexdigest()
            return {
                "priority": priority_code,
                "prioridad": priority_label,
                "status": "active",
                "estado": "abierta",
                "problema": headline,
                "hipotesis": hypothesis_text,
                "impacto": impact_text,
                "datos_clave": datos_clave,
                "acciones": '; '.join(action_lines) if action_lines else None,
                "sucursal_id": branch_id,
                "branch_name": branch_name,
                "summary": summary_text,
                "dedupe_clave": dedupe_clave,
                "creada_en": timestamp_iso,
                "agente_id": str(EL_CAJAS_AGENT_UUID),
                "agent_source": self.AGENT_NAME,
            }
        except Exception as exc:  # pragma: no cover - logging defensivo
            logger.warning({
                "event": "elcajas_build_alert_failed",
                "branch_id": branch_id,
                "error": str(exc),
            })
            return None


    def _compose_alert_operation(
        self,
        payload: Dict[str, Any],
        *,
        branch_id: str,
        branch_name: str,
    ) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        prioridad = payload.get('prioridad')
        if not prioridad and payload.get('priority'):
            prioridad = self._priority_to_spanish(str(payload.get('priority')))
        if prioridad:
            values['prioridad'] = prioridad
        estado = payload.get('estado') or 'abierta'
        values['estado'] = estado
        problema = payload.get('problema') or payload.get('summary')
        if problema:
            values['problema'] = problema
        hipotesis = payload.get('hipotesis')
        if hipotesis:
            values['hipotesis'] = hipotesis
        impacto = payload.get('impacto')
        if impacto:
            values['impacto'] = impacto
        datos_clave = payload.get('datos_clave')
        if datos_clave:
            if not isinstance(datos_clave, (list, tuple)):
                datos_clave = [str(datos_clave)]
            values['datos_clave'] = list(datos_clave)
        acciones = payload.get('acciones')
        if acciones:
            values['acciones'] = acciones
        if branch_id:
            values['sucursal_id'] = branch_id
        dispositivo_id = payload.get('dispositivo_id')
        if dispositivo_id:
            values['dispositivo_id'] = dispositivo_id
        dedupe = payload.get('dedupe_clave')
        if dedupe:
            values['dedupe_clave'] = dedupe
        agente_id = payload.get('agente_id')
        if agente_id:
            values['agente_id'] = agente_id
        creada_en = payload.get('creada_en')
        if creada_en:
            if isinstance(creada_en, str):
                try:
                    created_dt = datetime.fromisoformat(creada_en.replace('Z', '+00:00'))
                except ValueError:
                    created_dt = datetime.now(timezone.utc)
            elif isinstance(creada_en, datetime):
                created_dt = creada_en if creada_en.tzinfo else creada_en.replace(tzinfo=timezone.utc)
            else:
                created_dt = datetime.now(timezone.utc)
            values['creada_en'] = created_dt

        allowed_columns = {
            'creada_en',
            'agente_id',
            'prioridad',
            'estado',
            'problema',
            'hipotesis',
            'impacto',
            'datos_clave',
            'acciones',
            'sucursal_id',
            'dispositivo_id',
            'evento_id',
            'dedupe_clave',
        }
        sanitized_values = {
            key: value
            for key, value in values.items()
            if key in allowed_columns and value is not None
        }


        return {
            'table': 'public.alertas',
            'values': sanitized_values,
            'description': f"Insert alerta El Cajas - {branch_name}",
            'branch_id': branch_id,
            'branch_name': branch_name,
            'source': self.AGENT_NAME,
            'payload': payload,
        }


    def _persist_recommendation_artifact(
        self,
        *,
        session_id: str,
        branch_id: str,
        branch_name: str,
        severity: str,
        diff_total: float,
        deviation_pct: float,
        recommendations: List[Dict[str, Any]],
        generated_at: datetime,
    ) -> Optional[Dict[str, Any]]:
        if not recommendations:
            return None

        sanitized_session = self._session_storage.sanitize_session_id(session_id or 'default')
        session_dir = self._workspace_root / 'data' / 'sessions' / f'session_{sanitized_session}'
        artifact_dir = session_dir / 'capi_elcajas'
        artifact_dir.mkdir(parents=True, exist_ok=True)

        branch_token = self._sanitize_token(branch_id or branch_name or 'branch')
        timestamp_token = generated_at.strftime('%Y%m%d_%H%M%S')
        filename = f'recommendation_{branch_token}_{timestamp_token}.json'
        file_path = artifact_dir / filename

        summary = self._render_recommendation_summary(branch_name, diff_total, deviation_pct, severity)
        hypothesis = f"Desvio detectado en {branch_name}"
        impact = f"Diferencia de {abs(diff_total):,.0f} ARS ({deviation_pct:.1%})"
        suggested_actions = [
            f"{item.get('channel')}: {item.get('action')} {self._format_amount(item.get('amount'))} ARS - {item.get('reason')}"
            for item in recommendations
            if isinstance(item, dict)
        ]

        artifact_payload = {
            'branch_id': branch_id,
            'branch_name': branch_name,
            'severity': severity,
            'difference_ars': diff_total,
            'deviation_pct': deviation_pct,
            'hypothesis': hypothesis,
            'impact': impact,
            'summary': summary,
            'suggested_actions': suggested_actions,
            'recommendations': recommendations,
            'generated_at': generated_at.isoformat(),
        }
        file_path.write_text(json.dumps(artifact_payload, ensure_ascii=False, indent=2), encoding='utf-8')

        relative_path = file_path.relative_to(session_dir).as_posix()
        return {
            'path': file_path.as_posix(),
            'filename': filename,
            'relative_path': relative_path,
            'created_at': generated_at.isoformat(),
            'summary': summary,
            'hypothesis': hypothesis,
            'impact': impact,
            'suggested_actions': suggested_actions,
        }

    def _render_recommendation_summary(
        self,
        branch_name: str,
        diff_total: float,
        deviation_pct: float,
        severity: str,
    ) -> str:
        direction = 'exceso' if diff_total > 0 else 'déficit' if diff_total < 0 else 'Desvio'
        magnitude = f"{abs(diff_total):,.0f} ARS"
        pct = f"{abs(deviation_pct):.1%}"
        return f"{branch_name}: {direction} de {magnitude} ({pct}). Severidad: {severity}"

    def _sanitize_token(self, value: str) -> str:
        if not value:
            return 'item'
        token = re.sub(r'[^A-Za-z0-9_-]+', '_', value.strip())
        token = token.strip('_')
        return token or 'item'

    def _format_amount(self, value: Any) -> str:
        try:
            return f"{float(value):,.0f}"
        except (TypeError, ValueError):
            return '0'


    def _render_alert_description(
        self,
        diff_total: float,
        deviation_pct: float,
        recommendations: List[ChannelRecommendation],
    ) -> str:
        direction = "exceso" if diff_total > 0 else "deficit"
        actions = "; ".join(
            f"{rec.channel}: {rec.action} {rec.amount:,.0f} (coste~{rec.estimated_cost:,.0f})" for rec in recommendations
        ) or "Sin accion definida"
        return f"Se detecto un {direction} de {abs(diff_total):,.0f} ARS ({deviation_pct:.1%}). Acciones sugeridas: {actions}."

    def _priority_from_deviation(
        self,
        deviation_pct: float,
        recommendations: List[ChannelRecommendation],
    ) -> str:
        magnitude = abs(deviation_pct)
        if any(rec.channel == "ATM" and rec.action == "deposit" for rec in recommendations):
            return "critical"
        if magnitude >= 0.15:
            return "critical"
        if magnitude >= 0.08:
            return "high"
        return "medium" if recommendations else "low"

    def _priority_to_spanish(self, priority: str) -> str:
        mapping = {
            'critical': 'critica',
            'high': 'alta',
            'alert': 'alta',
            'medium': 'media',
            'warning': 'media',
            'low': 'baja',
            'ok': 'baja',
        }
        return mapping.get((priority or '').lower(), 'media')

    def _estimate_weight(self, amount: float) -> float:
        bill_count = amount / AVERAGE_BILL_VALUE if AVERAGE_BILL_VALUE > 0 else 0
        return bill_count / 1000.0

    def _safe_ratio(self, numerator: float, denominator: float) -> float:
        if not denominator:
            return 0.0
        try:
            return numerator / denominator
        except ZeroDivisionError:
            return 0.0

    def _to_float(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

