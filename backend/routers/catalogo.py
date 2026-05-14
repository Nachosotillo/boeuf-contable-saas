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
    """Crea el catálogo de cuentas default al registrar empresa nueva."""
    from models import EstadoFinancieroEnum, NaturalezaEnum, TipoCuentaEnum
    ef_map = {"Situación Financiera": EstadoFinancieroEnum.situacion,
              "Estado de Resultado": EstadoFinancieroEnum.resultado}
    nat_map = {"Deudora": NaturalezaEnum.deudora, "Acreedora": NaturalezaEnum.acreedora}

    for codigo, nombre, tipo, nat, ef, subcat in CATALOGO_DEFAULT:
        # Mapeo de Tipo
        tipo_enum = TipoCuentaEnum.cuenta
        if tipo.lower() == "grupo":
            tipo_enum = TipoCuentaEnum.grupo
        elif tipo.lower() == "subgrupo":
            tipo_enum = TipoCuentaEnum.subgrupo
            
        db.add(CatalogoCuenta(
            empresa_id=empresa_id,
            codigo=codigo, nombre=nombre,
            tipo=tipo_enum,
            naturaleza=nat_map.get(nat) if nat else None,
            estado_financiero=ef_map.get(ef) if ef else None,
            subcategoria=subcat if subcat else None,
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
