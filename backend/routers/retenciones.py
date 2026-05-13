"""
routers/retenciones.py — Retenciones ISLR Decreto 1808
"""
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import RetencionIslr, Usuario
from schemas import RetencionIslrCreate, RetencionIslrOut, CONCEPTOS_ISLR
from routers.auth import get_current_user, require_roles

router = APIRouter()
R = lambda v: Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)


@router.post("/", response_model=RetencionIslrOut, status_code=201)
async def crear_retencion(
    data: RetencionIslrCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db)
):
    tasa = CONCEPTOS_ISLR[data.concepto]
    retenido = R(data.monto_bruto * tasa)
    neto = R(data.monto_bruto - retenido)

    obj = RetencionIslr(
        empresa_id=current_user.empresa_id,
        fecha_pago=data.fecha_pago,
        numero_factura=data.numero_factura,
        beneficiario_nombre=data.beneficiario_nombre,
        beneficiario_rif=data.beneficiario_rif,
        concepto=data.concepto,
        tasa_retencion=tasa,
        monto_bruto=data.monto_bruto,
        monto_retenido=retenido,
        monto_neto_pagado=neto,
    )
    db.add(obj)
    await db.flush()
    return RetencionIslrOut.model_validate(obj)


@router.get("/", response_model=list[RetencionIslrOut])
async def listar_retenciones(
    mes: int | None = None,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    q = select(RetencionIslr).where(RetencionIslr.empresa_id == current_user.empresa_id)
    if mes:
        from sqlalchemy import extract
        q = q.where(extract("month", RetencionIslr.fecha_pago) == mes)
    result = await db.execute(q.order_by(RetencionIslr.fecha_pago.desc()))
    return [RetencionIslrOut.model_validate(r) for r in result.scalars().all()]


@router.get("/conceptos")
async def listar_conceptos():
    """Retorna la tabla de conceptos y tasas del Decreto 1808."""
    return [{"concepto": k, "tasa_pct": float(v * 100)} for k, v in CONCEPTOS_ISLR.items()]
