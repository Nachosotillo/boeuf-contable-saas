import asyncio
import logging
from sqlalchemy import text
from database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate():
    logger.info("Iniciando actualización de la base de datos...")
    async with engine.begin() as conn:
        # 1. Modificar catalogo_cuenta
        try:
            await conn.execute(text("ALTER TABLE catalogo_cuenta ADD COLUMN subcategoria VARCHAR(255);"))
            logger.info("Columna 'subcategoria' añadida a catalogo_cuenta.")
        except Exception as e:
            logger.warning(f"Aviso catalogo_cuenta (probablemente ya existe): {e}")

        # 2. Modificar movimiento_inventario
        try:
            await conn.execute(text("ALTER TABLE movimiento_inventario ADD COLUMN articulo_id INTEGER;"))
            logger.info("Columna 'articulo_id' añadida a movimiento_inventario.")
        except Exception as e:
            logger.warning(f"Aviso articulo_id: {e}")

        try:
            await conn.execute(text("ALTER TABLE movimiento_inventario ADD COLUMN lote VARCHAR(50);"))
            logger.info("Columna 'lote' añadida a movimiento_inventario.")
        except Exception as e:
            logger.warning(f"Aviso lote: {e}")

        try:
            await conn.execute(text("ALTER TABLE movimiento_inventario ADD COLUMN fecha_vencimiento DATE;"))
            logger.info("Columna 'fecha_vencimiento' añadida a movimiento_inventario.")
        except Exception as e:
            logger.warning(f"Aviso fecha_vencimiento: {e}")

        # 3. Nomina
        try:
            await conn.execute(text("ALTER TABLE nomina_empleado ADD COLUMN porcentaje_ari NUMERIC(5,4) DEFAULT 0;"))
            logger.info("Columna 'porcentaje_ari' añadida a nomina_empleado.")
        except Exception as e:
            logger.warning(f"Aviso porcentaje_ari: {e}")

        try:
            await conn.execute(text("ALTER TABLE nomina_periodo ADD COLUMN rpe_empleado NUMERIC(14,2) DEFAULT 0;"))
            await conn.execute(text("ALTER TABLE nomina_periodo ADD COLUMN rpe_patrono NUMERIC(14,2) DEFAULT 0;"))
            logger.info("Columnas 'rpe_empleado' y 'rpe_patrono' añadidas a nomina_periodo.")
        except Exception as e:
            logger.warning(f"Aviso rpe_empleado/patrono: {e}")

        # 4. Actualizar subcuentas en catálogo
        # As we changed 2.1.11 to a subgroup, existing companies need these accounts inserted or updated
        # It's safer to just let the user run the Nuclear option since they have no data,
        # but just in case, we won't crash if they don't.
        # Actually, because the user explicitly stated they will drop the DB again to avoid collisions,
        # create_all will just generate the new schema perfectly!
        # But we still keep the migration commands for good practice.

    logger.info("Actualización completada. Puedes iniciar el servidor.")

if __name__ == "__main__":
    asyncio.run(migrate())
