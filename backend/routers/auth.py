"""
Router: Autenticación (JWT)
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import get_db
from models import Usuario, Empresa
from schemas import UsuarioCreate, UsuarioOut, TokenResponse, EmpresaCreate
from config import settings

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Usuario).where(Usuario.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.activo:
        raise credentials_exception
    return user


def require_roles(*roles):
    """Dependency que valida que el usuario tenga uno de los roles requeridos."""
    async def _check(current_user: Usuario = Depends(get_current_user)):
        if current_user.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol requerido: {roles}. Tu rol: {current_user.rol}"
            )
        return current_user
    return _check


@router.post("/registro", response_model=TokenResponse, status_code=201)
async def registro(
    empresa_data: EmpresaCreate,
    usuario_data: UsuarioCreate,
    db: AsyncSession = Depends(get_db)
):
    """Registro de nueva empresa + usuario admin."""
    # Verificar RIF único
    existing = await db.execute(select(Empresa).where(Empresa.rif == empresa_data.rif))
    if existing.scalar_one_or_none():
        raise HTTPException(400, detail=f"Ya existe una empresa con RIF {empresa_data.rif}")

    # Verificar email único
    existing_user = await db.execute(select(Usuario).where(Usuario.email == usuario_data.email))
    if existing_user.scalar_one_or_none():
        raise HTTPException(400, detail="El email ya está registrado")

    # Crear empresa
    empresa = Empresa(**empresa_data.model_dump())
    db.add(empresa)
    await db.flush()  # Para obtener empresa.id

    # Crear usuario admin
    usuario = Usuario(
        empresa_id=empresa.id,
        nombre=usuario_data.nombre,
        email=usuario_data.email,
        contrasena_hash=hash_password(usuario_data.password),
        rol="admin",
    )
    db.add(usuario)
    await db.flush()

    token = create_access_token({"sub": str(usuario.id), "empresa_id": empresa.id})
    return TokenResponse(
        access_token=token,
        usuario=UsuarioOut.model_validate(usuario)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login con email y contraseña."""
    result = await db.execute(select(Usuario).where(Usuario.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.contrasena_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    if not user.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")

    user.ultimo_acceso = datetime.utcnow()
    token = create_access_token({"sub": str(user.id), "empresa_id": user.empresa_id})
    return TokenResponse(
        access_token=token,
        usuario=UsuarioOut.model_validate(user)
    )


@router.get("/me", response_model=UsuarioOut)
async def me(current_user: Usuario = Depends(get_current_user)):
    return current_user
