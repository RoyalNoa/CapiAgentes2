from __future__ import annotations

from fastapi import APIRouter

# Reuse the agents endpoints router
try:
    from src.api.agents_endpoints import router as agents_router
except Exception as e:  # pragma: no cover
    agents_router = None

router = APIRouter(prefix="")

# Optionally expose a demo ping
@router.get("/api/demo/ping", include_in_schema=False)
async def demo_ping():
    return {"status": "ok", "component": "demo_interface"}

# Include agents router if available
if agents_router is not None:
    router.include_router(agents_router)