import json
import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy import event, inspect
from typing import Dict, Any, Optional

from .context import get_current_user_id, get_current_tenant_id, get_current_ip_address, get_current_user_agent

logger = logging.getLogger(__name__)

# Función auxiliar para serializar valores (ej: datetime a string)
def serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    # Generic fallback for other non-serializable objects (like UUIDs, memory addresses, custom objects)
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)

def extract_model_data(target) -> Dict[str, Any]:
    """Extrae los datos actuales del modelo"""
    data = {}
    mapper = inspect(target).mapper
    for column in mapper.columns:
        val = getattr(target, column.key)
        data[column.key] = serialize_value(val)
    return data

def extract_changed_data(target) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Extrae los valores originales y los nuevos valores para las columnas modificadas"""
    old_values = {}
    new_values = {}
    inspr = inspect(target)
    
    for attr in inspr.attrs:
        # Check if attribute corresponds to a column and if it has history
        if hasattr(attr, 'history') and attr.history.has_changes():
            old_val = attr.history.deleted[0] if attr.history.deleted else None
            new_val = attr.history.added[0] if attr.history.added else None
            
            old_values[attr.key] = serialize_value(old_val)
            new_values[attr.key] = serialize_value(new_val)
            
    return old_values, new_values

def is_auditable(target) -> bool:
    """Determina si un modelo debe ser auditado o no."""
    table_name = target.__tablename__
    # Omitir logs de auditoría para no crear recursión infinita
    if table_name in ("audit_logs", "notifications", "ai_insights"):
        return False
    # Omitir también tablas de asociación como role_permissions que no son modelos directos
    return True

def create_audit_log_entry(
    connection,
    action: str,
    target,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None
):
    """Inserta el registro de auditoría interactuando directamente con la conexión (sync)"""
    if not is_auditable(target):
        return

    # Extraer el tenant ID (puede venir del contexto o de la misma entidad)
    tenant_id = get_current_tenant_id()
    if not tenant_id and hasattr(target, "tenant_id"):
        tenant_id = target.tenant_id

    # Omitir si a pesar de todo no hay un tenant identificable
    if not tenant_id:
        # Algunos requests del superadmin, comandos cron, o tablas globales 
        # podrían no tener tenant
        return

    user_id = get_current_user_id()
    ip_address = get_current_ip_address()
    user_agent = get_current_user_agent()
    
    entity_type = target.__class__.__name__
    
    # Intentar sacar un ID si existe (puede que no exista todavía en un before_insert)
    # Por lo que usamos esto en AFTER eventos
    entity_id = getattr(target, "id", None)
    if not entity_id:
        return
        
    description = f"{action} realizada en {entity_type} #{entity_id}"
    
    # Preparar datos JSON
    old_json = json.dumps(old_values) if old_values else None
    new_json = json.dumps(new_values) if new_values else None
    
    try:
        # Insertar usando raw SQL pues la conexión está en modo sincrónico en eventos
        from sqlalchemy import text
        
        stmt = text("""
            INSERT INTO audit_logs (
                tenant_id, user_id, action, entity_type, entity_id, 
                old_values, new_values, description, ip_address, user_agent, created_at
            ) VALUES (
                :tenant_id, :user_id, :action, :entity_type, :entity_id, 
                :old_values, :new_values, :description, :ip_address, :user_agent, :created_at
            )
        """)
        
        connection.execute(stmt, {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "old_values": old_json,
            "new_values": new_json,
            "description": description,
            "ip_address": ip_address[:50] if ip_address else None,
            "user_agent": user_agent[:255] if user_agent else None,
            "created_at": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error escribiendo Audit Log: {e}")

# Registrar Listeners en una base (Base o Session). Es mejor mapearlo en los mapper de eventos o Session
def setup_audit_listeners(Base):
    """
    Configura los event listeners en la clase Base.
    """
        
    @event.listens_for(Base, "after_insert", propagate=True)
    def receive_after_insert(mapper, connection, target):
        new_values = extract_model_data(target)
        create_audit_log_entry(connection, "CREATE", target, old_values=None, new_values=new_values)

    @event.listens_for(Base, "after_update", propagate=True)
    def receive_after_update(mapper, connection, target):
        old_values, new_values = extract_changed_data(target)
        if not old_values and not new_values:
            return # Nada cambió
            
        create_audit_log_entry(connection, "UPDATE", target, old_values=old_values, new_values=new_values)

    @event.listens_for(Base, "after_delete", propagate=True)
    def receive_after_delete(mapper, connection, target):
        old_values = extract_model_data(target)
        create_audit_log_entry(connection, "DELETE", target, old_values=old_values, new_values=None)
