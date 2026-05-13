"""
Scheduler APScheduler — Tasa BCV automática diaria a las 8:00 AM
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx
import logging
from datetime import date
from decimal import Decimal

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def actualizar_tasa_bcv():
    """
    Obtiene la tasa USD/VES del BCV desde API pública
    y la guarda en la tabla tasa_cambio_bcv.
    """
    from database import AsyncSessionLocal
    from models import TasaCambioBcv
    from sqlalchemy import select
    from config import settings

    async with AsyncSessionLocal() as db:
        try:
            # Intentar API pública (dolarapi.com)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(settings.BCV_API_URL)
                response.raise_for_status()
                data = response.json()
                tasa = Decimal(str(data.get("promedio") or data.get("precio") or 0))

            if tasa <= 0:
                logger.warning("Tasa BCV inválida recibida: %s", tasa)
                return

            hoy = date.today()
            existing = await db.execute(
                select(TasaCambioBcv).where(TasaCambioBcv.fecha == hoy)
            )
            record = existing.scalar_one_or_none()

            if record:
                record.tasa_usd = tasa
                record.fuente = "API DolarAPI"
            else:
                db.add(TasaCambioBcv(
                    fecha=hoy,
                    tasa_usd=tasa,
                    fuente="API DolarAPI"
                ))

            await db.commit()
            logger.info("✅ Tasa BCV actualizada: %s Bs./USD", tasa)

        except Exception as e:
            logger.error("❌ Error actualizando tasa BCV: %s", e)
            await db.rollback()


def start_scheduler():
    scheduler.add_job(
        actualizar_tasa_bcv,
        CronTrigger(hour=8, minute=0),
        id="tasa_bcv_diaria",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("🕗 Scheduler iniciado — tasa BCV se actualiza a las 8:00 AM")
