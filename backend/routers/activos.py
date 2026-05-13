"""
routers/activos.py — Activos Fijos con depreciación línea recta
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import ActivoFijo, Asiento, LineaAsiento, CatalogoCuenta, Usuario
from schemas import ActivoFijoCreate, ActivoFijoOut
from routers.auth import get_current_user, require_roles
from routers.asientos import get_proximo_numero

router = APIRouter()
R2 = lambda v: Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)


@router.post("/", response_model=ActivoFijoOut, status_code=201)
async def crear_activo(
    data: ActivoFijoCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(
        select(ActivoFijo).where(
            ActivoFijo.empresa_id == current_user.empresa_id,
            ActivoFijo.codigo_activo == data.codigo_activo,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, detail=f"Ya existe activo {data.codigo_activo}")

    dep_mens = R2(data.costo_original * Decimal("100") / data.vida_util_anos / Decimal("12") / Decimal("100"))
    acum = R2(dep_mens * data.meses_depreciados) if hasattr(data, "meses_depreciados") else Decimal("0")
    neto = R2(data.costo_original - acum)

    obj = ActivoFijo(
        empresa_id=current_user.empresa_id,
        codigo_activo=data.codigo_activo,
        descripcion=data.descripcion,
        fecha_compra=data.fecha_compra,
        costo_original=data.costo_original,
        vida_util_anos=data.vida_util_anos,
        meses_depreciados=0,
        depreciacion_acumulada=Decimal("0"),
        valor_neto=data.costo_original,
        cuenta_activo_codigo=data.cuenta_activo_codigo,
        cuenta_depreciacion_codigo=data.cuenta_depreciacion_codigo,
    )
    db.add(obj)
    await db.flush()
    return ActivoFijoOut.model_validate(obj)


@router.get("/", response_model=list[ActivoFijoOut])
async def listar_activos(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ActivoFijo).where(
            ActivoFijo.empresa_id == current_user.empresa_id,
            ActivoFijo.activo == True,
        ).order_by(ActivoFijo.codigo_activo)
    )
    activos = result.scalars().all()
    out = []
    for a in activos:
        dep_mens = R2(a.costo_original * Decimal(str(100 / a.vida_util_anos / 12 / 100)))
        out.append(ActivoFijoOut(
            **{f: getattr(a, f) for f in ActivoFijoCreate.model_fields},
            id=a.id, empresa_id=a.empresa_id,
            meses_depreciados=a.meses_depreciados,
            depreciacion_acumulada=a.depreciacion_acumulada,
            valor_neto=a.valor_neto,
            depreciacion_mensual=dep_mens,
        ))
    return out


@router.post("/generar-depreciacion")
async def generar_depreciacion_mensual(
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db)
):
    """
    Genera el asiento de ajuste de depreciación mensual
    para todos los activos activos.
    """
    result = await db.execute(
        select(ActivoFijo).where(
            ActivoFijo.empresa_id == current_user.empresa_id,
            ActivoFijo.activo == True,
        )
    )
    activos = result.scalars().all()
    if not activos:
        raise HTTPException(400, detail="Sin activos registrados")

    # Resolver cuentas de depreciación
    res_cta = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.empresa_id == current_user.empresa_id,
            CatalogoCuenta.codigo.in_(["6.2.10", "1.2.06"]),
        )
    )
    cuentas = {c.codigo: c for c in res_cta.scalars().all()}

    numero = await get_proximo_numero(current_user.empresa_id, db)
    total_dep = Decimal("0")
    lineas_data = []

    for a in activos:
        dep = R2(a.costo_original * Decimal(str(100 / a.vida_util_anos / 12 / 100)))
        total_dep += dep
        a.meses_depreciados += 1
        a.depreciacion_acumulada = R2(a.depreciacion_acumulada + dep)
        a.valor_neto = R2(a.costo_original - a.depreciacion_acumulada)

        # Usar cuenta de depreciación acumulada específica si existe en catálogo
        cta_acum_cod = a.cuenta_depreciacion_codigo or "1.2.06"
        res_cta_ac = await db.execute(
            select(CatalogoCuenta).where(
                CatalogoCuenta.empresa_id == current_user.empresa_id,
                CatalogoCuenta.codigo == cta_acum_cod,
            )
        )
        cta_acum = res_cta_ac.scalar_one_or_none() or cuentas.get("1.2.06")
        lineas_data.append((cuentas.get("6.2.10"), dep, cta_acum, dep))

    asiento = Asiento(
        empresa_id=current_user.empresa_id,
        numero_asiento=numero,
        fecha=date.today(),
        mes=date.today().month,
        descripcion=f"Depreciación mensual — {len(activos)} activos",
        referencia=f"DEPR-{date.today().strftime('%Y%m')}",
        total_debe=total_dep,
        total_haber=total_dep,
        cuadra=True,
        creado_por=current_user.id,
    )
    db.add(asiento)
    await db.flush()

    for cta_gasto, debe, cta_acum, haber in lineas_data:
        if cta_gasto:
            db.add(LineaAsiento(asiento_id=asiento.id, cuenta_id=cta_gasto.id, debe=debe, haber=Decimal("0")))
        if cta_acum:
            db.add(LineaAsiento(asiento_id=asiento.id, cuenta_id=cta_acum.id, debe=Decimal("0"), haber=haber))

    return {"numero_asiento": numero, "total_depreciacion": float(total_dep),
            "activos_depreciados": len(activos)}
