"""
plantillas_seed.py — Plantillas de asiento recurrentes de El Cuadre Frío.

Todo está denominado en USD; al instanciar se multiplica por la tasa BCV del mes,
de modo que cada plantilla cuadra por construcción (Σ debe USD == Σ haber USD).

Plantillas:
  SERV-FIJOS       (mensual)    Gastos fijos de servicios + IVA C.F. (servicios gravados)
  CIERRE-INCES     (trimestral) INCES 2% sobre salarios del trimestre
  CIERRE-PRESTAC   (trimestral) Prestaciones Art. 142 LOTTT (15 días salario integral)
  CIERRE-INTERESES (trimestral) Intereses Art. 143 LOTTT

IVA: marco como GRAVADOS alquiler, internet, vigilancia, honorarios, combustible,
fumigación/mantenimientos/EPP; EXENTOS agua y electricidad (servicios públicos).
Ajusta la lista GRAVADO_USD si tu cátedra clasifica distinto.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from sqlalchemy import select
from models import (PlantillaAsiento, LineaPlantilla, OrigenAsientoEnum,
                    PeriodicidadEnum)
from routers.asientos import crear_asiento_interno

R = lambda v: Decimal(str(v)).quantize(Decimal("0.01"), ROUND_HALF_UP)

# ── Gastos fijos mensuales (USD), consolidados por cuenta ────────────────────
SERV_DEBE = [
    ("6.2.03", Decimal("850"), "Alquiler planta de producción", True),
    ("6.2.22", Decimal("55"),  "Agua potable",                   False),
    ("6.2.05", Decimal("107"), "Internet empresarial + web",     True),
    ("6.2.04", Decimal("212"), "Electricidad + generador",       False),
    ("6.2.17", Decimal("220"), "Vigilancia y seguridad 24/7",    True),
    ("6.2.08", Decimal("310"), "Honorarios contador + legal",    True),
    ("6.1.06", Decimal("141"), "Combustible y logística distrib.",True),
    ("6.2.15", Decimal("434"), "Fumigación + mant. planta/cava + EPP", True),
]  # (cuenta, usd, desc, gravado)
IVA_ALIC = Decimal("0.16")
GRAVADO_USD = sum(u for _, u, _, g in SERV_DEBE if g)         # 2.062
IVA_USD     = R(GRAVADO_USD * IVA_ALIC)                       # 329.92
TOTAL_SERV  = R(sum(u for _, u, _, _ in SERV_DEBE) + IVA_USD) # 2.658,92

PLANTILLAS = [
    {
        "codigo": "SERV-FIJOS", "nombre": "Gastos fijos mensuales (servicios)",
        "periodicidad": PeriodicidadEnum.mensual, "origen": OrigenAsientoEnum.servicios,
        "lineas": (
            [(c, True, u, d) for c, u, d, _ in SERV_DEBE]
            + [("1.1.15", True, IVA_USD, "IVA crédito fiscal servicios gravados"),
               ("2.2.10", False, TOTAL_SERV, "Pago (socios ene / Banco feb+)")]
        ),
    },
    {
        "codigo": "CIERRE-INCES", "nombre": "INCES 2% del trimestre",
        "periodicidad": PeriodicidadEnum.trimestral, "origen": OrigenAsientoEnum.impuesto,
        "lineas": [("6.2.21", True, Decimal("75.90"), "Contribución INCES 2% s/ salarios trimestre"),
                   ("2.1.13", False, Decimal("75.90"), "INCES por pagar")],
    },
    {
        "codigo": "CIERRE-PRESTAC", "nombre": "Prestaciones Art. 142 LOTTT (trimestre)",
        "periodicidad": PeriodicidadEnum.trimestral, "origen": OrigenAsientoEnum.nomina,
        "lineas": [("6.2.18", True, Decimal("711.56"), "Garantía antigüedad 15 días salario integral"),
                   ("2.1.18", False, Decimal("711.56"), "Prestaciones sociales — fideicomiso")],
    },
    {
        "codigo": "CIERRE-INTERESES", "nombre": "Intereses prestaciones Art. 143 LOTTT (trimestre)",
        "periodicidad": PeriodicidadEnum.trimestral, "origen": OrigenAsientoEnum.nomina,
        "lineas": [("6.2.19", True, Decimal("21.35"), "Intereses sobre prestaciones (3% ref.)"),
                   ("2.1.18", False, Decimal("21.35"), "Prestaciones sociales — fideicomiso (intereses)")],
    },
]


async def sembrar_plantillas(empresa_id: int, db) -> dict:
    """Crea/actualiza las plantillas recurrentes. Idempotente por (empresa, codigo)."""
    res = await db.execute(select(PlantillaAsiento).where(PlantillaAsiento.empresa_id == empresa_id))
    existentes = {p.codigo: p for p in res.scalars().all()}
    creadas = 0
    for pl in PLANTILLAS:
        if pl["codigo"] in existentes:
            obj = existentes[pl["codigo"]]
            for ln in list(obj.lineas):
                await db.delete(ln)
            await db.flush()
        else:
            obj = PlantillaAsiento(empresa_id=empresa_id, codigo=pl["codigo"])
            db.add(obj); creadas += 1
        obj.nombre = pl["nombre"]; obj.origen = pl["origen"]
        obj.periodicidad = pl["periodicidad"]; obj.activa = True
        await db.flush()
        for orden, (cta, es_debe, usd, desc) in enumerate(pl["lineas"]):
            db.add(LineaPlantilla(plantilla_id=obj.id, orden=orden, cuenta_codigo=cta,
                                  es_debe=es_debe, monto_usd=usd, descripcion=desc))
    await db.flush()
    return {"creadas": creadas, "total": len(PLANTILLAS)}


async def instanciar_plantilla(
    db, *, empresa_id: int, usuario_id: int, codigo: str, fecha: date, tasa: Decimal,
    cuenta_pago_override: str | None = None, es_prueba: bool = False,
):
    """Convierte una plantilla en un Asiento real a la tasa dada (USD × tasa)."""
    res = await db.execute(
        select(PlantillaAsiento).where(
            PlantillaAsiento.empresa_id == empresa_id,
            PlantillaAsiento.codigo == codigo, PlantillaAsiento.activa == True,
        )
    )
    pl = res.scalar_one_or_none()
    if not pl:
        raise ValueError(f"Plantilla {codigo} no encontrada")
    lineas = []
    for ln in pl.lineas:
        cta = ln.cuenta_codigo
        if cuenta_pago_override and not ln.es_debe and cta == "2.2.10":
            cta = cuenta_pago_override
        monto = R((ln.monto_usd or Decimal("0")) * tasa)
        lineas.append({"cuenta_codigo": cta,
                       "debe": monto if ln.es_debe else 0,
                       "haber": 0 if ln.es_debe else monto,
                       "descripcion": ln.descripcion})
    return await crear_asiento_interno(
        db, empresa_id=empresa_id, usuario_id=usuario_id, fecha=fecha,
        origen=pl.origen, es_prueba=es_prueba, descripcion=pl.nombre,
        referencia=f"{pl.codigo}-{fecha:%Y%m}", lineas=lineas)
