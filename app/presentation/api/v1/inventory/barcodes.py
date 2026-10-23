from fastapi import APIRouter, Depends, HTTPException, Query
from app.presentation.dependencies import require_permission
from app.infrastructure.external.barcode_service import BarcodeService
from app.infrastructure.persistence.models.identity.user import User

router = APIRouter()

@router.get("/generate/{data}")
async def generate_barcode(
    data: str,
    code_type: str = Query("code128", description="Tipo de código de barras (code128, ean13, etc.)"),
    current_user: User = Depends(require_permission("barcodes:generate"))
):
    """
    Genera un código de barras para el dato proporcionado (generalmente un SKU o Barcode).
    Devuelve la imagen en formato Base64.
    """
    try:
        barcode_base64 = BarcodeService.generate_barcode_base64(data, code_type)
        return {"image": barcode_base64, "data": data, "type": code_type}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/qr/{data}")
async def generate_qr(
    data: str,
    current_user: User = Depends(require_permission("barcodes:generate"))
):
    """
    Genera un código QR para el dato proporcionado.
    Devuelve la imagen en formato Base64.
    """
    try:
        qr_base64 = BarcodeService.generate_qr_base64(data)
        return {"image": qr_base64, "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
