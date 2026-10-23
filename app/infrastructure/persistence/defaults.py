"""Datos de referencia que todo tenant necesita desde su creación."""

DEFAULT_BRANCH_NAME = "Sucursal Principal"

DEFAULT_EXPENSE_CATEGORIES: list[tuple[str, str]] = [
    ("Servicios Públicos", "Pago de luz, agua, internet, etc."),
    ("Arriendo", "Pago de alquiler del local"),
    ("Suministros", "Papelería, limpieza, etc."),
    ("Pago a Proveedores", "Pagos directos a proveedores de mercancía"),
    ("Otros", "Gastos varios no clasificados"),
]
