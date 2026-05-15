"""
Boeuf Contable SaaS — Backend API
Python 3.11+ | FastAPI | PostgreSQL | SQLAlchemy 2.0

FLUJO DE DEPLOY CORRECTO (Render + Neon):
  1. Verificar que DATABASE_URL en Render apunte a la misma BD que ves en Neon.
  2. En la BD correcta (Neon SQL Editor):
       DROP SCHEMA public CASCADE;
       CREATE SCHEMA public;
  3. Push a GitHub → "Clear build cache & deploy" en Render.

USUARIOS SEMILLA:
  - admin@boeuf.com        / boeuf123     → Empresa Demo C.A.        (admin)
  - usuario@elcuadrefrio.com / cuadre123  → El Cuadre Frío C.A.      (admin)
  - ricky@rickyricon.com   / ricky123     → Rickyricon C.A.           (admin)
  - amigo@rickyricontest.com / amigo123   → Ricky Ricón Test C.A.     (admin)
    (empresa aislada para que el amigo pruebe con su propio profesor)
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

# ─── Definición de empresas/usuarios semilla ─────────────────────────────────
# Cada entrada es completamente aislada (empresa_id distinto = datos separados).
# Para agregar más: copiar el bloque y cambiar email, rif, nombre, password.

SEED_ACCOUNTS = [
    {
        "empresa_nombre": "Empresa Demo C.A.",
        "rif":            "J-00000000-0",
        "admin_nombre":   "Administrador",
        "admin_email":    "admin@boeuf.com",
        "admin_password": "boeuf123",
    },
    {
        "empresa_nombre": "El Cuadre Frío C.A.",
        "rif":            "J-11111111-1",
        "admin_nombre":   "Usuario",
        "admin_email":    "usuario@elcuadrefrio.com",
        "admin_password": "cuadre123",
    },
    {
        "empresa_nombre": "Rickyricon C.A.",
        "rif":            "J-98765432-1",
        "admin_nombre":   "Ricky (Admin)",
        "admin_email":    "ricky@rickyricon.com",
        "admin_password": "ricky123",
    },
    {
        # Empresa aislada para el amigo — ve solo su propio dashboard y datos.
        "empresa_nombre": "Ricky Ricón Test C.A.",
        "rif":            "J-55555555-5",
        "admin_nombre":   "Ricky Ricón",
        "admin_email":    "amigo@rickyricontest.com",
        "admin_password": "amigo123",
    },
]


async def _sembrar_cuenta(seed: dict, db) -> None:
    """Crea empresa + usuario admin + catálogo si el usuario no existe aún."""
    from sqlalchemy import select
    from models import Usuario, Empresa, TipoPersonaEnum, RolEnum
    from routers.auth import hash_password
    from routers.catalogo import sembrar_catalogo_default

    res = await db.execute(
        select(Usuario).where(Usuario.email == seed["admin_email"])
    )
    existing_user = res.scalar_one_or_none()

    if not existing_user:
        logger.info(f"Creando cuenta: {seed['admin_email']}...")
        emp = Empresa(
            nombre_razon_social=seed["empresa_nombre"],
            rif=seed["rif"],
            tipo_persona=TipoPersonaEnum.juridica,
        )
        db.add(emp)
        await db.flush()

        db.add(Usuario(
            nombre=seed["admin_nombre"],
            email=seed["admin_email"],
            contrasena_hash=hash_password(seed["admin_password"]),
            rol=RolEnum.admin,
            empresa_id=emp.id,
        ))
        await sembrar_catalogo_default(emp.id, db)
        await db.commit()
        logger.info(f">>> Creado: {seed['admin_email']} / {seed['admin_password']}")
    else:
        # Ya existe: actualizar catálogo con cuentas nuevas (UPSERT, no duplica)
        res_emp = await db.execute(
            select(Empresa).where(Empresa.rif == seed["rif"])
        )
        emp = res_emp.scalar_one_or_none()
        if emp:
            await sembrar_catalogo_default(emp.id, db)
            await db.commit()
            logger.info(f"Catálogo actualizado para: {seed['empresa_nombre']}")


@asynccontextmanager
async def lifespan(app: FastAPI):

    # ── 1. Migraciones incrementales (columnas/tablas nuevas sin borrar datos) ─
    try:
        from update_db import migrate
        await migrate()
    except Exception as e:
        logger.warning(f"Error en migración incremental: {e}")

    # ── 2. Crear tablas faltantes (create_all nunca borra ni modifica) ─────────
    logger.info("Verificando/creando tablas...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tablas OK.")

    # ── 3. Sembrar todas las cuentas (una por una, aisladas por empresa_id) ────
    try:
        async with AsyncSessionLocal() as db:
            for seed in SEED_ACCOUNTS:
                await _sembrar_cuenta(seed, db)
    except Exception as e:
        logger.error(f"Error en siembra inicial: {e}")

    # ── 4. Scheduler tasa BCV ──────────────────────────────────────────────────
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
    """
    Muestra tablas, usuarios y empresas actuales.
    Útil para verificar que el deploy llegó a la BD correcta.
    También muestra la URL de conexión (sin password) para comparar con Neon.
    """
    try:
        from sqlalchemy import select, text
        from models import Usuario, Empresa
        import os

        async with AsyncSessionLocal() as db:
            users    = (await db.execute(select(Usuario.email, Usuario.nombre))).fetchall()
            empresas = (await db.execute(select(Empresa.nombre_razon_social, Empresa.rif))).fetchall()
            tables   = [
                t[0] for t in (await db.execute(
                    text("SELECT table_name FROM information_schema.tables "
                         "WHERE table_schema='public' ORDER BY table_name")
                )).fetchall()
            ]

            # Mostrar host de BD sin credenciales (para comparar con Neon)
            db_url = os.getenv("DATABASE_URL", "no definida")
            try:
                from urllib.parse import urlparse
                parsed = urlparse(db_url)
                db_host = f"{parsed.scheme}://***@{parsed.hostname}{parsed.path}"
            except Exception:
                db_host = "no parseable"

            return {
                "status":       "ok",
                "db_host":      db_host,
                "tables_count": len(tables),
                "tables":       tables,
                "users":        [{"email": u[0], "nombre": u[1]} for u in users],
                "empresas":     [{"nombre": e[0], "rif": e[1]} for e in empresas],
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}
