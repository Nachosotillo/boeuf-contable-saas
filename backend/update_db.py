"""
update_db.py — Migraciones incrementales sin Alembic.
Se ejecuta al arrancar la app (antes de create_all) para añadir columnas
o tablas que no existen en el schema actual sin borrar datos.
"""
import asyncio
import logging
from sqlalchemy import text
from database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    logger.info("Iniciando migraciones incrementales...")

    async with engine.begin() as conn:

        # ── catalogo_cuenta ───────────────────────────────────────────────────
        for stmt, desc in [
            ("ALTER TABLE catalogo_cuenta ADD COLUMN IF NOT EXISTS subcategoria VARCHAR(255);",
             "catalogo_cuenta.subcategoria"),
        ]:
            try:
                await conn.execute(text(stmt))
                logger.info(f"  OK: {desc}")
            except Exception as e:
                logger.warning(f"  SKIP {desc}: {e}")

        # ── movimiento_inventario ─────────────────────────────────────────────
        for col, tipo in [
            ("articulo_id",       "INTEGER"),
            ("lote",              "VARCHAR(50)"),
            ("fecha_vencimiento", "DATE"),
        ]:
            try:
                await conn.execute(text(
                    f"ALTER TABLE movimiento_inventario ADD COLUMN IF NOT EXISTS {col} {tipo};"
                ))
                logger.info(f"  OK: movimiento_inventario.{col}")
            except Exception as e:
                logger.warning(f"  SKIP movimiento_inventario.{col}: {e}")

        # ── nomina_empleado ───────────────────────────────────────────────────
        # Añadir porcentaje_ari si no existe, luego corregir precisión a (6,4)
        try:
            await conn.execute(text(
                "ALTER TABLE nomina_empleado "
                "ADD COLUMN IF NOT EXISTS porcentaje_ari NUMERIC(6,4) DEFAULT 0 NOT NULL;"
            ))
            logger.info("  OK: nomina_empleado.porcentaje_ari (creada)")
        except Exception:
            pass
        try:
            # Si ya existía con (7,4) la corregimos a (6,4)
            await conn.execute(text(
                "ALTER TABLE nomina_empleado "
                "ALTER COLUMN porcentaje_ari TYPE NUMERIC(6,4);"
            ))
            logger.info("  OK: nomina_empleado.porcentaje_ari (tipo actualizado)")
        except Exception as e:
            logger.warning(f"  SKIP porcentaje_ari tipo: {e}")

        # ── nomina_periodo ────────────────────────────────────────────────────
        for col in ["rpe_empleado", "rpe_patrono"]:
            try:
                await conn.execute(text(
                    f"ALTER TABLE nomina_periodo "
                    f"ADD COLUMN IF NOT EXISTS {col} NUMERIC(14,2) DEFAULT 0;"
                ))
                logger.info(f"  OK: nomina_periodo.{col}")
            except Exception as e:
                logger.warning(f"  SKIP nomina_periodo.{col}: {e}")

        # ── nomina_programacion (tabla nueva) ─────────────────────────────────
        # create_all la creará si no existe, pero por si acaso también la
        # manejamos aquí para garantizar que exista antes de que el router
        # de nómina intente usarla.
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS nomina_programacion (
                    id               SERIAL PRIMARY KEY,
                    empresa_id       INTEGER NOT NULL UNIQUE
                                     REFERENCES empresa(id) ON DELETE CASCADE,
                    proxima_fecha    DATE    NOT NULL,
                    ultima_ejecucion DATE,
                    intervalo_dias   INTEGER NOT NULL DEFAULT 30,
                    creado_en        TIMESTAMP DEFAULT NOW(),
                    actualizado_en   TIMESTAMP DEFAULT NOW()
                );
            """))
            logger.info("  OK: tabla nomina_programacion")
        except Exception as e:
            logger.warning(f"  SKIP nomina_programacion: {e}")

        # ── linea_asiento: descripcion (usada en algunos reportes) ────────────
        try:
            await conn.execute(text(
                "ALTER TABLE linea_asiento "
                "ADD COLUMN IF NOT EXISTS descripcion VARCHAR(500);"
            ))
            logger.info("  OK: linea_asiento.descripcion")
        except Exception as e:
            logger.warning(f"  SKIP linea_asiento.descripcion: {e}")

    logger.info("Migraciones completadas.")


if __name__ == "__main__":
    asyncio.run(migrate())
