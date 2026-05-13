"""
utils/auditoria.py — Helper para registrar logs de auditoría
"""
from sqlalchemy.ext.asyncio import AsyncSession
from models import LogAuditoria, Usuario


async def registrar_log(
    db: AsyncSession,
    usuario: Usuario,
    tabla: str,
    registro_id: int,
    accion: str,
    datos_antes: dict = None,
    datos_despues: dict = None,
    descripcion: str = None,
):
    log = LogAuditoria(
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        tabla_afectada=tabla,
        registro_id=registro_id,
        accion=accion,
        datos_antes=datos_antes,
        datos_despues=datos_despues,
        descripcion=descripcion,
    )
    db.add(log)
