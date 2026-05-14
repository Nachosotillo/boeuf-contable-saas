"""
Modelos ORM — SQLAlchemy 2.0
Todas las tablas del sistema contable venezolano
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Numeric, Boolean, Date, DateTime,
    ForeignKey, Text, Enum as SAEnum, UniqueConstraint,
    CheckConstraint, Index, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import enum


# ─── Enumeraciones ────────────────────────────────────────────────────────────

class TipoPersonaEnum(str, enum.Enum):
    juridica = "Jurídica"
    natural = "Natural"


class TipoContribuyenteEnum(str, enum.Enum):
    ordinario = "Ordinario"
    spe = "SPE"


class RolEnum(str, enum.Enum):
    admin = "admin"
    contador = "contador"
    gerente_nomina = "gerente_nomina"
    gerente_ventas = "gerente_ventas"
    gerente_compras = "gerente_compras"
    visualizador = "visualizador"


class TipoCuentaEnum(str, enum.Enum):
    grupo = "Grupo"
    subgrupo = "Subgrupo"
    cuenta = "Cuenta"


class NaturalezaEnum(str, enum.Enum):
    deudora = "Deudora"
    acreedora = "Acreedora"


class EstadoFinancieroEnum(str, enum.Enum):
    situacion = "Situación Financiera"
    resultado = "Estado de Resultado"
    flujo = "Flujo de Caja"
    cierre = "Cierre"
    ninguno = "Ninguno"


class TipoAjusteEnum(str, enum.Enum):
    depreciacion = "depr"
    provision = "prov"
    diferimiento = "difer"
    otro = "otro"


class TipoMovimientoInvEnum(str, enum.Enum):
    entrada = "E"
    salida = "S"


class TipoArticuloInventarioEnum(str, enum.Enum):
    materia_prima = "Materia Prima"
    producto_proceso = "Producto en Proceso"
    producto_terminado = "Producto Terminado"
    suministros = "Suministros"


class TipoNominaEnum(str, enum.Enum):
    mod = "MOD"
    moi = "MOI"


class TipoFacturaEnum(str, enum.Enum):
    compra = "Compra"
    venta = "Venta"
    nota_debito = "Nota Débito"
    nota_credito = "Nota Crédito"


class AccionAuditoriaEnum(str, enum.Enum):
    crear = "CREAR"
    actualizar = "ACTUALIZAR"
    eliminar = "ELIMINAR"
    reversion = "REVERSIÓN"


# ─── Tablas principales ───────────────────────────────────────────────────────

class Empresa(Base):
    __tablename__ = "empresa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre_razon_social: Mapped[str] = mapped_column(String(255), nullable=False)
    rif: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    tipo_persona: Mapped[TipoPersonaEnum] = mapped_column(SAEnum(TipoPersonaEnum), nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(String(500))
    telefono: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    moneda_defecto: Mapped[str] = mapped_column(String(3), default="VES")
    tipo_contribuyente: Mapped[TipoContribuyenteEnum] = mapped_column(
        SAEnum(TipoContribuyenteEnum), default=TipoContribuyenteEnum.ordinario
    )
    es_spe_calificado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_inicio_ejercicio: Mapped[Optional[date]] = mapped_column(Date)
    fecha_fin_ejercicio: Mapped[Optional[date]] = mapped_column(Date)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    cuentas: Mapped[List["CatalogoCuenta"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    asientos: Mapped[List["Asiento"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    ajustes: Mapped[List["Ajuste"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    empleados: Mapped[List["NominaEmpleado"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    activos: Mapped[List["ActivoFijo"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    articulos_inventario: Mapped[List["ArticuloInventario"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    inventario: Mapped[List["MovimientoInventario"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    iva_compras: Mapped[List["LibroIvaCompra"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    iva_ventas: Mapped[List["LibroIvaVenta"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    igtf_ops: Mapped[List["OperacionIgtf"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    retenciones_islr: Mapped[List["RetencionIslr"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    parametros: Mapped[List["ParametroSistema"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    logs: Mapped[List["LogAuditoria"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolEnum] = mapped_column(SAEnum(RolEnum), default=RolEnum.visualizador)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    ultimo_acceso: Mapped[Optional[datetime]] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="usuarios")


class CatalogoCuenta(Base):
    __tablename__ = "catalogo_cuenta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    tipo: Mapped[TipoCuentaEnum] = mapped_column(SAEnum(TipoCuentaEnum), nullable=False)
    naturaleza: Mapped[Optional[NaturalezaEnum]] = mapped_column(SAEnum(NaturalezaEnum))
    estado_financiero: Mapped[Optional[EstadoFinancieroEnum]] = mapped_column(SAEnum(EstadoFinancieroEnum))
    subcategoria: Mapped[Optional[str]] = mapped_column(String(100))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    es_generada_auto: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="cuentas")
    lineas: Mapped[List["LineaAsiento"]] = relationship(back_populates="cuenta")
    lineas_ajuste: Mapped[List["LineaAjuste"]] = relationship(back_populates="cuenta")

    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_empresa_codigo"),
        Index("idx_catalogo_empresa", "empresa_id"),
    )


class Asiento(Base):
    __tablename__ = "asiento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    numero_asiento: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mes: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(500))
    referencia: Mapped[Optional[str]] = mapped_column(String(100))
    total_debe: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_haber: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    cuadra: Mapped[bool] = mapped_column(Boolean, default=False)
    reversado: Mapped[bool] = mapped_column(Boolean, default=False)
    asiento_reverso_id: Mapped[Optional[int]] = mapped_column(ForeignKey("asiento.id"))
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modificado_por: Mapped[Optional[int]] = mapped_column(ForeignKey("usuario.id"))
    modificado_en: Mapped[Optional[datetime]] = mapped_column(DateTime)

    empresa: Mapped["Empresa"] = relationship(back_populates="asientos")
    lineas: Mapped[List["LineaAsiento"]] = relationship(back_populates="asiento", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("empresa_id", "numero_asiento", name="uq_empresa_numero_asiento"),
        Index("idx_asiento_empresa_mes", "empresa_id", "mes", "fecha"),
    )


class LineaAsiento(Base):
    __tablename__ = "linea_asiento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asiento_id: Mapped[int] = mapped_column(ForeignKey("asiento.id", ondelete="CASCADE"), nullable=False, index=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("catalogo_cuenta.id"), nullable=False, index=True)
    debe: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    haber: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    moneda: Mapped[str] = mapped_column(String(3), default="VES")
    tasa_cambio_aplicada: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    descripcion: Mapped[Optional[str]] = mapped_column(String(500))
    numero_factura: Mapped[Optional[str]] = mapped_column(String(50))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    asiento: Mapped["Asiento"] = relationship(back_populates="lineas")
    cuenta: Mapped["CatalogoCuenta"] = relationship(back_populates="lineas")

    __table_args__ = (
        CheckConstraint(
            "(debe > 0 AND haber = 0) OR (debe = 0 AND haber > 0) OR (debe = 0 AND haber = 0)",
            name="chk_linea_valida"
        ),
    )


class Ajuste(Base):
    __tablename__ = "ajuste"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    numero_ajuste: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(500))
    referencia: Mapped[Optional[str]] = mapped_column(String(100))
    tipo: Mapped[TipoAjusteEnum] = mapped_column(SAEnum(TipoAjusteEnum), nullable=False)
    total_debe: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_haber: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="ajustes")
    lineas: Mapped[List["LineaAjuste"]] = relationship(back_populates="ajuste", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("empresa_id", "numero_ajuste", name="uq_empresa_numero_ajuste"),
    )


class LineaAjuste(Base):
    __tablename__ = "linea_ajuste"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ajuste_id: Mapped[int] = mapped_column(ForeignKey("ajuste.id", ondelete="CASCADE"), nullable=False, index=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("catalogo_cuenta.id"), nullable=False, index=True)
    debe: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    haber: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    descripcion: Mapped[Optional[str]] = mapped_column(String(500))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ajuste: Mapped["Ajuste"] = relationship(back_populates="lineas")
    cuenta: Mapped["CatalogoCuenta"] = relationship(back_populates="lineas_ajuste")


class NominaEmpleado(Base):
    __tablename__ = "nomina_empleado"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    cedula: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo: Mapped[Optional[str]] = mapped_column(String(100))
    tipo: Mapped[TipoNominaEnum] = mapped_column(SAEnum(TipoNominaEnum), default=TipoNominaEnum.moi)
    salario_base: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    bono_alimentacion: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    anos_servicio: Mapped[int] = mapped_column(Integer, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_inicio: Mapped[Optional[date]] = mapped_column(Date)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="empleados")
    periodos: Mapped[List["NominaPeriodo"]] = relationship(back_populates="empleado", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("empresa_id", "cedula", name="uq_empresa_cedula"),
        Index("idx_empleado_empresa", "empresa_id"),
    )


class NominaPeriodo(Base):
    __tablename__ = "nomina_periodo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("nomina_empleado.id", ondelete="CASCADE"), nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    salario_base: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    islr_deducido: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    sso_empleado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    faov_empleado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    inces_empleado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    proteccion_pensiones_emp: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_deducciones: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    neto_a_pagar: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    sso_patrono: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    faov_patrono: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    inces_patrono: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    proteccion_pensiones_pat: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    costo_total_empresa: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empleado: Mapped["NominaEmpleado"] = relationship(back_populates="periodos")

    __table_args__ = (
        UniqueConstraint("empresa_id", "empleado_id", "mes", "anio", name="uq_nomina_periodo"),
    )


class ActivoFijo(Base):
    __tablename__ = "activo_fijo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo_activo: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_compra: Mapped[date] = mapped_column(Date, nullable=False)
    costo_original: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    vida_util_anos: Mapped[int] = mapped_column(Integer, nullable=False)
    meses_depreciados: Mapped[int] = mapped_column(Integer, default=0)
    depreciacion_acumulada: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    valor_neto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    cuenta_activo_codigo: Mapped[Optional[str]] = mapped_column(String(20))
    cuenta_depreciacion_codigo: Mapped[Optional[str]] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="activos")

    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo_activo", name="uq_empresa_activo"),
    )


class ArticuloInventario(Base):
    __tablename__ = "articulo_inventario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo_sku: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[TipoArticuloInventarioEnum] = mapped_column(SAEnum(TipoArticuloInventarioEnum), nullable=False)
    unidad_medida: Mapped[str] = mapped_column(String(20), default="kg")
    stock_minimo: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    stock_actual: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="articulos_inventario")
    movimientos: Mapped[List["MovimientoInventario"]] = relationship(back_populates="articulo", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo_sku", name="uq_empresa_sku"),
    )


class MovimientoInventario(Base):
    __tablename__ = "movimiento_inventario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulo_inventario.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo: Mapped[TipoMovimientoInvEnum] = mapped_column(SAEnum(TipoMovimientoInvEnum), nullable=False)
    lote: Mapped[Optional[str]] = mapped_column(String(50))
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    costo_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    saldo_unidades: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    saldo_valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="inventario")
    articulo: Mapped["ArticuloInventario"] = relationship(back_populates="movimientos")


class LibroIvaCompra(Base):
    __tablename__ = "libro_iva_compra"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    numero_factura: Mapped[str] = mapped_column(String(100), nullable=False)
    proveedor: Mapped[str] = mapped_column(String(255), nullable=False)
    rif_proveedor: Mapped[str] = mapped_column(String(20), nullable=False)
    base_imponible: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    alicuota_iva: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.16"))
    iva_credito_fiscal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    retencion_iva_75: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    iva_neto_pagado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    igtf_aplicado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_factura: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="iva_compras")


class LibroIvaVenta(Base):
    __tablename__ = "libro_iva_venta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    numero_factura: Mapped[str] = mapped_column(String(100), nullable=False)
    cliente: Mapped[str] = mapped_column(String(255), nullable=False)
    rif_cliente: Mapped[str] = mapped_column(String(20), nullable=False)
    base_imponible: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    alicuota_iva: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.16"))
    iva_debito_fiscal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    retencion_iva_recibida: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    iva_neto_cobrado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    igtf_percibido: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_factura: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    cliente_es_spe: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="iva_ventas")


class OperacionIgtf(Base):
    __tablename__ = "operacion_igtf"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    numero_operacion: Mapped[str] = mapped_column(String(50), nullable=False)
    cliente_pagador: Mapped[str] = mapped_column(String(255), nullable=False)
    rif: Mapped[str] = mapped_column(String(20), nullable=False)
    moneda: Mapped[str] = mapped_column(String(5), nullable=False)
    tasa_bcv: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    monto_divisas: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    equivalente_bs: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    igtf_3_pct: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="igtf_ops")


class RetencionIslr(Base):
    __tablename__ = "retencion_islr"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    asiento_id: Mapped[Optional[int]] = mapped_column(ForeignKey("asiento.id"))
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    numero_factura: Mapped[Optional[str]] = mapped_column(String(50))
    beneficiario_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    beneficiario_rif: Mapped[str] = mapped_column(String(20), nullable=False)
    concepto: Mapped[str] = mapped_column(String(100), nullable=False)
    tasa_retencion: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    monto_bruto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monto_retenido: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monto_neto_pagado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    numero_comprobante: Mapped[Optional[str]] = mapped_column(String(50))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="retenciones_islr")


class TasaCambioBcv(Base):
    __tablename__ = "tasa_cambio_bcv"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    tasa_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    tasa_eur: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    tasa_cny: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    fuente: Mapped[str] = mapped_column(String(50), default="API")
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ParametroSistema(Base):
    __tablename__ = "parametro_sistema"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    clave: Mapped[str] = mapped_column(String(100), nullable=False)
    valor: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    base_legal: Mapped[Optional[str]] = mapped_column(String(500))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="parametros")

    __table_args__ = (
        UniqueConstraint("empresa_id", "clave", name="uq_empresa_clave"),
    )


class LogAuditoria(Base):
    __tablename__ = "log_auditoria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False, index=True)
    tabla_afectada: Mapped[str] = mapped_column(String(100))
    registro_id: Mapped[Optional[int]] = mapped_column(Integer)
    accion: Mapped[AccionAuditoriaEnum] = mapped_column(SAEnum(AccionAuditoriaEnum), nullable=False)
    datos_antes: Mapped[Optional[dict]] = mapped_column(JSON)
    datos_despues: Mapped[Optional[dict]] = mapped_column(JSON)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    empresa: Mapped["Empresa"] = relationship(back_populates="logs")

    __table_args__ = (
        Index("idx_auditoria_empresa_fecha", "empresa_id", "creado_en"),
    )
