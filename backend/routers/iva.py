"""
routers/iva.py — Libros de IVA Compras y Ventas con asiento contable automático.

Cada registro, en UNA sola transacción:
  (a) crea la fila del Libro de IVA (Compras o Ventas) con sus cálculos, y
  (b) genera el asiento de Diario correspondiente (origen=compra/venta),
quedando enlazados por libro.asiento_id. Así el Libro y el Diario nunca se
desincronizan, y la exportación del Libro de Compras/Ventas (Paso E) sale de
esta misma data.

ASIENTO DE COMPRA
  DEBE  cuenta_debito (base)  ·  1.1.15 IVA Crédito Fiscal  ·  6.3.06 IGTF (si divisas)
  HABER cuenta_pago (total - retención)  ·  2.1.06 Retención IVA por Enterar (si la empresa retiene)

ASIENTO DE VENTA
  DEBE  cuenta_cobro (total - retención)  ·  1.1.16 Retención IVA por Recuperar (si el cliente retiene)
  HABER cuenta_venta (base)  ·  2.1.05 IVA Débito Fiscal
"""
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, extract, func

from database import get_db
from models import LibroIvaCompra, LibroIvaVenta, Usuario, OrigenAsientoEnum
from schemas import (LibroIvaCompraCreate, LibroIvaCompraOut,
                     LibroIvaVentaCreate, LibroIvaVentaOut, LiquidacionIvaOut)
from routers.auth import get_current_user, require_roles
from routers.asientos import crear_asiento_interno

router = APIRouter()
R = lambda v: Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)
ZERO = Decimal("0")

C_IVA_CF   = "1.1.15"   # IVA Crédito Fiscal (compras)
C_IVA_DF   = "2.1.05"   # IVA Débito Fiscal (ventas)
C_IGTF_CMP = "6.3.06"   # IGTF - gasto en compras en divisas
C_RET_ENT  = "2.1.06"   # Retenciones de IVA por Enterar (la empresa retiene)
C_RET_REC  = "1.1.16"   # Retenciones de IVA por Recuperar (al cliente retener)


@router.post("/compras", response_model=LibroIvaCompraOut, status_code=201)
async def registrar_compra_iva(
    data: LibroIvaCompraCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_compras")),
    db: AsyncSession = Depends(get_db),
):
    base   = data.base_imponible
    iva    = R(base * data.alicuota_iva)
    ret_75 = R(iva * Decimal("0.75")) if data.cliente_es_spe else ZERO
    neto   = R(iva - ret_75)
    igtf   = R(base * Decimal("0.03")) if data.paga_en_divisas else ZERO
    total  = R(base + iva + igtf)

    asiento_id = None
    if data.generar_asiento:
        lineas = [
            {"cuenta_codigo": data.cuenta_debito, "debe": base, "haber": 0,
             "descripcion": "Compra (base imponible)", "numero_factura": data.numero_factura},
            {"cuenta_codigo": C_IVA_CF, "debe": iva, "haber": 0,
             "descripcion": "IVA crédito fiscal", "numero_factura": data.numero_factura},
        ]
        if igtf > 0:
            lineas.append({"cuenta_codigo": C_IGTF_CMP, "debe": igtf, "haber": 0,
                           "descripcion": "IGTF 3% pago en divisas"})
        lineas.append({"cuenta_codigo": data.cuenta_pago, "debe": 0, "haber": R(total - ret_75),
                       "descripcion": "Pago / cuenta por pagar", "numero_factura": data.numero_factura})
        if ret_75 > 0:
            lineas.append({"cuenta_codigo": C_RET_ENT, "debe": 0, "haber": ret_75,
                           "descripcion": "Retención IVA 75% por enterar"})

        asiento = await crear_asiento_interno(
            db, empresa_id=current_user.empresa_id, usuario_id=current_user.id,
            fecha=data.fecha, origen=OrigenAsientoEnum.compra,
            descripcion=f"Compra a {data.proveedor} - Fact. {data.numero_factura}",
            referencia=f"COMP-{data.numero_factura}", lineas=lineas)
        asiento_id = asiento.id

    obj = LibroIvaCompra(
        empresa_id=current_user.empresa_id, fecha=data.fecha,
        numero_factura=data.numero_factura, proveedor=data.proveedor,
        rif_proveedor=data.rif_proveedor, base_imponible=base,
        alicuota_iva=data.alicuota_iva, iva_credito_fiscal=iva,
        retencion_iva_75=ret_75, iva_neto_pagado=neto, igtf_aplicado=igtf,
        total_factura=total, asiento_id=asiento_id,
    )
    db.add(obj)
    await db.flush()
    await db.commit()
    await db.refresh(obj)
    return LibroIvaCompraOut.model_validate(obj)


@router.post("/ventas", response_model=LibroIvaVentaOut, status_code=201)
async def registrar_venta_iva(
    data: LibroIvaVentaCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_ventas")),
    db: AsyncSession = Depends(get_db),
):
    base         = data.base_imponible
    iva          = R(base * data.alicuota_iva)
    ret_recibida = R(iva * Decimal("0.75")) if data.cliente_es_spe else ZERO
    neto         = R(iva - ret_recibida)
    total        = R(base + iva)

    asiento_id = None
    if data.generar_asiento:
        if not data.cuenta_venta:
            raise HTTPException(422, "cuenta_venta es obligatoria para generar el asiento (ej. 4.1.01.01).")
        lineas = [
            {"cuenta_codigo": data.cuenta_cobro, "debe": R(total - ret_recibida), "haber": 0,
             "descripcion": "Cobro / cuenta por cobrar", "numero_factura": data.numero_factura},
        ]
        if ret_recibida > 0:
            lineas.append({"cuenta_codigo": C_RET_REC, "debe": ret_recibida, "haber": 0,
                           "descripcion": "Retención IVA soportada por recuperar"})
        lineas += [
            {"cuenta_codigo": data.cuenta_venta, "debe": 0, "haber": base,
             "descripcion": "Venta (ingreso)", "numero_factura": data.numero_factura},
            {"cuenta_codigo": C_IVA_DF, "debe": 0, "haber": iva,
             "descripcion": "IVA débito fiscal", "numero_factura": data.numero_factura},
        ]
        asiento = await crear_asiento_interno(
            db, empresa_id=current_user.empresa_id, usuario_id=current_user.id,
            fecha=data.fecha, origen=OrigenAsientoEnum.venta,
            descripcion=f"Venta a {data.cliente} - Fact. {data.numero_factura}",
            referencia=f"VENT-{data.numero_factura}", lineas=lineas)
        asiento_id = asiento.id

    obj = LibroIvaVenta(
        empresa_id=current_user.empresa_id, fecha=data.fecha,
        numero_factura=data.numero_factura, cliente=data.cliente,
        rif_cliente=data.rif_cliente, base_imponible=base,
        alicuota_iva=data.alicuota_iva, iva_debito_fiscal=iva,
        retencion_iva_recibida=ret_recibida, iva_neto_cobrado=neto,
        igtf_percibido=ZERO, total_factura=total,
        cliente_es_spe=data.cliente_es_spe, asiento_id=asiento_id,
    )
    db.add(obj)
    await db.flush()
    await db.commit()
    await db.refresh(obj)
    return LibroIvaVentaOut.model_validate(obj)


@router.get("/compras", response_model=list[LibroIvaCompraOut])
async def listar_compras(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(LibroIvaCompra).where(LibroIvaCompra.empresa_id == current_user.empresa_id)
    if mes:
        q = q.where(extract("month", LibroIvaCompra.fecha) == mes)
    res = await db.execute(q.order_by(LibroIvaCompra.fecha, LibroIvaCompra.id))
    return [LibroIvaCompraOut.model_validate(r) for r in res.scalars().all()]


@router.get("/ventas", response_model=list[LibroIvaVentaOut])
async def listar_ventas(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(LibroIvaVenta).where(LibroIvaVenta.empresa_id == current_user.empresa_id)
    if mes:
        q = q.where(extract("month", LibroIvaVenta.fecha) == mes)
    res = await db.execute(q.order_by(LibroIvaVenta.fecha, LibroIvaVenta.id))
    return [LibroIvaVentaOut.model_validate(r) for r in res.scalars().all()]


@router.get("/liquidacion", response_model=LiquidacionIvaOut)
async def liquidacion_iva(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    def suma(model, campo):
        q = select(func.sum(campo)).where(model.empresa_id == current_user.empresa_id)
        if mes:
            q = q.where(extract("month", model.fecha) == mes)
        return q

    df = (await db.execute(suma(LibroIvaVenta, LibroIvaVenta.iva_debito_fiscal))).scalar() or 0
    cf = (await db.execute(suma(LibroIvaCompra, LibroIvaCompra.iva_credito_fiscal))).scalar() or 0
    rr = (await db.execute(suma(LibroIvaVenta, LibroIvaVenta.retencion_iva_recibida))).scalar() or 0

    neto = Decimal(str(df)) - Decimal(str(cf)) - Decimal(str(rr))
    return LiquidacionIvaOut(
        iva_debito_fiscal=Decimal(str(df)),
        iva_credito_fiscal=Decimal(str(cf)),
        retenciones_recibidas=Decimal(str(rr)),
        iva_neto=abs(neto),
        tipo="A_PAGAR" if neto >= 0 else "A_FAVOR",
    )
