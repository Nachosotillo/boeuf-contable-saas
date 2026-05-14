// ─── Auth ──────────────────────────────────────────────────────────────────

export interface Usuario {
  id: number
  nombre: string
  email: string
  rol: 'admin' | 'contador' | 'gerente_nomina' | 'gerente_ventas' | 'gerente_compras' | 'visualizador'
  empresa_id: number
  activo: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  usuario: Usuario
}

// ─── Empresa ───────────────────────────────────────────────────────────────

export interface Empresa {
  id: number
  nombre_razon_social: string
  rif: string
  tipo_persona: 'Jurídica' | 'Natural'
  direccion?: string
  telefono?: string
  email?: string
  tipo_contribuyente: 'Ordinario' | 'SPE'
  es_spe_calificado: boolean
}

// ─── Catálogo ──────────────────────────────────────────────────────────────

export interface CatalogoCuenta {
  id: number
  empresa_id: number
  codigo: string
  nombre: string
  tipo: 'Grupo' | 'Subgrupo' | 'Cuenta'
  naturaleza?: 'Deudora' | 'Acreedora'
  estado_financiero?: 'Situación Financiera' | 'Estado de Resultado' | 'Flujo de Caja' | 'Ninguno'
  subcategoria?: string
  activa: boolean
}

export interface CuentaCreate {
  codigo: string
  nombre: string
  tipo: 'Grupo' | 'Subgrupo' | 'Cuenta'
  naturaleza?: 'Deudora' | 'Acreedora'
  estado_financiero?: string
  subcategoria?: string
}

// ─── Asientos ──────────────────────────────────────────────────────────────

export interface LineaAsientoIn {
  cuenta_codigo: string
  debe: number
  haber: number
  moneda?: string
  descripcion?: string
  numero_factura?: string
}

export interface LineaAsientoOut {
  id: number
  cuenta_id: number
  cuenta_codigo?: string
  cuenta_nombre?: string
  debe: number
  haber: number
  moneda: string
}

export interface AsientoCreate {
  fecha: string
  descripcion?: string
  referencia?: string
  lineas: LineaAsientoIn[]
}

export interface AsientoOut {
  id: number
  numero_asiento: string
  fecha: string
  mes: number
  descripcion?: string
  referencia?: string
  total_debe: number
  total_haber: number
  cuadra: boolean
  lineas: LineaAsientoOut[]
}

// ─── Ajustes ───────────────────────────────────────────────────────────────

export type TipoAjuste = 'depr' | 'prov' | 'difer' | 'otro'

export interface AjusteCreate {
  fecha: string
  descripcion?: string
  referencia?: string
  tipo: TipoAjuste
  lineas: { cuenta_codigo: string; debe: number; haber: number; descripcion?: string }[]
}

export interface AjusteOut {
  id: number
  numero_ajuste: string
  fecha: string
  tipo: TipoAjuste
  descripcion?: string
  total_debe: number
  total_haber: number
}

// ─── Nómina ────────────────────────────────────────────────────────────────

export interface EmpleadoCreate {
  cedula: string
  nombre_completo: string
  cargo?: string
  tipo: 'MOD' | 'MOI'
  salario_base: number
  bono_alimentacion?: number
  anos_servicio?: number
  fecha_inicio?: string
}

export interface EmpleadoOut extends EmpleadoCreate {
  id: number
  empresa_id: number
  activo: boolean
}

export interface NominaCalculadaOut {
  empleado_id: number
  cedula: string
  nombre: string
  cargo?: string
  salario_base: number
  islr_deducido: number
  sso_empleado: number
  faov_empleado: number
  inces_empleado: number
  proteccion_pensiones_emp: number
  total_deducciones: number
  neto_a_pagar: number
  sso_patrono: number
  faov_patrono: number
  inces_patrono: number
  proteccion_pensiones_pat: number
  costo_total_empresa: number
}

// ─── Inventario ────────────────────────────────────────────────────────────

export interface MovimientoInvCreate {
  fecha: string
  descripcion: string
  tipo: 'E' | 'S'
  unidad: string
  cantidad: number
  costo_unitario: number
}

export interface MovimientoInvOut extends MovimientoInvCreate {
  id: number
  costo_total: number
  saldo_unidades: number
  saldo_valor: number
}

// ─── Activos Fijos ─────────────────────────────────────────────────────────

export interface ActivoFijoCreate {
  codigo_activo: string
  descripcion: string
  fecha_compra: string
  costo_original: number
  vida_util_anos: number
  cuenta_activo_codigo?: string
  cuenta_depreciacion_codigo?: string
}

export interface ActivoFijoOut extends ActivoFijoCreate {
  id: number
  empresa_id: number
  meses_depreciados: number
  depreciacion_acumulada: number
  valor_neto: number
  depreciacion_mensual?: number
}

// ─── IVA ───────────────────────────────────────────────────────────────────

export interface LibroIvaCompraCreate {
  fecha: string
  numero_factura: string
  proveedor: string
  rif_proveedor: string
  base_imponible: number
  alicuota_iva?: number
  paga_en_divisas?: boolean
  cliente_es_spe?: boolean
}

export interface LibroIvaCompraOut {
  id: number
  fecha: string
  numero_factura: string
  proveedor: string
  rif_proveedor: string
  base_imponible: number
  alicuota_iva: number
  iva_credito_fiscal: number
  retencion_iva_75: number
  iva_neto_pagado: number
  igtf_aplicado: number
  total_factura: number
}

export interface LibroIvaVentaCreate {
  fecha: string
  numero_factura: string
  cliente: string
  rif_cliente: string
  base_imponible: number
  alicuota_iva?: number
  cliente_es_spe?: boolean
}

export interface LibroIvaVentaOut {
  id: number
  fecha: string
  numero_factura: string
  cliente: string
  rif_cliente: string
  base_imponible: number
  alicuota_iva: number
  iva_debito_fiscal: number
  retencion_iva_recibida: number
  iva_neto_cobrado: number
  total_factura: number
  cliente_es_spe: boolean
}

export interface LiquidacionIvaOut {
  iva_debito_fiscal: number
  iva_credito_fiscal: number
  retenciones_recibidas: number
  iva_neto: number
  tipo: 'A_PAGAR' | 'A_FAVOR'
}

// ─── IGTF ──────────────────────────────────────────────────────────────────

export interface OperacionIgtfCreate {
  fecha: string
  numero_operacion: string
  cliente_pagador: string
  rif: string
  moneda: string
  tasa_bcv: number
  monto_divisas: number
}

export interface OperacionIgtfOut extends OperacionIgtfCreate {
  id: number
  equivalente_bs: number
  igtf_3_pct: number
}

// ─── Retenciones ISLR ──────────────────────────────────────────────────────

export interface RetencionIslrCreate {
  fecha_pago: string
  numero_factura?: string
  beneficiario_nombre: string
  beneficiario_rif: string
  concepto: string
  monto_bruto: number
}

export interface RetencionIslrOut {
  id: number
  fecha_pago: string
  numero_factura?: string
  beneficiario_nombre: string
  beneficiario_rif: string
  concepto: string
  tasa_retencion: number
  monto_bruto: number
  monto_retenido: number
  monto_neto_pagado: number
}

// ─── Tasas BCV ─────────────────────────────────────────────────────────────

export interface TasaBcvOut {
  fecha: string
  tasa_usd: number
  tasa_eur?: number
  fuente: string
}

// ─── Reportes ──────────────────────────────────────────────────────────────

export interface LineaBalance {
  codigo: string
  nombre: string
  debe: number
  haber: number
}

export interface BalanceComprobacion {
  periodo: string
  lineas: LineaBalance[]
  total_debe: number
  total_haber: number
  cuadra: boolean
}

export interface LineaBalanceAjustado {
  codigo: string
  nombre: string
  debe_bc: number
  haber_bc: number
  ajuste_debe: number
  ajuste_haber: number
  saldo_ajustado_deudor: number
  saldo_ajustado_acreedor: number
}

export interface BalanceAjustado {
  periodo: string
  lineas: LineaBalanceAjustado[]
  total_deudor: number
  total_acreedor: number
  cuadra: boolean
}

export interface LineaMayor {
  fecha: string
  numero_asiento: string
  descripcion?: string
  debe: number
  haber: number
  saldo_acumulado: number
}

export interface MayorGeneral {
  cuenta_codigo: string
  cuenta_nombre: string
  lineas: LineaMayor[]
  total_debe: number
  total_haber: number
  saldo_final: number
}

export interface EstadoResultado {
  ingresos: Record<string, number>
  costo_ventas: number
  gastos_operativos: Record<string, number>
  utilidad_bruta: number
  utilidad_neta: number
}

export interface SituacionFinanciera {
  activo_corriente: Record<string, number>
  activo_no_corriente: Record<string, number>
  total_activos: number
  pasivo_corriente: Record<string, number>
  total_pasivos: number
  patrimonio: Record<string, number>
  total_patrimonio: number
  ecuacion_cuadra: boolean
}
