"""
Router: Nómina
- ISLR progresivo 6 tramos (tabla Venezuela 2025)
- SSO, FAOV, INCES, Protección Pensiones
- Generación automática de asiento contable
"""

from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models import NominaEmpleado, Asiento, LineaAsiento, CatalogoCuenta, Usuario
from schemas import EmpleadoCreate, EmpleadoOut, NominaCalculadaOut
from routers.auth import get_current_user, require_roles
from routers.asientos import get_proximo_numero

router = APIRouter()

# ─── Parámetros tributarios vigentes ─────────────────────────────────────────

PARAMS = {
    "SSO_EMP":   Decimal("0.04"),
    "SSO_PAT":   Decimal("0.09"),
    "FAOV_EMP":  Decimal("0.01"),
    "FAOV_PAT":  Decimal("0.02"),
    "INCES_EMP": Decimal("0.005"),
    "INCES_PAT": Decimal("0.02"),
    "PEN_EMP":   Decimal("0.09"),
    "PEN_PAT":   Decimal("0.09"),
}

# Tabla ISLR progresivo 2025 (6 tramos)
ISLR_TRAMOS = [
    (Decimal("0"),     Decimal("3000"),  Decimal("0.00"),  Decimal("0")),
    (Decimal("3000"),  Decimal("5000"),  Decimal("0.06"),  Decimal("0")),
    (Decimal("5000"),  Decimal("10000"), Decimal("0.09"),  Decimal("120")),
    (Decimal("10000"), Decimal("15000"), Decimal("0.12"),  Decimal("570")),
    (Decimal("15000"), Decimal("20000"), Decimal("0.16"),  Decimal("1170")),
    (Decimal("20000"), None,             Decimal("0.34"),  Decimal("1970")),
]


def calcular_islr(salario: Decimal) -> Decimal:
    """Cálculo ISLR progresivo mensual según tabla 2025."""
    for desde, hasta, tasa, acumulado in ISLR_TRAMOS:
        if hasta is None or salario <= hasta:
            if salario <= desde:
                return Decimal("0")
            return (acumulado + (salario - desde) * tasa).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return Decimal("0")


def calcular_nomina_empleado(empleado: NominaEmpleado) -> NominaCalculadaOut:
    s = empleado.salario_base
    r = lambda v: v.quantize(Decimal("0.01"), ROUND_HALF_UP)

    islr = calcular_islr(s)
    sso_e = r(s * PARAMS["SSO_EMP"])
    faov_e = r(s * PARAMS["FAOV_EMP"])
    inces_e = r(s * PARAMS["INCES_EMP"])
    pen_e = r(s * PARAMS["PEN_EMP"])
    total_ded = islr + sso_e + faov_e + inces_e + pen_e
    neto = r(s - total_ded)

    sso_p = r(s * PARAMS["SSO_PAT"])
    faov_p = r(s * PARAMS["FAOV_PAT"])
    inces_p = r(s * PARAMS["INCES_PAT"])
    pen_p = r(s * PARAMS["PEN_PAT"])
    costo = r(s + sso_p + faov_p + inces_p + pen_p)

    return NominaCalculadaOut(
        empleado_id=empleado.id,
        cedula=empleado.cedula,
        nombre=empleado.nombre_completo,
        cargo=empleado.cargo,
        salario_base=s,
        islr_deducido=islr,
        sso_empleado=sso_e,
        faov_empleado=faov_e,
        inces_empleado=inces_e,
        proteccion_pensiones_emp=pen_e,
        total_deducciones=total_ded,
        neto_a_pagar=neto,
        sso_patrono=sso_p,
        faov_patrono=faov_p,
        inces_patrono=inces_p,
        proteccion_pensiones_pat=pen_p,
        costo_total_empresa=costo,
    )


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/empleados", response_model=EmpleadoOut, status_code=201)
async def crear_empleado(
    data: EmpleadoCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.empresa_id == current_user.empresa_id,
            NominaEmpleado.cedula == data.cedula,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, detail=f"Ya existe empleado con cédula {data.cedula}")

    emp = NominaEmpleado(**data.model_dump(), empresa_id=current_user.empresa_id)
    db.add(emp)
    await db.flush()
    return EmpleadoOut.model_validate(emp)


@router.get("/empleados", response_model=list[EmpleadoOut])
async def listar_empleados(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.empresa_id == current_user.empresa_id,
            NominaEmpleado.activo == True,
        )
    )
    return [EmpleadoOut.model_validate(e) for e in result.scalars().all()]


@router.get("/calcular", response_model=list[NominaCalculadaOut])
async def calcular_nomina(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Calcula la nómina completa sin persistir."""
    result = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.empresa_id == current_user.empresa_id,
            NominaEmpleado.activo == True,
        )
    )
    empleados = result.scalars().all()
    return [calcular_nomina_empleado(e) for e in empleados]


@router.post("/generar-asiento")
async def generar_asiento_nomina(
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db)
):
    """
    Genera automáticamente el asiento contable de nómina:
    DEBE:  6.1.01 Sueldos y Salarios
           6.1.02 SSO Patronal
           6.1.03 FAOV Patronal
           6.1.04 INCES Patronal
           6.1.05 Protección Pensiones Patronal
    HABER: 2.1.20 Nómina por Pagar
           2.1.11 SSO/FAOV/INCES por Pagar
           2.1.12 Protección Pensiones por Pagar
    """
    result = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.empresa_id == current_user.empresa_id,
            NominaEmpleado.activo == True,
        )
    )
    empleados = result.scalars().all()
    if not empleados:
        raise HTTPException(400, detail="No hay empleados activos")

    # Calcular totales
    r = lambda v: v.quantize(Decimal("0.01"), ROUND_HALF_UP)
    tot_sal = ZERO = Decimal("0")
    tot_neto = tot_sso_p = tot_faov_p = tot_inces_p = tot_pen_p = ZERO
    tot_sso_e = tot_faov_e = tot_inces_e = tot_pen_e = ZERO

    for emp in empleados:
        c = calcular_nomina_empleado(emp)
        tot_sal += emp.salario_base
        tot_neto += c.neto_a_pagar
        tot_sso_p += c.sso_patrono
        tot_faov_p += c.faov_patrono
        tot_inces_p += c.inces_patrono
        tot_pen_p += c.proteccion_pensiones_pat
        tot_sso_e += c.sso_empleado
        tot_faov_e += c.faov_empleado
        tot_inces_e += c.inces_empleado
        tot_pen_e += c.proteccion_pensiones_emp

    # Resolver cuentas
    codigos_needed = ["6.1.01", "6.1.02", "6.1.03", "6.1.04", "6.1.05",
                      "2.1.20", "2.1.11", "2.1.12"]
    res_cuentas = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.empresa_id == current_user.empresa_id,
            CatalogoCuenta.codigo.in_(codigos_needed),
        )
    )
    cuentas = {c.codigo: c for c in res_cuentas.scalars().all()}

    missing = [c for c in codigos_needed if c not in cuentas]
    if missing:
        raise HTTPException(400, detail=f"Cuentas faltantes en catálogo: {missing}")

    from datetime import date
    numero = await get_proximo_numero(current_user.empresa_id, db)

    asiento = Asiento(
        empresa_id=current_user.empresa_id,
        numero_asiento=numero,
        fecha=date.today(),
        mes=date.today().month,
        descripcion=f"Nómina mensual — {len(empleados)} empleados",
        referencia=f"NOM-{date.today().strftime('%Y%m')}",
        total_debe=r(tot_sal + tot_sso_p + tot_faov_p + tot_inces_p + tot_pen_p),
        total_haber=r(tot_neto + (tot_sso_e + tot_sso_p) + (tot_faov_e + tot_faov_p) + (tot_inces_e + tot_inces_p) + (tot_pen_e + tot_pen_p)),
        cuadra=True,
        creado_por=current_user.id,
    )
    db.add(asiento)
    await db.flush()

    lineas_data = [
        ("6.1.01", tot_sal, Decimal("0")),
        ("6.1.02", tot_sso_p, Decimal("0")),
        ("6.1.03", tot_faov_p, Decimal("0")),
        ("6.1.04", tot_inces_p, Decimal("0")),
        ("6.1.05", tot_pen_p, Decimal("0")),
        ("2.1.20", Decimal("0"), tot_neto),
        ("2.1.11", Decimal("0"), r(tot_sso_e + tot_sso_p + tot_faov_e + tot_faov_p + tot_inces_e + tot_inces_p)),
        ("2.1.12", Decimal("0"), r(tot_pen_e + tot_pen_p)),
    ]

    for codigo, debe, haber in lineas_data:
        db.add(LineaAsiento(
            asiento_id=asiento.id,
            cuenta_id=cuentas[codigo].id,
            debe=r(debe),
            haber=r(haber),
        ))

    return {"numero_asiento": numero, "mensaje": "Asiento de nómina generado correctamente"}


@router.get("/islr-tabla")
async def tabla_islr():
    """Devuelve la tabla ISLR progresiva vigente."""
    return [
        {"tramo": i + 1, "desde": float(d), "hasta": float(h) if h else None,
         "tasa_pct": float(t * 100), "acumulado": float(a)}
        for i, (d, h, t, a) in enumerate(ISLR_TRAMOS)
    ]
