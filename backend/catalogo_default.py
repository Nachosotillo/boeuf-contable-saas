"""
Catálogo de cuentas contables — El Cuadre Frío C.A.
Empresa de producción y distribución de alimentos congelados.

Cuentas nuevas añadidas (marcadas con [NUEVO]):
  - Nómina: 2.1.10 corregido, 2.1.22, 2.1.23 ya existían
  - Logística: 6.1.06, 6.1.07, 6.1.08 (combustible, mantenimiento vehículos, peajes)
  - Alquileres: 5.1.10 ya existía (planta), 6.2.03 ya existía (oficinas),
    + 6.1.09 (alquiler depósito/distribución) [NUEVO]
  - Servicios básicos planta: 5.1.11 ya existía
  - Cadena de frío: 5.1.16 [NUEVO]
  - Cuentas de bancos adicionales: 1.1.06 [NUEVO]
  - Anticipos a proveedores: 1.1.32 [NUEVO]
  - Préstamo accionistas: 2.2.10 [NUEVO]
  - Dividendos por pagar: 2.1.35 [NUEVO]
"""

CATALOGO_DEFAULT = [
    # ── ACTIVOS ───────────────────────────────────────────────────────────────
    ("1",         "ACTIVOS",                                    "Grupo",    "",          "",                      ""),
    ("1.1",       "ACTIVO CORRIENTE",                           "Subgrupo", "",          "",                      "Activo Corriente"),

    # Caja y Bancos
    ("1.1.01",    "Caja",                                       "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.02",    "Caja Chica",                                 "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.03",    "Banco — Cuenta Corriente BDV",               "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.04",    "Banco — Cuenta Corriente Mercantil",         "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.05",    "Banco — Cuenta de Ahorros",                  "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.06",    "Banco — Cuenta en Divisas (USD)",            "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),   # [NUEVO]

    # Cuentas por cobrar
    ("1.1.10",    "Cuentas por Cobrar — Clientes",              "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.11",    "Cuentas por Cobrar — Otras",                 "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.12",    "Provisión Cuentas Incobrables",              "Cuenta",   "Acreedora", "Situación Financiera",  "Activo Corriente"),

    # Impuestos por recuperar
    ("1.1.15",    "IVA Crédito Fiscal",                         "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.16",    "Retenciones de IVA por Recuperar",           "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.17",    "Retenciones de ISLR por Recuperar",          "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.18",    "Impuestos y Cargas Sociales por Recuperar",  "Grupo",    "",          "Situación Financiera",  "Activo Corriente"),
    ("1.1.18.01", "IVA Crédito Fiscal por Recuperar",           "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.18.02", "ISLR por Recuperar — Compras",               "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.18.03", "Retenciones IVA por Recuperar",              "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.18.04", "Protección Pensiones — Aporte Retenido",     "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.40",    "Aporte Fondo Pensiones por Recuperar",       "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),

    # Inventarios
    ("1.1.20",    "INVENTARIO DE MATERIA PRIMA",                "Grupo",    "",          "Situación Financiera",  "Activo Corriente"),
    ("1.1.20.01", "Inventario Inicial — MP",                    "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.20.02", "Inventario Final — MP",                      "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.21",    "INVENTARIO DE PRODUCTOS EN PROCESO",         "Grupo",    "",          "Situación Financiera",  "Activo Corriente"),
    ("1.1.21.01", "Inventario Inicial — PEP",                   "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.21.02", "Inventario Final — PEP",                     "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.22",    "INVENTARIO DE PRODUCTOS TERMINADOS",         "Grupo",    "",          "Situación Financiera",  "Activo Corriente"),
    ("1.1.22.01", "Inventario Inicial — PT",                    "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.22.02", "Inventario Final — PT",                      "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.25",    "Materiales y Suministros de Planta",         "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),

    # Anticipos y prepagados
    ("1.1.30",    "Gastos Pagados por Anticipado",              "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.31",    "Seguros Pagados por Anticipado",             "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),
    ("1.1.32",    "Anticipos a Proveedores",                    "Cuenta",   "Deudora",   "Situación Financiera",  "Activo Corriente"),   # [NUEVO]

    # Activo No Corriente
    ("1.2",       "ACTIVO NO CORRIENTE",                        "Subgrupo", "",          "",                      "Activo No Corriente"),
    ("1.2.01",    "Terrenos",                                   "Cuenta",   "Deudora",   "Situación Financiera",  "Activo No Corriente"),
    ("1.2.02",    "Edificio / Planta de Producción",            "Cuenta",   "Deudora",   "Situación Financiera",  "Activo No Corriente"),
    ("1.2.03",    "Depreciación Acum. — Edificio",              "Cuenta",   "Acreedora", "Situación Financiera",  "Activo No Corriente"),
    ("1.2.05",    "Maquinaria y Equipos de Producción",         "Cuenta",   "Deudora",   "Situación Financiera",  "Activo No Corriente"),
    ("1.2.06",    "Depreciación Acum. — Maquinaria",            "Cuenta",   "Acreedora", "Situación Financiera",  "Activo No Corriente"),
    ("1.2.08",    "Equipos de Refrigeración / Congelación",     "Cuenta",   "Deudora",   "Situación Financiera",  "Activo No Corriente"),
    ("1.2.09",    "Depreciación Acum. — Refrigeración",         "Cuenta",   "Acreedora", "Situación Financiera",  "Activo No Corriente"),
    ("1.2.10",    "Vehículos de Distribución",                  "Cuenta",   "Deudora",   "Situación Financiera",  "Activo No Corriente"),
    ("1.2.11",    "Depreciación Acum. — Vehículos",             "Cuenta",   "Acreedora", "Situación Financiera",  "Activo No Corriente"),
    ("1.2.12",    "Equipos de Cómputo",                         "Cuenta",   "Deudora",   "Situación Financiera",  "Activo No Corriente"),
    ("1.2.13",    "Depreciación Acum. — Cómputo",               "Cuenta",   "Acreedora", "Situación Financiera",  "Activo No Corriente"),
    ("1.2.15",    "Mobiliario y Enseres",                       "Cuenta",   "Deudora",   "Situación Financiera",  "Activo No Corriente"),
    ("1.2.16",    "Depreciación Acum. — Mobiliario",            "Cuenta",   "Acreedora", "Situación Financiera",  "Activo No Corriente"),
    ("1.2.20",    "Activos Intangibles — Marcas",               "Cuenta",   "Deudora",   "Situación Financiera",  "Activo No Corriente"),
    ("1.2.21",    "Amortización Acum. — Intangibles",           "Cuenta",   "Acreedora", "Situación Financiera",  "Activo No Corriente"),

    # ── PASIVOS ───────────────────────────────────────────────────────────────
    ("2",         "PASIVOS",                                    "Grupo",    "",          "",                      ""),
    ("2.1",       "PASIVO CORRIENTE",                           "Subgrupo", "",          "",                      "Pasivo Corriente"),
    ("2.1.01",    "Cuentas por Pagar — Proveedores",            "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.02",    "Cuentas por Pagar — Otras",                  "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.05",    "IVA Débito Fiscal",                          "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.06",    "Retenciones de IVA por Enterar",             "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.07",    "Retenciones de ISLR por Enterar",            "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.08",    "Retenciones de IGTF por Enterar",            "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.09",    "Impuesto Municipal (IAE) por Pagar",         "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),

    # Nómina y cargas sociales
    ("2.1.10",    "Nómina por Pagar",                           "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.11",    "Retenciones y Aportes por Pagar",            "Subgrupo", "",          "",                      "Pasivo Corriente"),
    ("2.1.11.01", "Retenciones y Aportes IVSS",                 "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.11.02", "Retenciones y Aportes BANAVIH",              "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.12",    "Protección Pensiones por Pagar",             "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.13",    "INCES por Pagar",                            "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.14",    "IGTF Percibido por Enterar",                 "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.15",    "Provisión para Utilidades",                  "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.16",    "Provisión para Vacaciones",                  "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.17",    "Provisión para Bono Vacacional",             "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.18",    "Prestaciones Sociales por Pagar (Fideicomiso)","Cuenta", "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.21",    "IGTF por Enterar — Cobros en Divisas",       "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.22",    "Protección de Pensiones por Pagar",          "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.23",    "Retención Protección Pensiones — Empleados", "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),

    # Anticipos y otros pasivos corrientes
    ("2.1.20",    "Anticipos de Clientes",                      "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.25",    "Préstamos Bancarios — Corto Plazo",          "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.30",    "ISLR por Pagar",                             "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),
    ("2.1.35",    "Dividendos por Pagar",                       "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),   # [NUEVO]

    # Alquileres por pagar (planta + depósito + oficina)
    ("2.1.40",    "Alquiler Planta por Pagar",                  "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),   # [NUEVO]
    ("2.1.41",    "Alquiler Depósito / Distribución por Pagar", "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),   # [NUEVO]
    ("2.1.42",    "Alquiler Oficinas Administrativas por Pagar","Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo Corriente"),   # [NUEVO]

    # Pasivo No Corriente
    ("2.2",       "PASIVO NO CORRIENTE",                        "Subgrupo", "",          "",                      "Pasivo No Corriente"),
    ("2.2.01",    "Préstamos Bancarios — Largo Plazo",          "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo No Corriente"),
    ("2.2.05",    "Obligaciones por Arrendamiento Financiero",  "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo No Corriente"),
    ("2.2.10",    "Préstamos de Accionistas",                   "Cuenta",   "Acreedora", "Situación Financiera",  "Pasivo No Corriente"),  # [NUEVO]

    # ── PATRIMONIO ────────────────────────────────────────────────────────────
    ("3",         "PATRIMONIO",                                 "Grupo",    "",          "",                      ""),
    ("3.1.01",    "Capital Social",                             "Cuenta",   "Acreedora", "Situación Financiera",  "Patrimonio"),
    ("3.1.02",    "Reserva Legal",                              "Cuenta",   "Acreedora", "Situación Financiera",  "Patrimonio"),
    ("3.1.03",    "Reserva Estatutaria",                        "Cuenta",   "Acreedora", "Situación Financiera",  "Patrimonio"),
    ("3.1.04",    "Ajuste por Inflación — Patrimonio",          "Cuenta",   "Acreedora", "Situación Financiera",  "Patrimonio"),
    ("3.1.05",    "Utilidades Retenidas de Ejercicios Anteriores","Cuenta", "Acreedora", "Situación Financiera",  "Patrimonio"),
    ("3.1.06",    "Pérdidas Acumuladas",                        "Cuenta",   "Deudora",   "Situación Financiera",  "Patrimonio"),
    ("3.1.08",    "REI — Reexpresión por Inflación",            "Cuenta",   "Acreedora", "Situación Financiera",  "Patrimonio"),

    # ── INGRESOS ──────────────────────────────────────────────────────────────
    ("4",         "INGRESOS",                                   "Grupo",    "",          "",                      ""),
    ("4.1",       "INGRESOS OPERACIONALES",                     "Subgrupo", "",          "",                      "Ingresos Operacionales"),
    ("4.1.01",    "Ventas — Tequeños",                          "Cuenta",   "Acreedora", "Estado de Resultado",   "Ingresos Operacionales"),
    ("4.1.02",    "Ventas — Pasapalos",                         "Cuenta",   "Acreedora", "Estado de Resultado",   "Ingresos Operacionales"),
    ("4.1.03",    "Ventas — Masas",                             "Cuenta",   "Acreedora", "Estado de Resultado",   "Ingresos Operacionales"),
    ("4.1.05",    "Devoluciones en Ventas",                     "Cuenta",   "Deudora",   "Estado de Resultado",   "Ingresos Operacionales"),
    ("4.1.06",    "Descuentos en Ventas",                       "Cuenta",   "Deudora",   "Estado de Resultado",   "Ingresos Operacionales"),
    ("4.2",       "OTROS INGRESOS",                             "Subgrupo", "",          "",                      "Otros Ingresos"),
    ("4.2.01",    "Intereses Ganados",                          "Cuenta",   "Acreedora", "Estado de Resultado",   "Otros Ingresos"),
    ("4.2.02",    "Ganancia en Venta de Activos",               "Cuenta",   "Acreedora", "Estado de Resultado",   "Otros Ingresos"),
    ("4.2.03",    "Ingresos Varios",                            "Cuenta",   "Acreedora", "Estado de Resultado",   "Otros Ingresos"),
    ("4.2.04",    "Ganancia en Diferencial Cambiario",          "Cuenta",   "Acreedora", "Estado de Resultado",   "Otros Ingresos"),
    ("4.3.01",    "Ganancia Monetaria por Inflación",           "Cuenta",   "Acreedora", "Estado de Resultado",   "Ajuste Inflación"),

    # ── COSTOS DE PRODUCCIÓN ──────────────────────────────────────────────────
    ("5",         "COSTOS DE PRODUCCIÓN",                       "Grupo",    "",          "",                      ""),
    ("5.1.01",    "Materia Prima Usada en Producción",          "Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Producción"),
    ("5.1.02",    "Mano de Obra Directa",                       "Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Producción"),
    ("5.1.10",    "Costos Ind. de Fabricación — Arrendamiento", "Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Producción"),
    ("5.1.11",    "Costos Ind. de Fabricación — Servicios",     "Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Producción"),
    ("5.1.12",    "Costos Ind. de Fabricación — Depreciaciones","Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Producción"),
    ("5.1.13",    "Costos Ind. de Fabricación — Mantenimiento", "Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Producción"),
    ("5.1.14",    "Costos Ind. de Fabricación — Otros",         "Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Producción"),
    ("5.1.15",    "CIF Aplicados (contrapartida)",              "Cuenta",   "Acreedora", "Estado de Resultado",   "Costo de Producción"),
    ("5.1.16",    "Costos de Cadena de Frío — Transporte",      "Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Producción"),  # [NUEVO]
    ("5.1.20",    "Costo de Ventas — Tequeños",                 "Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Ventas"),
    ("5.1.21",    "Costo de Ventas — Pasapalos",                "Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Ventas"),
    ("5.1.22",    "Costo de Ventas — Masas",                    "Cuenta",   "Deudora",   "Estado de Resultado",   "Costo de Ventas"),

    # ── GASTOS ────────────────────────────────────────────────────────────────
    ("6",         "GASTOS",                                     "Grupo",    "",          "",                      ""),

    # Gastos de Ventas y Distribución
    ("6.1",       "GASTOS DE VENTAS",                           "Subgrupo", "",          "",                      "Gastos de Ventas"),
    ("6.1.01",    "Sueldos y Salarios — Ventas",                "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos de Ventas"),
    ("6.1.02",    "Comisiones sobre Ventas",                    "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos de Ventas"),
    ("6.1.03",    "Publicidad y Mercadeo",                      "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos de Ventas"),
    ("6.1.04",    "Fletes y Distribución",                      "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos de Ventas"),
    ("6.1.05",    "Empaques y Materiales de Distribución",      "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos de Ventas"),
    ("6.1.06",    "Combustible — Flota de Distribución",        "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos de Ventas"),   # [NUEVO]
    ("6.1.07",    "Mantenimiento y Reparación de Vehículos",    "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos de Ventas"),   # [NUEVO]
    ("6.1.08",    "Peajes y Viáticos de Distribución",          "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos de Ventas"),   # [NUEVO]
    ("6.1.09",    "Alquiler — Depósito / Centro de Distribución","Cuenta",  "Deudora",   "Estado de Resultado",   "Gastos de Ventas"),   # [NUEVO]

    # Gastos Administrativos
    ("6.2",       "GASTOS ADMINISTRATIVOS",                     "Subgrupo", "",          "",                      "Gastos Administrativos"),
    ("6.2.01",    "Sueldos y Salarios — Administración",        "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.02",    "Prestaciones Sociales — Administración",     "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.03",    "Alquiler de Oficinas",                       "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.04",    "Servicios Públicos (electricidad, agua, gas)","Cuenta",  "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.05",    "Telefonía e Internet",                       "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.06",    "Papelería y Útiles de Oficina",              "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.07",    "Gastos de Representación",                   "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.08",    "Honorarios Profesionales",                   "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.09",    "Seguros",                                    "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.10",    "Depreciación — Administrativos",             "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.11",    "Amortización — Intangibles",                 "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.12",    "Gastos Bancarios",                           "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.13",    "Impuestos Municipales (Patente)",            "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.14",    "Multas y Sanciones",                         "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.15",    "Gastos Varios Administrativos",              "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.16",    "Impuesto Municipal IAE",                     "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.17",    "Impuesto a los Grandes Patrimonios (IGP)",   "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.18",    "Antigüedad LOTTT (Art. 142)",                "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.19",    "Intereses sobre Prestaciones Sociales",      "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.20",    "Contribución Protección de Pensiones — 9%",  "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),
    ("6.2.21",    "Alquiler — Planta de Producción",            "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Administrativos"),  # [NUEVO]

    # Gastos Financieros
    ("6.3",       "GASTOS FINANCIEROS",                         "Subgrupo", "",          "",                      "Gastos Financieros"),
    ("6.3.01",    "Intereses sobre Préstamos",                  "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Financieros"),
    ("6.3.02",    "Comisiones Bancarias",                       "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Financieros"),
    ("6.3.03",    "Pérdida en Venta de Activos",                "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Financieros"),
    ("6.3.04",    "IGTF Pagado (Gasto no deducible ISLR)",      "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Financieros"),
    ("6.3.05",    "Pérdida en Diferencial Cambiario",           "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Financieros"),
    ("6.3.06",    "IGTF — Gasto Generado en Compras",           "Cuenta",   "Deudora",   "Estado de Resultado",   "Gastos Financieros"),

    # ISLR
    ("6.4",       "IMPUESTO SOBRE LA RENTA",                    "Subgrupo", "",          "",                      "ISLR"),
    ("6.4.01",    "Impuesto sobre la Renta (ISLR) Estimado",    "Cuenta",   "Deudora",   "Estado de Resultado",   "ISLR"),

    # Ajuste por Inflación
    ("6.5.01",    "Pérdida Monetaria por Inflación",            "Cuenta",   "Deudora",   "Estado de Resultado",   "Ajuste Inflación"),

    # ── CUENTAS DE CIERRE ─────────────────────────────────────────────────────
    ("7",         "CUENTAS DE CIERRE",                          "Grupo",    "",          "",                      ""),
    ("7.1.01",    "Resumen de Pérdidas y Ganancias",            "Cuenta",   "Deudora",   "Cierre",                "Cierre"),
]
