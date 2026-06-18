"""
routers/setup.py — Inicialización completa de la clase 2025 en un solo endpoint.

POST /setup/clase-2025  (solo admin) ejecuta, en orden y en una transacción:
  1. Catálogo de cuentas (204 cuentas)         sembrar_catalogo_default
  2. Tasas BCV 2025 (serie diaria)             sembrar_tasas_2025
  3. 5 artículos PT con enlace contable        _sembrar_articulos_pt
  4. 15 empleados (roster + %ARI)              sembrar_empleados
  5. Plantillas recurrentes                    sembrar_plantillas
  6. Precarga del Primer Trimestre (20 asientos del plan, es_prueba=False)
  7. Purga de asientos de prueba

Idempotente: si ya existe la apertura, omite la precarga salvo reset_precarga=True.
"""
from decimal import Decimal
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import get_db
from models import (Usuario, Asiento, ArticuloInventario,
                    TipoArticuloInventarioEnum, OrigenAsientoEnum)
from routers.auth import require_roles
from routers.asientos import crear_asiento_interno
from routers.catalogo import sembrar_catalogo_default
from tasas_2025_seed import sembrar_tasas_2025
from nomina_empleados_seed import sembrar_empleados
from plantillas_seed import sembrar_plantillas

router = APIRouter()
D = lambda v: Decimal(str(v))

# ── 5 artículos de Producto Terminado (SKU → cuentas) ───────────────────────
ARTICULOS_PT = [
    ("TQ-30/50", "Tequeños Clásicos (30/50 u)",   "1.1.22.01", "5.2.01"),
    ("MP-15",    "Minipizzas Surtidas (15/25 u)", "1.1.22.02", "5.2.02"),
    ("MF-500",   "Masa Fácil Hojaldre (500 g)",   "1.1.22.03", "5.2.03"),
    ("TJ-20",    "Tequeños Jumbo (20 u)",         "1.1.22.04", "5.2.04"),
    ("PS-20/30", "Pastelitos Rellenos (20/30 u)", "1.1.22.05", "5.2.05"),
]

# ── Precarga del Primer Trimestre — montos EXACTOS del plan (docx) ───────────
# (fecha, codigo, origen, descripcion, [(cuenta, debe, haber), ...])
PRECARGA_Q1 = [
    (date(2025,1,2), "APERTURA", OrigenAsientoEnum.apertura, "Asiento de apertura — aportes en bienes y MP", [
        ("1.2.10", "2102892.00", 0), ("1.2.05", "1945175.10", 0), ("1.2.08", "630867.60", 0),
        ("1.2.12", "184003.05", 0), ("1.2.15", "236575.35", 0), ("1.1.20.01", "420578.40", 0),
        ("3.1.01", 0, "5520091.50")]),
    (date(2025,1,3), "FOLIADO", OrigenAsientoEnum.servicios, "Foliado y sellado de libros", [
        ("6.2.15", "7885.84", 0), ("2.2.10", 0, "7885.84")]),
    (date(2025,1,6), "IAE-LIC", OrigenAsientoEnum.impuesto, "IAE — licencia inicial de actividades", [
        ("6.2.13", "10514.46", 0), ("2.2.10", 0, "10514.46")]),
    (date(2025,1,8), "MAQ-FISCAL", OrigenAsientoEnum.compra, "Impresora fiscal + software homologado", [
        ("1.2.12", "81487.07", 0), ("1.1.15", "13037.93", 0), ("2.1.02", 0, "94525.00")]),
    (date(2025,1,9), "MAQ-INSTAL", OrigenAsientoEnum.compra, "Instalación y configuración (capitalizable)", [
        ("1.2.12", "9463.01", 0), ("1.1.15", "1514.09", 0), ("2.1.02", 0, "10977.10")]),
    (date(2025,1,10), "TALONARIOS", OrigenAsientoEnum.compra, "Talonarios y papelería autorizada", [
        ("6.2.06", "2365.75", 0), ("1.1.15", "378.52", 0), ("2.2.10", 0, "2744.27")]),
    (date(2025,1,10), "PAGO-MAQ", OrigenAsientoEnum.compra, "Pago en divisas máquina fiscal (IGTF 3%)", [
        ("2.1.02", "105502.09", 0), ("6.3.04", "3165.06", 0), ("2.2.10", 0, "108667.15")]),
    (date(2025,1,15), "IAE-IND", OrigenAsientoEnum.impuesto, "IAE — impuesto actividad industrial", [
        ("6.2.16", "7144.54", 0), ("2.1.09", 0, "7144.54")]),
    (date(2025,1,20), "COMPRA-MP-ENE", OrigenAsientoEnum.compra, "Compra MP enero (60% crédito / 40% contado)", [
        ("1.1.20.01", "289833.00", 0), ("1.1.15", "46373.28", 0),
        ("2.1.01", 0, "201723.77"), ("2.2.10", 0, "134482.51")]),
    (date(2025,1,31), "NOM-ENE-DEV", OrigenAsientoEnum.nomina, "Devengo nómina enero", [
        ("5.1.10", "145496.17", 0), ("5.1.11", "49938.23", 0), ("6.2.01", "152944.87", 0), ("6.1.01", "57676.77", 0),
        ("2.1.10", 0, "402023.01"), ("2.1.11.01", 0, "2933.11"), ("2.1.11.02", 0, "733.28"), ("2.1.23", 0, "366.64")]),
    (date(2025,1,31), "NOM-ENE-PAT", OrigenAsientoEnum.nomina, "Aportes patronales enero (14%)", [
        ("5.1.10", "3651.90", 0), ("5.1.11", "1265.99", 0), ("6.2.01", "3927.82", 0), ("6.1.01", "1420.18", 0),
        ("2.1.11.01", 0, "7332.79"), ("2.1.11.02", 0, "1466.55"), ("2.1.23", 0, "1466.55")]),
    (date(2025,1,31), "NOM-ENE-PEN", OrigenAsientoEnum.nomina, "Pensiones 9% enero", [
        ("6.2.20", "6599.50", 0), ("2.1.12", 0, "6599.50")]),
    (date(2025,1,31), "NOM-ENE-PAGO", OrigenAsientoEnum.nomina, "Pago neto nómina enero", [
        ("2.1.10", "402023.01", 0), ("2.2.10", 0, "402023.01")]),
    (date(2025,1,31), "VENTAS-ENE", OrigenAsientoEnum.venta, "Ventas enero (45% detal contado / 55% mayorista crédito)", [
        ("1.1.01", "372944.91", 0), ("1.1.10", "455821.57", 0),
        ("4.1.01.01", 0, "141819.09"), ("4.1.02.01", 0, "136889.36"), ("4.1.03.01", 0, "175755.65"),
        ("4.1.04.01", 0, "24291.43"), ("4.1.05.01", 0, "235698.33"), ("2.1.05", 0, "114312.62")]),
    (date(2025,1,31), "IVA-COMP-ENE", OrigenAsientoEnum.iva, "Compensación IVA enero (DF vs CF)", [
        ("2.1.05", "81385.11", 0), ("1.1.15", 0, "81385.11")]),
    (date(2025,2,15), "IVA-ENT-ENE", OrigenAsientoEnum.iva, "Enteramiento IVA enero (cuota a pagar)", [
        ("2.1.05", "32927.51", 0), ("1.1.03", 0, "32927.51")]),
    (date(2025,2,20), "COMPRA-MP-FEB", OrigenAsientoEnum.compra, "Compra MP febrero (60% crédito / 40% banco)", [
        ("1.1.20.01", "398327.68", 0), ("1.1.15", "63732.43", 0),
        ("2.1.01", 0, "277236.07"), ("1.1.03", 0, "184824.04")]),
    (date(2025,3,31), "CIERRE-INCES", OrigenAsientoEnum.cierre, "INCES 2% del trimestre", [
        ("6.2.21", "5280.09", 0), ("2.1.13", 0, "5280.09")]),
    (date(2025,3,31), "CIERRE-PRESTAC", OrigenAsientoEnum.cierre, "Prestaciones Art. 142 LOTTT (trimestre)", [
        ("6.2.18", "49500.67", 0), ("2.1.18", 0, "49500.67")]),
    (date(2025,3,31), "CIERRE-INTERESES", OrigenAsientoEnum.cierre, "Intereses Art. 143 LOTTT (trimestre)", [
        ("6.2.19", "1485.24", 0), ("2.1.18", 0, "1485.24")]),
]


async def _sembrar_articulos_pt(empresa_id: int, db: AsyncSession) -> int:
    res = await db.execute(select(ArticuloInventario).where(ArticuloInventario.empresa_id == empresa_id))
    existentes = {a.codigo_sku: a for a in res.scalars().all()}
    creados = 0
    for sku, desc, c_inv, c_cost in ARTICULOS_PT:
        if sku in existentes:
            a = existentes[sku]; a.cuenta_inventario = c_inv; a.cuenta_costo = c_cost; a.activo = True
        else:
            db.add(ArticuloInventario(
                empresa_id=empresa_id, codigo_sku=sku, descripcion=desc,
                tipo=TipoArticuloInventarioEnum.producto_terminado, unidad_medida="paquete",
                cuenta_inventario=c_inv, cuenta_costo=c_cost, activo=True))
            creados += 1
    await db.flush()
    return creados


async def _precargar_q1(empresa_id: int, usuario_id: int, db: AsyncSession) -> list[str]:
    numeros = []
    for fecha, codigo, origen, desc, lineas in PRECARGA_Q1:
        ls = [{"cuenta_codigo": c, "debe": d, "haber": h, "descripcion": desc} for c, d, h in lineas]
        a = await crear_asiento_interno(
            db, empresa_id=empresa_id, usuario_id=usuario_id, fecha=fecha,
            origen=origen, es_prueba=False, descripcion=desc, referencia=f"Q1-{codigo}", lineas=ls)
        numeros.append(a.numero_asiento)
    return numeros


@router.post("/clase-2025")
async def setup_clase_2025(
    reset_precarga: bool = Query(False, description="Si True, borra y recarga la precarga del Q1"),
    current_user: Usuario = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    emp, uid = current_user.empresa_id, current_user.id
    resumen = {}

    resumen["catalogo"]   = await sembrar_catalogo_default(emp, db)
    resumen["tasas"]      = await sembrar_tasas_2025(db, sobrescribir=False)
    resumen["articulos"]  = await _sembrar_articulos_pt(emp, db)
    resumen["empleados"]  = await sembrar_empleados(emp, db)
    resumen["plantillas"] = await sembrar_plantillas(emp, db)

    # Precarga Q1 (idempotente por la apertura)
    if reset_precarga:
        refs = [f"Q1-{c[1]}" for c in PRECARGA_Q1]
        await db.execute(delete(Asiento).where(Asiento.empresa_id == emp, Asiento.referencia.in_(refs)))
        await db.flush()
    ya = await db.execute(
        select(Asiento).where(Asiento.empresa_id == emp, Asiento.origen == OrigenAsientoEnum.apertura).limit(1))
    if ya.scalar_one_or_none():
        resumen["precarga"] = "omitida (ya existe la apertura; usa reset_precarga=true para recargar)"
    else:
        nums = await _precargar_q1(emp, uid, db)
        resumen["precarga"] = {"asientos": len(nums), "rango": f"{nums[0]}…{nums[-1]}" if nums else None}

    # Purga de pruebas
    res = await db.execute(delete(Asiento).where(Asiento.empresa_id == emp, Asiento.es_prueba == True))
    resumen["pruebas_purgadas"] = res.rowcount

    await db.commit()
    return {"mensaje": "Setup clase-2025 completado", "resumen": resumen}
