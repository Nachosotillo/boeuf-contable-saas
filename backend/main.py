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
    # 0. Migración forzada automática (añadir columnas faltantes)
    try:
        from update_db import migrate
        await migrate()
    except Exception as e:
        logger.warning(f"Error en migración forzada: {e}")

    # 1. Crear tablas si no existen
    logger.info("Verificando tablas de base de datos...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Crear usuarios y empresas por defecto
    try:
        from sqlalchemy import select
        from models import Usuario, Empresa, TipoPersonaEnum, RolEnum
        from routers.auth import hash_password
        from routers.catalogo import sembrar_catalogo_default
        
        async with AsyncSessionLocal() as db:
            # Crear "El Cuadre Frío C.A."
            result1 = await db.execute(select(Usuario).where(Usuario.email == "usuario@elcuadrefrio.com"))
            if not result1.scalar_one_or_none():
                logger.info("Creando cuenta para El Cuadre Frío C.A...")
                emp_cuadre = Empresa(
                    nombre_razon_social="El Cuadre Frío C.A.", 
                    rif="J-11111111-1",
                    tipo_persona=TipoPersonaEnum.juridica
                )
                db.add(emp_cuadre)
                await db.flush()
                
                admin_cuadre = Usuario(
                    nombre="Usuario",
                    email="usuario@elcuadrefrio.com",
                    contrasena_hash=hash_password("cuadre123"),
                    rol=RolEnum.admin,
                    empresa_id=emp_cuadre.id
                )
                db.add(admin_cuadre)
                await sembrar_catalogo_default(emp_cuadre.id, db)
                await db.commit()
                logger.info(">>> Creado: usuario@elcuadrefrio.com / cuadre123")

            # Crear "Rickyricon"
            result2 = await db.execute(select(Usuario).where(Usuario.email == "ricky@rickyricon.com"))
            if not result2.scalar_one_or_none():
                logger.info("Creando cuenta para Rickyricon...")
                emp_ricky = Empresa(
                    nombre_razon_social="Rickyricon C.A.", 
                    rif="J-98765432-1",
                    tipo_persona=TipoPersonaEnum.juridica
                )
                db.add(emp_ricky)
                await db.flush()
                
                admin_ricky = Usuario(
                    nombre="Ricky (Admin)",
                    email="ricky@rickyricon.com",
                    contrasena_hash=hash_password("ricky123"),
                    rol=RolEnum.admin,
                    empresa_id=emp_ricky.id
                )
                db.add(admin_ricky)
                await sembrar_catalogo_default(emp_ricky.id, db)
                await db.commit()
                logger.info(">>> Creado: ricky@rickyricon.com / ricky123")

    except Exception as e:
        logger.error(f"Error en la creación de cuentas semilla: {e}")
    
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

@app.get("/debug", tags=["Health"])
async def debug_db():
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import select, text
        from models import Usuario, Empresa
        
        async with AsyncSessionLocal() as db:
            result_users = await db.execute(select(Usuario.email, Usuario.nombre))
            users = result_users.fetchall()
            
            result_empresas = await db.execute(select(Empresa.nombre_razon_social))
            empresas = result_empresas.fetchall()
            
            # Check if tables exist
            tables_res = await db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = [t[0] for t in tables_res.fetchall()]
            
            return {
                "status": "ok",
                "tables_count": len(tables),
                "tables": tables,
                "users": [{"email": u[0], "nombre": u[1]} for u in users],
                "empresas": [e[0] for e in empresas]
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}
