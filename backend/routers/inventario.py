"""
routers/inventario.py — Gestión de Inventario PEPS por Artículo
"""
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import ArticuloInventario, MovimientoInventario, Usuario
from schemas import (
    ArticuloInventarioCreate, ArticuloInventarioOut, ArticuloInventarioUpdate,
    MovimientoInvCreate, MovimientoInvOut
)
from routers.auth import get_current_user, require_roles

router = APIRouter()
R4 = lambda v: Decimal(str(v)).quantize(Decimal("0.0001"), ROUND_HALF_UP)
R2 = lambda v: Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)


# ─── Artículos de Inventario ──────────────────────────────────────────────────

@router.get("/articulos", response_model=list[ArticuloInventarioOut])
async def listar_articulos(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ArticuloInventario)
        .where(ArticuloInventario.empresa_id == current_user.empresa_id)
        .order_by(ArticuloInventario.descripcion)
    )
    return [ArticuloInventarioOut.model_validate(r) for r in result.scalars().all()]


@router.post("/articulos", response_model=ArticuloInventarioOut, status_code=201)
async def crear_articulo(
    data: ArticuloInventarioCreate,
    current_user: Usuario = Depends(require_roles("admin", "gerente_compras")),
    db: AsyncSession = Depends(get_db)
):
    # Validar SKU único
    exist = await db.execute(
        select(ArticuloInventario).where(
            ArticuloInventario.empresa_id == current_user.empresa_id,
            ArticuloInventario.codigo_sku == data.codigo_sku
        )
    )
    if exist.scalar_one_or_none():
        raise HTTPException(400, "El SKU ya existe")

    obj = ArticuloInventario(**data.model_dump(), empresa_id=current_user.empresa_id)
    db.add(obj)
    await db.flush()
    return ArticuloInventarioOut.model_validate(obj)


@router.put("/articulos/{articulo_id}", response_model=ArticuloInventarioOut)
async def actualizar_articulo(
    articulo_id: int,
    data: ArticuloInventarioUpdate,
    current_user: Usuario = Depends(require_roles("admin", "gerente_compras")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ArticuloInventario).where(
            ArticuloInventario.id == articulo_id,
            ArticuloInventario.empresa_id == current_user.empresa_id
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Artículo no encontrado")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    return ArticuloInventarioOut.model_validate(obj)


# ─── Movimientos de Inventario ────────────────────────────────────────────────

@router.post("/movimientos", response_model=MovimientoInvOut, status_code=201)
async def registrar_movimiento(
    data: MovimientoInvCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_compras")),
    db: AsyncSession = Depends(get_db)
):
    # Validar artículo
    res_art = await db.execute(
        select(ArticuloInventario).where(
            ArticuloInventario.id == data.articulo_id,
            ArticuloInventario.empresa_id == current_user.empresa_id
        )
    )
    articulo = res_art.scalar_one_or_none()
    if not articulo:
        raise HTTPException(404, "Artículo no encontrado")

    # Obtener saldo actual del artículo
    result = await db.execute(
        select(MovimientoInventario)
        .where(
            MovimientoInventario.empresa_id == current_user.empresa_id,
            MovimientoInventario.articulo_id == data.articulo_id
        )
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
        if saldo_uds < data.cantidad:
            raise HTTPException(400, f"Stock insuficiente para {articulo.descripcion}")
        nuevo_saldo_uds = R4(saldo_uds - data.cantidad)
        nuevo_saldo_val = R2(saldo_val - costo_total)

    # Registrar movimiento
    obj = MovimientoInventario(
        empresa_id=current_user.empresa_id,
        articulo_id=data.articulo_id,
        fecha=data.fecha,
        descripcion=data.descripcion,
        tipo=data.tipo,
        lote=data.lote,
        fecha_vencimiento=data.fecha_vencimiento,
        cantidad=data.cantidad,
        costo_unitario=data.costo_unitario,
        costo_total=costo_total,
        saldo_unidades=nuevo_saldo_uds,
        saldo_valor=nuevo_saldo_val,
    )
    db.add(obj)
    
    # Actualizar stock en el maestro del artículo
    articulo.stock_actual = nuevo_saldo_uds
    
    await db.flush()
    return MovimientoInvOut.model_validate(obj)


@router.get("/movimientos", response_model=list[MovimientoInvOut])
async def listar_movimientos(
    articulo_id: int = None,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    q = select(MovimientoInventario).where(MovimientoInventario.empresa_id == current_user.empresa_id)
    if articulo_id:
        q = q.where(MovimientoInventario.articulo_id == articulo_id)
    q = q.order_by(MovimientoInventario.fecha.desc(), MovimientoInventario.id.desc())
    
    result = await db.execute(q)
    return [MovimientoInvOut.model_validate(r) for r in result.scalars().all()]


@router.get("/saldo")
async def saldo_inventario(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Sumariza el stock actual y valor estimado del inventario general
    result = await db.execute(
        select(ArticuloInventario).where(ArticuloInventario.empresa_id == current_user.empresa_id)
    )
    articulos = result.scalars().all()
    
    total_unidades = sum(a.stock_actual for a in articulos)
    
    # Para el valor total exacto, tendríamos que buscar el saldo_valor de la última transacción de cada artículo.
    # Por simplicidad en este endpoint, podemos hacer un query por cada uno o usar SQL puro:
    # "SELECT SUM(saldo_valor) FROM (SELECT DISTINCT ON (articulo_id) saldo_valor FROM movimiento_inventario ORDER BY articulo_id, id DESC)"
    
    return {
        "saldo_unidades": float(total_unidades),
        "total_articulos": len(articulos)
    }
