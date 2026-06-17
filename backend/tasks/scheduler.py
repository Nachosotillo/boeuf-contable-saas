"""
Scheduler APScheduler — Tasa BCV automática diaria a las 8:00 AM

MODO CLASE 2025: el fetch automático está APAGADO por defecto para no pisar las
tasas reales del ejercicio 2025. Se controla con settings.TASA_AUTO_FETCH:
  - False (defecto) → no se programa el job y actualizar_tasa_bcv() no hace nada.
  - True            → comportamiento original (consulta la API y guarda la tasa de hoy).

Para reactivarlo en producción, define TASA_AUTO_FETCH=true en la config/entorno.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx
import logging
from datetime import date
from decimal import Decimal

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def _auto_fetch_activo() -> bool:
    try:
        from config import settings
        return bool(getattr(settings, "TASA_AUTO_FETCH", False))
    except Exception:
        return False


async def actualizar_tasa_bcv():
    """
    Obtiene la tasa USD/VES del BCV desde API pública y la guarda en tasa_cambio_bcv.
    No hace nada si TASA_AUTO_FETCH está apagado (modo clase 2025).
    """
    if not _auto_fetch_activo():
        logger.info("⏸️  TASA_AUTO_FETCH apagado — se omite el fetch del BCV (modo 2025).")
        return

    from database import AsyncSessionLocal
    from models import TasaCambioBcv
    from sqlalchemy import select
    from config import settings

    async with AsyncSessionLocal() as db:
        try:
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
                # No pisar una tasa fijada manualmente.
                if record.fuente == "MANUAL":
                    logger.info("Tasa de %s es MANUAL — no se sobrescribe.", hoy)
                    return
                record.tasa_usd = tasa
                record.fuente = "API DolarAPI"
            else:
                db.add(TasaCambioBcv(fecha=hoy, tasa_usd=tasa, fuente="API DolarAPI"))

            await db.commit()
            logger.info("✅ Tasa BCV actualizada: %s Bs./USD", tasa)

        except Exception as e:
            logger.error("❌ Error actualizando tasa BCV: %s", e)
            await db.rollback()


def start_scheduler():
    if not _auto_fetch_activo():
        logger.info("🕗 Scheduler: fetch BCV DESACTIVADO (TASA_AUTO_FETCH=false). Modo clase 2025.")
        return
    scheduler.add_job(
        actualizar_tasa_bcv,
        CronTrigger(hour=8, minute=0),
        id="tasa_bcv_diaria",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("🕗 Scheduler iniciado — tasa BCV se actualiza a las 8:00 AM")
