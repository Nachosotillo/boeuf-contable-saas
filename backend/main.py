"""
Boeuf Contable SaaS — Backend API
Python 3.11+ | FastAPI | PostgreSQL | SQLAlchemy 2.0
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from database import engine, Base, AsyncSessionLocal
from routers import (
    auth, empresas, catalogo, asientos, ajustes,
    reportes, seniat, nomina, inventario, activos,
    iva, igtf, retenciones, tasas
)
from tasks.scheduler import start_scheduler

# Configurar logs básicos
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Crear tablas si no existen
    logger.info("Verificando tablas de base de datos...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Crear admin por defecto (con manejo de errores para no tumbar la app)
    try:
        from sqlalchemy import select
        from models import Usuario, Empresa, TipoPersonaEnum, RolEnum
        from routers.auth import hash_password
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Usuario).limit(1))
            if not result.scalar_one_or_none():
                logger.info("Base de datos vacía. Creando usuario admin inicial...")
                empresa = Empresa(
                    nombre_razon_social="Empresa Demo C.A.", 
                    rif="J-12345678-9",
                    tipo_persona=TipoPersonaEnum.juridica
                )
                db.add(empresa)
                await db.flush()
                
                admin = Usuario(
                    nombre="Administrador",
                    email="admin@boeuf.com",
                    contrasena_hash=hash_password("admin123"),
                    rol=RolEnum.admin,
                    empresa_id=empresa.id
                )
                db.add(admin)
                await db.commit()
                logger.info(">>> Usuario admin creado: admin@boeuf.com / admin123")
    except Exception as e:
        logger.error(f"Error en la creación del usuario semilla: {e}")
    
    # 3. Iniciar scheduler (tasa BCV diaria)
    start_scheduler()
    yield

app = FastAPI(
    title="Boeuf Contable SaaS",
    description="Sistema contable multitenant para PyMES venezolanas",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Autenticación"])
app.include_router(empresas.router,     prefix="/api/v1/empresas",     tags=["Empresas"])
app.include_router(catalogo.router,     prefix="/api/v1/catalogo",     tags=["Catálogo de Cuentas"])
app.include_router(asientos.router,     prefix="/api/v1/asientos",     tags=["Asientos"])
app.include_router(ajustes.router,      prefix="/api/v1/ajustes",      tags=["Ajustes"])
app.include_router(reportes.router,     prefix="/api/v1/reportes",     tags=["Reportes"])
app.include_router(seniat.router,       prefix="/api/v1/seniat",       tags=["SENIAT"])
app.include_router(nomina.router,       prefix="/api/v1/nomina",       tags=["Nómina"])
app.include_router(inventario.router,   prefix="/api/v1/inventario",   tags=["Inventario"])
app.include_router(activos.router,      prefix="/api/v1/activos",      tags=["Activos Fijos"])
app.include_router(iva.router,          prefix="/api/v1/iva",          tags=["IVA"])
app.include_router(igtf.router,         prefix="/api/v1/igtf",         tags=["IGTF"])
app.include_router(retenciones.router,  prefix="/api/v1/retenciones",  tags=["Retenciones ISLR"])
app.include_router(tasas.router,        prefix="/api/v1/tasas",        tags=["Tasas BCV"])

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": "Boeuf Contable SaaS v1.0.0"}
