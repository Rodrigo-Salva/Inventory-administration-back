from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.sql import expression
from ..models.base import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    subdomain = Column(String(50), unique=True, index=True)
    plan = Column(String(20), default="free")  # free, pro, enterprise
    expires_at = Column(DateTime(timezone=True), server_default=func.now() + expression.literal_column("interval '30 days'"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())