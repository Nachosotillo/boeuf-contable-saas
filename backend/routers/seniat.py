"""
Router: Generador de archivos TXT para SENIAT
- Libro IVA Ventas
- Libro IVA Compras
- Retenciones ISLR (Decreto 1808)
- IGTF
Formato oficial SENIAT — listo para copiar/pegar en portal
"""

from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import LibroIvaCompra, LibroIvaVenta, RetencionIslr, OperacionIgtf, Empresa, Usuario
from routers.auth import get_current_user

router = APIRouter()


async def _get_empresa(empresa_id: int, db: AsyncSession) -> Empresa:
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    return result.scalar_one_or_none()


@router.get("/exportar-iva-ventas", response_class=PlainTextResponse)
async def exportar_iva_ventas(
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(default=date.today().year),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Genera TXT del Libro IVA Ventas para el SENIAT."""
    empresa = await _get_empresa(current_user.empresa_id, db)
    periodo = f"{anio}{str(mes).zfill(2)}"

    result = await db.execute(
        select(LibroIvaVenta).where(
            LibroIvaVenta.empresa_id == current_user.empresa_id,
            LibroIvaVenta.fecha >= date(anio, mes, 1),
            LibroIvaVenta.fecha <= _ultimo_dia(anio, mes),
        ).order_by(LibroIvaVenta.fecha)
    )
    ventas = result.scalars().all()

    lines = [
        f"RIF|{empresa.rif}|{periodo}|LIBRO_IVA_VENTAS",
        f"ENCABEZADO|{empresa.nombre_razon_social}|{empresa.rif}|{periodo}",
    ]

    sum_base = sum_iva = sum_ret = sum_total = 0
    for i, v in enumerate(ventas, 1):
        lines.append(
            f"{i}|{v.fecha}|{v.numero_factura}|{v.cliente}|{v.rif_cliente}"
            f"|{v.base_imponible:.2f}|{float(v.alicuota_iva):.2f}"
            f"|{v.iva_debito_fiscal:.2f}|{v.retencion_iva_recibida:.2f}"
            f"|{v.iva_neto_cobrado:.2f}|{v.igtf_percibido:.2f}|{v.total_factura:.2f}"
        )
        sum_base += float(v.base_imponible)
        sum_iva += float(v.iva_debito_fiscal)
        sum_ret += float(v.retencion_iva_recibida)
        sum_total += float(v.total_factura)

    if not ventas:
        lines.append(f"1|{periodo}|SIN_OPERACIONES|N/A|N/A|0.00|0.16|0.00|0.00|0.00|0.00|0.00")

    iva_neto = sum_iva - sum_ret
    lines.append(f"TOTALES|{len(ventas)}|{sum_base:.2f}|{sum_iva:.2f}|{sum_ret:.2f}|{iva_neto:.2f}|{sum_total:.2f}")
    lines.append(f"IVA_PERIODO|DEBITO|{sum_iva:.2f}")

    txt = "\n".join(lines) + "\n"
    filename = f"SENIAT_IVA_Ventas_{periodo}.txt"
    return PlainTextResponse(
        content=txt,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/exportar-iva-compras", response_class=PlainTextResponse)
async def exportar_iva_compras(
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(default=date.today().year),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Genera TXT del Libro IVA Compras para el SENIAT."""
    empresa = await _get_empresa(current_user.empresa_id, db)
    periodo = f"{anio}{str(mes).zfill(2)}"

    result = await db.execute(
        select(LibroIvaCompra).where(
            LibroIvaCompra.empresa_id == current_user.empresa_id,
            LibroIvaCompra.fecha >= date(anio, mes, 1),
            LibroIvaCompra.fecha <= _ultimo_dia(anio, mes),
        ).order_by(LibroIvaCompra.fecha)
    )
    compras = result.scalars().all()

    lines = [
        f"RIF|{empresa.rif}|{periodo}|LIBRO_IVA_COMPRAS",
        f"ENCABEZADO|{empresa.nombre_razon_social}|{empresa.rif}|{periodo}",
    ]

    sum_base = sum_iva = sum_ret = sum_total = 0
    for i, c in enumerate(compras, 1):
        lines.append(
            f"{i}|{c.fecha}|{c.numero_factura}|{c.proveedor}|{c.rif_proveedor}"
            f"|{c.base_imponible:.2f}|{float(c.alicuota_iva):.2f}"
            f"|{c.iva_credito_fiscal:.2f}|{c.retencion_iva_75:.2f}"
            f"|{c.iva_neto_pagado:.2f}|{c.igtf_aplicado:.2f}|{c.total_factura:.2f}"
        )
        sum_base += float(c.base_imponible)
        sum_iva += float(c.iva_credito_fiscal)
        sum_ret += float(c.retencion_iva_75)
        sum_total += float(c.total_factura)

    if not compras:
        lines.append(f"1|{periodo}|SIN_OPERACIONES|N/A|N/A|0.00|0.16|0.00|0.00|0.00|0.00|0.00")

    lines.append(f"TOTALES|{len(compras)}|{sum_base:.2f}|{sum_iva:.2f}|{sum_ret:.2f}|{sum_total:.2f}")
    lines.append(f"IVA_PERIODO|CREDITO|{sum_iva:.2f}")

    txt = "\n".join(lines) + "\n"
    filename = f"SENIAT_IVA_Compras_{periodo}.txt"
    return PlainTextResponse(
        content=txt,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/exportar-islr", response_class=PlainTextResponse)
async def exportar_islr(
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(default=date.today().year),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Genera TXT de Retenciones ISLR (Decreto 1808) para el SENIAT."""
    empresa = await _get_empresa(current_user.empresa_id, db)
    periodo = f"{anio}{str(mes).zfill(2)}"

    result = await db.execute(
        select(RetencionIslr).where(
            RetencionIslr.empresa_id == current_user.empresa_id,
            RetencionIslr.fecha_pago >= date(anio, mes, 1),
            RetencionIslr.fecha_pago <= _ultimo_dia(anio, mes),
        ).order_by(RetencionIslr.fecha_pago)
    )
    retenciones = result.scalars().all()

    lines = [
        f"RIF|{empresa.rif}|{periodo}|RETENCIONES_ISLR_D1808",
        f"ENCABEZADO|{empresa.nombre_razon_social}|{empresa.rif}|{periodo}",
        f"BASE_LEGAL|Decreto_1808_Art9|Agente_Retencion_PJ",
    ]

    sum_bruto = sum_ret = sum_neto = 0
    for i, r in enumerate(retenciones, 1):
        comprobante = r.numero_comprobante or f"COMP-{periodo}-{str(i).zfill(4)}"
        lines.append(
            f"{i}|{r.fecha_pago}|{r.numero_factura or 'S/N'}|{r.beneficiario_nombre}"
            f"|{r.beneficiario_rif}|{r.concepto}|{float(r.tasa_retencion)*100:.1f}%"
            f"|{r.monto_bruto:.2f}|{r.monto_retenido:.2f}|{r.monto_neto_pagado:.2f}"
            f"|{comprobante}"
        )
        sum_bruto += float(r.monto_bruto)
        sum_ret += float(r.monto_retenido)
        sum_neto += float(r.monto_neto_pagado)

    if not retenciones:
        lines.append(f"1|{periodo}|S/N|SIN_RETENCIONES|N/A|N/A|0%|0.00|0.00|0.00|S/N")

    lines.append(f"TOTALES|{len(retenciones)}|{sum_bruto:.2f}|{sum_ret:.2f}|{sum_neto:.2f}")

    txt = "\n".join(lines) + "\n"
    filename = f"SENIAT_Retenciones_ISLR_{periodo}.txt"
    return PlainTextResponse(
        content=txt,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/exportar-igtf", response_class=PlainTextResponse)
async def exportar_igtf(
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(default=date.today().year),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Genera TXT de declaración IGTF."""
    empresa = await _get_empresa(current_user.empresa_id, db)
    periodo = f"{anio}{str(mes).zfill(2)}"

    result = await db.execute(
        select(OperacionIgtf).where(
            OperacionIgtf.empresa_id == current_user.empresa_id,
            OperacionIgtf.fecha >= date(anio, mes, 1),
            OperacionIgtf.fecha <= _ultimo_dia(anio, mes),
        ).order_by(OperacionIgtf.fecha)
    )
    ops = result.scalars().all()

    lines = [
        f"RIF|{empresa.rif}|{periodo}|IGTF_3PCT",
        f"ENCABEZADO|{empresa.nombre_razon_social}|{empresa.rif}|{periodo}",
        f"BASE_LEGAL|Ley_IGTF_Art24|Alicuota_3pct_Divisas",
    ]

    sum_bs = sum_igtf = 0
    for i, op in enumerate(ops, 1):
        lines.append(
            f"{i}|{op.fecha}|{op.numero_operacion}|{op.cliente_pagador}|{op.rif}"
            f"|{op.moneda}|{op.tasa_bcv:.4f}|{op.monto_divisas:.4f}"
            f"|{op.equivalente_bs:.2f}|{op.igtf_3_pct:.2f}"
        )
        sum_bs += float(op.equivalente_bs)
        sum_igtf += float(op.igtf_3_pct)

    lines.append(f"TOTALES_IGTF|{len(ops)}|{sum_bs:.2f}|{sum_igtf:.2f}")

    txt = "\n".join(lines) + "\n"
    filename = f"SENIAT_IGTF_{periodo}.txt"
    return PlainTextResponse(
        content=txt,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def _ultimo_dia(anio: int, mes: int) -> date:
    from calendar import monthrange
    return date(anio, mes, monthrange(anio, mes)[1])
