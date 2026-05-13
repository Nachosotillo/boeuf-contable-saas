"""
routers/iva.py — Libros IVA Compras y Ventas con cálculo automático
"""
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import LibroIvaCompra, LibroIvaVenta, Usuario
from schemas import (LibroIvaCompraCreate, LibroIvaCompraOut,
                     LibroIvaVentaCreate, LibroIvaVentaOut, LiquidacionIvaOut)
from routers.auth import get_current_user, require_roles

router = APIRouter()
R = lambda v: Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)


@router.post("/compras", response_model=LibroIvaCompraOut, status_code=201)
async def registrar_compra_iva(
    data: LibroIvaCompraCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_compras")),
    db: AsyncSession = Depends(get_db)
):
    base = data.base_imponible
    iva = R(base * data.alicuota_iva)
    ret_75 = R(iva * Decimal("0.75")) if data.cliente_es_spe else Decimal("0")
    neto = R(iva - ret_75)
    igtf = R(base * Decimal("0.03")) if data.paga_en_divisas else Decimal("0")
    total = R(base + iva + igtf)

    obj = LibroIvaCompra(
        empresa_id=current_user.empresa_id,
        fecha=data.fecha,
        numero_factura=data.numero_factura,
        proveedor=data.proveedor,
        rif_proveedor=data.rif_proveedor,
        base_imponible=base,
        alicuota_iva=data.alicuota_iva,
        iva_credito_fiscal=iva,
        retencion_iva_75=ret_75,
        iva_neto_pagado=neto,
        igtf_aplicado=igtf,
        total_factura=total,
    )
    db.add(obj)
    await db.flush()
    return LibroIvaCompraOut.model_validate(obj)


@router.post("/ventas", response_model=LibroIvaVentaOut, status_code=201)
async def registrar_venta_iva(
    data: LibroIvaVentaCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_ventas")),
    db: AsyncSession = Depends(get_db)
):
    base = data.base_imponible
    iva = R(base * data.alicuota_iva)
    ret_recibida = R(iva * Decimal("0.75")) if data.cliente_es_spe else Decimal("0")
    neto = R(iva - ret_recibida)
    total = R(base + iva)

    obj = LibroIvaVenta(
        empresa_id=current_user.empresa_id,
        fecha=data.fecha,
        numero_factura=data.numero_factura,
        cliente=data.cliente,
        rif_cliente=data.rif_cliente,
        base_imponible=base,
        alicuota_iva=data.alicuota_iva,
        iva_debito_fiscal=iva,
        retencion_iva_recibida=ret_recibida,
        iva_neto_cobrado=neto,
        igtf_percibido=Decimal("0"),
        total_factura=total,
        cliente_es_spe=data.cliente_es_spe,
    )
    db.add(obj)
    await db.flush()
    return LibroIvaVentaOut.model_validate(obj)


@router.get("/compras", response_model=list[LibroIvaCompraOut])
async def listar_compras(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    q = select(LibroIvaCompra).where(LibroIvaCompra.empresa_id == current_user.empresa_id)
    if mes:
        from sqlalchemy import extract
        q = q.where(extract("month", LibroIvaCompra.fecha) == mes)
    result = await db.execute(q.order_by(LibroIvaCompra.fecha))
    return [LibroIvaCompraOut.model_validate(r) for r in result.scalars().all()]


@router.get("/ventas", response_model=list[LibroIvaVentaOut])
async def listar_ventas(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    q = select(LibroIvaVenta).where(LibroIvaVenta.empresa_id == current_user.empresa_id)
    if mes:
        from sqlalchemy import extract
        q = q.where(extract("month", LibroIvaVenta.fecha) == mes)
    result = await db.execute(q.order_by(LibroIvaVenta.fecha))
    return [LibroIvaVentaOut.model_validate(r) for r in result.scalars().all()]


@router.get("/liquidacion", response_model=LiquidacionIvaOut)
async def liquidacion_iva(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import extract, func
    def filtro_mes(model, campo):
        q = select(func.sum(campo)).where(model.empresa_id == current_user.empresa_id)
        if mes:
            q = q.where(extract("month", model.fecha) == mes)
        return q

    df = (await db.execute(filtro_mes(LibroIvaVenta, LibroIvaVenta.iva_debito_fiscal))).scalar() or 0
    cf = (await db.execute(filtro_mes(LibroIvaCompra, LibroIvaCompra.iva_credito_fiscal))).scalar() or 0
    rr = (await db.execute(filtro_mes(LibroIvaVenta, LibroIvaVenta.retencion_iva_recibida))).scalar() or 0

    neto = Decimal(str(df)) - Decimal(str(cf)) - Decimal(str(rr))
    return LiquidacionIvaOut(
        iva_debito_fiscal=Decimal(str(df)),
        iva_credito_fiscal=Decimal(str(cf)),
        retenciones_recibidas=Decimal(str(rr)),
        iva_neto=abs(neto),
        tipo="A_PAGAR" if neto >= 0 else "A_FAVOR",
    )
