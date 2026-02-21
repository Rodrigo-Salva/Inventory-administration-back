from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.sql import expression
from sqlalchemy.orm import relationship
from .base import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    subdomain = Column(String(50), unique=True, index=True)
    tax_id = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    logo_url = Column(String(255), nullable=True)
    plan = Column(String(20), default="free")  # free, pro, enterprise
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    users = relationship("User", back_populates="tenant")
    products = relationship("Product", back_populates="tenant")
    categories = relationship("Category", back_populates="tenant")
    suppliers = relationship("Supplier", back_populates="tenant")

