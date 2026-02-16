# 📦 Inventory SaaS - Sistema de Gestión de Inventario Multi-Tenant

Sistema completo de gestión de inventario construido con **FastAPI**, **PostgreSQL** y **SQLAlchemy**, diseñado para soportar múltiples tenants (empresas) con autenticación JWT y control de acceso basado en roles.

## 🚀 Características

- ✅ **Multi-tenant**: Soporte para múltiples empresas con aislamiento de datos
- 🔐 **Autenticación JWT**: Sistema seguro de autenticación y autorización
- 👥 **Control de Acceso por Roles**: Admin, Manager, User
- 📊 **Gestión Completa de Inventario**:
  - Productos con categorías y proveedores
  - Movimientos de inventario (entradas, salidas, ajustes, transferencias)
  - Alertas de stock bajo automáticas
  - Historial completo de movimientos
- 🐳 **Docker Ready**: Configuración completa para desarrollo y producción
- 🔄 **Migraciones con Alembic**: Control de versiones de base de datos
- 🚦 **Rate Limiting**: Protección contra abuso de API
- 📝 **Logging Estructurado**: Logs en formato JSON
- ⚡ **Async/Await**: Operaciones asíncronas para mejor rendimiento

## 📋 Requisitos Previos

- Python 3.11+
- PostgreSQL 14+
- Redis (opcional, para rate limiting y caché)
- Docker y Docker Compose (opcional)

## 🛠️ Instalación

### Opción 1: Instalación Local

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd inventory-saas
```

2. **Crear entorno virtual**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

5. **Ejecutar migraciones**
```bash
alembic upgrade head
```

6. **Iniciar el servidor**
```bash
uvicorn app.main:app --reload --port 8002
```

### Opción 2: Docker

```bash
# Desarrollo
docker-compose -f docker-compose.dev.yml up

# Producción
docker-compose up -d
```

## 🔧 Configuración

Copia `.env.example` a `.env` y configura las siguientes variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/inventory_db

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

## 📚 API Endpoints

### Autenticación
- `POST /auth/login` - Iniciar sesión
- `POST /auth/register` - Registrar nuevo usuario

### Productos
- `GET /api/v1/products` - Listar productos
- `POST /api/v1/products` - Crear producto
- `GET /api/v1/products/{id}` - Obtener producto
- `PUT /api/v1/products/{id}` - Actualizar producto
- `DELETE /api/v1/products/{id}` - Eliminar producto

### Inventario
- `POST /api/v1/inventory/add-stock` - Agregar stock
- `POST /api/v1/inventory/remove-stock` - Remover stock
- `GET /api/v1/inventory/movements` - Listar movimientos
- `GET /api/v1/inventory/alerts` - Alertas de stock bajo

### Categorías y Proveedores
- `GET /api/v1/categories` - Listar categorías
- `POST /api/v1/categories` - Crear categoría
- `GET /api/v1/suppliers` - Listar proveedores
- `POST /api/v1/suppliers` - Crear proveedor

**Documentación interactiva**: `http://localhost:8002/docs`

## 🗄️ Estructura del Proyecto

```
inventory-saas/
├── app/
│   ├── api/          # Endpoints de la API
│   ├── core/         # Configuración y seguridad
│   ├── models/       # Modelos SQLAlchemy
│   ├── schemas/      # Esquemas Pydantic
│   ├── services/     # Lógica de negocio
│   └── main.py       # Punto de entrada
├── alembic/          # Migraciones de BD
├── .env.example      # Variables de entorno ejemplo
├── requirements.txt  # Dependencias Python
└── docker-compose.yml
```

## 🔐 Roles y Permisos

| Rol | Permisos |
|-----|----------|
| **Admin** | Acceso completo al sistema |
| **Manager** | Gestión de inventario, productos, reportes |
| **User** | Consulta de inventario y productos |

## 🧪 Testing

```bash
# Ejecutar tests (cuando estén disponibles)
pytest

# Con cobertura
pytest --cov=app
```

## 📦 Migraciones de Base de Datos

```bash
# Crear nueva migración
alembic revision --autogenerate -m "descripción"

# Aplicar migraciones
alembic upgrade head

# Revertir última migración
alembic downgrade -1
```

## 🐳 Docker

```bash
# Construir imagen
docker build -t inventory-saas .

# Ejecutar con docker-compose
docker-compose up -d

# Ver logs
docker-compose logs -f app
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT.

## 👨‍💻 Autor

Rodrigo Salva

---

⭐ Si este proyecto te fue útil, considera darle una estrella en GitHub!
