from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.crm_dto import CreateCustomerCommand, DeleteCustomerCommand, UpdateCustomerCommand
from app.application.sales.crm_use_cases import CreateCustomer, DeleteCustomer, UpdateCustomer
from app.application.shared.pagination import PaginatedResponse, PaginationParams, create_pagination_metadata
from app.domain.sales.errors import CustomerNotFoundError
from app.infrastructure.logging import get_logger
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.repositories.sales.customer_repo import CustomerRepository
from app.presentation.api.v1.sales.crm_deps import get_create_customer, get_delete_customer, get_update_customer
from app.presentation.dependencies import has_permission, require_any_permission, require_permission
from app.presentation.schemas.sales.customer import CustomerCreate, CustomerOut, CustomerSummary, CustomerUpdate

logger = get_logger(__name__)
router = APIRouter()


async def _customer_or_404(db: AsyncSession, customer_id: int, tenant_id: int):
    customer = await CustomerRepository(db).get_by_id(customer_id, tenant_id)
    if not customer:
        raise CustomerNotFoundError()
    return customer


@router.get("/", response_model=PaginatedResponse[CustomerOut])
async def list_customers(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Buscar por nombre, documento o email"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    current_user: User = Depends(require_permission("customers:view")),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los clientes con paginación y filtros"""
    customers, total = await CustomerRepository(db).get_filtered(
        tenant_id=current_user.tenant_id, search=search, is_active=is_active, pagination=pagination
    )
    return PaginatedResponse(
        items=customers,
        metadata=create_pagination_metadata(total_items=total, page=pagination.page, page_size=pagination.page_size),
    )


@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer: CustomerCreate,
    current_user: User = Depends(require_permission("customers:create")),
    use_case: CreateCustomer = Depends(get_create_customer),
    db: AsyncSession = Depends(get_db),
):
    """Crea un cliente (el saldo deudor lo gestiona el sistema; el límite de crédito exige 'credits:manage')"""
    customer_id = await use_case.execute(
        CreateCustomerCommand(
            current_user.tenant_id, customer.model_dump(), has_permission(current_user, "credits:manage")
        )
    )
    logger.info(f"Cliente creado: {customer_id}")
    return await _customer_or_404(db, customer_id, current_user.tenant_id)


@router.get("/active", response_model=List[CustomerSummary])
async def get_active_customers(
    current_user: User = Depends(require_any_permission("customers:view", "pos:sales", "sales:create")),
    db: AsyncSession = Depends(get_db),
):
    """Clientes activos (para selectores del POS y cotizaciones)"""
    return await CustomerRepository(db).get_active_customers(current_user.tenant_id)


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: int,
    current_user: User = Depends(require_permission("customers:view")),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene un cliente por ID"""
    return await _customer_or_404(db, customer_id, current_user.tenant_id)


@router.put("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    current_user: User = Depends(require_permission("customers:edit")),
    use_case: UpdateCustomer = Depends(get_update_customer),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza un cliente (el saldo deudor no se puede editar; el límite de crédito exige 'credits:manage')"""
    await use_case.execute(
        UpdateCustomerCommand(
            current_user.tenant_id, customer_id, customer_update.model_dump(exclude_unset=True),
            has_permission(current_user, "credits:manage"),
        )
    )
    return await _customer_or_404(db, customer_id, current_user.tenant_id)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    current_user: User = Depends(require_permission("customers:delete")),
    use_case: DeleteCustomer = Depends(get_delete_customer),
):
    """Elimina un cliente (borrado lógico; no se permite con saldo pendiente)"""
    await use_case.execute(DeleteCustomerCommand(current_user.tenant_id, customer_id))
    return None
