"""
Router: Nómina
- ISLR progresivo: Calculado según % ARI del empleado
- SSO y Paro Forzoso: Con topes de 5 y 10 salarios mínimos
- FAOV, INCES, Protección Pensiones
- Generación automática de asiento contable
"""

from typing import Optional, List
from datetime import date
import calendar
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, Query
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

def get_mondays_in_month(year: int, month: int) -> int:
    """Calcula cuántos lunes tiene un mes específico."""
    count = 0
    matrix = calendar.monthcalendar(year, month)
    for week in matrix:
        if week[0] != 0:  # El índice 0 es Lunes en calendar.monthcalendar
            count += 1
    return count

async def calcular_nomina_empleado(empleado: NominaEmpleado, tasa_bcv: Decimal, lunes_mes: int = 4) -> NominaCalculadaOut:
    s = empleado.salario_base or Decimal("0")
    r = lambda v: v.quantize(Decimal("0.01"), ROUND_HALF_UP)
    
    # 1. Antigüedad (Años de servicio)
    fecha_ing = empleado.fecha_inicio or date.today()
    today = date.today()
    anos = today.year - fecha_ing.year - ((today.month, today.day) < (fecha_ing.month, fecha_ing.day))
    anos = max(0, anos)

    # 2. Salario Integral (Base + Alícuota Vacaciones + Alícuota Utilidades)
    # BV: 15 días + 1 por año (tope 30). Utilidades: 30 días.
    dias_bv = min(15 + anos, 30)
    dias_util = 30
    alic_vac = ((s / Decimal("30")) * Decimal(str(dias_bv))) / Decimal("12")
    alic_util = ((s / Decimal("30")) * Decimal(str(dias_util))) / Decimal("12")
    salario_integral = s + alic_vac + alic_util

    # FIX 1: Usar "if empleado.porcentaje_ari" en lugar de "is not None"
    # para capturar tanto None como 0.0000 sin calcular ISLR incorrecto.
    # El valor se fuerza a Decimal limpio para evitar errores de precisión.
    ari_raw = empleado.porcentaje_ari
    ari = Decimal(str(ari_raw)) if ari_raw else Decimal("0")
    islr = r((s * ari) / Decimal("100"))
    
    # 4. Topes Legales (SSO: 5 SM, RPE: 10 SM)
    tope_sso = PARAMS["SALARIO_MINIMO_BS"] * Decimal("5")
    base_sso = min(s, tope_sso)
    
    tope_rpe = PARAMS["SALARIO_MINIMO_BS"] * Decimal("10")
    base_rpe = min(s, tope_rpe)
    
    # 5. SSO (Semanal: (Base * 12) / 52)
    sso_sem = (base_sso * Decimal("12")) / Decimal("52")
    sso_e = r(sso_sem * Decimal("0.04") * Decimal(str(lunes_mes)))
    sso_p = r(sso_sem * Decimal("0.10") * Decimal(str(lunes_mes)))

    # 6. RPE (Paro Forzoso)
    rpe_sem = (base_rpe * Decimal("12")) / Decimal("52")
    rpe_e = r(rpe_sem * Decimal("0.005") * Decimal(str(lunes_mes)))
    rpe_p = r(rpe_sem * Decimal("0.02") * Decimal(str(lunes_mes)))

    # 7. FAOV (1% Empleado / 2% Patrono del Salario Integral)
    faov_e = r(salario_integral * Decimal("0.01"))
    faov_p = r(salario_integral * Decimal("0.02"))
    
    # 8. INCES e Impuesto a las Pensiones
    inces_e = r(s * Decimal("0.00"))
    inces_p = r(s * Decimal("0.02"))
    
    tasa = Decimal(str(tasa_bcv)) if tasa_bcv else Decimal("36.50")
    piso_pensiones = PARAMS["INGRESO_MINIMO_PENSIONES_USD"] * tasa
    base_pensiones = max(s, piso_pensiones)
    pen_e = r(s * Decimal("0.00"))
    pen_p = r(base_pensiones * Decimal("0.09"))
    
    total_ded = islr + sso_e + rpe_e + faov_e + inces_e + pen_e
    neto = r(s - total_ded)
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
    # Buscar si ya existe (activo o inactivo)
    result = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.empresa_id == current_user.empresa_id,
            NominaEmpleado.cedula == data.cedula,
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        if existing.activo:
            raise HTTPException(400, detail=f"Ya existe un empleado activo con cédula {data.cedula}")
        else:
            # Si existía pero estaba inactivo, lo reactivamos y actualizamos sus datos.
            # FIX 2: Forzar porcentaje_ari como Decimal explícito para evitar
            # que setattr lo guarde con tipo incorrecto desde model_dump().
            for key, value in data.model_dump().items():
                setattr(existing, key, value)
            existing.porcentaje_ari = Decimal(str(data.porcentaje_ari))
            existing.activo = True
            # FIX 3: Agregar commit para garantizar persistencia en BD.
            # Sin esto, el valor queda en la transacción pero no se escribe al disco,
            # y al recalcular en otro request se lee el valor anterior (0).
            await db.flush()
            await db.commit()
            await db.refresh(existing)
            return EmpleadoOut.model_validate(existing)

    # Si no existe, crear uno nuevo.
    # FIX 2 (también aquí): Asegurar que porcentaje_ari sea Decimal limpio al insertar.
    emp_data = data.model_dump()
    emp_data["porcentaje_ari"] = Decimal(str(data.porcentaje_ari))
    emp = NominaEmpleado(**emp_data, empresa_id=current_user.empresa_id)
    db.add(emp)
    # FIX 3: Commit también en el alta de empleado nuevo.
    await db.flush()
    await db.commit()
    await db.refresh(emp)
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
    mes: int = Query(default=date.today().month, ge=1, le=12),
    anio: int = Query(default=date.today().year),
    lunes: Optional[int] = Query(None, description="Forzar cantidad de lunes"),
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
    
    lunes_del_mes = lunes if lunes else get_mondays_in_month(anio, mes)
    
    tasa_bcv = await obtener_tasa_actual(db)
    valor_bcv = tasa_bcv.tasa_usd if tasa_bcv else Decimal("36.50")
    
    return [await calcular_nomina_empleado(e, valor_bcv, lunes_del_mes) for e in empleados]


@router.delete("/empleados/{emp_id}")
async def eliminar_empleado(
    emp_id: int,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.id == emp_id,
            NominaEmpleado.empresa_id == current_user.empresa_id
        )
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, detail="Empleado no encontrado")
    
    emp.activo = False  # Desactivación lógica
    await db.commit()
    return {"message": "Empleado desactivado"}


@router.post("/generar-asiento")
async def generar_asiento_nomina(
    mes: Optional[int] = Query(None, ge=1, le=12, description="Mes de la nómina (default: mes actual)"),
    anio: Optional[int] = Query(None, description="Año de la nómina (default: año actual)"),
    lunes: Optional[int] = Query(None, description="Forzar cantidad de lunes"),
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db)
):
    """
    Genera automáticamente el asiento contable de nómina:
    DEBE:  6.1.01 Sueldos y Salarios
           6.1.02 SSO Patronal + RPE Patronal
           6.1.03 FAOV Patronal
           6.1.04 INCES Patronal
           6.1.05 Protección Pensiones Patronal
    HABER: 2.1.20 Nómina por Pagar
           2.1.11.01 Retenciones y Aportes IVSS (SSO + RPE empleado + patrono)
           2.1.11.02 Retenciones y Aportes BANAVIH (FAOV empleado + patrono)
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

    # FIX (lunes consistente): Calcular lunes del mes correcto en lugar de usar default=4.
    # Esto garantiza que el asiento use los mismos valores que el endpoint /calcular.
    hoy = date.today()
    mes_nomina = mes if mes else hoy.month
    anio_nomina = anio if anio else hoy.year
    lunes_del_mes = lunes if lunes else get_mondays_in_month(anio_nomina, mes_nomina)

    # Calcular totales
    r = lambda v: v.quantize(Decimal("0.01"), ROUND_HALF_UP)
    ZERO = Decimal("0")
    tot_sal = tot_neto = tot_sso_p = tot_faov_p = tot_inces_p = tot_pen_p = tot_rpe_p = ZERO
    tot_sso_e = tot_faov_e = tot_inces_e = tot_pen_e = tot_rpe_e = ZERO

    for emp in empleados:
        # FIX: Pasar lunes_del_mes para que los cálculos del asiento sean idénticos
        # a los que ve el usuario en la pantalla de /calcular.
        c = await calcular_nomina_empleado(emp, valor_bcv, lunes_del_mes)
        tot_sal   += emp.salario_base
        tot_neto  += c.neto_a_pagar
        tot_sso_p += c.sso_patrono
        tot_faov_p += c.faov_patrono
        tot_inces_p += c.inces_patrono
        tot_pen_p += c.proteccion_pensiones_pat
        tot_rpe_p += c.rpe_patrono
        
        tot_sso_e   += c.sso_empleado
        tot_faov_e  += c.faov_empleado
        tot_inces_e += c.inces_empleado
        tot_pen_e   += c.proteccion_pensiones_emp
        tot_rpe_e   += c.rpe_empleado

    # Resolver cuentas (y crear si faltan)
    codigos_needed = {
        "6.1.01": ("Sueldos y Salarios — Ventas", "Deudora", "Estado de Resultado"),
        "6.1.02": ("Aportes Sociales Patronales", "Deudora", "Estado de Resultado"),
        "6.1.03": ("FAOV Patronal", "Deudora", "Estado de Resultado"),
        "6.1.04": ("INCES Patronal", "Deudora", "Estado de Resultado"),
        "6.1.05": ("Protección Pensiones Patronal", "Deudora", "Estado de Resultado"),
        "2.1.20": ("Nómina por Pagar", "Acreedora", "Situación Financiera"),
        "2.1.11.01": ("Retenciones y Aportes IVSS", "Acreedora", "Situación Financiera"),
        "2.1.11.02": ("Retenciones y Aportes BANAVIH", "Acreedora", "Situación Financiera"),
        "2.1.12": ("Protección Pensiones por Pagar", "Acreedora", "Situación Financiera"),
    }
    
    res_cuentas = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.empresa_id == current_user.empresa_id,
            CatalogoCuenta.codigo.in_(list(codigos_needed.keys())),
        )
    )
    cuentas = {c.codigo: c for c in res_cuentas.scalars().all()}

    from models import TipoCuentaEnum, NaturalezaEnum, EstadoFinancieroEnum
    for cod, (nom, nat, ef) in codigos_needed.items():
        if cod not in cuentas:
            new_c = CatalogoCuenta(
                empresa_id=current_user.empresa_id,
                codigo=cod,
                nombre=nom,
                tipo=TipoCuentaEnum.cuenta,
                naturaleza=NaturalezaEnum.deudora if nat == "Deudora" else NaturalezaEnum.acreedora,
                estado_financiero=EstadoFinancieroEnum.situacion if ef == "Situación Financiera" else EstadoFinancieroEnum.resultado,
                es_generada_auto=True
            )
            db.add(new_c)
            await db.flush()
            cuentas[cod] = new_c

    numero = await get_proximo_numero(current_user.empresa_id, db)

    total_debe  = r(tot_sal + tot_sso_p + tot_rpe_p + tot_faov_p + tot_inces_p + tot_pen_p)
    total_haber = r(
        tot_neto
        + r(tot_sso_e + tot_sso_p + tot_rpe_e + tot_rpe_p)
        + r(tot_faov_e + tot_faov_p)
        + r(tot_inces_e + tot_inces_p)
        + r(tot_pen_e + tot_pen_p)
    )

    asiento = Asiento(
        empresa_id=current_user.empresa_id,
        numero_asiento=numero,
        fecha=date.today(),
        mes=mes_nomina,
        descripcion=f"Nómina mensual — {len(empleados)} empleados",
        referencia=f"NOM-{anio_nomina}{mes_nomina:02d}",
        total_debe=total_debe,
        total_haber=total_haber,
        cuadra=(total_debe == total_haber),
        creado_por=current_user.id,
    )
    db.add(asiento)
    await db.flush()

    lineas_data = [
        ("6.1.01",    r(tot_sal),              Decimal("0")),
        ("6.1.02",    r(tot_sso_p + tot_rpe_p), Decimal("0")),
        ("6.1.03",    r(tot_faov_p),             Decimal("0")),
        ("6.1.04",    r(tot_inces_p),            Decimal("0")),
        ("6.1.05",    r(tot_pen_p),              Decimal("0")),
        ("2.1.20",    Decimal("0"),              r(tot_neto)),
        ("2.1.11.01", Decimal("0"),              r(tot_sso_e + tot_sso_p + tot_rpe_e + tot_rpe_p)),
        ("2.1.11.02", Decimal("0"),              r(tot_faov_e + tot_faov_p)),
        ("2.1.12",    Decimal("0"),              r(tot_pen_e + tot_pen_p)),
    ]

    for codigo, debe, haber in lineas_data:
        db.add(LineaAsiento(
            asiento_id=asiento.id,
            cuenta_id=cuentas[codigo].id,
            debe=r(debe),
            haber=r(haber),
        ))

    await db.commit()
    return {"numero_asiento": numero, "mensaje": "Asiento de nómina generado correctamente"}
