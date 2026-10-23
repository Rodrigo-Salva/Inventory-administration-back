"""El script de datos de ejemplo sobre una base migrada: crea todo con stock por sucursal y es repetible."""

import os
import subprocess
import sys

from support import ROOT, TEST_DATABASE_URL, sql


def run_seed(*args):
    return subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "app.infrastructure.seeds.seed_data", *args],
        cwd=ROOT, env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL, "PYTHONIOENCODING": "utf-8"},
        capture_output=True, text=True,
    )


def test_seed_creates_demo_data_with_branch_stock_and_is_repeatable(migrated_database):
    first = run_seed()
    assert first.returncode == 0, first.stderr[-2000:]
    products = sql("SELECT count(*) FROM products", fetch=True)[0][0]
    assert products > 0
    rows = sql("SELECT p.stock, COALESCE(SUM(pb.stock), 0) FROM products p "
               "LEFT JOIN product_branches pb ON pb.product_id = p.id GROUP BY p.id", fetch=True)
    assert all(stock == total for stock, total in rows)  # products.stock = suma de sucursales
    assert sql("SELECT count(*) FROM branches WHERE name='Sucursal Principal'", fetch=True)[0][0] == 1
    assert sql("SELECT branch_id IS NOT NULL FROM users WHERE email='admin@demo.com'", fetch=True)[0][0] is True

    again = run_seed()  # repetible: no duplica nada
    assert again.returncode == 0, again.stderr[-2000:]
    assert sql("SELECT count(*) FROM products", fetch=True)[0][0] == products

    cleaned = run_seed("--clean")  # --clean vacía datos y NO toca el esquema
    assert cleaned.returncode == 0, cleaned.stderr[-2000:]
    assert sql("SELECT version_num FROM alembic_version", fetch=True)[0][0] == "a1b2c3d4e5f6"
    assert sql("SELECT count(*) FROM products", fetch=True)[0][0] == products
