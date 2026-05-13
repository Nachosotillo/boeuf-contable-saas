"""
routers/igtf.py
"""
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import OperacionIgtf, Usuario
from schemas import OperacionIgtfCreate, OperacionIgtfOut
from routers.auth import get_current_user, require_roles

router = APIRouter()
R = lambda v: Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)


@router.post("/", response_model=OperacionIgtfOut, status_code=201)
async def registrar_igtf(
    data: OperacionIgtfCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db)
):
    equiv = R(data.monto_divisas * data.tasa_bcv)
    igtf = R(equiv * Decimal("0.03"))
    obj = OperacionIgtf(
        empresa_id=current_user.empresa_id,
        fecha=data.fecha,
        numero_operacion=data.numero_operacion,
        cliente_pagador=data.cliente_pagador,
        rif=data.rif,
        moneda=data.moneda,
        tasa_bcv=data.tasa_bcv,
        monto_divisas=data.monto_divisas,
        equivalente_bs=equiv,
        igtf_3_pct=igtf,
    )
    db.add(obj)
    await db.flush()
    return OperacionIgtfOut.model_validate(obj)


@router.get("/", response_model=list[OperacionIgtfOut])
async def listar_igtf(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OperacionIgtf).where(OperacionIgtf.empresa_id == current_user.empresa_id)
        .order_by(OperacionIgtf.fecha.desc())
    )
    return [OperacionIgtfOut.model_validate(r) for r in result.scalars().all()]
