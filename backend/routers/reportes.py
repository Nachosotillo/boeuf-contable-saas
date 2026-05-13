"""
Router: Reportes Contables
- Balance de Comprobación
- Balance Ajustado (BC + Ajustes)
- Mayor General
- Estado de Resultados
- Estado de Situación Financiera
"""

from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from collections import defaultdict

from database import get_db
from models import Asiento, LineaAsiento, Ajuste, LineaAjuste, CatalogoCuenta, Usuario
from schemas import (
    BalanceComprobacionOut, LineaBalanceOut,
    BalanceAjustadoOut, LineaBalanceAjustadoOut,
    MayorGeneralOut, LineaMayorOut,
    EstadoResultadoOut, SituacionFinancieraOut
)
from routers.auth import get_current_user

router = APIRouter()

ZERO = Decimal("0.00")


async def _get_saldos_bc(empresa_id: int, mes: int | None, db: AsyncSession) -> dict:
    """Calcula saldos del Diario General por cuenta."""
    q = (
        select(LineaAsiento, CatalogoCuenta)
        .join(Asiento, LineaAsiento.asiento_id == Asiento.id)
        .join(CatalogoCuenta, LineaAsiento.cuenta_id == CatalogoCuenta.id)
        .where(Asiento.empresa_id == empresa_id)
    )
    if mes:
        q = q.where(Asiento.mes == mes)
    result = await db.execute(q)
    rows = result.all()

    saldos = defaultdict(lambda: {"cuenta": None, "debe": ZERO, "haber": ZERO})
    for linea, cuenta in rows:
        s = saldos[cuenta.codigo]
        s["cuenta"] = cuenta
        s["debe"] += linea.debe
        s["haber"] += linea.haber
    return saldos


async def _get_saldos_ajustes(empresa_id: int, mes: int | None, db: AsyncSession) -> dict:
    """Calcula saldos de los Ajustes por cuenta."""
    q = (
        select(LineaAjuste, CatalogoCuenta)
        .join(Ajuste, LineaAjuste.ajuste_id == Ajuste.id)
        .join(CatalogoCuenta, LineaAjuste.cuenta_id == CatalogoCuenta.id)
        .where(Ajuste.empresa_id == empresa_id)
    )
    if mes:
        q = q.where(Ajuste.mes == mes)
    result = await db.execute(q)
    rows = result.all()

    saldos = defaultdict(lambda: {"cuenta": None, "debe": ZERO, "haber": ZERO})
    for linea, cuenta in rows:
        s = saldos[cuenta.codigo]
        s["cuenta"] = cuenta
        s["debe"] += linea.debe
        s["haber"] += linea.haber
    return saldos


@router.get("/balance-comprobacion", response_model=BalanceComprobacionOut)
async def balance_comprobacion(
    mes: int | None = Query(None, ge=1, le=12, description="Filtrar por mes (0 = todos)"),
    anio: int | None = Query(None),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    saldos_bc = await _get_saldos_bc(current_user.empresa_id, mes, db)
    saldos_aj = await _get_saldos_ajustes(current_user.empresa_id, mes, db)

    # Combinar BC + Ajustes
    all_codes = set(list(saldos_bc.keys()) + list(saldos_aj.keys()))
    lineas = []
    total_debe = ZERO
    total_haber = ZERO

    for codigo in sorted(all_codes):
        bc = saldos_bc.get(codigo, {"cuenta": None, "debe": ZERO, "haber": ZERO})
        aj = saldos_aj.get(codigo, {"cuenta": None, "debe": ZERO, "haber": ZERO})
        cuenta = bc["cuenta"] or aj["cuenta"]
        debe = bc["debe"] + aj["debe"]
        haber = bc["haber"] + aj["haber"]
        total_debe += debe
        total_haber += haber
        lineas.append(LineaBalanceOut(
            codigo=codigo,
            nombre=cuenta.nombre if cuenta else codigo,
            debe=debe,
            haber=haber,
        ))

    return BalanceComprobacionOut(
        periodo=f"Mes {mes}" if mes else "Acumulado",
        lineas=lineas,
        total_debe=total_debe,
        total_haber=total_haber,
        cuadra=abs(total_debe - total_haber) <= Decimal("0.01"),
    )


@router.get("/balance-ajustado", response_model=BalanceAjustadoOut)
async def balance_ajustado(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    saldos_bc = await _get_saldos_bc(current_user.empresa_id, mes, db)
    saldos_aj = await _get_saldos_ajustes(current_user.empresa_id, mes, db)

    all_codes = set(list(saldos_bc.keys()) + list(saldos_aj.keys()))
    lineas = []
    total_deudor = ZERO
    total_acreedor = ZERO

    for codigo in sorted(all_codes):
        bc = saldos_bc.get(codigo, {"cuenta": None, "debe": ZERO, "haber": ZERO})
        aj = saldos_aj.get(codigo, {"cuenta": None, "debe": ZERO, "haber": ZERO})
        cuenta = bc["cuenta"] or aj["cuenta"]

        debe_total = bc["debe"] + aj["debe"]
        haber_total = bc["haber"] + aj["haber"]

        if debe_total > haber_total:
            saldo_deudor = debe_total - haber_total
            saldo_acreedor = ZERO
        else:
            saldo_deudor = ZERO
            saldo_acreedor = haber_total - debe_total

        total_deudor += saldo_deudor
        total_acreedor += saldo_acreedor

        lineas.append(LineaBalanceAjustadoOut(
            codigo=codigo,
            nombre=cuenta.nombre if cuenta else codigo,
            debe_bc=bc["debe"],
            haber_bc=bc["haber"],
            ajuste_debe=aj["debe"],
            ajuste_haber=aj["haber"],
            saldo_ajustado_deudor=saldo_deudor,
            saldo_ajustado_acreedor=saldo_acreedor,
        ))

    return BalanceAjustadoOut(
        periodo=f"Mes {mes}" if mes else "Acumulado",
        lineas=lineas,
        total_deudor=total_deudor,
        total_acreedor=total_acreedor,
        cuadra=abs(total_deudor - total_acreedor) <= Decimal("0.01"),
    )


@router.get("/mayor-general", response_model=MayorGeneralOut)
async def mayor_general(
    cuenta_codigo: str = Query(..., description="Código de cuenta, ej: 1.1.03"),
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verificar que la cuenta existe para esta empresa
    res = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.empresa_id == current_user.empresa_id,
            CatalogoCuenta.codigo == cuenta_codigo,
        )
    )
    cuenta = res.scalar_one_or_none()
    if not cuenta:
        from fastapi import HTTPException
        raise HTTPException(404, detail=f"Cuenta {cuenta_codigo} no encontrada")

    # Movimientos del Diario
    q = (
        select(LineaAsiento, Asiento)
        .join(Asiento, LineaAsiento.asiento_id == Asiento.id)
        .where(
            Asiento.empresa_id == current_user.empresa_id,
            LineaAsiento.cuenta_id == cuenta.id,
        )
        .order_by(Asiento.fecha, Asiento.numero_asiento)
    )
    if mes:
        q = q.where(Asiento.mes == mes)
    result = await db.execute(q)
    rows_diario = result.all()

    # Movimientos de Ajustes
    q2 = (
        select(LineaAjuste, Ajuste)
        .join(Ajuste, LineaAjuste.ajuste_id == Ajuste.id)
        .where(
            Ajuste.empresa_id == current_user.empresa_id,
            LineaAjuste.cuenta_id == cuenta.id,
        )
        .order_by(Ajuste.fecha, Ajuste.numero_ajuste)
    )
    if mes:
        q2 = q2.where(Ajuste.mes == mes)
    result2 = await db.execute(q2)
    rows_ajuste = result2.all()

    # Combinar y ordenar por fecha
    all_movs = []
    for linea, asiento in rows_diario:
        all_movs.append({
            "fecha": asiento.fecha,
            "numero": asiento.numero_asiento,
            "desc": asiento.descripcion,
            "debe": linea.debe,
            "haber": linea.haber,
        })
    for linea, ajuste in rows_ajuste:
        all_movs.append({
            "fecha": ajuste.fecha,
            "numero": ajuste.numero_ajuste,
            "desc": ajuste.descripcion,
            "debe": linea.debe,
            "haber": linea.haber,
        })
    all_movs.sort(key=lambda x: (x["fecha"], x["numero"]))

    saldo = ZERO
    total_debe = ZERO
    total_haber = ZERO
    lineas_out = []

    for m in all_movs:
        saldo += m["debe"] - m["haber"]
        total_debe += m["debe"]
        total_haber += m["haber"]
        lineas_out.append(LineaMayorOut(
            fecha=m["fecha"],
            numero_asiento=m["numero"],
            descripcion=m["desc"],
            debe=m["debe"],
            haber=m["haber"],
            saldo_acumulado=saldo,
        ))

    return MayorGeneralOut(
        cuenta_codigo=cuenta.codigo,
        cuenta_nombre=cuenta.nombre,
        lineas=lineas_out,
        total_debe=total_debe,
        total_haber=total_haber,
        saldo_final=total_debe - total_haber,
    )


@router.get("/estado-resultado", response_model=EstadoResultadoOut)
async def estado_resultado(
    mes: int | None = Query(None, ge=1, le=12),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    saldos = await _get_saldos_bc(current_user.empresa_id, mes, db)
    saldos_aj = await _get_saldos_ajustes(current_user.empresa_id, mes, db)

    ingresos = {}
    costo_ventas = ZERO
    gastos = {}

    for codigo in set(list(saldos.keys()) + list(saldos_aj.keys())):
        bc = saldos.get(codigo, {"cuenta": None, "debe": ZERO, "haber": ZERO})
        aj = saldos_aj.get(codigo, {"cuenta": None, "debe": ZERO, "haber": ZERO})
        cuenta = bc["cuenta"] or aj["cuenta"]
        if not cuenta or not cuenta.estado_financiero:
            continue
        if cuenta.estado_financiero.value != "Estado de Resultado":
            continue

        haber = bc["haber"] + aj["haber"]
        debe = bc["debe"] + aj["debe"]

        if codigo.startswith("4."):
            ingresos[cuenta.nombre] = haber
        elif codigo.startswith("5."):
            costo_ventas += debe
        elif codigo.startswith("6."):
            gastos[cuenta.nombre] = debe

    total_ingresos = sum(ingresos.values())
    total_gastos = sum(gastos.values())
    utilidad_bruta = total_ingresos - costo_ventas
    utilidad_neta = utilidad_bruta - total_gastos

    return EstadoResultadoOut(
        ingresos=ingresos,
        costo_ventas=costo_ventas,
        gastos_operativos=gastos,
        utilidad_bruta=utilidad_bruta,
        utilidad_neta=utilidad_neta,
    )


@router.get("/situacion-financiera", response_model=SituacionFinancieraOut)
async def situacion_financiera(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Balance general acumulado (sin filtro de mes)."""
    saldos_bc = await _get_saldos_bc(current_user.empresa_id, None, db)
    saldos_aj = await _get_saldos_ajustes(current_user.empresa_id, None, db)

    def saldo_neto(codigo: str) -> Decimal:
        bc = saldos_bc.get(codigo, {"debe": ZERO, "haber": ZERO})
        aj = saldos_aj.get(codigo, {"debe": ZERO, "haber": ZERO})
        return (bc["debe"] + aj["debe"]) - (bc["haber"] + aj["haber"])

    # Activo Corriente
    ac = {
        "Caja":                    max(ZERO, saldo_neto("1.1.01")),
        "Caja Chica":              max(ZERO, saldo_neto("1.1.02")),
        "Banco BDV":               max(ZERO, saldo_neto("1.1.03")),
        "Banco Mercantil":         max(ZERO, saldo_neto("1.1.04")),
        "Cuentas x Cobrar":        max(ZERO, saldo_neto("1.1.10")),
        "IVA Crédito Fiscal":      max(ZERO, saldo_neto("1.1.15")),
        "Ret. IVA x Recuperar":    max(ZERO, saldo_neto("1.1.16")),
        "Ret. ISLR x Recuperar":   max(ZERO, saldo_neto("1.1.17")),
        "Inventario MP":           max(ZERO, saldo_neto("1.1.20")),
        "Inventario PT":           max(ZERO, saldo_neto("1.1.22")),
        "Seguros Anticipados":     max(ZERO, saldo_neto("1.1.31")),
    }
    total_ac = sum(ac.values())

    # Activo No Corriente (Neto)
    anc = {
        "Maquinaria (Neto)":      saldo_neto("1.2.05") + saldo_neto("1.2.06"),
        "Vehículos (Neto)":       saldo_neto("1.2.10") + saldo_neto("1.2.11"),
        "Refrigeración (Neto)":   saldo_neto("1.2.08") + saldo_neto("1.2.09"),
        "Equipos Cómputo":        max(ZERO, saldo_neto("1.2.12")),
        "Mobiliario":             max(ZERO, saldo_neto("1.2.15")),
    }
    total_anc = sum(v for v in anc.values() if v > 0)
    total_activos = total_ac + total_anc

    # Pasivo Corriente
    pc = {
        "Ctas x Pagar Prov.":    abs(min(ZERO, saldo_neto("2.1.01"))),
        "IVA Débito Fiscal":      abs(min(ZERO, saldo_neto("2.1.05"))),
        "Ret. ISLR x Pagar":      abs(min(ZERO, saldo_neto("2.1.07"))),
        "IGTF x Enterar":         abs(min(ZERO, saldo_neto("2.1.10"))),
        "SSO/FAOV/INCES x Pagar": abs(min(ZERO, saldo_neto("2.1.11"))),
        "Pensiones x Pagar":      abs(min(ZERO, saldo_neto("2.1.12"))),
        "Prov. Utilidades":       abs(min(ZERO, saldo_neto("2.1.15"))),
        "Prov. Vacaciones":       abs(min(ZERO, saldo_neto("2.1.16"))),
        "Nómina x Pagar":         abs(min(ZERO, saldo_neto("2.1.20"))),
    }
    total_pasivos = sum(pc.values())

    # Patrimonio
    pat = {
        "Capital Social":  abs(min(ZERO, saldo_neto("3.1.01"))),
        "Reserva Legal":   abs(min(ZERO, saldo_neto("3.1.02"))),
    }
    total_patrimonio = sum(pat.values())

    return SituacionFinancieraOut(
        activo_corriente=ac,
        activo_no_corriente=anc,
        total_activos=total_activos,
        pasivo_corriente=pc,
        total_pasivos=total_pasivos,
        patrimonio=pat,
        total_patrimonio=total_patrimonio,
        ecuacion_cuadra=abs(total_activos - (total_pasivos + total_patrimonio)) <= Decimal("1.00"),
    )
