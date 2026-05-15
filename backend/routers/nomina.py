"""
Router: Nómina
- ISLR progresivo: Calculado según % ARI del empleado
- SSO y Paro Forzoso: Con topes de 5 y 10 salarios mínimos
- FAOV, INCES, Protección Pensiones
- Generación automática de asiento contable cada 30 días
- Programación automática del próximo pago al crear empleado

ESTRUCTURA DEL ASIENTO DE NÓMINA (cuadrado):
══════════════════════════════════════════════════════════════════
DEBE:
  5.1.02   Mano de Obra Directa (MOD)              → salario bruto MOD
  6.2.01   Sueldos y Salarios — Administración      → salario bruto MOI
  6.2.02   Prestaciones Sociales — Administración   → SSO+RPE+FAOV+INCES patrono
  6.2.20   Contribución Protección de Pensiones 9%  → pensiones patrono

HABER:
  2.1.10    Nómina por Pagar                        → neto a pagar
  2.1.11.01 Retenciones y Aportes IVSS              → SSO+RPE (emp+pat)
  2.1.11.02 Retenciones y Aportes BANAVIH           → FAOV (emp+pat)
  2.1.13    INCES por Pagar                         → INCES (emp+pat)
  2.1.22    Protección de Pensiones por Pagar       → pensiones patrono
  2.1.23    Retención Protección Pensiones — Emp.   → pensiones empleado

CUADRE:
  DEBE  = salarios_brutos + aportes_patronales + pensiones_patrono
  HABER = neto + IVSS_total + BANAVIH_total + INCES_total + pensiones_total
══════════════════════════════════════════════════════════════════
"""

from typing import Optional
from datetime import date, timedelta
import calendar
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import (
    NominaEmpleado, NominaProgramacion, Asiento, LineaAsiento,
    CatalogoCuenta, Usuario, TipoNominaEnum,
    TipoCuentaEnum, NaturalezaEnum, EstadoFinancieroEnum,
)
from schemas import EmpleadoCreate, EmpleadoOut, NominaCalculadaOut
from routers.auth import get_current_user, require_roles
from routers.asientos import get_proximo_numero
from routers.tasas import obtener_tasa_actual

router = APIRouter()

# ─── Parámetros tributarios vigentes ─────────────────────────────────────────

PARAMS = {
    "SALARIO_MINIMO_BS":            Decimal("130.00"),
    "INGRESO_MINIMO_PENSIONES_USD": Decimal("130.00"),
    "SSO_EMP":   Decimal("0.04"),
    "SSO_PAT":   Decimal("0.10"),
    "RPE_EMP":   Decimal("0.005"),
    "RPE_PAT":   Decimal("0.02"),
    "FAOV_EMP":  Decimal("0.01"),
    "FAOV_PAT":  Decimal("0.02"),
    "INCES_EMP": Decimal("0.00"),
    "INCES_PAT": Decimal("0.02"),
    "PEN_EMP":   Decimal("0.00"),
    "PEN_PAT":   Decimal("0.09"),
}

# ─── Mapa de cuentas contables de nómina ─────────────────────────────────────
# IMPORTANTE: Los códigos 6.1.02-6.1.05 son Comisiones/Publicidad/Fletes/Empaques
# y NO se usan en nómina. Los aportes patronales van a 6.2.02 y pensiones a 6.2.20.

CUENTAS_NOMINA = {
    "MOD":       "5.1.02",    # Mano de Obra Directa
    "MOI":       "6.2.01",    # Sueldos y Salarios — Administración
    "APORTES":   "6.2.02",    # Prestaciones Sociales (SSO+RPE+FAOV+INCES patronal)
    "PENSIONES": "6.2.20",    # Contribución Protección de Pensiones 9%
    "NOMINA_XP": "2.1.10",    # Nómina por Pagar
    "IVSS":      "2.1.11.01", # Retenciones IVSS
    "BANAVIH":   "2.1.11.02", # Retenciones BANAVIH/FAOV
    "INCES_XP":  "2.1.13",    # INCES por Pagar
    "PEN_PAT":   "2.1.22",    # Protección de Pensiones por Pagar (patrono)
    "PEN_EMP":   "2.1.23",    # Retención Protección Pensiones — Empleados
}

CUENTAS_NOMINA_DEF = {
    "5.1.02":    ("Mano de Obra Directa",                      "Deudora",   "resultado"),
    "6.2.01":    ("Sueldos y Salarios — Administración",        "Deudora",   "resultado"),
    "6.2.02":    ("Prestaciones Sociales — Administración",     "Deudora",   "resultado"),
    "6.2.20":    ("Contribución Protección de Pensiones — 9%",  "Deudora",   "resultado"),
    "2.1.10":    ("Nómina por Pagar",                           "Acreedora", "situacion"),
    "2.1.11.01": ("Retenciones y Aportes IVSS",                 "Acreedora", "situacion"),
    "2.1.11.02": ("Retenciones y Aportes BANAVIH",              "Acreedora", "situacion"),
    "2.1.13":    ("INCES por Pagar",                            "Acreedora", "situacion"),
    "2.1.22":    ("Protección de Pensiones por Pagar",          "Acreedora", "situacion"),
    "2.1.23":    ("Retención Protección Pensiones — Empleados", "Acreedora", "situacion"),
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_mondays_in_month(year: int, month: int) -> int:
    return sum(1 for w in calendar.monthcalendar(year, month) if w[0] != 0)


async def _resolver_cuentas(empresa_id: int, db: AsyncSession) -> dict:
    """Devuelve {codigo: CatalogoCuenta}, creando las faltantes automáticamente."""
    codigos = list(CUENTAS_NOMINA_DEF.keys())
    res = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.empresa_id == empresa_id,
            CatalogoCuenta.codigo.in_(codigos),
        )
    )
    cuentas = {c.codigo: c for c in res.scalars().all()}

    ef_map = {
        "resultado": EstadoFinancieroEnum.resultado,
        "situacion": EstadoFinancieroEnum.situacion,
    }
    for cod, (nombre, naturaleza, ef_key) in CUENTAS_NOMINA_DEF.items():
        if cod not in cuentas:
            new_c = CatalogoCuenta(
                empresa_id=empresa_id,
                codigo=cod,
                nombre=nombre,
                tipo=TipoCuentaEnum.cuenta,
                naturaleza=NaturalezaEnum.deudora if naturaleza == "Deudora" else NaturalezaEnum.acreedora,
                estado_financiero=ef_map[ef_key],
                es_generada_auto=True,
            )
            db.add(new_c)
            await db.flush()
            cuentas[cod] = new_c

    return cuentas


async def calcular_nomina_empleado(
    empleado: NominaEmpleado, tasa_bcv: Decimal, lunes_mes: int = 4
) -> NominaCalculadaOut:
    s = empleado.salario_base or Decimal("0")
    r = lambda v: v.quantize(Decimal("0.01"), ROUND_HALF_UP)

    fecha_ing = empleado.fecha_inicio or date.today()
    today = date.today()
    anos = max(0, today.year - fecha_ing.year - (
        (today.month, today.day) < (fecha_ing.month, fecha_ing.day)
    ))

    dias_bv  = min(15 + anos, 30)
    alic_vac  = ((s / Decimal("30")) * Decimal(str(dias_bv))) / Decimal("12")
    alic_util = ((s / Decimal("30")) * Decimal("30")) / Decimal("12")
    salario_integral = s + alic_vac + alic_util

    ari_raw = empleado.porcentaje_ari
    ari  = Decimal(str(ari_raw)) if ari_raw else Decimal("0")
    islr = r((s * ari) / Decimal("100"))

    base_sso = min(s, PARAMS["SALARIO_MINIMO_BS"] * Decimal("5"))
    base_rpe = min(s, PARAMS["SALARIO_MINIMO_BS"] * Decimal("10"))

    sso_sem = (base_sso * Decimal("12")) / Decimal("52")
    sso_e   = r(sso_sem * Decimal("0.04")  * Decimal(str(lunes_mes)))
    sso_p   = r(sso_sem * Decimal("0.10")  * Decimal(str(lunes_mes)))

    rpe_sem = (base_rpe * Decimal("12")) / Decimal("52")
    rpe_e   = r(rpe_sem * Decimal("0.005") * Decimal(str(lunes_mes)))
    rpe_p   = r(rpe_sem * Decimal("0.02")  * Decimal(str(lunes_mes)))

    faov_e = r(salario_integral * Decimal("0.01"))
    faov_p = r(salario_integral * Decimal("0.02"))

    inces_e = r(s * Decimal("0.00"))
    inces_p = r(s * Decimal("0.02"))

    tasa           = Decimal(str(tasa_bcv)) if tasa_bcv else Decimal("36.50")
    base_pensiones = max(s, PARAMS["INGRESO_MINIMO_PENSIONES_USD"] * tasa)
    pen_e = r(s * Decimal("0.00"))
    pen_p = r(base_pensiones * Decimal("0.09"))

    total_ded = islr + sso_e + rpe_e + faov_e + inces_e + pen_e
    neto  = r(s - total_ded)
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


async def _ejecutar_asiento_nomina(empresa_id: int, usuario_id: int, db: AsyncSession) -> str:
    """
    Lógica central del asiento de nómina.
    Reutilizada por el endpoint manual y el automático de 30 días.
    """
    hoy = date.today()

    result = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.empresa_id == empresa_id,
            NominaEmpleado.activo == True,
        )
    )
    empleados = result.scalars().all()
    if not empleados:
        raise HTTPException(400, detail="No hay empleados activos para generar nómina")

    tasa_bcv  = await obtener_tasa_actual(db)
    valor_bcv = tasa_bcv.tasa_usd if tasa_bcv else Decimal("36.50")
    lunes_del_mes = get_mondays_in_month(hoy.year, hoy.month)

    r    = lambda v: v.quantize(Decimal("0.01"), ROUND_HALF_UP)
    ZERO = Decimal("0")

    tot_sal_mod = tot_sal_moi = ZERO
    tot_neto = tot_sso_p = tot_faov_p = tot_inces_p = tot_pen_p = tot_rpe_p = ZERO
    tot_sso_e = tot_faov_e = tot_inces_e = tot_pen_e = tot_rpe_e = ZERO

    for emp in empleados:
        c = await calcular_nomina_empleado(emp, valor_bcv, lunes_del_mes)
        if emp.tipo == TipoNominaEnum.mod:
            tot_sal_mod += emp.salario_base
        else:
            tot_sal_moi += emp.salario_base

        tot_neto    += c.neto_a_pagar
        tot_sso_p   += c.sso_patrono
        tot_faov_p  += c.faov_patrono
        tot_inces_p += c.inces_patrono
        tot_pen_p   += c.proteccion_pensiones_pat
        tot_rpe_p   += c.rpe_patrono
        tot_sso_e   += c.sso_empleado
        tot_faov_e  += c.faov_empleado
        tot_inces_e += c.inces_empleado
        tot_pen_e   += c.proteccion_pensiones_emp
        tot_rpe_e   += c.rpe_empleado

    cuentas = await _resolver_cuentas(empresa_id, db)

    # Montos del DEBE
    d_mod       = r(tot_sal_mod)
    d_moi       = r(tot_sal_moi)
    d_aportes   = r(tot_sso_p + tot_rpe_p + tot_faov_p + tot_inces_p)
    d_pensiones = r(tot_pen_p)

    # Montos del HABER
    h_nomina_xp = r(tot_neto)
    h_ivss      = r(tot_sso_e + tot_sso_p + tot_rpe_e + tot_rpe_p)
    h_banavih   = r(tot_faov_e + tot_faov_p)
    h_inces     = r(tot_inces_e + tot_inces_p)
    h_pen_pat   = r(tot_pen_p)
    h_pen_emp   = r(tot_pen_e)

    total_debe  = r(d_mod + d_moi + d_aportes + d_pensiones)
    total_haber = r(h_nomina_xp + h_ivss + h_banavih + h_inces + h_pen_pat + h_pen_emp)

    # Absorber diferencia de redondeo en Nómina por Pagar (máx. 5 céntimos)
    diff = total_debe - total_haber
    if abs(diff) > Decimal("0.05"):
        raise HTTPException(
            500,
            detail=f"El asiento no cuadra (diferencia={diff:.2f} Bs.). Revisa los parámetros."
        )
    if diff != ZERO:
        h_nomina_xp = r(h_nomina_xp + diff)
        total_haber = total_debe

    numero = await get_proximo_numero(empresa_id, db)

    asiento = Asiento(
        empresa_id=empresa_id,
        numero_asiento=numero,
        fecha=hoy,
        mes=hoy.month,
        descripcion=f"Nómina mensual — {len(empleados)} empleado(s)",
        referencia=f"NOM-{hoy.strftime('%Y%m')}",
        total_debe=total_debe,
        total_haber=total_haber,
        cuadra=True,
        creado_por=usuario_id,
    )
    db.add(asiento)
    await db.flush()

    lineas = [
        (CUENTAS_NOMINA["MOD"],       d_mod,        ZERO),
        (CUENTAS_NOMINA["MOI"],       d_moi,        ZERO),
        (CUENTAS_NOMINA["APORTES"],   d_aportes,    ZERO),
        (CUENTAS_NOMINA["PENSIONES"], d_pensiones,  ZERO),
        (CUENTAS_NOMINA["NOMINA_XP"], ZERO,         h_nomina_xp),
        (CUENTAS_NOMINA["IVSS"],      ZERO,         h_ivss),
        (CUENTAS_NOMINA["BANAVIH"],   ZERO,         h_banavih),
        (CUENTAS_NOMINA["INCES_XP"],  ZERO,         h_inces),
        (CUENTAS_NOMINA["PEN_PAT"],   ZERO,         h_pen_pat),
        (CUENTAS_NOMINA["PEN_EMP"],   ZERO,         h_pen_emp),
    ]

    for codigo, debe, haber in lineas:
        if debe == ZERO and haber == ZERO:
            continue
        db.add(LineaAsiento(
            asiento_id=asiento.id,
            cuenta_id=cuentas[codigo].id,
            debe=r(debe),
            haber=r(haber),
        ))

    await db.commit()
    return numero


async def _programar_proximo_pago(empresa_id: int, db: AsyncSession):
    """Crea o actualiza NominaProgramacion. Próxima fecha = hoy + 30 días."""
    hoy     = date.today()
    proxima = hoy + timedelta(days=30)

    res = await db.execute(
        select(NominaProgramacion).where(NominaProgramacion.empresa_id == empresa_id)
    )
    prog = res.scalar_one_or_none()

    if prog:
        if prog.proxima_fecha <= hoy:
            prog.proxima_fecha    = proxima
            prog.ultima_ejecucion = hoy
    else:
        db.add(NominaProgramacion(
            empresa_id=empresa_id,
            proxima_fecha=proxima,
            ultima_ejecucion=hoy,
            intervalo_dias=30,
        ))
    await db.flush()


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/empleados", response_model=EmpleadoOut, status_code=201)
async def crear_empleado(
    data: EmpleadoCreate,
    background_tasks: BackgroundTasks,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db),
):
    """Alta de empleado. Programa automáticamente el primer pago a 30 días."""
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
        for key, value in data.model_dump().items():
            setattr(existing, key, value)
        existing.porcentaje_ari = Decimal(str(data.porcentaje_ari))
        existing.activo = True
        await db.flush()
        await db.commit()
        await db.refresh(existing)
        emp_out = EmpleadoOut.model_validate(existing)
    else:
        emp_data = data.model_dump()
        emp_data["porcentaje_ari"] = Decimal(str(data.porcentaje_ari))
        emp = NominaEmpleado(**emp_data, empresa_id=current_user.empresa_id)
        db.add(emp)
        await db.flush()
        await db.commit()
        await db.refresh(emp)
        emp_out = EmpleadoOut.model_validate(emp)

    await _programar_proximo_pago(current_user.empresa_id, db)
    await db.commit()
    return emp_out


@router.get("/empleados", response_model=list[EmpleadoOut])
async def listar_empleados(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    lunes: Optional[int] = Query(None, description="Forzar cantidad de lunes del mes"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    tasa_bcv  = await obtener_tasa_actual(db)
    valor_bcv = tasa_bcv.tasa_usd if tasa_bcv else Decimal("36.50")
    return [await calcular_nomina_empleado(e, valor_bcv, lunes_del_mes) for e in empleados]


@router.delete("/empleados/{emp_id}")
async def eliminar_empleado(
    emp_id: int,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.id == emp_id,
            NominaEmpleado.empresa_id == current_user.empresa_id,
        )
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, detail="Empleado no encontrado")
    emp.activo = False
    await db.commit()
    return {"message": "Empleado desactivado"}


@router.post("/generar-asiento")
async def generar_asiento_nomina(
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db),
):
    """Genera el asiento de nómina manualmente y reprograma el próximo pago a +30 días."""
    numero = await _ejecutar_asiento_nomina(
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        db=db,
    )
    await _programar_proximo_pago(current_user.empresa_id, db)
    await db.commit()
    return {
        "numero_asiento": numero,
        "mensaje": "Asiento de nómina generado correctamente",
        "proximo_pago": (date.today() + timedelta(days=30)).isoformat(),
    }


@router.get("/programacion")
async def ver_programacion_nomina(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve la fecha del próximo pago de nómina programado."""
    res = await db.execute(
        select(NominaProgramacion).where(
            NominaProgramacion.empresa_id == current_user.empresa_id
        )
    )
    prog = res.scalar_one_or_none()
    if not prog:
        return {"mensaje": "No hay nómina programada aún. Agrega empleados primero."}
    hoy  = date.today()
    dias = (prog.proxima_fecha - hoy).days
    return {
        "proxima_fecha":    prog.proxima_fecha.isoformat(),
        "ultima_ejecucion": prog.ultima_ejecucion.isoformat() if prog.ultima_ejecucion else None,
        "dias_restantes":   max(0, dias),
        "vencida":          dias < 0,
    }


@router.post("/ejecutar-automatico")
async def ejecutar_nomina_automatica(
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db),
):
    """
    Llama a este endpoint desde n8n o cron diariamente.
    Solo genera el asiento si la fecha programada ya llegó o venció.
    """
    res = await db.execute(
        select(NominaProgramacion).where(
            NominaProgramacion.empresa_id == current_user.empresa_id
        )
    )
    prog = res.scalar_one_or_none()

    if not prog:
        return {"ejecutado": False, "motivo": "No hay nómina programada"}

    hoy = date.today()
    if prog.proxima_fecha > hoy:
        dias = (prog.proxima_fecha - hoy).days
        return {
            "ejecutado": False,
            "motivo": f"Próximo pago en {dias} día(s) ({prog.proxima_fecha.isoformat()})",
        }

    numero = await _ejecutar_asiento_nomina(
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        db=db,
    )
    await _programar_proximo_pago(current_user.empresa_id, db)
    await db.commit()

    return {
        "ejecutado":      True,
        "numero_asiento": numero,
        "proximo_pago":   (hoy + timedelta(days=30)).isoformat(),
    }
