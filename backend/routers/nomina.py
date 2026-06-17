"""
Router: Nómina — El Cuadre Frío

Genera la secuencia de 4 asientos mensuales del plan, valorados a la tasa BCV del
mes (forward-fill por fecha). Estructura 20% salarial / 80% no salarial + cestaticket.
Cargas patronales y retenciones SOLO sobre el salario base (20%).

Asientos por mes (todos vía crear_asiento_interno, origen='nomina'):
  1) DEVENGO        DEBE 5.1.10/5.1.11/6.2.01/6.1.01 (bruto por función)
                    HABER 2.1.10 neto · 2.1.11.01 IVSS 4% · 2.1.11.02 FAOV 1%
                          · 2.1.23 RPE 0,5% · 2.1.30 ISLR (si aplica)
  2) APORTES PAT.   DEBE mismas cuentas de función (14% = IVSS 10 + FAOV 2 + RPE 2)
                    HABER 2.1.11.01 · 2.1.11.02 · 2.1.23
  3) PENSIONES 9%   DEBE 6.2.20 · HABER 2.1.12
  4) PAGO DEL NETO  DEBE 2.1.10 · HABER cuenta_pago (2.2.10 socios / 1.1.03 banco)

INCES 2%, prestaciones (Art.142) e intereses (Art.143) son TRIMESTRALES → cierre.

El %ARI es entrada MANUAL por empleado (campo porcentaje_ari); el código lo aplica,
no lo calcula. `aplicar_islr=False` reproduce el plan (sin retención de ISLR).
"""
from typing import Optional
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import (
    NominaEmpleado, NominaProgramacion, Usuario,
    TipoNominaEnum, OrigenAsientoEnum,
)
from schemas import EmpleadoCreate, EmpleadoOut, NominaCalculadaOut
from routers.auth import get_current_user, require_roles
from routers.asientos import crear_asiento_interno
from routers.tasas import obtener_tasa_para_fecha

router = APIRouter()
R = lambda v: Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)
ZERO = Decimal("0")

# Cestaticket en USD por nivel (se convierte a Bs por la tasa del mes)
CESTA_USD = {1: Decimal("60"), 2: Decimal("50"), 3: Decimal("45"), 4: Decimal("40")}

# Alícuotas planas sobre el salario base (20%)
DED_EMP = {"IVSS": Decimal("0.04"), "FAOV": Decimal("0.01"), "RPE": Decimal("0.005")}
APO_PAT = {"IVSS": Decimal("0.10"), "FAOV": Decimal("0.02"), "RPE": Decimal("0.02")}
PEN_PAT = Decimal("0.09")

# Cuentas de pasivo de nómina
C_NETO   = "2.1.10"      # Nómina por Pagar
C_IVSS   = "2.1.11.01"   # IVSS — aporte patronal y obrero
C_FAOV   = "2.1.11.02"   # BANAVIH / FAOV
C_RPE    = "2.1.23"      # Otras Retenciones de Nómina (RPE)
C_ISLR   = "2.1.30"      # ISLR por Pagar
C_PEN_G  = "6.2.20"      # Contribución Pensiones 9% (gasto)
C_PEN_P  = "2.1.12"      # Protección Pensiones por Pagar — Patronal


def _cuenta_func(emp: NominaEmpleado) -> str:
    if emp.cuenta_gasto:
        return emp.cuenta_gasto
    return "5.1.10" if emp.tipo == TipoNominaEnum.mod else "6.2.01"


def _calc_emp(emp: NominaEmpleado, tasa: Decimal, aplicar_islr: bool) -> dict:
    """Calcula los montos en Bs de un empleado para una tasa dada."""
    usd = emp.remun_total_usd or ZERO
    base  = R(usd * Decimal("0.20") * tasa)
    comp  = R(usd * Decimal("0.80") * tasa)
    cesta = R(CESTA_USD.get(emp.nivel or 4, Decimal("40")) * tasa)
    bruto = R(base + comp + cesta)

    islr  = R(base * (emp.porcentaje_ari or ZERO) / Decimal("100")) if aplicar_islr else ZERO
    ivss_e = R(base * DED_EMP["IVSS"])
    faov_e = R(base * DED_EMP["FAOV"])
    rpe_e  = R(base * DED_EMP["RPE"])
    ded_e  = R(islr + ivss_e + faov_e + rpe_e)
    neto   = R(bruto - ded_e)

    ivss_p = R(base * APO_PAT["IVSS"])
    faov_p = R(base * APO_PAT["FAOV"])
    rpe_p  = R(base * APO_PAT["RPE"])
    pen_p  = R(base * PEN_PAT)

    return dict(func=_cuenta_func(emp), base=base, comp=comp, cesta=cesta, bruto=bruto,
                islr=islr, ivss_e=ivss_e, faov_e=faov_e, rpe_e=rpe_e, neto=neto,
                ivss_p=ivss_p, faov_p=faov_p, rpe_p=rpe_p, pen_p=pen_p)


async def _empleados_activos(empresa_id: int, db: AsyncSession):
    res = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.empresa_id == empresa_id,
            NominaEmpleado.activo == True,
        )
    )
    return res.scalars().all()


async def generar_nomina_mes(
    db: AsyncSession, *, empresa_id: int, usuario_id: int, fecha: date,
    cuenta_pago: str = "2.2.10", aplicar_islr: bool = False, es_prueba: bool = False,
) -> list[str]:
    """Genera los 4 asientos de la nómina del mes de `fecha`. Devuelve sus números."""
    empleados = await _empleados_activos(empresa_id, db)
    if not empleados:
        raise HTTPException(400, "No hay empleados activos para generar nómina")

    tasa_rec = await obtener_tasa_para_fecha(db, fecha)
    if not tasa_rec:
        raise HTTPException(503, "No hay tasa BCV para la fecha. Ejecuta /tasas/seed-2025.")
    tasa = tasa_rec.tasa_usd

    calc = [_calc_emp(e, tasa, aplicar_islr) for e in empleados]
    periodo = fecha.strftime("%m/%Y")

    # Acumular por función y totales
    bruto_func = defaultdict(lambda: ZERO)
    cargapat_func = defaultdict(lambda: ZERO)
    t = defaultdict(lambda: ZERO)
    for c in calc:
        bruto_func[c["func"]] += c["bruto"]
        cargapat_func[c["func"]] += R(c["ivss_p"] + c["faov_p"] + c["rpe_p"])
        for k in ("neto", "islr", "ivss_e", "faov_e", "rpe_e",
                  "ivss_p", "faov_p", "rpe_p", "pen_p"):
            t[k] += c[k]

    numeros = []

    # ── 1) DEVENGO ─────────────────────────────────────────────────────────────
    lineas = [{"cuenta_codigo": f, "debe": R(m), "haber": 0,
               "descripcion": "Devengo bruto (base+complemento+cestaticket)"}
              for f, m in sorted(bruto_func.items())]
    lineas += [
        {"cuenta_codigo": C_NETO, "debe": 0, "haber": R(t["neto"]), "descripcion": "Neto a pagar"},
        {"cuenta_codigo": C_IVSS, "debe": 0, "haber": R(t["ivss_e"]), "descripcion": "IVSS retención obrero 4%"},
        {"cuenta_codigo": C_FAOV, "debe": 0, "haber": R(t["faov_e"]), "descripcion": "FAOV retención obrero 1%"},
        {"cuenta_codigo": C_RPE,  "debe": 0, "haber": R(t["rpe_e"]),  "descripcion": "RPE retención obrero 0,5%"},
    ]
    if aplicar_islr and t["islr"] > 0:
        lineas.append({"cuenta_codigo": C_ISLR, "debe": 0, "haber": R(t["islr"]),
                       "descripcion": "ISLR retenido (ARI s/ base 20%)"})
    a = await crear_asiento_interno(
        db, empresa_id=empresa_id, usuario_id=usuario_id, fecha=fecha,
        origen=OrigenAsientoEnum.nomina, es_prueba=es_prueba,
        descripcion=f"Devengo de nómina {periodo}", referencia=f"NOM-{fecha:%Y%m}-DEV",
        lineas=lineas)
    numeros.append(a.numero_asiento)

    # ── 2) APORTES PATRONALES (14%) ────────────────────────────────────────────
    lineas = [{"cuenta_codigo": f, "debe": R(m), "haber": 0,
               "descripcion": "Carga patronal IVSS+FAOV+RPE (14%)"}
              for f, m in sorted(cargapat_func.items())]
    lineas += [
        {"cuenta_codigo": C_IVSS, "debe": 0, "haber": R(t["ivss_p"]), "descripcion": "IVSS aporte patronal 10%"},
        {"cuenta_codigo": C_FAOV, "debe": 0, "haber": R(t["faov_p"]), "descripcion": "FAOV aporte patronal 2%"},
        {"cuenta_codigo": C_RPE,  "debe": 0, "haber": R(t["rpe_p"]),  "descripcion": "RPE aporte patronal 2%"},
    ]
    a = await crear_asiento_interno(
        db, empresa_id=empresa_id, usuario_id=usuario_id, fecha=fecha,
        origen=OrigenAsientoEnum.nomina, es_prueba=es_prueba,
        descripcion=f"Aportes patronales de nómina {periodo}", referencia=f"NOM-{fecha:%Y%m}-PAT",
        lineas=lineas)
    numeros.append(a.numero_asiento)

    # ── 3) PENSIONES 9% ────────────────────────────────────────────────────────
    if t["pen_p"] > 0:
        a = await crear_asiento_interno(
            db, empresa_id=empresa_id, usuario_id=usuario_id, fecha=fecha,
            origen=OrigenAsientoEnum.nomina, es_prueba=es_prueba,
            descripcion=f"Contribución Protección Pensiones 9% {periodo}",
            referencia=f"NOM-{fecha:%Y%m}-PEN",
            lineas=[
                {"cuenta_codigo": C_PEN_G, "debe": R(t["pen_p"]), "haber": 0,
                 "descripcion": "Pensiones 9% s/ base"},
                {"cuenta_codigo": C_PEN_P, "debe": 0, "haber": R(t["pen_p"]),
                 "descripcion": "Pensiones por pagar patronal"},
            ])
        numeros.append(a.numero_asiento)

    # ── 4) PAGO DEL NETO ───────────────────────────────────────────────────────
    a = await crear_asiento_interno(
        db, empresa_id=empresa_id, usuario_id=usuario_id, fecha=fecha,
        origen=OrigenAsientoEnum.nomina, es_prueba=es_prueba,
        descripcion=f"Pago neto de nómina {periodo}", referencia=f"NOM-{fecha:%Y%m}-PAGO",
        lineas=[
            {"cuenta_codigo": C_NETO,     "debe": R(t["neto"]), "haber": 0,
             "descripcion": "Cancelación nómina por pagar"},
            {"cuenta_codigo": cuenta_pago, "debe": 0, "haber": R(t["neto"]),
             "descripcion": "Pago del neto al personal"},
        ])
    numeros.append(a.numero_asiento)

    return numeros


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/empleados", response_model=EmpleadoOut, status_code=201)
async def crear_empleado(
    data: EmpleadoCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.empresa_id == current_user.empresa_id,
            NominaEmpleado.cedula == data.cedula,
        )
    )
    emp = res.scalar_one_or_none()
    payload = data.model_dump()
    if emp:
        for k, v in payload.items():
            setattr(emp, k, v)
        emp.activo = True
    else:
        emp = NominaEmpleado(**payload, empresa_id=current_user.empresa_id)
        db.add(emp)
    await db.flush()
    await db.commit()
    await db.refresh(emp)
    return EmpleadoOut.model_validate(emp)


@router.get("/empleados", response_model=list[EmpleadoOut])
async def listar_empleados(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.empresa_id == current_user.empresa_id,
            NominaEmpleado.activo == True,
        ).order_by(NominaEmpleado.nombre_completo)
    )
    return [EmpleadoOut.model_validate(e) for e in res.scalars().all()]


@router.delete("/empleados/{emp_id}")
async def eliminar_empleado(
    emp_id: int,
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(NominaEmpleado).where(
            NominaEmpleado.id == emp_id,
            NominaEmpleado.empresa_id == current_user.empresa_id,
        )
    )
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, "Empleado no encontrado")
    emp.activo = False
    await db.commit()
    return {"mensaje": "Empleado desactivado"}


@router.get("/calcular", response_model=list[NominaCalculadaOut])
async def calcular_nomina(
    fecha: date = Query(default_factory=date.today),
    aplicar_islr: bool = Query(False),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vista previa (no persiste) de la nómina a la tasa de `fecha`."""
    empleados = await _empleados_activos(current_user.empresa_id, db)
    tasa_rec = await obtener_tasa_para_fecha(db, fecha)
    tasa = tasa_rec.tasa_usd if tasa_rec else Decimal("57.97")
    out = []
    for e in empleados:
        c = _calc_emp(e, tasa, aplicar_islr)
        out.append(NominaCalculadaOut(
            empleado_id=e.id, cedula=e.cedula, nombre=e.nombre_completo, cargo=e.cargo,
            salario_base=c["base"], islr_deducido=c["islr"],
            sso_empleado=c["ivss_e"], faov_empleado=c["faov_e"], inces_empleado=ZERO,
            rpe_empleado=c["rpe_e"], proteccion_pensiones_emp=ZERO,
            total_deducciones=R(c["islr"] + c["ivss_e"] + c["faov_e"] + c["rpe_e"]),
            neto_a_pagar=c["neto"],
            sso_patrono=c["ivss_p"], faov_patrono=c["faov_p"], inces_patrono=ZERO,
            rpe_patrono=c["rpe_p"], proteccion_pensiones_pat=c["pen_p"],
            costo_total_empresa=R(c["bruto"] + c["ivss_p"] + c["faov_p"] + c["rpe_p"] + c["pen_p"]),
        ))
    return out


@router.post("/generar-asiento")
async def generar_asiento_nomina(
    fecha: date = Query(default_factory=date.today, description="Fecha del mes (toma la tasa BCV de esa fecha)"),
    cuenta_pago: str = Query("2.2.10", description="2.2.10 socios (ene) o 1.1.03 Banco BDV (feb+)"),
    aplicar_islr: bool = Query(False, description="True retiene el %ARI sobre la base 20% (default: plan, sin ISLR)"),
    current_user: Usuario = Depends(require_roles("admin", "contador", "gerente_nomina")),
    db: AsyncSession = Depends(get_db),
):
    """Genera los 4 asientos de la nómina del mes y los persiste."""
    numeros = await generar_nomina_mes(
        db, empresa_id=current_user.empresa_id, usuario_id=current_user.id,
        fecha=fecha, cuenta_pago=cuenta_pago, aplicar_islr=aplicar_islr,
    )
    await _programar_proximo_pago(current_user.empresa_id, fecha, db)
    await db.commit()
    return {"asientos": numeros, "mensaje": f"Nómina {fecha:%m/%Y} generada ({len(numeros)} asientos)"}


async def _programar_proximo_pago(empresa_id: int, fecha: date, db: AsyncSession):
    proxima = fecha + timedelta(days=30)
    res = await db.execute(
        select(NominaProgramacion).where(NominaProgramacion.empresa_id == empresa_id)
    )
    prog = res.scalar_one_or_none()
    if prog:
        prog.proxima_fecha = proxima
        prog.ultima_ejecucion = fecha
    else:
        db.add(NominaProgramacion(empresa_id=empresa_id, proxima_fecha=proxima,
                                  ultima_ejecucion=fecha, intervalo_dias=30))
    await db.flush()


@router.get("/programacion")
async def ver_programacion(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(NominaProgramacion).where(NominaProgramacion.empresa_id == current_user.empresa_id)
    )
    prog = res.scalar_one_or_none()
    if not prog:
        return {"mensaje": "No hay nómina programada aún."}
    hoy = date.today()
    return {
        "proxima_fecha": prog.proxima_fecha.isoformat(),
        "ultima_ejecucion": prog.ultima_ejecucion.isoformat() if prog.ultima_ejecucion else None,
        "dias_restantes": max(0, (prog.proxima_fecha - hoy).days),
        "vencida": prog.proxima_fecha < hoy,
    }
