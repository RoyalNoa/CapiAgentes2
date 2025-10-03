"""
Maps API endpoints for sucursal geodata feeds.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..infrastructure.database.postgres_client import (
    get_postgres_client,
    PostgreSQLClient,
)
from ..core.exceptions import DatabaseError

router = APIRouter(prefix="/api/maps", tags=["Maps"])


class SucursalResponse(BaseModel):
    sucursal_id: str
    sucursal_numero: int
    sucursal_nombre: str
    telefonos: Optional[str] = None
    calle: Optional[str] = None
    altura: Optional[int] = None
    barrio: Optional[str] = None
    comuna: Optional[int] = None
    codigo_postal: Optional[int] = None
    codigo_postal_argentino: Optional[str] = None
    saldo_total_sucursal: float
    caja_teorica_sucursal: Optional[float] = None
    total_atm: float
    total_ats: float
    total_tesoro: float
    total_cajas_ventanilla: float
    total_buzon_depositos: float
    total_recaudacion: float
    total_caja_chica: float
    total_otros: float
    direccion_sucursal: Optional[str] = None
    latitud: float
    longitud: float
    observacion: Optional[str] = None
    medido_en: Optional[datetime] = None


async def get_db_client() -> PostgreSQLClient:
    return get_postgres_client()


@router.get(
    "/sucursales",
    response_model=List[SucursalResponse],
    summary="Listado de sucursales",
    description="Devuelve sucursales con geolocalizacion para renderizar en mapas.",
)
async def list_sucursales(
    db: PostgreSQLClient = Depends(get_db_client),
) -> List[SucursalResponse]:
    try:
        rows = await db.get_sucursales()
        return [SucursalResponse(**row) for row in rows]
    except DatabaseError as exc:
        raise HTTPException(status_code=500, detail="Database error") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal server error") from exc

