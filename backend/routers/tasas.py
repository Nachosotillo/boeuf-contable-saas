"""
routers/tasas.py — Tasas de cambio BCV

Cambios:
  - Siembra de la serie real 2025 (POST /tasas/seed-2025).
  - Override MANUAL por fecha (POST /tasas/manual) — para la clase y correcciones.
  - Lookup por fecha con forward-fill (GET /tasas/por-fecha/{fecha}): devuelve la
    tasa vigente para ese día (última publicada <= fecha). Es la que deben usar los
    asientos para sellar `tasa_cambio_aplicada`.
  - El fetch automático del BCV queda gobernado por settings.TASA_AUTO_FETCH
    (ver tasks/scheduler.py). Por defecto está APAGADO para no pisar las tasas 2025.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import TasaCambioBcv, Usuario
from schemas import TasaBcvOut
from routers.auth import get_current_user, require_roles

router = APIRouter()


# ─── Helpers reutilizables por otros routers (asientos, etc.) ──────────────────

async def obtener_tasa_actual(db: AsyncSession) -> Optional[TasaCambioBcv]:
    """Última tasa cargada (la más reciente por fecha)."""
    result = await db.execute(
        select(TasaCambioBcv).order_by(TasaCambioBcv.fecha.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def obtener_tasa_para_fecha(db: AsyncSession, fecha: date) -> Optional[TasaCambioBcv]:
    """
    Tasa vigente para una fecha (forward-fill):
    la última tasa publicada con fecha <= `fecha`. Si la fecha es anterior a la
    primera tasa cargada, devuelve la más antigua disponible (p. ej. el asiento de
    constitución del 02/01 toma la tasa del 03/01).
    """
    result = await db.execute(
        select(TasaCambioBcv)
        .where(TasaCambioBcv.fecha <= fecha)
        .order_by(TasaCambioBcv.fecha.desc())
        .limit(1)
    )
    tasa = result.scalar_one_or_none()
    if tasa:
        return tasa
    result = await db.execute(
        select(TasaCambioBcv).order_by(TasaCambioBcv.fecha.asc()).limit(1)
    )
    return result.scalar_one_or_none()


# ─── Lectura ───────────────────────────────────────────────────────────────────

@router.get("/actual", response_model=TasaBcvOut)
async def tasa_actual(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tasa = await obtener_tasa_actual(db)
    if not tasa:
        raise HTTPException(
            503,
            detail="No hay tasas cargadas. Ejecuta POST /tasas/seed-2025 o carga una manual.",
        )
    return TasaBcvOut.model_validate(tasa)


@router.get("/por-fecha/{fecha}", response_model=TasaBcvOut)
async def tasa_por_fecha(
    fecha: date,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tasa vigente para `fecha` (forward-fill). La `fecha` devuelta puede ser
    anterior a la solicitada: es la última publicación que aplica a ese día."""
    tasa = await obtener_tasa_para_fecha(db, fecha)
    if not tasa:
        raise HTTPException(
            404, detail="No hay tasas cargadas. Ejecuta POST /tasas/seed-2025."
        )
    return TasaBcvOut.model_validate(tasa)


@router.get("/historico", response_model=list[TasaBcvOut])
async def historico_tasas(
    limit: int = 30,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TasaCambioBcv).order_by(TasaCambioBcv.fecha.desc()).limit(limit)
    )
    return [TasaBcvOut.model_validate(t) for t in result.scalars().all()]


# ─── Escritura: override manual y siembra ──────────────────────────────────────

class TasaManualIn(BaseModel):
    fecha: date
    tasa_usd: Decimal = Field(..., gt=0, decimal_places=4)
    tasa_eur: Optional[Decimal] = Field(default=None, gt=0, decimal_places=4)
    tasa_cny: Optional[Decimal] = Field(default=None, gt=0, decimal_places=4)


@router.post("/manual", response_model=TasaBcvOut)
async def set_tasa_manual(
    data: TasaManualIn,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db),
):
    """Crea o sobrescribe la tasa de una fecha concreta (fuente = MANUAL).
    Útil para fijar/corregir un cierre puntual sin tocar el resto de la serie."""
    result = await db.execute(
        select(TasaCambioBcv).where(TasaCambioBcv.fecha == data.fecha)
    )
    rec = result.scalar_one_or_none()
    if rec:
        rec.tasa_usd = data.tasa_usd
        if data.tasa_eur is not None:
            rec.tasa_eur = data.tasa_eur
        if data.tasa_cny is not None:
            rec.tasa_cny = data.tasa_cny
        rec.fuente = "MANUAL"
    else:
        rec = TasaCambioBcv(
            fecha=data.fecha,
            tasa_usd=data.tasa_usd,
            tasa_eur=data.tasa_eur,
            tasa_cny=data.tasa_cny,
            fuente="MANUAL",
        )
        db.add(rec)
    await db.flush()
    return TasaBcvOut.model_validate(rec)


@router.post("/seed-2025")
async def seed_2025(
    sobrescribir: bool = False,
    current_user: Usuario = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Siembra la serie diaria real del BCV 2025 (240 puntos).
    `sobrescribir=False` no pisa fechas ya cargadas (respeta overrides manuales).
    `sobrescribir=True` re-sincroniza desde el consolidado."""
    from tasas_2025_seed import sembrar_tasas_2025
    res = await sembrar_tasas_2025(db, sobrescribir)
    return {"mensaje": "Serie BCV 2025 procesada", **res}


@router.post("/forzar-actualizacion")
async def forzar_actualizacion(
    current_user: Usuario = Depends(require_roles("admin")),
):
    """Dispara el fetch del BCV en background. Respeta settings.TASA_AUTO_FETCH:
    si está apagado (modo clase 2025), no hace nada para no pisar las tasas."""
    from tasks.scheduler import actualizar_tasa_bcv
    import asyncio
    asyncio.create_task(actualizar_tasa_bcv())
    return {"mensaje": "Solicitud enviada (sujeta a TASA_AUTO_FETCH)"}
