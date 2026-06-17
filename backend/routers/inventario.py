"""
routers/inventario.py — Inventario PERPETUO (continuo) con PROMEDIO PONDERADO móvil.

Reglas:
  - ENTRADA: se valora al costo de la entrada; el promedio se recalcula solo.
  - SALIDA : se valora al PROMEDIO PONDERADO vigente (saldo_valor / saldo_unidades).
             El costo_unitario que venga en el request se ignora en salidas.
  - Si una SALIDA de Producto Terminado se marca con generar_asiento_costo=True,
    se crea automáticamente el asiento de costo:
        Debe  cuenta_costo (5.2.0x)  /  Haber cuenta_inventario (1.1.22.0x)
    y el movimiento queda enlazado a ese asiento (asiento_id).

Cada artículo declara su `cuenta_inventario` y `cuenta_costo` para el enganche contable.
El kardex (movimiento_inventario) es el auxiliar; las cuentas 1.1.2x son el control.
"""
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models import (
    ArticuloInventario, MovimientoInventario, Usuario,
    TipoArticuloInventarioEnum, TipoMovimientoInvEnum, OrigenAsientoEnum,
)
from schemas import (
    ArticuloInventarioCreate, ArticuloInventarioOut, ArticuloInventarioUpdate,
    MovimientoInvCreate, MovimientoInvOut,
)
from routers.auth import get_current_user, require_roles
from routers.asientos import crear_asiento_interno

router = APIRouter()
R4 = lambda v: Decimal(str(v)).quantize(Decimal("0.0001"), ROUND_HALF_UP)
R2 = lambda v: Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)
ZERO = Decimal("0")


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _ultimo_saldo(db: AsyncSession, empresa_id: int, articulo_id: int):
    """Devuelve (saldo_unidades, saldo_valor) del último movimiento del artículo."""
    res = await db.execute(
        select(MovimientoInventario)
        .where(
            MovimientoInventario.empresa_id == empresa_id,
            MovimientoInventario.articulo_id == articulo_id,
        )
        .order_by(MovimientoInventario.id.desc())
        .limit(1)
    )
    ult = res.scalar_one_or_none()
    if ult:
        return ult.saldo_unidades, ult.saldo_valor
    return ZERO, ZERO


def costo_promedio(saldo_uds: Decimal, saldo_val: Decimal) -> Decimal:
    """Promedio ponderado vigente."""
    if saldo_uds and saldo_uds > 0:
        return R4(saldo_val / saldo_uds)
    return ZERO


# ─── Artículos de Inventario ──────────────────────────────────────────────────

@router.get("/articulos", response_model=list[ArticuloInventarioOut])
async def listar_articulos(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    exist = await db.execute(
        select(ArticuloInventario).where(
            ArticuloInventario.empresa_id == current_user.empresa_id,
            ArticuloInventario.codigo_sku == data.codigo_sku,
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
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ArticuloInventario).where(
            ArticuloInventario.id == articulo_id,
            ArticuloInventario.empresa_id == current_user.empresa_id,
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
    generar_asiento_costo: bool = Query(
        False,
        description="Si la salida es una VENTA de PT, crea el asiento de costo "
                    "(Debe cuenta_costo / Haber cuenta_inventario).",
    ),
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_compras", "gerente_ventas")),
    db: AsyncSession = Depends(get_db),
):
    res_art = await db.execute(
        select(ArticuloInventario).where(
            ArticuloInventario.id == data.articulo_id,
            ArticuloInventario.empresa_id == current_user.empresa_id,
        )
    )
    articulo = res_art.scalar_one_or_none()
    if not articulo:
        raise HTTPException(404, "Artículo no encontrado")

    saldo_uds, saldo_val = await _ultimo_saldo(db, current_user.empresa_id, data.articulo_id)

    if data.tipo == TipoMovimientoInvEnum.entrada:
        costo_unit = R4(data.costo_unitario)
        costo_total = R2(data.cantidad * costo_unit)
        nuevo_uds = R4(saldo_uds + data.cantidad)
        nuevo_val = R2(saldo_val + costo_total)
    else:  # SALIDA → promedio ponderado vigente
        if saldo_uds < data.cantidad:
            raise HTTPException(
                400, f"Stock insuficiente de {articulo.descripcion}: "
                     f"hay {saldo_uds}, se piden {data.cantidad}"
            )
        costo_unit = costo_promedio(saldo_uds, saldo_val)   # ignora el costo del request
        costo_total = R2(data.cantidad * costo_unit)
        nuevo_uds = R4(saldo_uds - data.cantidad)
        # Si se vacía el stock, el valor cae a 0 (evita residuos de redondeo)
        nuevo_val = ZERO if nuevo_uds == 0 else R2(saldo_val - costo_total)

    mov = MovimientoInventario(
        empresa_id=current_user.empresa_id,
        articulo_id=data.articulo_id,
        fecha=data.fecha,
        descripcion=data.descripcion,
        tipo=data.tipo,
        lote=data.lote,
        fecha_vencimiento=data.fecha_vencimiento,
        cantidad=data.cantidad,
        costo_unitario=costo_unit,
        costo_total=costo_total,
        saldo_unidades=nuevo_uds,
        saldo_valor=nuevo_val,
    )
    db.add(mov)
    articulo.stock_actual = nuevo_uds
    await db.flush()

    # Asiento de costo automático (solo salidas marcadas como venta)
    if generar_asiento_costo and data.tipo == TipoMovimientoInvEnum.salida:
        if not articulo.cuenta_costo or not articulo.cuenta_inventario:
            raise HTTPException(
                400,
                f"El artículo {articulo.codigo_sku} no tiene configuradas "
                f"cuenta_costo y cuenta_inventario para generar el asiento de costo.",
            )
        asiento = await crear_asiento_interno(
            db,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            fecha=data.fecha,
            origen=OrigenAsientoEnum.costo_venta,
            descripcion=f"Costo de ventas — {articulo.descripcion} ({data.cantidad} {articulo.unidad_medida})",
            referencia=data.lote,
            lineas=[
                {"cuenta_codigo": articulo.cuenta_costo, "debe": costo_total, "haber": 0,
                 "descripcion": "Costo de la mercancía vendida"},
                {"cuenta_codigo": articulo.cuenta_inventario, "debe": 0, "haber": costo_total,
                 "descripcion": "Salida de inventario PT"},
            ],
        )
        mov.asiento_id = asiento.id
        await db.flush()

    return MovimientoInvOut.model_validate(mov)


@router.get("/movimientos", response_model=list[MovimientoInvOut])
async def listar_movimientos(
    articulo_id: int | None = None,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(MovimientoInventario).where(
        MovimientoInventario.empresa_id == current_user.empresa_id
    )
    if articulo_id:
        q = q.where(MovimientoInventario.articulo_id == articulo_id)
    q = q.order_by(MovimientoInventario.fecha.desc(), MovimientoInventario.id.desc())
    result = await db.execute(q)
    return [MovimientoInvOut.model_validate(r) for r in result.scalars().all()]


@router.get("/kardex/{articulo_id}")
async def kardex_articulo(
    articulo_id: int,
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Kardex de un artículo (base del Libro de Inventarios): movimientos en orden
    cronológico con saldos vivos y el costo promedio en cada punto."""
    res_art = await db.execute(
        select(ArticuloInventario).where(
            ArticuloInventario.id == articulo_id,
            ArticuloInventario.empresa_id == current_user.empresa_id,
        )
    )
    art = res_art.scalar_one_or_none()
    if not art:
        raise HTTPException(404, "Artículo no encontrado")

    q = select(MovimientoInventario).where(
        MovimientoInventario.empresa_id == current_user.empresa_id,
        MovimientoInventario.articulo_id == articulo_id,
    )
    if mes:
        q = q.where(func.extract("month", MovimientoInventario.fecha) == mes)
    q = q.order_by(MovimientoInventario.fecha, MovimientoInventario.id)
    movs = (await db.execute(q)).scalars().all()

    filas = []
    for m in movs:
        es_entrada = m.tipo == TipoMovimientoInvEnum.entrada
        filas.append({
            "fecha": m.fecha,
            "descripcion": m.descripcion,
            "tipo": m.tipo.value,
            "entrada_uds": m.cantidad if es_entrada else ZERO,
            "salida_uds": ZERO if es_entrada else m.cantidad,
            "costo_unitario": m.costo_unitario,
            "costo_movimiento": m.costo_total,
            "saldo_unidades": m.saldo_unidades,
            "saldo_valor": m.saldo_valor,
            "costo_promedio": costo_promedio(m.saldo_unidades, m.saldo_valor),
            "asiento_id": m.asiento_id,
        })

    return {
        "articulo": {
            "id": art.id,
            "codigo_sku": art.codigo_sku,
            "descripcion": art.descripcion,
            "tipo": art.tipo.value,
            "unidad_medida": art.unidad_medida,
            "cuenta_inventario": art.cuenta_inventario,
            "cuenta_costo": art.cuenta_costo,
            "metodo": "Promedio Ponderado",
        },
        "movimientos": filas,
        "saldo_final_unidades": filas[-1]["saldo_unidades"] if filas else ZERO,
        "saldo_final_valor": filas[-1]["saldo_valor"] if filas else ZERO,
    }


@router.get("/saldo")
async def saldo_inventario(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resumen del inventario: unidades y VALOR reales por artículo y totales.
    El valor sale del saldo_valor del último movimiento de cada artículo."""
    # Último movimiento por artículo (id máximo)
    sub = (
        select(
            MovimientoInventario.articulo_id.label("aid"),
            func.max(MovimientoInventario.id).label("mid"),
        )
        .where(MovimientoInventario.empresa_id == current_user.empresa_id)
        .group_by(MovimientoInventario.articulo_id)
        .subquery()
    )
    q = (
        select(ArticuloInventario, MovimientoInventario)
        .join(sub, sub.c.aid == ArticuloInventario.id, isouter=True)
        .join(MovimientoInventario, MovimientoInventario.id == sub.c.mid, isouter=True)
        .where(ArticuloInventario.empresa_id == current_user.empresa_id)
        .order_by(ArticuloInventario.descripcion)
    )
    rows = (await db.execute(q)).all()

    detalle = []
    total_uds = ZERO
    total_val = ZERO
    for art, mov in rows:
        uds = mov.saldo_unidades if mov else ZERO
        val = mov.saldo_valor if mov else ZERO
        total_uds += uds
        total_val += val
        detalle.append({
            "articulo_id": art.id,
            "codigo_sku": art.codigo_sku,
            "descripcion": art.descripcion,
            "tipo": art.tipo.value,
            "saldo_unidades": float(uds),
            "saldo_valor": float(val),
            "costo_promedio": float(costo_promedio(uds, val)),
        })

    return {
        "total_articulos": len(detalle),
        "total_unidades": float(total_uds),
        "total_valor": float(total_val),
        "detalle": detalle,
    }
