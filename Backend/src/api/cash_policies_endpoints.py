"""Endpoints for managing cash management policies."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

from src.application.services.cash_policy_service import CashPolicyService


router = APIRouter(prefix="/api/cash-policies", tags=["cash-policies"])


def get_cash_policy_service() -> CashPolicyService:
    return CashPolicyService()


class CashPolicyModel(BaseModel):
    channel: str = Field(..., description="Nombre del canal")
    max_surplus_pct: Optional[float] = Field(None, description="Exceso permitido vs. teórica (porcentaje)")
    max_deficit_pct: Optional[float] = Field(None, description="Déficit permitido vs. teórica (porcentaje)")
    min_buffer_amount: Optional[float] = Field(None, description="Colchón mínimo en pesos")
    daily_withdrawal_limit: Optional[float] = Field(None, description="Límite diario de retiro")
    daily_deposit_limit: Optional[float] = Field(None, description="Límite diario de depósito")
    reload_lead_hours: Optional[float] = Field(None, description="Anticipación requerida para recarga")
    sla_hours: Optional[float] = Field(None, description="SLA objetivo para normalizar")
    truck_fixed_cost: Optional[float] = Field(None, description="Costo fijo camión caudal")
    truck_variable_cost_per_kg: Optional[float] = Field(None, description="Tarifa variable por kilogramo transportado")
    notes: Optional[str] = Field(None, description="Notas operativas")
    updated_at: Optional[str] = Field(None, description="Última actualización ISO8601")

    model_config = ConfigDict(from_attributes=True)



class UpdateCashPolicyRequest(BaseModel):
    max_surplus_pct: Optional[float] = None
    max_deficit_pct: Optional[float] = None
    min_buffer_amount: Optional[float] = None
    daily_withdrawal_limit: Optional[float] = None
    daily_deposit_limit: Optional[float] = None
    reload_lead_hours: Optional[float] = None
    sla_hours: Optional[float] = None
    truck_fixed_cost: Optional[float] = None
    truck_variable_cost_per_kg: Optional[float] = None
    notes: Optional[str] = None


@router.get("", response_model=List[CashPolicyModel])
async def list_cash_policies(service: CashPolicyService = Depends(get_cash_policy_service)) -> List[Dict[str, Any]]:
    return await service.list_policies()


@router.put("/{channel}", response_model=CashPolicyModel, status_code=status.HTTP_200_OK)
async def upsert_cash_policy(
    channel: str,
    request: UpdateCashPolicyRequest,
    service: CashPolicyService = Depends(get_cash_policy_service),
) -> Dict[str, Any]:
    try:
        return await service.upsert_policy(channel, request.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

