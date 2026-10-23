"""Respuestas de descarga compartidas por los endpoints de exportación."""

from datetime import datetime

from fastapi.responses import StreamingResponse

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d")


def excel_response(buffer, name: str) -> StreamingResponse:
    return StreamingResponse(
        buffer,
        media_type=XLSX,
        headers={"Content-Disposition": f"attachment; filename={name}_{_stamp()}.xlsx"},
    )


def csv_response(content: str, name: str, stamp: str | None = None) -> StreamingResponse:
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={name}_{stamp or _stamp()}.csv"},
    )


def pdf_response(buffer, name: str) -> StreamingResponse:
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={name}_{_stamp()}.pdf"},
    )
