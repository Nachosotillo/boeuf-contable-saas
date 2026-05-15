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

from catalogo_default import CATALOGO_DEFAULT


async def sembrar_catalogo_default(empresa_id: int, db: AsyncSession):
    """
    Crea o actualiza el catálogo de cuentas para una empresa.
    Usa lógica UPSERT: si la cuenta ya existe por código, actualiza nombre
    y metadatos (por si el catálogo cambió). Si no existe, la crea.
    Así es seguro llamarlo en cada redeploy sin generar duplicados.
    """
    from models import EstadoFinancieroEnum, NaturalezaEnum, TipoCuentaEnum

    ef_map = {
        "Situación Financiera": EstadoFinancieroEnum.situacion,
        "Estado de Resultado":  EstadoFinancieroEnum.resultado,
        "Cierre":               EstadoFinancieroEnum.cierre,
        "Ninguno":              EstadoFinancieroEnum.ninguno,
    }
    nat_map = {
        "Deudora":   NaturalezaEnum.deudora,
        "Acreedora": NaturalezaEnum.acreedora,
    }
    tipo_map = {
        "grupo":    TipoCuentaEnum.grupo,
        "subgrupo": TipoCuentaEnum.subgrupo,
        "cuenta":   TipoCuentaEnum.cuenta,
    }

    # Cargar todas las cuentas existentes de esta empresa de una sola vez
    res = await db.execute(
        select(CatalogoCuenta).where(CatalogoCuenta.empresa_id == empresa_id)
    )
    existentes = {c.codigo: c for c in res.scalars().all()}

    for codigo, nombre, tipo, nat, ef, subcat in CATALOGO_DEFAULT:
        tipo_enum = tipo_map.get(tipo.lower(), TipoCuentaEnum.cuenta)
        nat_enum  = nat_map.get(nat) if nat else None
        ef_enum   = ef_map.get(ef)   if ef  else None
        subcat_val = subcat if subcat else None

        if codigo in existentes:
            # Actualizar campos que pueden haber cambiado entre versiones
            c = existentes[codigo]
            c.nombre              = nombre
            c.tipo                = tipo_enum
            c.naturaleza          = nat_enum
            c.estado_financiero   = ef_enum
            c.subcategoria        = subcat_val
            # No tocamos activa ni es_generada_auto para no pisar ediciones manuales
        else:
            db.add(CatalogoCuenta(
                empresa_id=empresa_id,
                codigo=codigo,
                nombre=nombre,
                tipo=tipo_enum,
                naturaleza=nat_enum,
                estado_financiero=ef_enum,
                subcategoria=subcat_val,
                es_generada_auto=True,
            ))


@router.get("/", response_model=list[CuentaOut])
async def listar_cuentas(
    solo_activas: bool = True,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(CatalogoCuenta).where(
        CatalogoCuenta.empresa_id == current_user.empresa_id
    )
    if solo_activas:
        q = q.where(CatalogoCuenta.activa == True)
    q = q.order_by(CatalogoCuenta.codigo)
    result = await db.execute(q)
    return [CuentaOut.model_validate(c) for c in result.scalars().all()]


@router.post("/", response_model=CuentaOut, status_code=201)
async def crear_cuenta(
    data: CuentaCreate,
    current_user: Usuario = Depends(require_roles("admin", "contador")),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
