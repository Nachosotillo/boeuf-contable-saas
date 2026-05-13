"""
routers/empresas.py
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Empresa, Usuario
from schemas import EmpresaCreate, EmpresaOut
from routers.auth import get_current_user, require_roles

router = APIRouter()


@router.get("/me", response_model=EmpresaOut)
async def mi_empresa(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Empresa).where(Empresa.id == current_user.empresa_id))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(404)
    return EmpresaOut.model_validate(empresa)


@router.put("/me", response_model=EmpresaOut)
async def actualizar_empresa(
    data: EmpresaCreate,
    current_user: Usuario = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Empresa).where(Empresa.id == current_user.empresa_id))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(404)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(empresa, field, value)
    return EmpresaOut.model_validate(empresa)
