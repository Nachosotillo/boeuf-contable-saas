"""
routers/ajustes.py
"""
from decimal import Decimal
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from database import get_db
from models import Ajuste, LineaAjuste, CatalogoCuenta, Usuario
from schemas import AjusteCreate, AjusteOut
from routers.auth import get_current_user, require_roles

router = APIRouter()


async def _proximo_numero_ajuste(empresa_id: int, db: AsyncSession) -> str:
    result = await db.execute(select(func.count(Ajuste.id)).where(Ajuste.empresa_id == empresa_id))
    count = result.scalar() or 0
    return f"AJ-{str(count + 1).zfill(3)}"


@router.post("/", response_model=AjusteOut, status_code=201)
async def crear_ajuste(
    data: AjusteCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db)
):
    codigos = [l.cuenta_codigo for l in data.lineas]
    result = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.empresa_id == current_user.empresa_id,
            CatalogoCuenta.codigo.in_(codigos),
        )
    )
    cuentas_db = {c.codigo: c for c in result.scalars().all()}
    missing = [c for c in codigos if c not in cuentas_db]
    if missing:
        raise HTTPException(400, detail=f"Cuentas no encontradas: {missing}")

    numero = await _proximo_numero_ajuste(current_user.empresa_id, db)
    td = sum(l.debe for l in data.lineas)
    th = sum(l.haber for l in data.lineas)

    ajuste = Ajuste(
        empresa_id=current_user.empresa_id,
        numero_ajuste=numero,
        fecha=data.fecha,
        mes=data.fecha.month,
        descripcion=data.descripcion,
        referencia=data.referencia,
        tipo=data.tipo,
        total_debe=td,
        total_haber=th,
        creado_por=current_user.id,
    )
    db.add(ajuste)
    await db.flush()

    for l in data.lineas:
        db.add(LineaAjuste(
            ajuste_id=ajuste.id,
            cuenta_id=cuentas_db[l.cuenta_codigo].id,
            debe=l.debe,
            haber=l.haber,
            descripcion=l.descripcion,
        ))
    await db.flush()
    return AjusteOut(id=ajuste.id, numero_ajuste=numero, fecha=data.fecha,
                     tipo=data.tipo, descripcion=data.descripcion,
                     total_debe=td, total_haber=th)


@router.get("/", response_model=list[AjusteOut])
async def listar_ajustes(
    mes: int | None = None,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    q = select(Ajuste).where(Ajuste.empresa_id == current_user.empresa_id)
    if mes:
        q = q.where(Ajuste.mes == mes)
    q = q.order_by(Ajuste.fecha.desc())
    result = await db.execute(q)
    return [AjusteOut(id=a.id, numero_ajuste=a.numero_ajuste, fecha=a.fecha,
                      tipo=a.tipo, descripcion=a.descripcion,
                      total_debe=a.total_debe, total_haber=a.total_haber)
            for a in result.scalars().all()]
