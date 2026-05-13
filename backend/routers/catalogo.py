"""
routers/catalogo.py — Catálogo de cuentas contables
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import CatalogoCuenta, Usuario
from schemas import CuentaCreate, CuentaOut, CuentaUpdate
from routers.auth import get_current_user, require_roles

router = APIRouter()

# Catálogo default venezolano (se carga al crear empresa)
CATALOGO_DEFAULT = [
    ("1.1.01","Caja","Cuenta","Deudora","Situación Financiera"),
    ("1.1.02","Caja Chica","Cuenta","Deudora","Situación Financiera"),
    ("1.1.03","Banco — Cuenta Corriente BDV","Cuenta","Deudora","Situación Financiera"),
    ("1.1.04","Banco — Cuenta Corriente Mercantil","Cuenta","Deudora","Situación Financiera"),
    ("1.1.10","Cuentas por Cobrar — Clientes","Cuenta","Deudora","Situación Financiera"),
    ("1.1.11","Cuentas por Cobrar — Otras","Cuenta","Deudora","Situación Financiera"),
    ("1.1.15","IVA Crédito Fiscal","Cuenta","Deudora","Situación Financiera"),
    ("1.1.16","Retenciones de IVA por Recuperar","Cuenta","Deudora","Situación Financiera"),
    ("1.1.17","Retenciones de ISLR por Recuperar","Cuenta","Deudora","Situación Financiera"),
    ("1.1.20","Inventario de Materia Prima","Cuenta","Deudora","Situación Financiera"),
    ("1.1.21","Inventario Productos en Proceso","Cuenta","Deudora","Situación Financiera"),
    ("1.1.22","Inventario Productos Terminados","Cuenta","Deudora","Situación Financiera"),
    ("1.1.31","Seguros Pagados por Anticipado","Cuenta","Deudora","Situación Financiera"),
    ("1.2.05","Maquinaria y Equipos Producción","Cuenta","Deudora","Situación Financiera"),
    ("1.2.06","Depreciación Acum. — Maquinaria","Cuenta","Acreedora","Situación Financiera"),
    ("1.2.08","Equipos de Refrigeración","Cuenta","Deudora","Situación Financiera"),
    ("1.2.09","Depreciación Acum. — Refrigeración","Cuenta","Acreedora","Situación Financiera"),
    ("1.2.10","Vehículos de Distribución","Cuenta","Deudora","Situación Financiera"),
    ("1.2.11","Depreciación Acum. — Vehículos","Cuenta","Acreedora","Situación Financiera"),
    ("1.2.12","Equipos de Cómputo","Cuenta","Deudora","Situación Financiera"),
    ("1.2.15","Mobiliario y Enseres","Cuenta","Deudora","Situación Financiera"),
    ("2.1.01","Cuentas por Pagar — Proveedores","Cuenta","Acreedora","Situación Financiera"),
    ("2.1.05","IVA Débito Fiscal","Cuenta","Acreedora","Situación Financiera"),
    ("2.1.07","Retenciones ISLR por Pagar","Cuenta","Acreedora","Situación Financiera"),
    ("2.1.10","IGTF por Enterar","Cuenta","Acreedora","Situación Financiera"),
    ("2.1.11","SSO/FAOV/INCES por Pagar","Cuenta","Acreedora","Situación Financiera"),
    ("2.1.12","Protección Pensiones por Pagar","Cuenta","Acreedora","Situación Financiera"),
    ("2.1.15","Provisión para Utilidades","Cuenta","Acreedora","Situación Financiera"),
    ("2.1.16","Provisión para Vacaciones","Cuenta","Acreedora","Situación Financiera"),
    ("2.1.17","Provisión Bono Vacacional","Cuenta","Acreedora","Situación Financiera"),
    ("2.1.20","Nómina por Pagar","Cuenta","Acreedora","Situación Financiera"),
    ("3.1.01","Capital Social","Cuenta","Acreedora","Situación Financiera"),
    ("3.1.02","Reserva Legal","Cuenta","Acreedora","Situación Financiera"),
    ("4.1.01","Ventas — Productos","Cuenta","Acreedora","Estado de Resultado"),
    ("4.1.02","Ventas — Servicios","Cuenta","Acreedora","Estado de Resultado"),
    ("5.1.01","Costo de Ventas","Cuenta","Deudora","Estado de Resultado"),
    ("6.1.01","Sueldos y Salarios","Cuenta","Deudora","Estado de Resultado"),
    ("6.1.02","SSO Patronal","Cuenta","Deudora","Estado de Resultado"),
    ("6.1.03","FAOV Patronal","Cuenta","Deudora","Estado de Resultado"),
    ("6.1.04","INCES Patronal","Cuenta","Deudora","Estado de Resultado"),
    ("6.1.05","Protección Pensiones Patronal","Cuenta","Deudora","Estado de Resultado"),
    ("6.2.01","Alquiler","Cuenta","Deudora","Estado de Resultado"),
    ("6.2.02","Prestaciones Sociales","Cuenta","Deudora","Estado de Resultado"),
    ("6.2.08","Honorarios Profesionales","Cuenta","Deudora","Estado de Resultado"),
    ("6.2.09","Seguros","Cuenta","Deudora","Estado de Resultado"),
    ("6.2.10","Depreciación — Producción","Cuenta","Deudora","Estado de Resultado"),
    ("6.2.11","Depreciación — Admin./Ventas","Cuenta","Deudora","Estado de Resultado"),
    ("6.3.06","IGTF Gasto","Cuenta","Deudora","Estado de Resultado"),
]


async def sembrar_catalogo_default(empresa_id: int, db: AsyncSession):
    """Crea el catálogo de cuentas default al registrar empresa nueva."""
    from models import EstadoFinancieroEnum, NaturalezaEnum, TipoCuentaEnum
    ef_map = {"Situación Financiera": EstadoFinancieroEnum.situacion,
              "Estado de Resultado": EstadoFinancieroEnum.resultado}
    nat_map = {"Deudora": NaturalezaEnum.deudora, "Acreedora": NaturalezaEnum.acreedora}

    for codigo, nombre, tipo, nat, ef in CATALOGO_DEFAULT:
        db.add(CatalogoCuenta(
            empresa_id=empresa_id,
            codigo=codigo, nombre=nombre,
            tipo=TipoCuentaEnum.cuenta,
            naturaleza=nat_map.get(nat),
            estado_financiero=ef_map.get(ef),
            es_generada_auto=True,
        ))


@router.get("/", response_model=list[CuentaOut])
async def listar_cuentas(
    solo_activas: bool = True,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    q = select(CatalogoCuenta).where(CatalogoCuenta.empresa_id == current_user.empresa_id)
    if solo_activas:
        q = q.where(CatalogoCuenta.activa == True)
    q = q.order_by(CatalogoCuenta.codigo)
    result = await db.execute(q)
    return [CuentaOut.model_validate(c) for c in result.scalars().all()]


@router.post("/", response_model=CuentaOut, status_code=201)
async def crear_cuenta(
    data: CuentaCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.empresa_id == current_user.empresa_id,
            CatalogoCuenta.codigo == data.codigo,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, detail=f"Ya existe la cuenta {data.codigo}")

    cuenta = CatalogoCuenta(**data.model_dump(), empresa_id=current_user.empresa_id)
    db.add(cuenta)
    await db.flush()
    return CuentaOut.model_validate(cuenta)


@router.put("/{cuenta_id}", response_model=CuentaOut)
async def actualizar_cuenta(
    cuenta_id: int,
    data: CuentaUpdate,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.id == cuenta_id,
            CatalogoCuenta.empresa_id == current_user.empresa_id,
        )
    )
    cuenta = result.scalar_one_or_none()
    if not cuenta:
        raise HTTPException(404, detail="Cuenta no encontrada")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(cuenta, field, value)
    return CuentaOut.model_validate(cuenta)


@router.delete("/{cuenta_id}", status_code=204)
async def desactivar_cuenta(
    cuenta_id: int,
    current_user: Usuario = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CatalogoCuenta).where(
            CatalogoCuenta.id == cuenta_id,
            CatalogoCuenta.empresa_id == current_user.empresa_id,
        )
    )
    cuenta = result.scalar_one_or_none()
    if not cuenta:
        raise HTTPException(404)
    cuenta.activa = False
