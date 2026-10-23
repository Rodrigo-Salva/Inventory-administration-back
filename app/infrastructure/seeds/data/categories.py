"""
Datos de categorías para seeds
"""

CATEGORIES = [
    # Electrónica - Raíz
    {
        "name": "Electrónica",
        "code": "ELEC",
        "description": "Productos electrónicos y tecnología",
        "parent_code": None,
        "display_order": 1
    },
    # Electrónica - Nivel 2
    {
        "name": "Laptops",
        "code": "ELEC-LAP",
        "description": "Computadoras portátiles",
        "parent_code": "ELEC",
        "display_order": 1
    },
    {
        "name": "Smartphones",
        "code": "ELEC-PHONE",
        "description": "Teléfonos inteligentes",
        "parent_code": "ELEC",
        "display_order": 2
    },
    {
        "name": "Accesorios",
        "code": "ELEC-ACC",
        "description": "Accesorios electrónicos",
        "parent_code": "ELEC",
        "display_order": 3
    },
    # Electrónica - Nivel 3
    {
        "name": "Gaming",
        "code": "ELEC-LAP-GAME",
        "description": "Laptops para gaming",
        "parent_code": "ELEC-LAP",
        "display_order": 1
    },
    {
        "name": "Ultrabooks",
        "code": "ELEC-LAP-ULTRA",
        "description": "Laptops ultradelgadas",
        "parent_code": "ELEC-LAP",
        "display_order": 2
    },
    {
        "name": "Android",
        "code": "ELEC-PHONE-AND",
        "description": "Smartphones Android",
        "parent_code": "ELEC-PHONE",
        "display_order": 1
    },
    {
        "name": "iOS",
        "code": "ELEC-PHONE-IOS",
        "description": "iPhones",
        "parent_code": "ELEC-PHONE",
        "display_order": 2
    },
    {
        "name": "Cables",
        "code": "ELEC-ACC-CABLE",
        "description": "Cables y conectores",
        "parent_code": "ELEC-ACC",
        "display_order": 1
    },
    {
        "name": "Cargadores",
        "code": "ELEC-ACC-CHAR",
        "description": "Cargadores y adaptadores",
        "parent_code": "ELEC-ACC",
        "display_order": 2
    },
    
    # Oficina - Raíz
    {
        "name": "Oficina",
        "code": "OFFICE",
        "description": "Productos para oficina",
        "parent_code": None,
        "display_order": 2
    },
    {
        "name": "Escritorio",
        "code": "OFFICE-DESK",
        "description": "Artículos de escritorio",
        "parent_code": "OFFICE",
        "display_order": 1
    },
    {
        "name": "Papelería",
        "code": "OFFICE-PAPER",
        "description": "Papel y documentos",
        "parent_code": "OFFICE",
        "display_order": 2
    },
    
    # Hogar - Raíz
    {
        "name": "Hogar",
        "code": "HOME",
        "description": "Productos para el hogar",
        "parent_code": None,
        "display_order": 3
    },
    {
        "name": "Cocina",
        "code": "HOME-KITCHEN",
        "description": "Artículos de cocina",
        "parent_code": "HOME",
        "display_order": 1
    },
    {
        "name": "Limpieza",
        "code": "HOME-CLEAN",
        "description": "Productos de limpieza",
        "parent_code": "HOME",
        "display_order": 2
    }
]
