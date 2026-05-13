"""
Router: Asientos Contables
Validación Debe=Haber en frontend + backend + BD
"""

from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database import get_db
from models import Asiento, LineaAsiento, CatalogoCuenta, Usuario, LogAuditoria
from schemas import AsientoCreate, AsientoOut, LineaAsientoOut
from routers.auth import get_current_user, require_roles
from utils.auditoria import registrar_log

router = APIRouter()


async def get_proximo_numero(empresa_id: int, db: AsyncSession) -> str:
    """Genera el próximo número correlativo de asiento."""
    result = await db.execute(
        select(func.count(Asiento.id)).where(Asiento.empresa_id == empresa_id)
    )
    count = result.scalar() or 0
    return f"A-{str(count + 1).zfill(3)}"


@router.get("/proximo-numero")
async def proximo_numero(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    numero = await get_proximo_numero(current_user.empresa_id, db)
    return {"numero": numero}


@router.post("/", response_model=AsientoOut, status_code=201)
async def crear_asiento(
    data: AsientoCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db)
):
    """
    Crea un asiento contable con validación completa:
    1. Pydantic valida Debe=Haber (schema)
    2. Verificamos que todas las cuentas existan para la empresa
    3. Transacción atómica: INSERT asiento + líneas + log auditoría
    """
    # 1. Resolver cuentas por código → id
    codigos = [l.cuenta_codigo for l in data.lineas]
    result = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.empresa_id == current_user.empresa_id,
            CatalogoCuenta.codigo.in_(codigos),
            CatalogoCuenta.activa == True,
        )
    )
    cuentas_db = {c.codigo: c for c in result.scalars().all()}

    codigos_invalidos = [c for c in codigos if c not in cuentas_db]
    if codigos_invalidos:
        raise HTTPException(400, detail=f"Cuentas no encontradas: {codigos_invalidos}")

    # 2. Generar número correlativo
    numero = await get_proximo_numero(current_user.empresa_id, db)

    # 3. Calcular totales
    total_debe = sum(l.debe for l in data.lineas)
    total_haber = sum(l.haber for l in data.lineas)

    # 4. Crear asiento
    asiento = Asiento(
        empresa_id=current_user.empresa_id,
        numero_asiento=numero,
        fecha=data.fecha,
        mes=data.fecha.month,
        descripcion=data.descripcion,
        referencia=data.referencia,
        total_debe=total_debe,
        total_haber=total_haber,
        cuadra=abs(total_debe - total_haber) <= Decimal("0.01"),
        creado_por=current_user.id,
    )
    db.add(asiento)
    await db.flush()

    # 5. Crear líneas
    for linea_in in data.lineas:
        cuenta = cuentas_db[linea_in.cuenta_codigo]
        linea = LineaAsiento(
            asiento_id=asiento.id,
            cuenta_id=cuenta.id,
            debe=linea_in.debe,
            haber=linea_in.haber,
            moneda=linea_in.moneda,
            tasa_cambio_aplicada=linea_in.tasa_cambio_aplicada,
            descripcion=linea_in.descripcion,
            numero_factura=linea_in.numero_factura,
        )
        db.add(linea)

    # 6. Log auditoría
    await registrar_log(db, current_user, "asiento", asiento.id, "CREAR",
                        datos_despues={"numero": numero, "total_debe": str(total_debe)})

    await db.flush()

    # 7. Recargar con relaciones para la respuesta
    result = await db.execute(
        select(Asiento)
        .options(selectinload(Asiento.lineas).selectinload(LineaAsiento.cuenta))
        .where(Asiento.id == asiento.id)
    )
    asiento_full = result.scalar_one()

    return _serialize_asiento(asiento_full)


@router.get("/", response_model=list[AsientoOut])
async def listar_asientos(
    mes: int | None = Query(None, ge=1, le=12),
    anio: int | None = Query(None),
    skip: int = 0,
    limit: int = Query(100, le=500),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    q = select(Asiento).options(
        selectinload(Asiento.lineas).selectinload(LineaAsiento.cuenta)
    ).where(Asiento.empresa_id == current_user.empresa_id)

    if mes:
        q = q.where(Asiento.mes == mes)
    if anio:
        q = q.where(func.extract("year", Asiento.fecha) == anio)

    q = q.order_by(Asiento.fecha.desc(), Asiento.numero_asiento.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    asientos = result.scalars().all()
    return [_serialize_asiento(a) for a in asientos]


@router.get("/{asiento_id}", response_model=AsientoOut)
async def obtener_asiento(
    asiento_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Asiento)
        .options(selectinload(Asiento.lineas).selectinload(LineaAsiento.cuenta))
        .where(Asiento.id == asiento_id, Asiento.empresa_id == current_user.empresa_id)
    )
    asiento = result.scalar_one_or_none()
    if not asiento:
        raise HTTPException(404, detail="Asiento no encontrado")
    return _serialize_asiento(asiento)


@router.delete("/{asiento_id}", status_code=204)
async def reversar_asiento(
    asiento_id: int,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db)
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

    # Crear asiento de reversión
    numero_rev = await get_proximo_numero(current_user.empresa_id, db)
    reverso = Asiento(
        empresa_id=current_user.empresa_id,
        numero_asiento=numero_rev,
        fecha=date.today(),
        mes=date.today().month,
        descripcion=f"REVERSIÓN de {original.numero_asiento}",
        referencia=f"REV-{original.numero_asiento}",
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
            descripcion=f"Reversión de línea {linea.id}",
        ))

    original.reversado = True
    await registrar_log(db, current_user, "asiento", asiento_id, "REVERSIÓN",
                        datos_antes={"numero": original.numero_asiento})


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
        lineas=lineas_out,
    )
