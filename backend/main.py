"""
Boeuf Contable SaaS — Backend API
Python 3.11+ | FastAPI | PostgreSQL | SQLAlchemy 2.0

FLUJO DE DEPLOY CORRECTO (Render + Neon):
  1. En Neon SQL Editor:
       DROP SCHEMA public CASCADE;
       CREATE SCHEMA public;
  2. Push a GitHub → Render detecta el cambio y redeploy automático.
  3. Al arrancar, este lifespan:
       a) Corre migrate() — añade columnas/tablas faltantes
       b) Corre create_all — crea tablas nuevas (nomina_programacion, etc.)
       c) Siembra catálogo con UPSERT (no duplica cuentas en redeployS)
       d) Inicia scheduler BCV

  Si los empleados siguen apareciendo tras el DROP:
  → Render tiene el proceso cacheado. Haz "Clear build cache & deploy" en
    el dashboard de Render, NO solo "Manual deploy".
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    # ── Paso 1: migraciones incrementales (columnas/tablas nuevas) ────────────
    try:
        from update_db import migrate
        await migrate()
    except Exception as e:
        logger.warning(f"Error en migración incremental: {e}")

    # ── Paso 2: crear tablas que no existen (incluye nomina_programacion) ─────
    logger.info("Verificando/creando tablas...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tablas OK.")

    # ── Paso 3: sembrar datos iniciales ───────────────────────────────────────
    # sembrar_catalogo_default ahora usa UPSERT:
    #   - Primera vez: crea todas las cuentas
    #   - Redeploysp posteriores: actualiza nombres/metadatos, no duplica
    try:
        from sqlalchemy import select
        from models import Usuario, Empresa, TipoPersonaEnum, RolEnum
        from routers.auth import hash_password
        from routers.catalogo import sembrar_catalogo_default

        async with AsyncSessionLocal() as db:

            # ── El Cuadre Frío C.A. ──────────────────────────────────────────
            res = await db.execute(
                select(Usuario).where(Usuario.email == "usuario@elcuadrefrio.com")
            )
            if not res.scalar_one_or_none():
                logger.info("Creando El Cuadre Frío C.A. (primera vez)...")
                emp = Empresa(
                    nombre_razon_social="El Cuadre Frío C.A.",
                    rif="J-11111111-1",
                    tipo_persona=TipoPersonaEnum.juridica,
                )
                db.add(emp)
                await db.flush()
                db.add(Usuario(
                    nombre="Usuario",
                    email="usuario@elcuadrefrio.com",
                    contrasena_hash=hash_password("cuadre123"),
                    rol=RolEnum.admin,
                    empresa_id=emp.id,
                ))
                await sembrar_catalogo_default(emp.id, db)
                await db.commit()
                logger.info(">>> usuario@elcuadrefrio.com / cuadre123")
            else:
                # Empresa ya existe → actualizar catálogo con cuentas nuevas
                res_emp = await db.execute(
                    select(Empresa).where(Empresa.rif == "J-11111111-1")
                )
                emp = res_emp.scalar_one_or_none()
                if emp:
                    await sembrar_catalogo_default(emp.id, db)
                    await db.commit()
                    logger.info("Catálogo El Cuadre Frío actualizado (upsert).")

            # ── Rickyricon C.A. ──────────────────────────────────────────────
            res2 = await db.execute(
                select(Usuario).where(Usuario.email == "ricky@rickyricon.com")
            )
            if not res2.scalar_one_or_none():
                logger.info("Creando Rickyricon C.A. (primera vez)...")
                emp2 = Empresa(
                    nombre_razon_social="Rickyricon C.A.",
                    rif="J-98765432-1",
                    tipo_persona=TipoPersonaEnum.juridica,
                )
                db.add(emp2)
                await db.flush()
                db.add(Usuario(
                    nombre="Ricky (Admin)",
                    email="ricky@rickyricon.com",
                    contrasena_hash=hash_password("ricky123"),
                    rol=RolEnum.admin,
                    empresa_id=emp2.id,
                ))
                await sembrar_catalogo_default(emp2.id, db)
                await db.commit()
                logger.info(">>> ricky@rickyricon.com / ricky123")
            else:
                res_emp2 = await db.execute(
                    select(Empresa).where(Empresa.rif == "J-98765432-1")
                )
                emp2 = res_emp2.scalar_one_or_none()
                if emp2:
                    await sembrar_catalogo_default(emp2.id, db)
                    await db.commit()
                    logger.info("Catálogo Rickyricon actualizado (upsert).")

    except Exception as e:
        logger.error(f"Error en siembra inicial: {e}")

    # ── Paso 4: scheduler de tasa BCV ─────────────────────────────────────────
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

app.include_router(auth.router,        prefix="/api/v1/auth",        tags=["Autenticación"])
app.include_router(empresas.router,    prefix="/api/v1/empresas",    tags=["Empresas"])
app.include_router(catalogo.router,    prefix="/api/v1/catalogo",    tags=["Catálogo de Cuentas"])
app.include_router(asientos.router,    prefix="/api/v1/asientos",    tags=["Asientos"])
app.include_router(ajustes.router,     prefix="/api/v1/ajustes",     tags=["Ajustes"])
app.include_router(reportes.router,    prefix="/api/v1/reportes",    tags=["Reportes"])
app.include_router(seniat.router,      prefix="/api/v1/seniat",      tags=["SENIAT"])
app.include_router(nomina.router,      prefix="/api/v1/nomina",      tags=["Nómina"])
app.include_router(inventario.router,  prefix="/api/v1/inventario",  tags=["Inventario"])
app.include_router(activos.router,     prefix="/api/v1/activos",     tags=["Activos Fijos"])
app.include_router(iva.router,         prefix="/api/v1/iva",         tags=["IVA"])
app.include_router(igtf.router,        prefix="/api/v1/igtf",        tags=["IGTF"])
app.include_router(retenciones.router, prefix="/api/v1/retenciones", tags=["Retenciones ISLR"])
app.include_router(tasas.router,       prefix="/api/v1/tasas",       tags=["Tasas BCV"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": "Boeuf Contable SaaS v1.0.0"}


@app.get("/debug", tags=["Health"])
async def debug_db():
    try:
        from sqlalchemy import select, text
        from models import Usuario, Empresa

        async with AsyncSessionLocal() as db:
            users    = (await db.execute(select(Usuario.email, Usuario.nombre))).fetchall()
            empresas = (await db.execute(select(Empresa.nombre_razon_social))).fetchall()
            tables   = [
                t[0] for t in (await db.execute(
                    text("SELECT table_name FROM information_schema.tables "
                         "WHERE table_schema='public' ORDER BY table_name")
                )).fetchall()
            ]
            return {
                "status":       "ok",
                "tables_count": len(tables),
                "tables":       tables,
                "users":        [{"email": u[0], "nombre": u[1]} for u in users],
                "empresas":     [e[0] for e in empresas],
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}
