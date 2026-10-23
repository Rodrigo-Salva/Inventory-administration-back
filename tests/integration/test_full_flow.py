"""Recorrido completo de la API real: compra -> venta -> caja -> anulación -> ajustes -> traslados."""

from decimal import Decimal

import pytest
from support import sql

pytestmark = pytest.mark.asyncio

API = "/api/v1"


async def main_branch(api, h):
    """Sucursal por defecto del negocio (se crea al registrarse)."""
    branches = await ok(await api.get(f"{API}/branches", headers=h))
    return next(b for b in branches["items"] if b["name"] == "Sucursal Principal")


def assert_stock_invariant():
    """El stock real vive por sucursal: products.stock SIEMPRE es la suma de sus sucursales."""
    rows = sql("SELECT p.sku, p.stock, COALESCE(SUM(pb.stock), 0) FROM products p "
               "LEFT JOIN product_branches pb ON pb.product_id = p.id GROUP BY p.id", fetch=True)
    assert all(stock == total for _, stock, total in rows), f"products.stock != suma de sucursales: {rows}"
    assert sql("SELECT count(*) FROM product_branches WHERE stock < 0", fetch=True)[0][0] == 0


async def register_and_login(api, email="owner@example.com", password="password123"):
    response = await api.post(f"{API}/auth/register", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def login(api, email, password):
    response = await api.post(f"{API}/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def ok(response, expected=(200, 201)):
    assert response.status_code in expected, f"{response.request.method} {response.request.url} -> {response.status_code}: {response.text}"
    return response.json() if response.content and response.headers.get("content-type", "").startswith("application/json") else None


async def stock_of(api, h, product_id):
    return (await ok(await api.get(f"{API}/products/{product_id}", headers=h)))["stock"]


async def test_health_readiness_checks_the_database(api):
    response = await api.get("/health/readiness")
    assert response.status_code == 200 and response.json()["checks"]["database"] == "ok"


async def test_inventory_money_flow_end_to_end(api):
    h = await register_and_login(api)

    me = await ok(await api.get(f"{API}/users/me", headers=h))
    assert me["email"] == "owner@example.com" and me["is_admin"] is True

    branch = await ok(await api.post(f"{API}/branches", json={"name": "Sucursal Central"}, headers=h))
    branch2 = await ok(await api.post(f"{API}/branches", json={"name": "Sucursal Norte"}, headers=h))
    supplier = await ok(await api.post(f"{API}/suppliers", json={"name": "Proveedor SA", "code": "PROV-1"}, headers=h))
    product = await ok(await api.post(
        f"{API}/products",
        json={"name": "Café 1kg", "sku": "CAFE-1", "price": "10.00", "cost": "5.00", "stock": 0},
        headers=h,
    ))
    pid = product["id"]

    # --- Compra: borrador -> recibida (ingresa stock a la sucursal) ---
    purchase = await ok(await api.post(
        f"{API}/purchases",
        json={"supplier_id": supplier["id"], "branch_id": branch["id"], "reference_number": "F-001",
              "items": [{"product_id": pid, "quantity": 10, "unit_cost": "4.00"}]},
        headers=h,
    ))
    assert purchase["status"] == "draft" and Decimal(purchase["total_amount"]) == Decimal("40.00")
    received = await ok(await api.post(f"{API}/purchases/{purchase['id']}/receive", headers=h))
    assert received["status"] == "received"
    assert await stock_of(api, h, pid) == 10
    await ok(await api.post(f"{API}/purchases/{purchase['id']}/receive", headers=h), expected=(400,))  # no se recibe dos veces

    # --- Caja + venta en efectivo ---
    session = await ok(await api.post(f"{API}/pos/open-session", json={"opening_balance": "100"}, headers=h))
    assert session["status"] == "open"
    await ok(await api.post(f"{API}/pos/open-session", json={"opening_balance": "5"}, headers=h), expected=(409,))

    sale = await ok(await api.post(
        f"{API}/sales",
        json={"payment_method": "cash", "branch_id": branch["id"],
              "items": [{"product_id": pid, "quantity": 3, "unit_price": "10.00"}]},
        headers=h,
    ))
    assert Decimal(sale["total_amount"]) == Decimal("30.00") and sale["status"] == "completed"
    assert await stock_of(api, h, pid) == 7
    assert_stock_invariant()
    # vender desde una sucursal SIN stock se rechaza aunque el producto tenga stock en otra
    await ok(await api.post(
        f"{API}/sales",
        json={"payment_method": "cash", "branch_id": branch2["id"],
              "items": [{"product_id": pid, "quantity": 1, "unit_price": "10"}]},
        headers=h,
    ), expected=(400,))
    await ok(await api.post(  # sucursal inexistente / ajena
        f"{API}/sales",
        json={"payment_method": "cash", "branch_id": 99999,
              "items": [{"product_id": pid, "quantity": 1, "unit_price": "10"}]},
        headers=h,
    ), expected=(404,))
    await ok(await api.post(  # sobreventa rechazada con el mensaje de dominio
        f"{API}/sales",
        json={"payment_method": "cash", "branch_id": branch["id"],
              "items": [{"product_id": pid, "quantity": 99, "unit_price": "10"}]},
        headers=h,
    ), expected=(400,))

    closed = await ok(await api.post(f"{API}/pos/close-session", json={"closing_balance": "130"}, headers=h))
    assert closed["status"] == "closed" and Decimal(closed["expected_balance"]) == Decimal("130.00")
    await ok(await api.post(f"{API}/pos/close-session", json={"closing_balance": "1"}, headers=h), expected=(404,))

    # --- Anulación revierte stock ---
    annulled = await ok(await api.post(f"{API}/sales/{sale['id']}/annul", headers=h))
    assert annulled["status"] == "annulled" and await stock_of(api, h, pid) == 10
    await ok(await api.post(f"{API}/sales/{sale['id']}/annul", headers=h), expected=(400,))

    # --- Ajustes ---
    await ok(await api.post(f"{API}/adjustments", json={"product_id": pid, "adjustment_type": "OUT", "quantity": 2, "reason": "DAMAGE", "branch_id": branch["id"]}, headers=h))
    assert await stock_of(api, h, pid) == 8
    await ok(await api.post(f"{API}/adjustments", json={"product_id": pid, "adjustment_type": "OUT", "quantity": 99, "reason": "LOSS", "branch_id": branch["id"]}, headers=h), expected=(400,))
    assert_stock_invariant()

    # --- Traslado entre sucursales (stock por sucursal viene de la compra recibida) ---
    transfer = await ok(await api.post(
        f"{API}/stock-transfers",
        json={"from_branch_id": branch["id"], "to_branch_id": branch2["id"], "status": "completed",
              "items": [{"product_id": pid, "quantity": 4}]},
        headers=h,
    ))
    assert transfer["status"] == "completed"
    await ok(await api.post(
        f"{API}/stock-transfers",
        json={"from_branch_id": branch["id"], "to_branch_id": branch["id"], "items": [{"product_id": pid, "quantity": 1}]},
        headers=h,
    ), expected=(400,))

    # --- Stock manual por sucursal y kardex ---
    await ok(await api.post(f"{API}/inventory/add-stock", json={"product_id": pid, "branch_id": branch["id"], "quantity": 5}, headers=h))
    kardex = await ok(await api.get(f"{API}/inventory/kardex/{pid}", headers=h))
    assert len(kardex) >= 4
    assert_stock_invariant()


async def test_credit_loyalty_and_quotes(api):
    h = await register_and_login(api)
    branch = await main_branch(api, h)  # las ventas salen de la sucursal del vendedor (la principal)
    supplier = await ok(await api.post(f"{API}/suppliers", json={"name": "P", "code": "P1"}, headers=h))
    product = await ok(await api.post(f"{API}/products", json={"name": "Té", "sku": "TE-1", "price": "20", "stock": 0}, headers=h))
    pid = product["id"]
    purchase = await ok(await api.post(f"{API}/purchases", json={
        "supplier_id": supplier["id"], "branch_id": branch["id"],
        "items": [{"product_id": pid, "quantity": 20, "unit_cost": "8"}]}, headers=h))
    await ok(await api.post(f"{API}/purchases/{purchase['id']}/receive", headers=h))

    # el saldo deudor no puede fijarlo el cliente
    customer = await ok(await api.post(
        f"{API}/customers", json={"name": "Ana", "current_balance": "500", "credit_limit": "1000"}, headers=h))
    assert Decimal(customer["current_balance"]) == 0 and Decimal(customer["credit_limit"]) == Decimal("1000")

    # venta a crédito -> crédito + saldo del cliente
    sale = await ok(await api.post(f"{API}/sales", json={
        "payment_method": "credit", "customer_id": customer["id"],
        "items": [{"product_id": pid, "quantity": 5, "unit_price": "20"}]}, headers=h))
    credits = await ok(await api.get(f"{API}/credits/customer/{customer['id']}", headers=h))
    assert len(credits) == 1 and Decimal(credits[0]["remaining_amount"]) == Decimal("100.00")

    pay = await ok(await api.post(f"{API}/credits/pay", json={"credit_id": credits[0]["id"], "amount": "40"}, headers=h))
    assert Decimal(pay["amount"]) == 40
    await ok(await api.post(f"{API}/credits/pay", json={"credit_id": credits[0]["id"], "amount": "-50"}, headers=h), expected=(422,))
    await ok(await api.post(f"{API}/credits/pay", json={"credit_id": credits[0]["id"], "amount": "9999"}, headers=h), expected=(400,))
    detail = await ok(await api.get(f"{API}/credits/{credits[0]['id']}", headers=h))
    assert Decimal(detail["remaining_amount"]) == Decimal("60.00")

    # un cliente con deuda no se elimina
    await ok(await api.delete(f"{API}/customers/{customer['id']}", headers=h), expected=(400,))

    # anular la venta a crédito libera la deuda
    await ok(await api.post(f"{API}/sales/{sale['id']}/annul", headers=h))
    refreshed = await ok(await api.get(f"{API}/customers/{customer['id']}", headers=h))
    assert Decimal(refreshed["current_balance"]) == 0

    # lealtad: configurar y ajustar puntos
    await ok(await api.put(f"{API}/loyalty/config", json={"points_per_amount": "10", "amount_per_point": "1", "is_active": True}, headers=h))
    await ok(await api.put(f"{API}/loyalty/config", json={"amount_per_point": "-1"}, headers=h), expected=(400,))
    await ok(await api.post(f"{API}/loyalty/transactions", json={"customer_id": customer["id"], "points": 50, "transaction_type": "adjust"}, headers=h))
    after = await ok(await api.get(f"{API}/customers/{customer['id']}", headers=h))
    assert after["id"] == customer["id"]
    await ok(await api.post(f"{API}/loyalty/transactions", json={"customer_id": customer["id"], "points": -999, "transaction_type": "adjust"}, headers=h), expected=(400,))

    # cotización -> venta (una sola vez)
    quote = await ok(await api.post(f"{API}/quotes", json={
        "customer_id": customer["id"], "valid_until": "2030-01-01",
        "items": [{"product_id": pid, "quantity": 2, "unit_price": 20}]}, headers=h))
    converted = await ok(await api.post(f"{API}/quotes/{quote['id']}/convert", headers=h))
    assert Decimal(converted["total_amount"]) == Decimal("40.00")
    await ok(await api.post(f"{API}/quotes/{quote['id']}/convert", headers=h), expected=(400,))
    assert (await ok(await api.get(f"{API}/quotes/{quote['id']}", headers=h)))["status"] == "converted"
    assert_stock_invariant()


async def test_catalog_import_labels_and_reports(api):
    h = await register_and_login(api)
    csv_body = "sku,nombre,precio,stock\nA-1,Alfa,12.5,3\nA-1,Duplicado,1,1\n,sin sku,1,1\nB-2,Beta,7,0\n"
    imported = await ok(await api.post(
        f"{API}/products/import-csv", files={"file": ("p.csv", csv_body.encode(), "text/csv")}, headers=h))
    assert imported["created"] == 2 and imported["skipped"] == 2
    assert_stock_invariant()  # el stock inicial del CSV (A-1: 3 unidades) quedó en la sucursal principal
    assert sql("SELECT pb.stock FROM product_branches pb JOIN products p ON p.id = pb.product_id WHERE p.sku='A-1'", fetch=True)[0][0] == 3
    assert sql("SELECT count(*) FROM inventory_movements WHERE movement_type='INITIAL'", fetch=True)[0][0] == 1

    bulk = await ok(await api.post(f"{API}/products/bulk", json={"products": [
        {"name": "Gamma", "sku": "C-3", "price": "3"}, {"name": "Dup", "sku": "A-1", "price": "3"}]}, headers=h))
    assert bulk["created"] == 1 and bulk["skipped"] == 1
    await ok(await api.post(f"{API}/products", json={"name": "X", "sku": "A-1", "price": "1"}, headers=h), expected=(409,))

    listing = await ok(await api.get(f"{API}/products", headers=h))
    first = listing["items"][0]["id"]
    label = await api.get(f"{API}/products/{first}/labels?quantity=2", headers=h)
    assert label.status_code == 200 and label.headers["content-type"] == "application/pdf"

    for path, kind in (("inventory-excel", "spreadsheet"), ("users-excel", "spreadsheet"),
                       ("suppliers-excel", "spreadsheet"), ("inventory-csv", "csv")):
        response = await api.get(f"{API}/reports/{path}", headers=h)
        assert response.status_code == 200 and kind in response.headers["content-type"], path
    dashboard = await ok(await api.get(f"{API}/reports/dashboard", headers=h))
    assert "stats" in dashboard and "comparison_trends" in dashboard


async def test_privilege_escalation_is_blocked(api):
    owner = await register_and_login(api)
    created = await ok(await api.post(
        f"{API}/users", json={"email": "Seller@Example.com", "password": "sellerpass1", "role": "SELLER"}, headers=owner))
    assert created["email"] == "seller@example.com"  # correo normalizado
    await ok(await api.post(f"{API}/users", json={"email": "seller@example.com", "password": "sellerpass1"}, headers=owner), expected=(400,))
    await ok(await api.post(f"{API}/users", json={"email": "root@example.com", "password": "rootpass123", "role": "SUPERADMIN"}, headers=owner), expected=(403,))

    seller = await login(api, "seller@example.com", "sellerpass1")
    # regresión: un vendedor intentaba ascender con PATCH /users/me
    patched = await ok(await api.patch(f"{API}/users/me", json={"first_name": "Eve", "role": "SUPERADMIN", "is_admin": True}, headers=seller))
    assert patched["first_name"] == "Eve" and patched["role"] == "SELLER" and patched["is_admin"] is False
    await ok(await api.post(f"{API}/users", json={"email": "x@example.com", "password": "password123"}, headers=seller), expected=(403,))
    await ok(await api.get(f"{API}/customers", headers=seller), expected=(403,))
    await ok(await api.put(f"{API}/loyalty/config", json={"is_active": False}, headers=seller), expected=(403,))
    await ok(await api.get(f"{API}/reports/users-excel", headers=seller), expected=(403,))

    # nadie borra su propia cuenta ni edita privilegios propios
    me = await ok(await api.get(f"{API}/users/me", headers=owner))
    await ok(await api.delete(f"{API}/users/{me['id']}", headers=owner), expected=(400,))
    await ok(await api.put(f"{API}/users/{me['id']}", json={"is_active": False}, headers=owner), expected=(403,))

    # roles: nombre duplicado y permisos inexistentes
    role = await ok(await api.post(f"{API}/roles", json={"name": "Cajero", "permission_ids": []}, headers=owner))
    await ok(await api.post(f"{API}/roles", json={"name": "cajero"}, headers=owner), expected=(409,))
    await ok(await api.post(f"{API}/roles", json={"name": "Otro", "permission_ids": [99999]}, headers=owner), expected=(400,))
    await ok(await api.delete(f"{API}/roles/{role['id']}", headers=owner))


async def test_catalog_admin_alerts_and_picking(api):
    h = await register_and_login(api)

    # --- categorías: código único, padre del tenant y sin ciclos ---
    root = await ok(await api.post(f"{API}/categories/", json={"name": "Bebidas", "code": "BEB"}, headers=h))
    child = await ok(await api.post(f"{API}/categories/", json={"name": "Café", "code": "CAF", "parent_id": root["id"]}, headers=h))
    await ok(await api.post(f"{API}/categories/", json={"name": "Otra", "code": "BEB"}, headers=h), expected=(409,))
    await ok(await api.post(f"{API}/categories/", json={"name": "Huérfana", "parent_id": 9999}, headers=h), expected=(404,))
    await ok(await api.put(f"{API}/categories/{root['id']}", json={"parent_id": child["id"]}, headers=h), expected=(400,))  # ciclo
    await ok(await api.put(f"{API}/categories/{root['id']}", json={"parent_id": root["id"]}, headers=h), expected=(400,))
    await ok(await api.delete(f"{API}/categories/{root['id']}", headers=h), expected=(400,))  # tiene hijos
    tree = await ok(await api.get(f"{API}/categories/tree", headers=h))
    assert tree[0]["children"][0]["id"] == child["id"]
    await ok(await api.delete(f"{API}/categories/{child['id']}", headers=h), expected=(204,))
    await ok(await api.delete(f"{API}/categories/{root['id']}", headers=h), expected=(204,))

    # --- proveedores ---
    supplier = await ok(await api.post(f"{API}/suppliers/", json={"name": "Prov", "code": "P-1"}, headers=h))
    await ok(await api.post(f"{API}/suppliers/", json={"name": "Otro", "code": "P-1"}, headers=h), expected=(409,))
    toggled = await ok(await api.patch(f"{API}/suppliers/{supplier['id']}/toggle-active", headers=h))
    assert toggled["is_active"] is False
    await ok(await api.get(f"{API}/suppliers/search?q=Prov&limit=1", headers=h))
    await ok(await api.get(f"{API}/suppliers/9999", headers=h), expected=(404,))

    # --- sucursal con stock no se elimina; sin stock sí ---
    branch = await main_branch(api, h)
    empty = await ok(await api.post(f"{API}/branches", json={"name": "Vacía"}, headers=h))
    live_supplier = await ok(await api.post(f"{API}/suppliers/", json={"name": "Vivo", "code": "P-2"}, headers=h))
    product = await ok(await api.post(f"{API}/products", json={"name": "Pan", "sku": "PAN-1", "price": "2", "min_stock": 5}, headers=h))
    pid = product["id"]
    purchase = await ok(await api.post(f"{API}/purchases", json={
        "supplier_id": live_supplier["id"], "branch_id": branch["id"],
        "items": [{"product_id": pid, "quantity": 8, "unit_cost": "1"}]}, headers=h))
    await ok(await api.post(f"{API}/purchases/{purchase['id']}/receive", headers=h))
    await ok(await api.delete(f"{API}/branches/{branch['id']}", headers=h), expected=(400,))
    await ok(await api.delete(f"{API}/branches/{empty['id']}", headers=h), expected=(200,))
    await ok(await api.delete(f"{API}/branches/{empty['id']}", headers=h), expected=(404,))

    # --- lotes: solo de productos del tenant; suman al stock ---
    batch = await ok(await api.post(f"{API}/product-batches", json={
        "product_id": pid, "batch_number": "L-1", "expiration_date": "2030-01-01", "initial_quantity": 5}, headers=h))
    assert (await ok(await api.get(f"{API}/product-batches/{batch['id']}", headers=h)))["batch_number"] == "L-1"
    await ok(await api.post(f"{API}/product-batches", json={
        "product_id": 99999, "batch_number": "X", "expiration_date": "2030-01-01", "initial_quantity": 1}, headers=h), expected=(404,))
    await ok(await api.get(f"{API}/product-batches/99999", headers=h), expected=(404,))
    assert await stock_of(api, h, pid) == 13

    # --- picking list ordenada por ubicación ---
    await ok(await api.post(f"{API}/inventory/add-stock", json={
        "product_id": pid, "branch_id": branch["id"], "quantity": 1, "aisle": "A10", "shelf": "2", "bin": "1"}, headers=h))
    sale = await ok(await api.post(f"{API}/sales", json={
        "payment_method": "cash", "items": [{"product_id": pid, "quantity": 1, "unit_price": "2"}]}, headers=h))
    picking = await ok(await api.get(f"{API}/sales/{sale['id']}/picking-list", headers=h))
    assert picking and picking[0]["sku"] == "PAN-1" and "location_str" in picking[0]
    assert await ok(await api.get(f"{API}/sales/999999/picking-list", headers=h)) == []

    # --- alertas: vender hasta el mínimo abre una alerta de stock bajo (sin duplicarla) ---
    await ok(await api.post(f"{API}/sales", json={
        "payment_method": "cash", "items": [{"product_id": pid, "quantity": 9, "unit_price": "2"}]}, headers=h))
    low = await ok(await api.get(f"{API}/products/low-stock/list", headers=h))
    assert any(p["id"] == pid for p in low)
    assert_stock_invariant()
