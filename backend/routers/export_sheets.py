"""
routers/export_sheets.py — Exportación de libros y catálogo a CSV (para Google Sheets).

Cada endpoint devuelve un CSV (UTF-8 con BOM) que Sheets importa directo
(Archivo → Importar) o vía Apps Script / n8n con el token del usuario.

  GET /export/catalogo.csv
  GET /export/diario.csv?mes=&incluir_prueba=
  GET /export/mayor.csv?mes=&cuenta=
  GET /export/balance.csv?mes=
  GET /export/compras.csv?mes=     (formato SENIAT)
  GET /export/ventas.csv?mes=      (formato SENIAT)
"""
import csv, io
from decimal import Decimal
from collections import defaultdict

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import (Asiento, LineaAsiento, CatalogoCuenta, Usuario,
                    LibroIvaCompra, LibroIvaVenta)
from routers.auth import get_current_user

router = APIRouter()
ZERO = Decimal("0.00")


def _csv(filename: str, headers: list[str], rows: list[list]) -> Response:
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM → Sheets/Excel leen acentos
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(["" if c is None else (f"{c:.2f}" if isinstance(c, Decimal) else c) for c in r])
    return Response(
        content=buf.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


async def _lineas_diario(empresa_id, mes, incluir_prueba, db):
    q = (select(LineaAsiento, Asiento, CatalogoCuenta)
         .join(Asiento, LineaAsiento.asiento_id == Asiento.id)
         .join(CatalogoCuenta, LineaAsiento.cuenta_id == CatalogoCuenta.id)
         .where(Asiento.empresa_id == empresa_id)
         .order_by(Asiento.fecha, Asiento.numero_asiento, LineaAsiento.id))
    if mes:
        q = q.where(Asiento.mes == mes)
    if not incluir_prueba:
        q = q.where(Asiento.es_prueba == False)
    return (await db.execute(q)).all()


@router.get("/catalogo.csv")
async def export_catalogo(
    solo_activas: bool = Query(True),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(CatalogoCuenta).where(CatalogoCuenta.empresa_id == current_user.empresa_id)
    if solo_activas:
        q = q.where(CatalogoCuenta.activa == True)
    cuentas = (await db.execute(q.order_by(CatalogoCuenta.codigo))).scalars().all()
    rows = [[c.codigo, c.nombre, c.tipo.value if c.tipo else "",
             c.naturaleza.value if c.naturaleza else "",
             c.estado_financiero.value if c.estado_financiero else "",
             c.subcategoria or "", "Sí" if c.activa else "No"] for c in cuentas]
    return _csv("catalogo_cuentas.csv",
                ["Código", "Cuenta", "Tipo", "Naturaleza", "Estado Financiero", "Subcategoría", "Activa"],
                rows)


@router.get("/diario.csv")
async def export_diario(
    mes: int | None = Query(None, ge=1, le=12),
    incluir_prueba: bool = Query(False),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filas = await _lineas_diario(current_user.empresa_id, mes, incluir_prueba, db)
    rows = []
    for ln, a, c in filas:
        rows.append([a.fecha.isoformat(), a.numero_asiento, a.origen.value if a.origen else "",
                     c.codigo, c.nombre, ln.descripcion or a.descripcion or "",
                     ln.numero_factura or "", ln.debe, ln.haber])
    return _csv("libro_diario.csv",
                ["Fecha", "N° Asiento", "Origen", "Código", "Cuenta", "Descripción",
                 "N° Factura", "Débito", "Crédito"], rows)


@router.get("/mayor.csv")
async def export_mayor(
    mes: int | None = Query(None, ge=1, le=12),
    cuenta: str | None = Query(None, description="Filtra un código; vacío = todas"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filas = await _lineas_diario(current_user.empresa_id, mes, False, db)
    # Agrupar por cuenta, ordenar y arrastrar saldo
    por_cuenta = defaultdict(list)
    for ln, a, c in filas:
        if cuenta and c.codigo != cuenta:
            continue
        por_cuenta[(c.codigo, c.nombre)].append((a, ln))
    rows = []
    for (cod, nom) in sorted(por_cuenta.keys()):
        saldo = ZERO
        for a, ln in por_cuenta[(cod, nom)]:
            saldo += ln.debe - ln.haber
            rows.append([cod, nom, a.fecha.isoformat(), a.numero_asiento,
                         ln.descripcion or a.descripcion or "", ln.debe, ln.haber, saldo])
        rows.append([cod, nom, "", "", "TOTAL CUENTA", None, None, saldo])
    return _csv("libro_mayor.csv",
                ["Código", "Cuenta", "Fecha", "N° Asiento", "Descripción", "Débito", "Crédito", "Saldo"], rows)


@router.get("/balance.csv")
async def export_balance(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filas = await _lineas_diario(current_user.empresa_id, mes, False, db)
    acum = defaultdict(lambda: {"nom": "", "debe": ZERO, "haber": ZERO})
    for ln, a, c in filas:
        s = acum[c.codigo]; s["nom"] = c.nombre
        s["debe"] += ln.debe; s["haber"] += ln.haber
    rows = []; td = th = sd = sa = ZERO
    for cod in sorted(acum.keys()):
        s = acum[cod]; debe, haber = s["debe"], s["haber"]
        deudor = debe - haber if debe > haber else ZERO
        acreedor = haber - debe if haber > debe else ZERO
        td += debe; th += haber; sd += deudor; sa += acreedor
        rows.append([cod, s["nom"], debe, haber, deudor, acreedor])
    rows.append(["", "TOTALES", td, th, sd, sa])
    return _csv("balance_comprobacion.csv",
                ["Código", "Cuenta", "Débitos", "Créditos", "Saldo Deudor", "Saldo Acreedor"], rows)


@router.get("/compras.csv")
async def export_compras(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(LibroIvaCompra).where(LibroIvaCompra.empresa_id == current_user.empresa_id)
    if mes:
        from sqlalchemy import extract
        q = q.where(extract("month", LibroIvaCompra.fecha) == mes)
    regs = (await db.execute(q.order_by(LibroIvaCompra.fecha, LibroIvaCompra.id))).scalars().all()
    rows = [[r.fecha.isoformat(), r.numero_factura, r.rif_proveedor, r.proveedor,
             r.base_imponible, r.alicuota_iva, r.iva_credito_fiscal,
             r.retencion_iva_75, r.igtf_aplicado, r.total_factura] for r in regs]
    return _csv("libro_compras_seniat.csv",
                ["Fecha", "N° Factura", "RIF Proveedor", "Proveedor", "Base Imponible",
                 "Alícuota", "IVA Crédito Fiscal", "Retención 75%", "IGTF", "Total"], rows)


@router.get("/ventas.csv")
async def export_ventas(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(LibroIvaVenta).where(LibroIvaVenta.empresa_id == current_user.empresa_id)
    if mes:
        from sqlalchemy import extract
        q = q.where(extract("month", LibroIvaVenta.fecha) == mes)
    regs = (await db.execute(q.order_by(LibroIvaVenta.fecha, LibroIvaVenta.id))).scalars().all()
    rows = [[r.fecha.isoformat(), r.numero_factura, r.rif_cliente, r.cliente,
             r.base_imponible, r.alicuota_iva, r.iva_debito_fiscal,
             r.retencion_iva_recibida, r.total_factura] for r in regs]
    return _csv("libro_ventas_seniat.csv",
                ["Fecha", "N° Factura", "RIF Cliente", "Cliente", "Base Imponible",
                 "Alícuota", "IVA Débito Fiscal", "Retención Recibida", "Total"], rows)
