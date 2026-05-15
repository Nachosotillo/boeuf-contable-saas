import asyncio
import logging
from sqlalchemy import text
from database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate():
    logger.info("Iniciando actualización de la base de datos (paso a paso)...")
    
    # 1. Modificar catalogo_cuenta
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE catalogo_cuenta ADD COLUMN subcategoria VARCHAR(255);"))
            logger.info("Columna 'subcategoria' añadida.")
        except Exception: pass

    # 2. Modificar movimiento_inventario
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE movimiento_inventario ADD COLUMN articulo_id INTEGER;"))
        except Exception: pass
        try:
            await conn.execute(text("ALTER TABLE movimiento_inventario ADD COLUMN lote VARCHAR(50);"))
        except Exception: pass
        try:
            await conn.execute(text("ALTER TABLE movimiento_inventario ADD COLUMN fecha_vencimiento DATE;"))
        except Exception: pass

    # 3. Nomina: Porcentaje ARI
    async with engine.begin() as conn:
        try:
            # Intentar añadirla
            await conn.execute(text("ALTER TABLE nomina_empleado ADD COLUMN porcentaje_ari NUMERIC(7,4) DEFAULT 0;"))
            logger.info("Columna 'porcentaje_ari' añadida.")
        except Exception:
            # Si ya existe, asegurar que el tipo sea NUMERIC(7,4)
            try:
                await conn.execute(text("ALTER TABLE nomina_empleado ALTER COLUMN porcentaje_ari TYPE NUMERIC(7,4);"))
                logger.info("Columna 'porcentaje_ari' actualizada a NUMERIC(7,4).")
            except Exception: pass

    # 4. Nomina: RPE
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE nomina_periodo ADD COLUMN rpe_empleado NUMERIC(14,2) DEFAULT 0;"))
        except Exception: pass
        try:
            await conn.execute(text("ALTER TABLE nomina_periodo ADD COLUMN rpe_patrono NUMERIC(14,2) DEFAULT 0;"))
        except Exception: pass

    logger.info("Actualización completada.")

if __name__ == "__main__":
    asyncio.run(migrate())
