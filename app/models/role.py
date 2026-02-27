from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

# Tabla intermedia para muchos a muchos entre Roles y Permisos
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Nombre legible: "Ver Productos"
    codename = Column(String(100), unique=True, nullable=False, index=True) # "products:view"
    module = Column(String(50), nullable=False) # "inventory", "sales", etc.
    description = Column(String(255), nullable=True)

class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=False) # Roles protegidos (Admin, Seller)
    
    tenant = relationship("Tenant")
    permissions = relationship("Permission", secondary=role_permissions, backref="roles")
    users = relationship("User", back_populates="role_obj")
