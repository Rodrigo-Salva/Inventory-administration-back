import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class UserRole(str, enum.Enum):
    SUPERADMIN = "SUPERADMIN" # Global admin (platform)
    ADMIN = "ADMIN"           # Tenant admin
    MANAGER = "MANAGER"       # Inventory/Reports manager
    SELLER = "SELLER"         # Sales only

class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    role = Column(SQLEnum(UserRole), default=UserRole.SELLER, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    
    tenant = relationship("Tenant", back_populates="users")
    role_obj = relationship("Role", back_populates="users")