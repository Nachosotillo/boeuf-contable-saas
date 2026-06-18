"""
Router: Asientos Contables

Novedades Paso B:
  - `crear_asiento_interno()`: único punto de creación validado. Lo usan el endpoint
    público, la precarga del Q1, y (Paso D) nómina, IVA, compras y ventas. Así todo
    el sistema produce asientos por el mismo camino: cuadre, guard de cuentas hoja,
    sellado de tasa del día, numeración y auditoría.
  - Guard de posteo: solo cuentas tipo "Cuenta" (hojas) reciben Debe/Haber.
    Grupos y subgrupos quedan bloqueados.
  - Sellado automático de `tasa_cambio_aplicada` con la tasa BCV vigente de la fecha
    (forward-fill) cuando la línea no la trae.
  - `origen` y `es_prueba` para clasificar y limpiar los asientos de prueba.
  - Numeración robusta (máximo correlativo, no count) — sobrevive a reversos/borrados.
"""

import re
from datetime import date
from decimal import Decimal
from typing import Optional, Iterable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from database import get_db
from models import (
    Asiento, LineaAsiento, CatalogoCuenta, Usuario,
    TipoCuentaEnum, OrigenAsientoEnum,
)
from schemas import AsientoCreate, AsientoOut, LineaAsientoOut
from routers.auth import get_current_user, require_roles
from routers.tasas import obtener_tasa_para_fecha
from utils.auditoria import registrar_log

router = APIRouter()

CENT = Decimal("0.01")


# ─── Numeración ────────────────────────────────────────────────────────────────

async def get_proximo_numero(empresa_id: int, db: AsyncSession) -> str:
    """Próximo correlativo basado en el máximo existente (formato A-###)."""
    result = await db.execute(
        select(Asiento.numero_asiento).where(Asiento.empresa_id == empresa_id)
    )
    maximo = 0
    for (num,) in result.all():
        m = re.match(r"A-(\d+)", num or "")
        if m:
            maximo = max(maximo, int(m.group(1)))
    return f"A-{str(maximo + 1).zfill(3)}"


@router.get("/proximo-numero")
async def proximo_numero(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"numero": await get_proximo_numero(current_user.empresa_id, db)}


# ─── Creador interno reutilizable ──────────────────────────────────────────────

def _d(v) -> Decimal:
    return Decimal(str(v or 0))


async def crear_asiento_interno(
    db: AsyncSession,
    *,
    empresa_id: int,
    usuario_id: int,
    fecha: date,
    lineas: Iterable[dict],
    descripcion: Optional[str] = None,
    referencia: Optional[str] = None,
    origen: OrigenAsientoEnum = OrigenAsientoEnum.manual,
    es_prueba: bool = False,
    numero: Optional[str] = None,
) -> Asiento:
    """
    Crea un asiento validado y balanceado. `lineas` es una lista de dicts con:
      cuenta_codigo, debe, haber, [moneda], [tasa_cambio_aplicada],
      [descripcion], [numero_factura]
    Devuelve el Asiento ya flush-eado (sin recargar relaciones).
    Lanza HTTPException 400 si hay cuentas inválidas, se postea a grupos/subgrupos,
    o el asiento no cuadra.
    """
    lineas = [dict(l) for l in lineas]
    if len(lineas) < 2:
        raise HTTPException(400, detail="Un asiento requiere al menos 2 líneas")

    # 1. Resolver cuentas
    codigos = [l["cuenta_codigo"] for l in lineas]
    res = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.empresa_id == empresa_id,
            CatalogoCuenta.codigo.in_(codigos),
            CatalogoCuenta.activa == True,
        )
    )
    cuentas = {c.codigo: c for c in res.scalars().all()}

    faltantes = [c for c in codigos if c not in cuentas]
    if faltantes:
        raise HTTPException(400, detail=f"Cuentas no encontradas o inactivas: {faltantes}")

    # 2. Guard: solo cuentas hoja (tipo == Cuenta) reciben movimientos
    no_hoja = [c for c in codigos if cuentas[c].tipo != TipoCuentaEnum.cuenta]
    if no_hoja:
        raise HTTPException(
            400,
            detail=f"No se puede postear a grupos/subgrupos: {no_hoja}. Usa una cuenta de detalle.",
        )

    # 3. Cuadre
    total_debe = sum(_d(l.get("debe")) for l in lineas)
    total_haber = sum(_d(l.get("haber")) for l in lineas)
    if abs(total_debe - total_haber) > CENT:
        raise HTTPException(
            400, detail=f"El asiento NO cuadra: Debe={total_debe} ≠ Haber={total_haber}"
        )

    # 4. Tasa del día (forward-fill) para sellar líneas que no la traigan
    tasa_rec = await obtener_tasa_para_fecha(db, fecha)
    tasa_dia = tasa_rec.tasa_usd if tasa_rec else None

    # 5. Asiento
    numero = numero or await get_proximo_numero(empresa_id, db)
    asiento = Asiento(
        empresa_id=empresa_id,
        numero_asiento=numero,
        fecha=fecha,
        mes=fecha.month,
        descripcion=descripcion,
        referencia=referencia,
        origen=origen,
        es_prueba=es_prueba,
        total_debe=total_debe,
        total_haber=total_haber,
        cuadra=abs(total_debe - total_haber) <= CENT,
        creado_por=usuario_id,
    )
    db.add(asiento)
    await db.flush()

    # 6. Líneas — Debe primero, luego Haber (orden natural del Diario)
    ordenadas = sorted(lineas, key=lambda l: 0 if _d(l.get("debe")) > 0 else 1)
    for l in ordenadas:
        cuenta = cuentas[l["cuenta_codigo"]]
        db.add(LineaAsiento(
            asiento_id=asiento.id,
            cuenta_id=cuenta.id,
            debe=_d(l.get("debe")),
            haber=_d(l.get("haber")),
            moneda=l.get("moneda", "VES"),
            tasa_cambio_aplicada=l.get("tasa_cambio_aplicada") or tasa_dia,
            descripcion=l.get("descripcion"),
            numero_factura=l.get("numero_factura"),
        ))

    await db.flush()
    return asiento


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=AsientoOut, status_code=201)
async def crear_asiento(
    data: AsientoCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db),
):
    asiento = await crear_asiento_interno(
        db,
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        fecha=data.fecha,
        lineas=[l.model_dump() for l in data.lineas],
        descripcion=data.descripcion,
        referencia=data.referencia,
        origen=data.origen or OrigenAsientoEnum.manual,
        es_prueba=data.es_prueba,
    )
    await registrar_log(
        db, current_user, "asiento", asiento.id, "CREAR",
        datos_despues={"numero": asiento.numero_asiento, "total_debe": str(asiento.total_debe)},
    )
    await db.flush()
    return await _cargar_y_serializar(asiento.id, current_user.empresa_id, db)


@router.get("/", response_model=list[AsientoOut])
async def listar_asientos(
    mes: int | None = Query(None, ge=1, le=12),
    anio: int | None = Query(None),
    origen: OrigenAsientoEnum | None = Query(None),
    incluir_prueba: bool = Query(True, description="Si False, oculta los asientos de prueba"),
    skip: int = 0,
    limit: int = Query(100, le=500),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Asiento).options(
        selectinload(Asiento.lineas).selectinload(LineaAsiento.cuenta)
    ).where(Asiento.empresa_id == current_user.empresa_id)

    if mes:
        q = q.where(Asiento.mes == mes)
    if anio:
        q = q.where(func.extract("year", Asiento.fecha) == anio)
    if origen:
        q = q.where(Asiento.origen == origen)
    if not incluir_prueba:
        q = q.where(Asiento.es_prueba == False)

    q = q.order_by(Asiento.fecha, Asiento.numero_asiento).offset(skip).limit(limit)
    result = await db.execute(q)
    return [_serialize_asiento(a) for a in result.scalars().all()]


@router.get("/{asiento_id}", response_model=AsientoOut)
async def obtener_asiento(
    asiento_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    asiento = await _cargar_y_serializar(asiento_id, current_user.empresa_id, db, devolver_modelo=False)
    if asiento is None:
        raise HTTPException(404, detail="Asiento no encontrado")
    return asiento


@router.delete("/{asiento_id}", status_code=204)
async def reversar_asiento(
    asiento_id: int,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db),
):
    """Reversión: crea un asiento espejo con Debe y Haber invertidos."""
    result = await db.execute(
        select(Asiento)
        .options(selectinload(Asiento.lineas))
        .where(Asiento.id == asiento_id, Asiento.empresa_id == current_user.empresa_id)
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(404, detail="Asiento no encontrado")
    if original.reversado:
        raise HTTPException(400, detail="El asiento ya fue reversado")

    numero_rev = await get_proximo_numero(current_user.empresa_id, db)
    reverso = Asiento(
        empresa_id=current_user.empresa_id,
        numero_asiento=numero_rev,
        fecha=date.today(),
        mes=date.today().month,
        descripcion=f"REVERSIÓN de {original.numero_asiento}",
        referencia=f"REV-{original.numero_asiento}",
        origen=OrigenAsientoEnum.reverso,
        es_prueba=original.es_prueba,
        total_debe=original.total_haber,
        total_haber=original.total_debe,
        cuadra=True,
        creado_por=current_user.id,
        asiento_reverso_id=original.id,
    )
    db.add(reverso)
    await db.flush()

    for linea in original.lineas:
        db.add(LineaAsiento(
            asiento_id=reverso.id,
            cuenta_id=linea.cuenta_id,
            debe=linea.haber,
            haber=linea.debe,
            moneda=linea.moneda,
            tasa_cambio_aplicada=linea.tasa_cambio_aplicada,
            descripcion=f"Reversión de {original.numero_asiento}",
        ))

    original.reversado = True
    await registrar_log(
        db, current_user, "asiento", asiento_id, "REVERSIÓN",
        datos_antes={"numero": original.numero_asiento},
    )


@router.post("/limpiar-prueba")
async def limpiar_asientos_prueba(
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db),
):
    """Elimina todos los asientos marcados como `es_prueba` (y sus líneas por cascada)."""
    res = await db.execute(
        select(func.count(Asiento.id)).where(
            Asiento.empresa_id == current_user.empresa_id,
            Asiento.es_prueba == True,
        )
    )
    n = res.scalar() or 0

    # Borra líneas y asientos de prueba de la empresa
    sub = select(Asiento.id).where(
        Asiento.empresa_id == current_user.empresa_id, Asiento.es_prueba == True
    )
    await db.execute(delete(LineaAsiento).where(LineaAsiento.asiento_id.in_(sub)))
    await db.execute(
        delete(Asiento).where(
            Asiento.empresa_id == current_user.empresa_id, Asiento.es_prueba == True
        )
    )
    await registrar_log(
        db, current_user, "asiento", 0, "ELIMINAR",
        datos_despues={"eliminados": n, "detalle": "limpieza de asientos de prueba"},
    )
    return {"eliminados": n}


# ─── Serialización ─────────────────────────────────────────────────────────────

def _serialize_asiento(a: Asiento) -> AsientoOut:
    lineas_out = []
    for l in a.lineas:
        lineas_out.append(LineaAsientoOut(
            id=l.id,
            cuenta_id=l.cuenta_id,
            cuenta_codigo=l.cuenta.codigo if l.cuenta else None,
            cuenta_nombre=l.cuenta.nombre if l.cuenta else None,
            debe=l.debe,
            haber=l.haber,
            moneda=l.moneda,
            tasa_cambio_aplicada=l.tasa_cambio_aplicada,
            numero_factura=l.numero_factura,
            descripcion=l.descripcion,
            folio_mayor=l.cuenta.folio_mayor if (l.cuenta and hasattr(l.cuenta, "folio_mayor")) else None,
        ))
    return AsientoOut(
        id=a.id,
        numero_asiento=a.numero_asiento,
        fecha=a.fecha,
        mes=a.mes,
        descripcion=a.descripcion,
        referencia=a.referencia,
        total_debe=a.total_debe,
        total_haber=a.total_haber,
        cuadra=a.cuadra,
        origen=a.origen.value if a.origen else None,
        es_prueba=a.es_prueba,
        lineas=lineas_out,
    )


async def _cargar_y_serializar(asiento_id: int, empresa_id: int, db: AsyncSession, devolver_modelo=True):
    result = await db.execute(
        select(Asiento)
        .options(selectinload(Asiento.lineas).selectinload(LineaAsiento.cuenta))
        .where(Asiento.id == asiento_id, Asiento.empresa_id == empresa_id)
    )
    asiento = result.scalar_one_or_none()
    if asiento is None:
        return None
    return _serialize_asiento(asiento)
