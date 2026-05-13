"""
Boeuf Contable SaaS — Backend API
Python 3.11+ | FastAPI | PostgreSQL | SQLAlchemy 2.0
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base
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
