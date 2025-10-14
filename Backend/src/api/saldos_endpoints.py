from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

from ..core.exceptions import DatabaseError
from ..infrastructure.database.postgres_client import (
    PostgreSQLClient,
    get_postgres_client,
)

router = APIRouter(prefix="/api/saldos", tags=["Saldos"])


def get_db_client() -> PostgreSQLClient:
    return get_postgres_client()


class SucursalBase(BaseModel):
    sucursal_numero: Optional[int] = None
    sucursal_nombre: Optional[str] = None
    telefonos: Optional[str] = None
    calle: Optional[str] = None
    altura: Optional[int] = None
    barrio: Optional[str] = None
    comuna: Optional[int] = None
    codigo_postal: Optional[int] = None
    codigo_postal_argentino: Optional[str] = None
    saldo_total_sucursal: Optional[float] = None
    caja_teorica_sucursal: Optional[float] = None
    total_atm: Optional[float] = None
    total_ats: Optional[float] = None
    total_tesoro: Optional[float] = None
    total_cajas_ventanilla: Optional[float] = None
    total_buzon_depositos: Optional[float] = None
    total_recaudacion: Optional[float] = None
    total_caja_chica: Optional[float] = None
    total_otros: Optional[float] = None
    direccion_sucursal: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    observacion: Optional[str] = None
    medido_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SucursalCreate(SucursalBase):
    sucursal_id: str = Field(..., min_length=1, max_length=255)
    sucursal_numero: int
    sucursal_nombre: str
    saldo_total_sucursal: float


class SucursalUpdate(SucursalBase):
    pass


class SucursalResponse(SucursalBase):
    sucursal_id: str


class DispositivoBase(BaseModel):
    sucursal_id: Optional[str] = None
    dispositivo_id: Optional[str] = None
    tipo_dispositivo: Optional[str] = None
    saldo_total: Optional[float] = None
    caja_teorica: Optional[float] = None
    cant_d1: Optional[int] = None
    cant_d2: Optional[int] = None
    cant_d3: Optional[int] = None
    cant_d4: Optional[int] = None
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    observacion: Optional[str] = None
    medido_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DispositivoCreate(DispositivoBase):
    sucursal_id: str
    dispositivo_id: str
    tipo_dispositivo: str
    saldo_total: float


class DispositivoUpdate(DispositivoBase):
    pass


class DispositivoResponse(DispositivoBase):
    id: int
    sucursal_id: str
    dispositivo_id: str
    tipo_dispositivo: str
    saldo_total: float


@router.get("/sucursales", response_model=List[SucursalResponse])
async def list_sucursales(db: PostgreSQLClient = Depends(get_db_client)) -> List[SucursalResponse]:
    try:
        rows = await db.get_sucursales()
        return [SucursalResponse(**row) for row in rows]
    except DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/sucursales", response_model=SucursalResponse, status_code=status.HTTP_201_CREATED)
async def create_sucursal(
    payload: SucursalCreate,
    db: PostgreSQLClient = Depends(get_db_client),
) -> SucursalResponse:
    try:
        record = await db.create_sucursal(payload.model_dump(exclude_unset=True))
        return SucursalResponse(**record)
    except DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/sucursales/{sucursal_id}", response_model=SucursalResponse)
async def update_sucursal(
    sucursal_id: str,
    payload: SucursalUpdate,
    db: PostgreSQLClient = Depends(get_db_client),
) -> SucursalResponse:
    try:
        record = await db.update_sucursal(sucursal_id, payload.model_dump(exclude_unset=True))
        return SucursalResponse(**record)
    except DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/sucursales/{sucursal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sucursal(
    sucursal_id: str,
    db: PostgreSQLClient = Depends(get_db_client),
) -> None:
    try:
        deleted = await db.delete_sucursal(sucursal_id)
    except DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")


@router.get("/dispositivos", response_model=List[DispositivoResponse])
async def list_dispositivos(db: PostgreSQLClient = Depends(get_db_client)) -> List[DispositivoResponse]:
    try:
        rows = await db.get_dispositivos()
        return [DispositivoResponse(**row) for row in rows]
    except DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/dispositivos", response_model=DispositivoResponse, status_code=status.HTTP_201_CREATED)
async def create_dispositivo(
    payload: DispositivoCreate,
    db: PostgreSQLClient = Depends(get_db_client),
) -> DispositivoResponse:
    try:
        record = await db.create_dispositivo(payload.model_dump(exclude_unset=True))
        return DispositivoResponse(**record)
    except DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/dispositivos/{record_id}", response_model=DispositivoResponse)
async def update_dispositivo(
    record_id: int,
    payload: DispositivoUpdate,
    db: PostgreSQLClient = Depends(get_db_client),
) -> DispositivoResponse:
    try:
        record = await db.update_dispositivo(record_id, payload.model_dump(exclude_unset=True))
        return DispositivoResponse(**record)
    except DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/dispositivos/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dispositivo(
    record_id: int,
    db: PostgreSQLClient = Depends(get_db_client),
) -> None:
    try:
        deleted = await db.delete_dispositivo(record_id)
    except DatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado")
