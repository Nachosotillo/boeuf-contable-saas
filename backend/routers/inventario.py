"""
routers/inventario.py — Inventario MP método PEPS
"""
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import MovimientoInventario, Usuario
from schemas import MovimientoInvCreate, MovimientoInvOut
from routers.auth import get_current_user, require_roles

router = APIRouter()
R4 = lambda v: Decimal(str(v)).quantize(Decimal("0.0001"), ROUND_HALF_UP)
R2 = lambda v: Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)


@router.post("/", response_model=MovimientoInvOut, status_code=201)
async def registrar_movimiento(
    data: MovimientoInvCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_compras")),
    db: AsyncSession = Depends(get_db)
):
    # Obtener saldo actual
    result = await db.execute(
        select(MovimientoInventario)
        .where(MovimientoInventario.empresa_id == current_user.empresa_id)
        .order_by(MovimientoInventario.id.desc())
        .limit(1)
    )
    ultimo = result.scalar_one_or_none()
    saldo_uds = (ultimo.saldo_unidades if ultimo else Decimal("0"))
    saldo_val = (ultimo.saldo_valor if ultimo else Decimal("0"))

    costo_total = R2(data.cantidad * data.costo_unitario)

    if data.tipo.value == "E":
        nuevo_saldo_uds = R4(saldo_uds + data.cantidad)
        nuevo_saldo_val = R2(saldo_val + costo_total)
    else:
        nuevo_saldo_uds = R4(saldo_uds - data.cantidad)
        nuevo_saldo_val = R2(saldo_val - costo_total)

    obj = MovimientoInventario(
        empresa_id=current_user.empresa_id,
        fecha=data.fecha,
        descripcion=data.descripcion,
        tipo=data.tipo,
        unidad=data.unidad,
        cantidad=data.cantidad,
        costo_unitario=data.costo_unitario,
        costo_total=costo_total,
        saldo_unidades=nuevo_saldo_uds,
        saldo_valor=nuevo_saldo_val,
    )
    db.add(obj)
    await db.flush()
    return MovimientoInvOut.model_validate(obj)


@router.get("/", response_model=list[MovimientoInvOut])
async def listar_movimientos(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MovimientoInventario)
        .where(MovimientoInventario.empresa_id == current_user.empresa_id)
        .order_by(MovimientoInventario.fecha, MovimientoInventario.id)
    )
    return [MovimientoInvOut.model_validate(r) for r in result.scalars().all()]


@router.get("/saldo")
async def saldo_inventario(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MovimientoInventario)
        .where(MovimientoInventario.empresa_id == current_user.empresa_id)
        .order_by(MovimientoInventario.id.desc()).limit(1)
    )
    ultimo = result.scalar_one_or_none()
    return {
        "saldo_unidades": float(ultimo.saldo_unidades) if ultimo else 0,
        "saldo_valor": float(ultimo.saldo_valor) if ultimo else 0,
    }
