from sqlalchemy import Column, DateTime, Integer, String, func

from app.infrastructure.persistence.database import Base


class ProcessedPayment(Base):
    """Pagos de suscripción ya aplicados: garantiza que una notificación repetida no renueve dos veces."""

    __tablename__ = "processed_payments"

    payment_id = Column(String(64), primary_key=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
