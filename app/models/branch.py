from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, TenantMixin, SoftDeleteMixin

class Branch(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)

    # El usuario pertenece a una sucursal principal ("matriz" u otra)
    # y los productos mantienen stock por sucursal.
    users = relationship("User", back_populates="branch")
