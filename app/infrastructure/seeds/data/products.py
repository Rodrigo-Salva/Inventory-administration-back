"""
Datos de productos para seeds
"""

PRODUCTS = [
    # Laptops Gaming
    {
        "name": "ASUS ROG Strix G15",
        "sku": "LAP-ASUS-001",
        "description": "Laptop gaming con RTX 3060, 16GB RAM, 512GB SSD",
        "category_code": "ELEC-LAP-GAME",
        "supplier_code": "TECH-001",
        "price": 1299.99,
        "cost": 950.00,
        "stock": 15,
        "min_stock": 3,
        "max_stock": 50,
        "barcode": "7501234567890",
        "is_active": True
    },
    {
        "name": "MSI Katana GF66",
        "sku": "LAP-MSI-001",
        "description": "Laptop gaming RTX 3050 Ti, 8GB RAM, 512GB SSD",
        "category_code": "ELEC-LAP-GAME",
        "supplier_code": "TECH-001",
        "price": 999.99,
        "cost": 750.00,
        "stock": 12,
        "min_stock": 2,
        "max_stock": 40,
        "barcode": "7501234567891",
        "is_active": True
    },
    
    # Ultrabooks
    {
        "name": "Dell XPS 13",
        "sku": "LAP-DELL-001",
        "description": "Ultrabook 13.3' FHD, i7, 16GB RAM, 512GB SSD",
        "category_code": "ELEC-LAP-ULTRA",
        "supplier_code": "TECH-001",
        "price": 1499.99,
        "cost": 1100.00,
        "stock": 8,
        "min_stock": 2,
        "max_stock": 30,
        "barcode": "7501234567892",
        "is_active": True
    },
    {
        "name": "MacBook Air M2",
        "sku": "LAP-APPLE-001",
        "description": "MacBook Air con chip M2, 8GB RAM, 256GB SSD",
        "category_code": "ELEC-LAP-ULTRA",
        "supplier_code": "TECH-001",
        "price": 1199.99,
        "cost": 900.00,
        "stock": 10,
        "min_stock": 3,
        "max_stock": 35,
        "barcode": "7501234567893",
        "is_active": True
    },
    
    # Smartphones Android
    {
        "name": "Samsung Galaxy S23",
        "sku": "PHONE-SAM-001",
        "description": "Smartphone 6.1' AMOLED, 8GB RAM, 128GB",
        "category_code": "ELEC-PHONE-AND",
        "supplier_code": "GLOBAL-001",
        "price": 799.99,
        "cost": 600.00,
        "stock": 25,
        "min_stock": 5,
        "max_stock": 100,
        "barcode": "7501234567894",
        "is_active": True
    },
    {
        "name": "Google Pixel 7",
        "sku": "PHONE-GOOGLE-001",
        "description": "Smartphone 6.3' OLED, 8GB RAM, 128GB",
        "category_code": "ELEC-PHONE-AND",
        "supplier_code": "GLOBAL-001",
        "price": 599.99,
        "cost": 450.00,
        "stock": 20,
        "min_stock": 4,
        "max_stock": 80,
        "barcode": "7501234567895",
        "is_active": True
    },
    
    # Smartphones iOS
    {
        "name": "iPhone 14",
        "sku": "PHONE-APPLE-001",
        "description": "iPhone 14 6.1' Super Retina XDR, 128GB",
        "category_code": "ELEC-PHONE-IOS",
        "supplier_code": "GLOBAL-001",
        "price": 899.99,
        "cost": 700.00,
        "stock": 18,
        "min_stock": 5,
        "max_stock": 90,
        "barcode": "7501234567896",
        "is_active": True
    },
    {
        "name": "iPhone 14 Pro",
        "sku": "PHONE-APPLE-002",
        "description": "iPhone 14 Pro 6.1' ProMotion, 256GB",
        "category_code": "ELEC-PHONE-IOS",
        "supplier_code": "GLOBAL-001",
        "price": 1199.99,
        "cost": 950.00,
        "stock": 12,
        "min_stock": 3,
        "max_stock": 60,
        "barcode": "7501234567897",
        "is_active": True
    },
    
    # Cables
    {
        "name": "Cable USB-C a USB-C 2m",
        "sku": "ACC-CABLE-001",
        "description": "Cable USB-C de alta velocidad, 2 metros",
        "category_code": "ELEC-ACC-CABLE",
        "supplier_code": "GLOBAL-001",
        "price": 19.99,
        "cost": 8.00,
        "stock": 150,
        "min_stock": 30,
        "max_stock": 500,
        "barcode": "7501234567898",
        "is_active": True
    },
    {
        "name": "Cable Lightning 1m",
        "sku": "ACC-CABLE-002",
        "description": "Cable Lightning certificado MFi, 1 metro",
        "category_code": "ELEC-ACC-CABLE",
        "supplier_code": "GLOBAL-001",
        "price": 24.99,
        "cost": 10.00,
        "stock": 120,
        "min_stock": 25,
        "max_stock": 400,
        "barcode": "7501234567899",
        "is_active": True
    },
    
    # Cargadores
    {
        "name": "Cargador USB-C 65W",
        "sku": "ACC-CHAR-001",
        "description": "Cargador rápido USB-C 65W con cable",
        "category_code": "ELEC-ACC-CHAR",
        "supplier_code": "GLOBAL-001",
        "price": 39.99,
        "cost": 18.00,
        "stock": 80,
        "min_stock": 15,
        "max_stock": 300,
        "barcode": "7501234567900",
        "is_active": True
    },
    {
        "name": "Cargador Inalámbrico 15W",
        "sku": "ACC-CHAR-002",
        "description": "Cargador inalámbrico Qi 15W",
        "category_code": "ELEC-ACC-CHAR",
        "supplier_code": "GLOBAL-001",
        "price": 29.99,
        "cost": 12.00,
        "stock": 60,
        "min_stock": 10,
        "max_stock": 250,
        "barcode": "7501234567901",
        "is_active": True
    },
    
    # Oficina - Escritorio
    {
        "name": "Mouse Inalámbrico Logitech",
        "sku": "OFFICE-MOUSE-001",
        "description": "Mouse inalámbrico ergonómico",
        "category_code": "OFFICE-DESK",
        "supplier_code": "OFFICE-001",
        "price": 29.99,
        "cost": 15.00,
        "stock": 45,
        "min_stock": 10,
        "max_stock": 200,
        "barcode": "7501234567902",
        "is_active": True
    },
    {
        "name": "Teclado Mecánico RGB",
        "sku": "OFFICE-KEY-001",
        "description": "Teclado mecánico con iluminación RGB",
        "category_code": "OFFICE-DESK",
        "supplier_code": "OFFICE-001",
        "price": 79.99,
        "cost": 40.00,
        "stock": 30,
        "min_stock": 5,
        "max_stock": 150,
        "barcode": "7501234567903",
        "is_active": True
    },
    
    # Oficina - Papelería
    {
        "name": "Resma Papel A4 500 hojas",
        "sku": "OFFICE-PAPER-001",
        "description": "Papel bond blanco A4, 75g/m²",
        "category_code": "OFFICE-PAPER",
        "supplier_code": "OFFICE-001",
        "price": 5.99,
        "cost": 3.00,
        "stock": 200,
        "min_stock": 50,
        "max_stock": 1000,
        "barcode": "7501234567904",
        "is_active": True
    },
    {
        "name": "Bolígrafos Azules Caja x12",
        "sku": "OFFICE-PEN-001",
        "description": "Caja de 12 bolígrafos azules",
        "category_code": "OFFICE-PAPER",
        "supplier_code": "OFFICE-001",
        "price": 8.99,
        "cost": 4.00,
        "stock": 100,
        "min_stock": 20,
        "max_stock": 500,
        "barcode": "7501234567905",
        "is_active": True
    },
    
    # Hogar - Cocina
    {
        "name": "Licuadora 600W",
        "sku": "HOME-BLEND-001",
        "description": "Licuadora de 600W con jarra de vidrio",
        "category_code": "HOME-KITCHEN",
        "supplier_code": "HOME-001",
        "price": 49.99,
        "cost": 25.00,
        "stock": 25,
        "min_stock": 5,
        "max_stock": 100,
        "barcode": "7501234567906",
        "is_active": True
    },
    {
        "name": "Juego de Ollas 5 piezas",
        "sku": "HOME-POTS-001",
        "description": "Set de ollas antiadherentes",
        "category_code": "HOME-KITCHEN",
        "supplier_code": "HOME-001",
        "price": 89.99,
        "cost": 45.00,
        "stock": 15,
        "min_stock": 3,
        "max_stock": 80,
        "barcode": "7501234567907",
        "is_active": True
    },
    
    # Hogar - Limpieza
    {
        "name": "Aspiradora 1200W",
        "sku": "HOME-VAC-001",
        "description": "Aspiradora con filtro HEPA",
        "category_code": "HOME-CLEAN",
        "supplier_code": "HOME-001",
        "price": 129.99,
        "cost": 70.00,
        "stock": 10,
        "min_stock": 2,
        "max_stock": 50,
        "barcode": "7501234567908",
        "is_active": True
    },
    {
        "name": "Trapeador con Balde",
        "sku": "HOME-MOP-001",
        "description": "Sistema de trapeador giratorio con balde",
        "category_code": "HOME-CLEAN",
        "supplier_code": "HOME-001",
        "price": 34.99,
        "cost": 18.00,
        "stock": 20,
        "min_stock": 5,
        "max_stock": 100,
        "barcode": "7501234567909",
        "is_active": True
    }
]
