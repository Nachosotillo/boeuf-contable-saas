"""
Router: Nómina
- ISLR progresivo: Calculado según % ARI del empleado
- SSO y Paro Forzoso: Con topes de 5 y 10 salarios mínimos
- FAOV, INCES, Protección Pensiones
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
from routers.tasas import obtener_tasa_actual

router = APIRouter()

# ─── Parámetros tributarios vigentes ─────────────────────────────────────────

PARAMS = {
    # Sueldo mínimo y equivalente
    "SALARIO_MINIMO_BS": Decimal("130.00"),
    "INGRESO_MINIMO_PENSIONES_USD": Decimal("130.00"),
    
    # Seguro Social (Tope: 5 salarios mínimos)
    "SSO_EMP":   Decimal("0.04"),
    "SSO_PAT":   Decimal("0.10"),  # Riesgo Medio
    
    # Régimen Prestacional de Empleo (Paro Forzoso) (Tope: 10 salarios mínimos)
    "RPE_EMP":   Decimal("0.005"),
    "RPE_PAT":   Decimal("0.02"),
    
    # FAOV (Sin tope)
    "FAOV_EMP":  Decimal("0.01"),
    "FAOV_PAT":  Decimal("0.02"),
    
    # INCES (Trabajador 0.5% solo en Utilidades, Empresa 2% en nómina regular)
    "INCES_EMP": Decimal("0.00"),
    "INCES_PAT": Decimal("0.02"),
    
    # Ley de Protección de Pensiones (100% Empresa, piso mínimo de 130 USD)
    "PEN_EMP":   Decimal("0.00"),
    "PEN_PAT":   Decimal("0.09"),
}

async def calcular_nomina_empleado(empleado: NominaEmpleado, tasa_bcv: Decimal) -> NominaCalculadaOut:
    s = empleado.salario_base or Decimal("0")
    r = lambda v: v.quantize(Decimal("0.01"), ROUND_HALF_UP)

    # Prevenir que porcentaje_ari sea None si la base de datos no lo llenó
    ari = empleado.porcentaje_ari if empleado.porcentaje_ari is not None else Decimal("0")

    # ISLR: Se aplica el porcentaje exacto de la planilla ARI del empleado
    islr = r(s * (ari / Decimal("100")))
    
    # Topes Legales
    tope_sso = PARAMS["SALARIO_MINIMO_BS"] * Decimal("5")
    base_sso = min(s, tope_sso)
    
    tope_rpe = PARAMS["SALARIO_MINIMO_BS"] * Decimal("10")
    base_rpe = min(s, tope_rpe)
    
    # tasa_bcv puede venir como flotante o decimal, aseguramos Decimal
    tasa = Decimal(str(tasa_bcv)) if tasa_bcv else Decimal("36.50")
    piso_pensiones = PARAMS["INGRESO_MINIMO_PENSIONES_USD"] * tasa
    base_pensiones = max(s, piso_pensiones)

    # Deducciones del Empleado
    sso_e = r(base_sso * PARAMS["SSO_EMP"])
    rpe_e = r(base_rpe * PARAMS["RPE_EMP"])
    faov_e = r(s * PARAMS["FAOV_EMP"])
    inces_e = r(s * PARAMS["INCES_EMP"])
    pen_e = r(s * PARAMS["PEN_EMP"])
    
    total_ded = islr + sso_e + rpe_e + faov_e + inces_e + pen_e
    neto = r(s - total_ded)

    # Aportes Patronales
    sso_p = r(base_sso * PARAMS["SSO_PAT"])
    rpe_p = r(base_rpe * PARAMS["RPE_PAT"])
    faov_p = r(s * PARAMS["FAOV_PAT"])
    inces_p = r(s * PARAMS["INCES_PAT"])
    pen_p = r(base_pensiones * PARAMS["PEN_PAT"])
    
    costo = r(s + sso_p + rpe_p + faov_p + inces_p + pen_p)

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
        rpe_empleado=rpe_e,
        proteccion_pensiones_emp=pen_e,
        total_deducciones=total_ded,
        neto_a_pagar=neto,
        sso_patrono=sso_p,
        faov_patrono=faov_p,
        inces_patrono=inces_p,
        rpe_patrono=rpe_p,
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
    
    tasa_bcv = await obtener_tasa_actual(db)
    valor_bcv = tasa_bcv.tasa_usd if tasa_bcv else Decimal("36.50")
    
    return [await calcular_nomina_empleado(e, valor_bcv) for e in empleados]


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
           2.1.11.01 Retenciones y Aportes IVSS
           2.1.11.02 Retenciones y Aportes BANAVIH
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

    tasa_bcv = await obtener_tasa_actual(db)
    valor_bcv = tasa_bcv.tasa_usd if tasa_bcv else Decimal("36.50")

    # Calcular totales
    r = lambda v: v.quantize(Decimal("0.01"), ROUND_HALF_UP)
    tot_sal = ZERO = Decimal("0")
    tot_neto = tot_sso_p = tot_faov_p = tot_inces_p = tot_pen_p = tot_rpe_p = ZERO
    tot_sso_e = tot_faov_e = tot_inces_e = tot_pen_e = tot_rpe_e = ZERO

    for emp in empleados:
        c = await calcular_nomina_empleado(emp, valor_bcv)
        tot_sal += emp.salario_base
        tot_neto += c.neto_a_pagar
        tot_sso_p += c.sso_patrono
        tot_faov_p += c.faov_patrono
        tot_inces_p += c.inces_patrono
        tot_pen_p += c.proteccion_pensiones_pat
        tot_rpe_p += c.rpe_patrono
        
        tot_sso_e += c.sso_empleado
        tot_faov_e += c.faov_empleado
        tot_inces_e += c.inces_empleado
        tot_pen_e += c.proteccion_pensiones_emp
        tot_rpe_e += c.rpe_empleado

    # Resolver cuentas
    codigos_needed = ["6.1.01", "6.1.02", "6.1.03", "6.1.04", "6.1.05",
                      "2.1.20", "2.1.11.01", "2.1.11.02", "2.1.12"]
    res_cuentas = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.empresa_id == current_user.empresa_id,
            CatalogoCuenta.codigo.in_(codigos_needed),
        )
    )
    cuentas = {c.codigo: c for c in res_cuentas.scalars().all()}

    missing = [c for c in codigos_needed if c not in cuentas]
    if missing:
        raise HTTPException(400, detail=f"Cuentas faltantes en catálogo: {missing}. Actualiza el catálogo o verifica los subgrupos.")

    from datetime import date
    numero = await get_proximo_numero(current_user.empresa_id, db)

    asiento = Asiento(
        empresa_id=current_user.empresa_id,
        numero_asiento=numero,
        fecha=date.today(),
        mes=date.today().month,
        descripcion=f"Nómina mensual — {len(empleados)} empleados",
        referencia=f"NOM-{date.today().strftime('%Y%m')}",
        total_debe=r(tot_sal + tot_sso_p + tot_faov_p + tot_inces_p + tot_pen_p + tot_rpe_p),
        total_haber=r(tot_neto + (tot_sso_e + tot_sso_p + tot_rpe_e + tot_rpe_p) + (tot_faov_e + tot_faov_p) + (tot_inces_e + tot_inces_p) + (tot_pen_e + tot_pen_p)),
        cuadra=True,
        creado_por=current_user.id,
    )
    db.add(asiento)
    await db.flush()

    lineas_data = [
        ("6.1.01", tot_sal, Decimal("0")),
        ("6.1.02", tot_sso_p + tot_rpe_p, Decimal("0")), # SSO y Paro se asientan juntos en gastos usualmente, pero como la cuenta 6.1.02 se llama SSO, podemos sumar.
        ("6.1.03", tot_faov_p, Decimal("0")),
        ("6.1.04", tot_inces_p, Decimal("0")),
        ("6.1.05", tot_pen_p, Decimal("0")),
        ("2.1.20", Decimal("0"), tot_neto),
        ("2.1.11.01", Decimal("0"), r(tot_sso_e + tot_sso_p + tot_rpe_e + tot_rpe_p)), # IVSS = SSO + RPE
        ("2.1.11.02", Decimal("0"), r(tot_faov_e + tot_faov_p)), # BANAVIH = FAOV
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
