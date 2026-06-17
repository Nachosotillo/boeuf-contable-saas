"""
nomina_empleados_seed.py — Roster de los 15 empleados de El Cuadre Frío, C.A.

Estructura salarial (todo en USD, se convierte a Bs por la tasa del mes):
  · salario_base       = remun_usd × 20% × BCV   (única parte gravable y cotizable)
  · complemento_no_sal = remun_usd × 80% × BCV   (no incide en ISLR/IVSS/prestaciones)
  · cestaticket        = cesta_usd × BCV         (fijo por nivel: N1 $60/N2 $50/N3 $45/N4 $40)
Retención ISLR: %ARI verificado, aplicado SOLO sobre el salario_base (20%).
Descuentos trabajador (sobre base): IVSS 4% + RPE 0,5% + FAOV 1% = 5,5%.
Carga patronal (sobre base): 25% (IVSS 10% + RPE 2% + FAOV 2% + Pensiones 9% + INCES 2%).
cuenta_gasto = cuenta del devengo: 5.1.10 MOD · 5.1.11 CIF apoyo · 6.2.01 Admin · 6.1.01 Ventas.
"""
from decimal import Decimal
from datetime import date
from sqlalchemy import select
from models import NominaEmpleado, TipoNominaEnum

CESTA_USD = {1: 60, 2: 50, 3: 45, 4: 40}

# (cedula, nombre, cargo, remun_usd, nivel, pct_ari, tipo, cuenta_gasto)
EMPLEADOS = [
    ("27066319", "José Ignacio González Sotillo", "Director Gerente (J.I. González)", 700, 1, Decimal("29.4149"), "MOI", "6.2.01"),
    ("31065739", "Isabella De León Espinoza", "Gerente de Producción (I. de León)", 560, 2, Decimal("28.2686"), "MOI", "5.1.11"),
    ("30580232", "Julianna Amérika Chirinos Saavedra", "Gerente Administrativo (J. Chirinos)", 560, 2, Decimal("28.2686"), "MOI", "6.2.01"),
    ("18234567", "Carlos Alberto Rivas Zapata", "Chofer Distribución Norte/Este", 350, 4, Decimal("24.8298"), "MOI", "6.1.01"),
    ("25123456", "Luis Alejandro Salazar Rodríguez", "Ayudante/Despachador N°1", 250, 4, Decimal("21.1617"), "MOI", "6.1.01"),
    ("22456789", "Mariana Sofía Rojas Méndez", "Analista Adm. Integral (Compras + Inventario + Facturación)", 480, 3, Decimal("27.2974"), "MOI", "6.2.01"),
    ("24345678", "Valentina del Carmen Vargas Zambrano", "Especialista Aseg. de Calidad", 400, 3, Decimal("25.9761"), "MOI", "6.2.01"),
    ("16789012", "Roberto Manuel Castillo López", "Supervisor de Planta", 600, 2, Decimal("28.6507"), "MOD", "5.1.10"),
    ("12345678", "Antonio David Suárez Calatayud", "Maestro Panadero / Op. Masas", 550, 2, Decimal("28.1644"), "MOD", "5.1.10"),
    ("26789123", "Jesús Rafael Méndez Contreras", "Operador de Producción N°1", 275, 4, Decimal("22.3288"), "MOD", "5.1.10"),
    ("27123890", "Gabriel José Ortiz de Ordaz", "Operador de Producción N°2", 275, 4, Decimal("22.3288"), "MOD", "5.1.10"),
    ("28567234", "Manuel David Silva Rivas", "Operador de Producción N°3", 275, 4, Decimal("22.3288"), "MOD", "5.1.10"),
    ("23890123", "Alejandro José Gómez Santos", "Operador Polivalente / Control Producción", 275, 4, Decimal("22.3288"), "MOD", "5.1.10"),
    ("19456123", "Ricardo Rafael Medina Gutiérrez", "Técnico de Mantenimiento", 500, 2, Decimal("27.5809"), "MOI", "5.1.11"),
    ("29012345", "Sofía Isabel Paredes Fernández", "Cajera / Vendedora Detal", 275, 4, Decimal("22.3288"), "MOI", "6.1.01"),
]


async def sembrar_empleados(empresa_id: int, db, tasa_ref: Decimal = Decimal('57.97')):
    """Crea/actualiza los 15 empleados. `tasa_ref` solo fija el snapshot en Bs
    (salario_base, complemento, cestaticket); los asientos mensuales recalculan
    en Bs con la tasa del mes a partir de remun_usd y el nivel."""
    res = await db.execute(select(NominaEmpleado).where(NominaEmpleado.empresa_id == empresa_id))
    existentes = {e.cedula: e for e in res.scalars().all()}
    creados = actualizados = 0
    for ced, nombre, cargo, usd, nivel, pct, tipo, cta in EMPLEADOS:
        usd_d = Decimal(str(usd))
        base  = (usd_d * Decimal('0.20') * tasa_ref).quantize(Decimal('0.01'))
        comp  = (usd_d * Decimal('0.80') * tasa_ref).quantize(Decimal('0.01'))
        cesta = (Decimal(str(CESTA_USD[nivel])) * tasa_ref).quantize(Decimal('0.01'))
        tipo_enum = TipoNominaEnum.mod if tipo == 'MOD' else TipoNominaEnum.moi
        if ced in existentes:
            e = existentes[ced]
            e.nombre_completo=nombre; e.cargo=cargo; e.tipo=tipo_enum
            e.remun_total_usd=usd_d; e.nivel=nivel; e.porcentaje_ari=pct
            e.salario_base=base; e.complemento_no_salarial=comp; e.bono_alimentacion=cesta
            e.cuenta_gasto=cta; actualizados+=1
        else:
            db.add(NominaEmpleado(
                empresa_id=empresa_id, cedula=ced, nombre_completo=nombre, cargo=cargo,
                tipo=tipo_enum, remun_total_usd=usd_d, nivel=nivel, porcentaje_ari=pct,
                salario_base=base, complemento_no_salarial=comp, bono_alimentacion=cesta,
                cuenta_gasto=cta, fecha_inicio=date(2025,1,2), activo=True,
            )); creados+=1
    await db.flush()
    return {"creados": creados, "actualizados": actualizados, "total": len(EMPLEADOS)}
