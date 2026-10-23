from datetime import datetime

from openpyxl import load_workbook

from app.application.reporting.dashboard import build_dashboard
from app.infrastructure.external.excel_report import build_csv, build_excel, safe_cell


def test_safe_cell_neutralizes_formulas_only_in_text():
    assert safe_cell("=HYPERLINK(\"http://x\")") == "'=HYPERLINK(\"http://x\")"
    assert safe_cell("+cmd") == "'+cmd" and safe_cell("@SUM(A1)") == "'@SUM(A1)"
    assert safe_cell("Café") == "Café" and safe_cell(-5) == -5 and safe_cell(None) is None


def test_excel_layout_with_range_subtitle():
    buffer = build_excel(
        sheet="Ventas", title="REPORTE", tenant_name="acme",
        headers=["ID", "Total"], rows=[[1, 10.5], [2, "=1+1"]],
        money_columns=(2,), show_range=True,
        start=datetime(2026, 1, 1), end=datetime(2026, 1, 31),
    )
    ws = load_workbook(buffer).active
    assert ws.title == "Ventas"
    assert ws["A1"].value == "REPORTE - ACME"
    assert "Rango: 01/01/2026 al 31/01/2026" in ws["A2"].value
    assert [c.value for c in ws[4]] == ["ID", "Total"]
    assert ws["B5"].value == 10.5 and ws["B5"].number_format == '"$"#,##0.00'
    assert ws["B6"].value == "=1+1" or str(ws["B6"].value).startswith("'")  # nunca fórmula activa


def test_excel_layout_without_subtitle_and_default_tenant():
    ws = load_workbook(
        build_excel(sheet="G", title="GASTOS", tenant_name=None, headers=["A"], rows=[[1]],
                    column_widths={"A": 40})
    ).active
    assert ws["A1"].value == "GASTOS - INVENTORY ADMINISTRATION"
    assert ws["A3"].value == "A" and ws["A4"].value == 1
    assert ws.column_dimensions["A"].width == 40


def test_csv_escapes_formulas():
    text = build_csv(["n"], [["=cmd|' /C calc'!A0"], ["ok"]])
    assert text.splitlines()[1].startswith("'=")


class FakeReader:
    async def get_dashboard_stats(self, tenant_id, start_date=None, end_date=None):
        return {"products": 3}

    async def get_sales_stats(self, tenant_id, start_date=None, end_date=None):
        return {"sales_count": 2, "total_revenue": 100}

    async def get_purchase_stats(self, tenant_id, start_date=None, end_date=None):
        return {"purchase_count": 1, "total_investment": 40}

    async def get_sales_trends(self, tenant_id):
        return [{"date": "2026-01-01", "revenue": 100, "count": 2}]

    async def get_purchase_trends(self, tenant_id):
        return [{"date": "2026-01-02", "investment": 40, "count": 1}]

    def __getattr__(self, name):
        async def empty(*args, **kwargs):
            return []
        return empty


async def test_dashboard_merges_stats_and_compares_trends():
    data = await build_dashboard(FakeReader(), tenant_id=1)
    assert data["stats"] == {
        "products": 3, "sales_count": 2, "total_revenue": 100, "purchase_count": 1, "total_investment": 40,
    }
    assert data["comparison_trends"] == [
        {"date": "2026-01-01", "sales": 100, "purchases": 0},
        {"date": "2026-01-02", "sales": 0, "purchases": 40},
    ]
    assert data["purchase_trends"] == [{"date": "2026-01-02", "revenue": 40, "count": 1}]
    assert data["top_selling_products"] == []
