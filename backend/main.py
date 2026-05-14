"""
Boeuf Contable SaaS — Backend API
Python 3.11+ | FastAPI | PostgreSQL | SQLAlchemy 2.0
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base, AsyncSessionLocal
from routers import (
    auth, empresas, catalogo, asientos, ajustes,
    reportes, seniat, nomina, inventario, activos,
    iva, igtf, retenciones, tasas
)
from tasks.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas si no existen
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Crear admin por defecto si no hay usuarios
    from sqlalchemy import select
    from models import Usuario, Empresa
    from routers.auth import hash_password
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Usuario).limit(1))
        if not result.scalar_one_or_none():
            # Crear empresa semilla
            empresa = Empresa(nombre="Empresa Demo C.A.", rif="J-12345678-9")
            db.add(empresa)
            await db.flush()
            # Crear admin semilla
            admin = Usuario(
                nombre="Administrador",
                email="admin@boeuf.com",
                contrasena_hash=hash_password("admin123"),
                rol="admin",
                empresa_id=empresa.id
            )
            db.add(admin)
            await db.commit()
            print(">>> Usuario admin inicial creado: admin@boeuf.com / admin123")

    # Iniciar scheduler (tasa BCV diaria)
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
    allow_origins=["*"],          # En producción: ["https://tudominio.com"]
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
