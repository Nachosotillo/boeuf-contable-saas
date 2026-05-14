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

        # 3. Empresa (articulos_inventario no es una columna real, es un relationship)
        # La tabla articulo_inventario se crea automáticamente con Base.metadata.create_all en main.py

    logger.info("Actualización completada. Puedes iniciar el servidor.")

if __name__ == "__main__":
    asyncio.run(migrate())
