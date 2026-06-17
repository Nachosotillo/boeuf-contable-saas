"""
Schemas Pydantic v2 — Validación de requests y responses
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from models import (
    TipoPersonaEnum, TipoContribuyenteEnum, RolEnum,
    TipoCuentaEnum, NaturalezaEnum, EstadoFinancieroEnum,
    TipoAjusteEnum, TipoMovimientoInvEnum, TipoArticuloInventarioEnum, TipoNominaEnum,
    OrigenAsientoEnum,
)


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: "UsuarioOut"


# ─── Empresa ──────────────────────────────────────────────────────────────────

class EmpresaCreate(BaseModel):
    nombre_razon_social: str = Field(..., min_length=2, max_length=255)
    rif: str = Field(..., pattern=r"^[JVGEjvge]-\d{7,8}-\d$")
    tipo_persona: TipoPersonaEnum
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    tipo_contribuyente: TipoContribuyenteEnum = TipoContribuyenteEnum.ordinario
    es_spe_calificado: bool = False
    fecha_inicio_ejercicio: Optional[date] = None
    fecha_fin_ejercicio: Optional[date] = None


class EmpresaOut(EmpresaCreate):
    id: int
    creado_en: datetime
    model_config = {"from_attributes": True}


# ─── Usuario ──────────────────────────────────────────────────────────────────

class UsuarioCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    rol: RolEnum = RolEnum.contador
    empresa_id: int


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    email: str
    rol: RolEnum
    empresa_id: int
    activo: bool
    model_config = {"from_attributes": True}


# ─── Catálogo ─────────────────────────────────────────────────────────────────

class CuentaCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    nombre: str = Field(..., min_length=2, max_length=255)
    descripcion: Optional[str] = None
    tipo: TipoCuentaEnum
    naturaleza: Optional[NaturalezaEnum] = None
    estado_financiero: Optional[EstadoFinancieroEnum] = None
    subcategoria: Optional[str] = None


class CuentaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    naturaleza: Optional[NaturalezaEnum] = None
    estado_financiero: Optional[EstadoFinancieroEnum] = None
    subcategoria: Optional[str] = None
    activa: Optional[bool] = None


class CuentaOut(CuentaCreate):
    id: int
    empresa_id: int
    activa: bool
    model_config = {"from_attributes": True}


# ─── Asientos ─────────────────────────────────────────────────────────────────

class LineaAsientoIn(BaseModel):
    cuenta_codigo: str
    debe: Decimal = Field(ge=0, decimal_places=2)
    haber: Decimal = Field(ge=0, decimal_places=2)
    moneda: str = "VES"
    tasa_cambio_aplicada: Optional[Decimal] = None
    descripcion: Optional[str] = None
    numero_factura: Optional[str] = None

    @field_validator("debe", "haber")
    @classmethod
    def no_negativo(cls, v):
        if v < 0:
            raise ValueError("Debe y Haber deben ser >= 0")
        return v


class AsientoCreate(BaseModel):
    fecha: date
    descripcion: Optional[str] = None
    referencia: Optional[str] = None
    origen: Optional[OrigenAsientoEnum] = None
    es_prueba: bool = False
    lineas: List[LineaAsientoIn] = Field(..., min_length=2)

    @field_validator("lineas")
    @classmethod
    def validar_cuadre(cls, lineas):
        total_debe = sum(l.debe for l in lineas)
        total_haber = sum(l.haber for l in lineas)
        if abs(total_debe - total_haber) > Decimal("0.01"):
            raise ValueError(
                f"El asiento NO cuadra: Debe={total_debe} ≠ Haber={total_haber}"
            )
        return lineas


class LineaAsientoOut(BaseModel):
    id: int
    cuenta_id: int
    cuenta_codigo: Optional[str] = None
    cuenta_nombre: Optional[str] = None
    debe: Decimal
    haber: Decimal
    moneda: str
    tasa_cambio_aplicada: Optional[Decimal] = None
    numero_factura: Optional[str] = None
    descripcion: Optional[str] = None
    folio_mayor: Optional[int] = None   # PR: folio del Mayor (se completa en la exportación)
    model_config = {"from_attributes": True}


class AsientoOut(BaseModel):
    id: int
    numero_asiento: str
    fecha: date
    mes: int
    descripcion: Optional[str]
    referencia: Optional[str]
    total_debe: Decimal
    total_haber: Decimal
    cuadra: bool
    origen: Optional[str] = None
    es_prueba: Optional[bool] = None
    lineas: List[LineaAsientoOut] = []
    model_config = {"from_attributes": True}


# ─── Ajustes ──────────────────────────────────────────────────────────────────

class LineaAjusteIn(BaseModel):
    cuenta_codigo: str
    debe: Decimal = Field(ge=0, decimal_places=2)
    haber: Decimal = Field(ge=0, decimal_places=2)
    descripcion: Optional[str] = None


class AjusteCreate(BaseModel):
    fecha: date
    descripcion: Optional[str] = None
    referencia: Optional[str] = None
    tipo: TipoAjusteEnum
    lineas: List[LineaAjusteIn] = Field(..., min_length=2)

    @field_validator("lineas")
    @classmethod
    def validar_cuadre(cls, lineas):
        total_debe = sum(l.debe for l in lineas)
        total_haber = sum(l.haber for l in lineas)
        if abs(total_debe - total_haber) > Decimal("0.01"):
            raise ValueError(f"El ajuste NO cuadra: Debe={total_debe} ≠ Haber={total_haber}")
        return lineas


class AjusteOut(BaseModel):
    id: int
    numero_ajuste: str
    fecha: date
    tipo: TipoAjusteEnum
    descripcion: Optional[str]
    total_debe: Decimal
    total_haber: Decimal
    lineas: List[LineaAjusteIn] = []
    model_config = {"from_attributes": True}


# ─── Nómina ───────────────────────────────────────────────────────────────────

class EmpleadoCreate(BaseModel):
    cedula: str = Field(..., min_length=5, max_length=20)
    nombre_completo: str = Field(..., min_length=2, max_length=255)
    cargo: Optional[str] = None
    tipo: TipoNominaEnum = TipoNominaEnum.moi
    salario_base: Decimal = Field(..., gt=0, decimal_places=2)
    bono_alimentacion: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    anos_servicio: int = Field(default=0, ge=0)
    # FIX: Se eliminó decimal_places=4 como validador estricto y se reemplaza
    # por un @field_validator que redondea explícitamente a 4 decimales.
    # Esto evita que Pydantic rechace o corrompa valores como "2.79" (2 decimales).
    porcentaje_ari: Decimal = Field(default=Decimal("0.0000"), ge=0, lt=100)
    fecha_inicio: Optional[date] = None

    @field_validator("porcentaje_ari", mode="before")
    @classmethod
    def normalizar_ari(cls, v):
        """
        Convierte el valor a Decimal con 4 decimales de precisión.
        Acepta int, float, str y Decimal. Ejemplo: "2.79" → Decimal("2.7900").
        """
        if v is None:
            return Decimal("0.0000")
        try:
            return Decimal(str(v)).quantize(Decimal("0.0001"))
        except Exception:
            raise ValueError(f"porcentaje_ari debe ser un número válido, se recibió: {v!r}")


class EmpleadoOut(EmpleadoCreate):
    id: int
    empresa_id: int
    activo: bool
    model_config = {"from_attributes": True}


class NominaCalculadaOut(BaseModel):
    empleado_id: int
    cedula: str
    nombre: str
    cargo: Optional[str]
    salario_base: Decimal
    islr_deducido: Decimal
    sso_empleado: Decimal
    faov_empleado: Decimal
    inces_empleado: Decimal
    rpe_empleado: Decimal
    proteccion_pensiones_emp: Decimal
    total_deducciones: Decimal
    neto_a_pagar: Decimal
    sso_patrono: Decimal
    faov_patrono: Decimal
    inces_patrono: Decimal
    rpe_patrono: Decimal
    proteccion_pensiones_pat: Decimal
    costo_total_empresa: Decimal


# ─── Inventario ───────────────────────────────────────────────────────────────

class ArticuloInventarioCreate(BaseModel):
    codigo_sku: str = Field(..., min_length=2, max_length=50)
    descripcion: str = Field(..., min_length=2, max_length=255)
    tipo: TipoArticuloInventarioEnum
    unidad_medida: str = "kg"
    stock_minimo: Decimal = Field(default=0, ge=0, decimal_places=4)


class ArticuloInventarioUpdate(BaseModel):
    descripcion: Optional[str] = None
    tipo: Optional[TipoArticuloInventarioEnum] = None
    unidad_medida: Optional[str] = None
    stock_minimo: Optional[Decimal] = None
    activo: Optional[bool] = None


class ArticuloInventarioOut(ArticuloInventarioCreate):
    id: int
    empresa_id: int
    stock_actual: Decimal
    activo: bool
    model_config = {"from_attributes": True}


class MovimientoInvCreate(BaseModel):
    articulo_id: int
    fecha: date
    descripcion: str
    tipo: TipoMovimientoInvEnum
    lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    cantidad: Decimal = Field(..., gt=0, decimal_places=4)
    costo_unitario: Decimal = Field(..., ge=0, decimal_places=4)


class MovimientoInvOut(MovimientoInvCreate):
    id: int
    costo_total: Decimal
    saldo_unidades: Decimal
    saldo_valor: Decimal
    model_config = {"from_attributes": True}


# ─── Activos Fijos ────────────────────────────────────────────────────────────

class ActivoFijoCreate(BaseModel):
    codigo_activo: str = Field(..., min_length=2, max_length=50)
    descripcion: str = Field(..., min_length=2, max_length=255)
    fecha_compra: date
    costo_original: Decimal = Field(..., gt=0, decimal_places=2)
    vida_util_anos: int = Field(..., gt=0)
    cuenta_activo_codigo: Optional[str] = None
    cuenta_depreciacion_codigo: Optional[str] = None


class ActivoFijoOut(ActivoFijoCreate):
    id: int
    empresa_id: int
    meses_depreciados: int
    depreciacion_acumulada: Decimal
    valor_neto: Decimal
    depreciacion_mensual: Optional[Decimal] = None
    model_config = {"from_attributes": True}


# ─── IVA ──────────────────────────────────────────────────────────────────────

class LibroIvaCompraCreate(BaseModel):
    fecha: date
    numero_factura: str
    proveedor: str
    rif_proveedor: str = Field(..., pattern=r"^[JVGEjvge]-\d{8}-\d$")
    base_imponible: Decimal = Field(..., gt=0, decimal_places=2)
    alicuota_iva: Decimal = Field(default=Decimal("0.16"), ge=0, le=1)
    paga_en_divisas: bool = False  # Activa IGTF 3%
    cliente_es_spe: bool = False   # Activa retención 75%


class LibroIvaVentaCreate(BaseModel):
    fecha: date
    numero_factura: str
    cliente: str
    rif_cliente: str
    base_imponible: Decimal = Field(..., gt=0, decimal_places=2)
    alicuota_iva: Decimal = Field(default=Decimal("0.16"), ge=0, le=1)
    cliente_es_spe: bool = False


class LibroIvaCompraOut(BaseModel):
    id: int
    fecha: date
    numero_factura: str
    proveedor: str
    rif_proveedor: str
    base_imponible: Decimal
    alicuota_iva: Decimal
    iva_credito_fiscal: Decimal
    retencion_iva_75: Decimal
    iva_neto_pagado: Decimal
    igtf_aplicado: Decimal
    total_factura: Decimal
    model_config = {"from_attributes": True}


class LibroIvaVentaOut(BaseModel):
    id: int
    fecha: date
    numero_factura: str
    cliente: str
    rif_cliente: str
    base_imponible: Decimal
    alicuota_iva: Decimal
    iva_debito_fiscal: Decimal
    retencion_iva_recibida: Decimal
    iva_neto_cobrado: Decimal
    total_factura: Decimal
    cliente_es_spe: bool
    model_config = {"from_attributes": True}


# ─── IGTF ─────────────────────────────────────────────────────────────────────

class OperacionIgtfCreate(BaseModel):
    fecha: date
    numero_operacion: str
    cliente_pagador: str
    rif: str
    moneda: str = "USD"
    tasa_bcv: Decimal = Field(..., gt=0, decimal_places=4)
    monto_divisas: Decimal = Field(..., gt=0, decimal_places=4)


class OperacionIgtfOut(OperacionIgtfCreate):
    id: int
    equivalente_bs: Decimal
    igtf_3_pct: Decimal
    model_config = {"from_attributes": True}


# ─── Retenciones ISLR ─────────────────────────────────────────────────────────

CONCEPTOS_ISLR = {
    "Honorarios Profesionales (PJ)": Decimal("0.03"),
    "Honorarios Profesionales (PN)": Decimal("0.03"),
    "Arrendamiento Inmuebles":        Decimal("0.05"),
    "Arrendamiento Muebles":          Decimal("0.03"),
    "Servicios — Contratistas PJ":    Decimal("0.02"),
    "Publicidad y Propaganda":        Decimal("0.03"),
    "Comisiones a PN":                Decimal("0.03"),
    "Intereses a PN":                 Decimal("0.03"),
}


class RetencionIslrCreate(BaseModel):
    fecha_pago: date
    numero_factura: Optional[str] = None
    beneficiario_nombre: str
    beneficiario_rif: str
    concepto: str
    monto_bruto: Decimal = Field(..., gt=0, decimal_places=2)

    @field_validator("concepto")
    @classmethod
    def validar_concepto(cls, v):
        if v not in CONCEPTOS_ISLR:
            raise ValueError(f"Concepto no válido. Opciones: {list(CONCEPTOS_ISLR.keys())}")
        return v


class RetencionIslrOut(BaseModel):
    id: int
    fecha_pago: date
    numero_factura: Optional[str]
    beneficiario_nombre: str
    beneficiario_rif: str
    concepto: str
    tasa_retencion: Decimal
    monto_bruto: Decimal
    monto_retenido: Decimal
    monto_neto_pagado: Decimal
    model_config = {"from_attributes": True}


# ─── Tasa BCV ─────────────────────────────────────────────────────────────────

class TasaBcvOut(BaseModel):
    fecha: date
    tasa_usd: Decimal
    tasa_eur: Optional[Decimal]
    fuente: str
    model_config = {"from_attributes": True}


# ─── Reportes ─────────────────────────────────────────────────────────────────

class LineaBalanceOut(BaseModel):
    codigo: str
    nombre: str
    debe: Decimal
    haber: Decimal


class BalanceComprobacionOut(BaseModel):
    periodo: str
    lineas: List[LineaBalanceOut]
    total_debe: Decimal
    total_haber: Decimal
    cuadra: bool


class LineaBalanceAjustadoOut(BaseModel):
    codigo: str
    nombre: str
    debe_bc: Decimal
    haber_bc: Decimal
    ajuste_debe: Decimal
    ajuste_haber: Decimal
    saldo_ajustado_deudor: Decimal
    saldo_ajustado_acreedor: Decimal


class BalanceAjustadoOut(BaseModel):
    periodo: str
    lineas: List[LineaBalanceAjustadoOut]
    total_deudor: Decimal
    total_acreedor: Decimal
    cuadra: bool


class LineaMayorOut(BaseModel):
    fecha: date
    numero_asiento: str
    descripcion: Optional[str]
    debe: Decimal
    haber: Decimal
    saldo_acumulado: Decimal


class MayorGeneralOut(BaseModel):
    cuenta_codigo: str
    cuenta_nombre: str
    lineas: List[LineaMayorOut]
    total_debe: Decimal
    total_haber: Decimal
    saldo_final: Decimal


class EstadoResultadoOut(BaseModel):
    ingresos: dict
    costo_ventas: Decimal
    gastos_operativos: dict
    utilidad_bruta: Decimal
    utilidad_neta: Decimal


class SituacionFinancieraOut(BaseModel):
    activo_corriente: dict
    activo_no_corriente: dict
    total_activos: Decimal
    pasivo_corriente: dict
    total_pasivos: Decimal
    patrimonio: dict
    total_patrimonio: Decimal
    ecuacion_cuadra: bool


class LiquidacionIvaOut(BaseModel):
    iva_debito_fiscal: Decimal
    iva_credito_fiscal: Decimal
    retenciones_recibidas: Decimal
    iva_neto: Decimal
    tipo: str  # "A_PAGAR" | "A_FAVOR"
