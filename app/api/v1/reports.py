from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
import csv
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.base import get_db
from ...dependencies import get_current_tenant
from ...repositories.report_repo import ReportRepository
from ...schemas.report import InventoryReport
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/dashboard", response_model=InventoryReport)
async def get_dashboard_data(
    days: int = Query(7, ge=1, le=30),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene todos los datos necesarios para el dashboard inicial"""
    repo = ReportRepository(db)
    
    stats = await repo.get_dashboard_stats(tenant_id)
    trends = await repo.get_movement_trends(tenant_id, days=days)
    recent = await repo.get_recent_movements(tenant_id)
    low_stock = await repo.get_low_stock_products(tenant_id)
    distribution = await repo.get_category_distribution(tenant_id)
    
    return {
        "stats": stats,
        "trends": trends,
        "recent_movements": recent,
        "low_stock_products": low_stock,
        "category_distribution": distribution
    }

@router.get("/inventory-csv")
async def export_inventory_csv(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Genera un reporte CSV del inventario actual"""
    from ...repositories.product_repo import ProductRepository
    repo = ProductRepository(db)
    
    # Obtener todos los productos (con relaciones para evitar errores de lazy load)
    products = await repo.get_all_with_relations(tenant_id=tenant_id, limit=2000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["ID", "SKU", "Nombre", "Categoría", "Stock", "Precio", "Costo", "Estado"])
    
    for p in products:
        writer.writerow([
            p.id, 
            p.sku, 
            p.name, 
            p.category.name if p.category else "", 
            p.stock, 
            p.price, 
            p.cost, 
            "Activo" if p.is_active else "Inactivo"
        ])
    
    filename = f"inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/inventory-excel")
async def export_inventory_excel(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Genera un reporte Excel profesional del inventario actual"""
    from ...repositories.product_repo import ProductRepository
    from ...repositories.tenant_repo import TenantRepository
    repo = ProductRepository(db)
    t_repo = TenantRepository(db)
    
    products = await repo.get_all_with_relations(tenant_id=tenant_id, limit=2000)
    tenant = await t_repo.get_by_id(tenant_id)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario"
    
    # Estilos profesionales
    title_font = Font(name='Arial', size=16, bold=True, color="1E40AF")
    header_font = Font(name='Arial', size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid") # Deep Blue
    center_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color="DDDDDD"),
        right=Side(style='thin', color="DDDDDD"),
        top=Side(style='thin', color="DDDDDD"),
        bottom=Side(style='thin', color="DDDDDD")
    )

    # Corporate Header
    ws.merge_cells('A1:I1')
    ws['A1'] = f"REPORTE DE INVENTARIO - {tenant.name.upper()}"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal="center")
    
    ws.merge_cells('A2:I2')
    ws['A2'] = f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    ws['A2'].font = Font(size=10, italic=True)
    ws['A2'].alignment = Alignment(horizontal="center")

    # Header row (shifted down)
    headers = ["ID", "SKU", "Nombre", "Categoría", "Stock", "Mínimo", "Precio", "Costo", "Estado"]
    header_row_idx = 4
    ws.append([]) # spacer
    ws.append(headers)
    
    for cell in ws[header_row_idx + 1]: # next row after spacer
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        cell.border = thin_border

    # Data rows (start from header_row_idx + 1)
    for idx, p in enumerate(products, start=header_row_idx + 2):
        row = [
            p.id,
            p.sku,
            p.name,
            p.category.name if p.category else "Sin categoría",
            p.stock,
            p.min_stock,
            float(p.price),
            float(p.cost) if p.cost else 0.0,
            "✅ ACTIVO" if p.is_active else "❌ INACTIVO"
        ]
        ws.append(row)
        
        # Zebra striping and borders
        row_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid") if idx % 2 == 0 else None
        for cell in ws[idx]:
            if row_fill:
                cell.fill = row_fill
            cell.border = thin_border
            # Currency format for Price and Cost
            if cell.column in [7, 8]:
                cell.number_format = '"$"#,##0.00'
            # Center ID and Stock
            if cell.column in [1, 5, 6]:
                cell.alignment = center_alignment

    # Auto-adjust column width
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    # Save to memory
    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    filename = f"Inventario_Profesional_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
