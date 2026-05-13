"""
routers/tasas.py — Tasas de cambio BCV
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import TasaCambioBcv, Usuario
from schemas import TasaBcvOut
from routers.auth import get_current_user

router = APIRouter()


@router.get("/actual", response_model=TasaBcvOut)
async def tasa_actual(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TasaCambioBcv).order_by(TasaCambioBcv.fecha.desc()).limit(1)
    )
    tasa = result.scalar_one_or_none()
    if not tasa:
        raise HTTPException(503, detail="Tasa BCV no disponible aún. Espera la actualización de las 8:00 AM.")
    return TasaBcvOut.model_validate(tasa)


@router.get("/historico", response_model=list[TasaBcvOut])
async def historico_tasas(
    limit: int = 30,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TasaCambioBcv).order_by(TasaCambioBcv.fecha.desc()).limit(limit)
    )
    return [TasaBcvOut.model_validate(t) for t in result.scalars().all()]


@router.post("/forzar-actualizacion")
async def forzar_actualizacion(
    current_user: Usuario = Depends(get_current_user),
):
    from tasks.scheduler import actualizar_tasa_bcv
    import asyncio
    asyncio.create_task(actualizar_tasa_bcv())
    return {"mensaje": "Actualización de tasa BCV iniciada en background"}
