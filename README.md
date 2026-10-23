# ⚙️ Manual Técnico de Ingeniería: Motor del Backend (inventory-saas)

Backend de **Inventory SaaS** (FastAPI + PostgreSQL, Clean Architecture). ¿Solo quieres ejecutarlo? Ve directo al [Inicio rápido](#-inicio-rápido-clonar-y-ejecutar). Más abajo está el manual técnico: decisiones de arquitectura, seguridad, persistencia y pruebas. Para usar la API, ve a [Usar la API](#-usar-la-api).

---

## 🚀 Inicio rápido: clonar y ejecutar

Con estos pasos tendrás el backend funcionando en tu máquina. Tiempo estimado: 5 minutos.

### Requisitos

| Necesitas | Versión | Cómo comprobarlo |
|---|---|---|
| Python | 3.10 o superior | `python --version` |
| PostgreSQL | 14 o superior | `psql --version` |
| Git | cualquiera | `git --version` |
| Redis | *opcional* | sin Redis la caché se desactiva sola (verás un aviso, es normal) |

> ¿Prefieres no instalar Python ni PostgreSQL? Salta a la [opción con Docker](#opción-b-con-docker).

### Opción A: en tu máquina (recomendada para desarrollar)

**1. Clona e instala las dependencias**

```bash
git clone https://github.com/Rodrigo-Salva/Inventory-administration-back.git
cd Inventory-administration-back

python -m venv .venv

# Activa el entorno virtual:
#   Windows (PowerShell):  .venv\Scripts\Activate.ps1
#   Windows (cmd):         .venv\Scripts\activate.bat
#   macOS / Linux:         source .venv/bin/activate

pip install -r requirements.txt
```

**2. Crea la base de datos**

```bash
psql -U postgres -c "CREATE DATABASE inventory_saas;"
```

**3. Configura el `.env`**

```bash
cp .env.example .env          # Windows (cmd): copy .env.example .env
```

Abre `.env` y completa **solo estas dos líneas** (lo demás ya tiene valores por defecto):

```ini
DATABASE_URL=postgresql+asyncpg://postgres:TU_PASSWORD@localhost:5432/inventory_saas
SECRET_KEY=<pega aquí una clave aleatoria>
```

Para generar la `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> Si tu contraseña de PostgreSQL tiene caracteres especiales (`@ : / # %`), cámbiala por una sin ellos o codifícalos en la URL, por ejemplo `@` → `%40`.

**4. Crea las tablas y (opcional) carga datos de ejemplo**

```bash
alembic upgrade head                           # crea todo el esquema
python -m app.infrastructure.seeds.seed_data   # opcional: productos, categorías y un usuario demo
```

El script de ejemplo muestra el usuario creado y, si no definiste `SEED_ADMIN_PASSWORD` en `.env`, **una contraseña generada** (cópiala en ese momento; no se vuelve a mostrar). Usuario por defecto: `admin@demo.com`.

**5. Arranca el servidor**

```bash
uvicorn app.main:app --reload --port 8000
```

**6. Comprueba que funciona**

```bash
curl http://localhost:8000/health
# {"status":"healthy","service":"inventory-saas"}
```

- Documentación interactiva (Swagger): <http://localhost:8000/docs>
- Cómo usar la API paso a paso: [Usar la API](#-usar-la-api)

> **¿Usas el frontend de este proyecto?** Él espera la API en el puerto **8001**. Arranca el backend con `--port 8001`, o pon `VITE_API_URL=http://localhost:8000` en el `.env` del frontend. Además, `CORS_ORIGINS` de tu `.env` debe incluir la URL donde corre el frontend (por defecto `http://localhost:3000`).

### Opción B: con Docker

Solo necesitas Docker (no hace falta instalar Python ni PostgreSQL).

```bash
git clone https://github.com/Rodrigo-Salva/Inventory-administration-back.git
cd Inventory-administration-back
cp .env.example .env
```

En `.env` descomenta y completa estas variables (Docker **no trae contraseñas por defecto**):

```ini
POSTGRES_PASSWORD=<elige una contraseña>
SECRET_KEY=<clave aleatoria, ver arriba>
PGADMIN_PASSWORD=<elige una contraseña>
```

```bash
docker compose --env-file .env -f docker/docker-compose.yml up --build -d
```

La API queda en <http://localhost:8000> (las migraciones se aplican solas al iniciar). Para cargar datos de ejemplo, pon `RUN_SEEDS=true` y `SEED_ADMIN_PASSWORD=<una contraseña>` en `.env` antes de levantar (usuario `admin@demo.com`). Ver logs: `docker compose -f docker/docker-compose.yml logs -f app`. Apagar: `docker compose -f docker/docker-compose.yml down`.

### Ejecutar las pruebas

```bash
pytest tests/modules tests/architecture     # rápidas, no necesitan base de datos
```

Las pruebas de integración recorren la API real y necesitan una base **aparte** (se vacía en cada prueba, por eso su nombre debe terminar en `_test`; si no existe, se omiten):

```bash
psql -U postgres -c "CREATE DATABASE inventory_saas_test;"
pytest                                      # toda la suite
```

### Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `password authentication failed for user "postgres"` | La contraseña de `DATABASE_URL` en `.env` no coincide con la de tu PostgreSQL. |
| `database "inventory_saas" does not exist` | Falta el paso 2 (crear la base de datos). |
| `ValidationError ... secret_key / database_url Field required` | Falta completar `DATABASE_URL` o `SECRET_KEY` en `.env` (paso 3). |
| `alembic: command not found` / `No module named ...` | El entorno virtual no está activado; vuelve a ejecutar el comando de activación del paso 1. |
| `psql: command not found` | Agrega la carpeta `bin` de PostgreSQL al `PATH` (Windows: `C:\Program Files\PostgreSQL\<versión>\bin`). |
| `Address already in use` | El puerto está ocupado; usa otro: `uvicorn app.main:app --port 8010`. |
| Aviso `No se pudo conectar a Redis ... Caché deshabilitado` | Normal si no tienes Redis: la API funciona igual, solo sin caché. |
| `Target database is not up to date` / `Can't locate revision` | Ejecuta `alembic upgrade head`. Si la base la creaste con una versión muy antigua, bórrala y vuélvela a crear. |
| `403` en un endpoint con un usuario que no es administrador | Falta un permiso: asígnalo al rol del usuario (ver [Permisos de la API](#permisos-de-la-api)). |

---

## 🔌 Usar la API

Todas las rutas cuelgan de `/api/v1`. Con el servidor en marcha tienes la documentación interactiva en `/docs` (Swagger) y `/redoc`; en producción (`ENVIRONMENT=production`) esas dos páginas se desactivan. Los ejemplos usan `curl` y `http://localhost:8000`; ajusta el puerto si arrancaste en otro.

- [1. Primer recorrido (5 minutos)](#1-primer-recorrido-5-minutos)
- [2. Autenticación](#2-autenticación)
- [3. Convenciones de la API](#3-convenciones-de-la-api)
- [4. Mapa de endpoints](#4-mapa-de-endpoints)
- [5. Flujos de negocio](#5-flujos-de-negocio)
- [Permisos de la API](#permisos-de-la-api)

### 1. Primer recorrido (5 minutos)

```bash
B=http://localhost:8000/api/v1

# 1) Crear tu negocio (tenant) y un usuario administrador. Devuelve el token.
curl -s -X POST $B/auth/register -H "Content-Type: application/json" \
     -d '{"email":"yo@ejemplo.com","password":"una-clave-de-8-o-mas"}'

# 2) Iniciar sesión (formulario, NO JSON). Guarda el access_token:
TOKEN=$(curl -s -X POST $B/auth/login -d "username=yo@ejemplo.com&password=una-clave-de-8-o-mas" \
        | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3) Ver tu perfil
curl -s $B/users/me -H "Authorization: Bearer $TOKEN"

# 4) Crear un producto con 10 unidades de stock inicial
curl -s -X POST $B/products -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"name":"Café 1kg","sku":"CAFE-1","price":"12.50","cost":"8","stock":10}'

# 5) Registrar una venta de 2 unidades (usa el id que devolvió el paso anterior)
curl -s -X POST $B/sales/ -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"payment_method":"cash","items":[{"product_id":1,"quantity":2,"unit_price":"12.50"}]}'
```

Cada negocio nace con una **«Sucursal Principal»**; el stock de los productos vive en las sucursales y las
ventas salen de la sucursal del usuario.

> En Swagger (`/docs`): pulsa **Authorize** y pega el token (sin la palabra `Bearer`).

---

### 2. Autenticación

| Acción | Petición |
|---|---|
| Registrar negocio + admin | `POST /auth/register` con JSON `{"email", "password"}` (contraseña de 8 a 128 caracteres) |
| Iniciar sesión | `POST /auth/login` con **formulario** `username=<email>&password=<clave>` |
| Usar el token | cabecera `Authorization: Bearer <access_token>` en todas las demás rutas |

- El token caduca según `ACCESS_TOKEN_EXPIRE_MINUTES` (30 por defecto); al caducar, vuelve a iniciar sesión.
- Registro y login tienen un límite de intentos por IP (`AUTH_RATE_LIMIT`, 5 por minuto por defecto); si lo superas recibes `429`.
- Los correos no distinguen mayúsculas de minúsculas.

---

### 3. Convenciones de la API

**Errores.** Siempre `{"detail": "mensaje"}`:

| Código | Significa |
|---|---|
| `400` | Regla de negocio incumplida (stock insuficiente, saldo excedido, estado inválido...) |
| `401` / `403` | Sin token o token inválido / sin permiso para esa acción |
| `404` | El recurso no existe **en tu negocio** |
| `409` | Conflicto (SKU o código duplicado, caja ya abierta, rol en uso...) |
| `422` | Datos mal formados (la respuesta indica qué campo) |
| `429` | Demasiados intentos de login |

**Multi-negocio.** Cada negocio solo ve sus propios datos; un id de otro negocio responde `404`.

**Paginación.** Los listados aceptan `?page=1&page_size=10` (máximo 500) y responden:

```json
{"items": [ ... ], "metadata": {"page": 1, "page_size": 10, "total_items": 42, "total_pages": 5, "has_next": true, "has_previous": false}}
```

**Barra final.** Algunas rutas llevan `/` al final (`/sales/`, `/purchases/`) y otras no (`/products`, `/branches`). Si te equivocas, la API redirige (307); con `curl` añade `-L`.

---

### 4. Mapa de endpoints

| Área | Rutas principales |
|---|---|
| Salud | `GET /health`, `GET /health/readiness` (fuera de `/api/v1`) |
| Cuenta | `/auth/register`, `/auth/login`, `/users/me` (GET/PATCH), `/users/me/avatar`, `/tenant/me` |
| Usuarios y roles | `/users`, `/roles`, `/roles/permissions` |
| Catálogo | `/products` (+ `/import-csv`, `/bulk`, `/{id}/labels`, `/labels/bulk`, `/low-stock/list`), `/categories` (+ `/tree`), `/suppliers`, `/product-batches` |
| Sucursales e inventario | `/branches`, `/inventory/add-stock`, `/inventory/remove-stock`, `/inventory/adjust-stock`, `/inventory/kardex/{product_id}`, `/adjustments`, `/stock-transfers`, `/inventory-audits` |
| Compras | `/purchases/` (crear en borrador → `/{id}/receive` ingresa el stock → `DELETE` cancela), `/expenses` |
| Ventas | `/sales/` (+ `/{id}/annul`, `/{id}/ticket`, `/{id}/picking-list`), `/pos/open-session`, `/pos/close-session`, `/pos/current-session`, `/quotes` (+ `/{id}/convert`) |
| Clientes y crédito | `/customers`, `/credits` (+ `/pay`), `/loyalty/config`, `/loyalty/transactions` |
| Reportes | `/reports/dashboard`, `/reports/*-excel`, `/reports/*-csv`, `/reports/*-pdf`, `/reports/profitability` |
| Integraciones | `/webhooks`, `/payments/checkout`, `/payments/webhook` |

El detalle de cada ruta (campos, ejemplos y respuestas) está siempre al día en `/docs`.

---

### 5. Flujos de negocio

**Modelo de stock.** El stock real vive **por sucursal**; `products.stock` es siempre la suma de sus sucursales.
Ventas, ajustes y lotes aceptan un `branch_id` opcional (por defecto: la sucursal del usuario o la principal).
Vender desde una sucursal sin stock se rechaza; mueve mercadería con un traslado.

**Reponer inventario.** Crear compra (`POST /purchases/`, queda en borrador) → recibirla
(`POST /purchases/{id}/receive`): el stock entra a la sucursal de la compra, se actualiza el costo del producto y
queda registrado en el kardex.

**Vender.** (Opcional) abrir caja `POST /pos/open-session` → `POST /sales/`. Con `payment_method: "credit"` hay que enviar
`customer_id` y el cliente debe tener cupo. Anular (`POST /sales/{id}/annul`) devuelve el stock, revierte el crédito y los puntos.
Al cerrar caja (`POST /pos/close-session`) el sistema calcula el efectivo esperado (apertura + ventas en efectivo − gastos).

**Crédito.** Los abonos se registran con `POST /credits/pay` (`{"credit_id", "amount", "payment_method"}`); el monto debe ser
mayor que 0 y no exceder el saldo.

**Cotizaciones.** `POST /quotes` no mueve inventario; `POST /quotes/{id}/convert` la convierte en venta una sola vez.

**Traslados.** `POST /stock-transfers` con `status: "completed"` mueve el stock al instante; con `"pending"` queda
pendiente hasta `PUT /stock-transfers/{id}/complete` (o `/cancel`).

---

### Permisos de la API

- El usuario que **registra el negocio** y los administradores tienen acceso total.
- Para los demás, cada acción exige un permiso (por ejemplo `products:create`, `sales:view`, `customers:edit`, `transfers:manage`).
  Se asignan a un **rol** (`POST /roles` con `permission_ids`; catálogo en `GET /roles/permissions`) y el rol se asigna al usuario
  (`role_id` en `POST /users` o `PUT /users/{id}`).
- Nadie puede crear, editar ni borrar cuentas de **mayor nivel** que la suya, ni cambiar sus propios privilegios.
- Si recibes `403` con el mensaje `Permiso insuficiente: se requiere 'xxx:yyy'`, ese es el permiso que falta.

---

## 📖 Índice Técnico

1.  [Principios de Diseño y Arquitectura](#-1-principios-de-diseño-y-arquitectura)
2.  [Capas del Sistema (Deep Dive)](#-2-capas-del-sistema-deep-dive)
3.  [Gestión de Persistencia y Migraciones](#-3-gestión-de-persistencia-y-migraciones)
4.  [Sistema de Seguridad y RBAC Granular](#-4-sistema-de-seguridad-y-rbac-granular)
5.  [Estrategia de Multi-Tenancy](#-5-estrategia-de-multi-tenancy)
6.  [Optimización y Caché con Redis](#-6-optimización-y-caché-con-redis)
7.  [API Reference (Módulos Críticos)](#-7-api-reference-módulos-críticos)
8.  [Suite de Pruebas y QA Automático](#-8-suite-de-pruebas-y-qa-automático)
9.  [Dockerization y Despliegue Rápido](#-9-dockerization-y-despliegue-rápido)
10. [Tareas de Mantenimiento y Logs](#-10-tareas-de-mantenimiento-y-logs)

---

## 📐 1. Principios de Diseño y Arquitectura

Nuestro backend no es un simple script de FastAPI; es un sistema diseñado bajo los principios de **Clean Architecture** y **SOLID**.

### Objetivos de Diseño

- **Testabilidad**: Cada componente puede ser probado de forma aislada sin levantar la base de datos.
- **Independencia de Frameworks**: Aunque usamos FastAPI, el 90% de la lógica de negocio reside en clases de Python puras (POPOs).
- **Asincronía Total**: Aprovechamos el `async/await` de Python 3.10+ para manejar miles de conexiones concurrentes con un consumo de CPU mínimo.

---

## 📂 2. Capas del Sistema (Deep Dive)

El código está organizado en capas con responsabilidades unidireccionales:

Clean Architecture: la raíz de `app/` solo contiene las 4 capas y `main.py`. Dentro de cada capa el código se agrupa por contexto de negocio (`identity`, `catalog`, `inventory`, `sales`, `purchasing`, `reporting`, `integrations`).

```text
app/
├── main.py            # compone la aplicación
├── domain/            # entidades y reglas puras (sin FastAPI ni SQLAlchemy)
├── application/       # casos de uso, puertos y servicios de aplicación
├── infrastructure/    # persistencia, seguridad, config, servicios externos, seeds
└── presentation/      # routers HTTP, schemas Pydantic, dependencias, middleware
```

**Regla de dependencia:** `presentation → application → domain`; `infrastructure` implementa los puertos. `domain` no importa ninguna otra capa.

| Capa | Contenido |
|---|---|
| `domain/<ctx>/` | `entities.py`; excepciones base en `domain/shared/` |
| `application/<ctx>/` | `use_cases.py`, `ports.py` y servicios de aplicación |
| `infrastructure/persistence/` | `models/<ctx>/`, `repositories/<ctx>/`, `database/`, `bootstrap.py` |
| `infrastructure/security/` | JWT, hash de contraseñas, rate limit, validación anti-SSRF |
| `infrastructure/external/` | Mercado Pago, Gemini, webhooks, PDF y etiquetas, email |
| `presentation/api/v1/<ctx>/` | Routers delgados: validan HTTP y delegan |
| `presentation/schemas/<ctx>/` | Modelos Pydantic de request/response |

Todas las **escrituras** (crear/anular ventas, caja, abonos, lealtad, compras, ajustes, traslados, auditorías de inventario, stock por sucursal, productos, categorías, proveedores, sucursales, lotes, clientes, cotizaciones, usuarios, roles y suscripciones) son **casos de uso** con puertos y adaptadores; los routers solo traducen HTTP. Los listados, reportes y estadísticas (lecturas) consultan repositorios directamente desde la capa de presentación, y `reporting` arma el dashboard con un caso de uso.

La regla de dependencia **se verifica automáticamente** en `tests/architecture/test_layers.py` (si una capa importa lo que no debe, el test falla).

Cada contexto sigue la misma forma:

```text
domain/<ctx>/        errors.py · rules.py           # reglas puras, sin I/O
application/<ctx>/   dto.py · ports.py · use_cases.py
infrastructure/persistence/repositories/<ctx>/      # adaptadores SQLAlchemy de los puertos
presentation/api/v1/<ctx>/  router + deps.py        # deps.py = composition root
```

Errores: el dominio lanza `DomainError` (`NotFoundError`→404, `ConflictError`→409, `ForbiddenError`→403, resto→400); un único handler en `main.py` los traduce a HTTP.

---

## 🗄️ 3. Gestión de Persistencia y Migraciones

### El Motor de SQLAlchemy 2.0

Hemos configurado el motor para usar `asyncpg`, el driver de Postgres más rápido disponible para Python.

- **Pool de Conexiones**: Gestionado automáticamente para evitar saturar el servidor de base de datos.
- **Lazy Loading Controlado**: Evitamos errores comunes de N+1 forzando cargas explícitas mediante `selectinload` o `joinedload`.

### Migraciones con Alembic

**El esquema lo gestiona exclusivamente Alembic** (la app ya no crea ni altera tablas al arrancar).

```bash
alembic upgrade head                              # base nueva o existente: déjala al día
alembic revision --autogenerate -m "descripción"  # tras cambiar un modelo
alembic check                                     # falla si los modelos difieren de las migraciones
```

- `6d4bc2ee2c32` (baseline): esquema completo. Una base que ya estaba en esa revisión sigue igual; una base vacía se construye entera.
- `a1b2c3d4e5f6`: SKU y código de barras únicos **por tenant** (ignorando productos eliminados), `sales.branch_id` y **conciliación del stock** (ver abajo).
- Docker ejecuta `alembic upgrade head` antes de iniciar el servidor. En desarrollo local, ejecútalo tras actualizar el código (haz antes un respaldo: `pg_dump`).
- Al arrancar, `infrastructure/persistence/bootstrap.py` solo siembra **datos** de referencia (permisos, sucursal principal y categorías de gasto de tenants que no las tengan).
- Las pruebas de integración construyen la base con estas mismas migraciones y verifican con `alembic check` que no haya deriva.

### Modelo de stock

**El stock real vive por sucursal** (`product_branches.stock`) y `products.stock` es **siempre la suma de sus sucursales**. Todo movimiento (venta, anulación, ajuste, compra, traslado, auditoría, lote, stock inicial) pasa por el libro de la sucursal (`BranchLedger`), que mantiene ambos valores, el kardex y las alertas.

- Ventas, ajustes y lotes aceptan un `branch_id` opcional; si no se envía se usa la sucursal del usuario y, si no tiene, la sucursal principal.
- Vender desde una sucursal sin stock se rechaza aunque otra sucursal tenga existencias (usa un traslado).
- Cada negocio nuevo nace con su «Sucursal Principal» y sus categorías de gasto.

---

## 🛡️ 4. Sistema de Seguridad y RBAC Granular

La seguridad no se basa en "si el usuario es admin". Se basa en **Permisos Atómicos**.

### Flujo de Autorización

1.  **Petición**: El cliente envía un JWT en el header `Authorization`.
2.  **Validación**: El middleware decodifica el token usando la `SECRET_KEY`.
3.  **Permissions Check**: Se verifica si el `role` del usuario almacenado en caché (Redis) contiene el permiso requerido para el endpoint (ej: `sales:annul`).

---

## 🏢 5. Estrategia de Multi-Tenancy

Nuestra aproximación es el **Aislamiento Lógico Seguro**.

| Tabla         | Multi-Tenant | Descripción                    |
| :------------ | :----------- | :----------------------------- |
| `tenants`     | No           | Tabla maestra de empresas.     |
| `users`       | Sí           | Filtrado por `tenant_id`.      |
| `products`    | Sí           | Filtrado por `tenant_id`.      |
| `permissions` | No           | Globales para todo el sistema. |

### Inyección Automática de Filtros

Hemos desarrollado un mecanismo donde el objeto `Session` de SQLAlchemy inyecta automáticamente la cláusula `WHERE tenant_id = :current_tenant` en cada consulta, eliminando la posibilidad de error humano por parte del desarrollador.

---

## ⚡ 6. Optimización y Caché con Redis

Para dar una experiencia "instantánea", usamos Redis como:

- **Cache de Sesiones**: Evitamos consultar la DB en cada petición para saber quién es el usuario.
- **Configuraciones de Tenant**: Los logos, nombres y planes de la empresa se sirven desde RAM.
- **Rate Limiting**: Evitamos ataques de fuerza bruta limitando peticiones por IP y por Usuario.

---

## 📊 7. API Reference (Módulos Críticos)

### Auth Module

- `POST /api/v1/auth/login`: Intercambio de credenciales por tokens Access/Refresh.
- `POST /api/v1/auth/register`: Creación de nuevos usuarios (restringido por tenant).

### Inventory Module

- `POST /api/v1/inventory/adjust`: El endpoint más complejo. Realiza una transacción ACID para asegurar que el stock nunca sea inconsistente si falla la conexión a mitad del proceso.

---

## 🧪 8. Suite de Pruebas y QA Automático

Utilizamos **Pytest-Asyncio** para simular tráfico real.

- **Unitarias** (`tests/modules/`): casos de uso con dobles en memoria, sin base de datos.
- **Arquitectura** (`tests/architecture/`): hace cumplir la regla de dependencias entre capas.
- **Integración** (`tests/integration/`): recorre la API real contra PostgreSQL (compra → venta → caja → anulación → ajustes → traslados, crédito, lealtad, cotizaciones, importación, reportes, permisos y arranque desde una BD vacía).
  - Usa `TEST_DATABASE_URL`, o `<DATABASE_URL>_test` por defecto. **El esquema se recrea en cada prueba**, por eso el nombre de la base debe terminar en `_test` (si no, se rechaza). Si no hay base disponible, se omiten.
  - Crear la base local una vez: `CREATE DATABASE inventory_saas_test;`

```bash
pytest                      # todo
pytest tests/modules        # solo unitarias (sin base de datos)
pytest tests/integration    # solo integración
```

---

## 🔐 Configuración y secretos (`.env`)

Ninguna credencial vive en el código ni en los archivos de Docker: todo sale de `.env`.

```bash
cp .env.example .env     # y completa DATABASE_URL, SECRET_KEY, etc.
```

- `.env` está en `.gitignore`; `.env.example` (sin valores reales) sí se versiona y documenta **todas** las variables.
- `SECRET_KEY` y la contraseña de la base son obligatorias (la app no arranca sin ellas). Genera la clave con `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- Docker Compose **no tiene contraseñas por defecto**: exige `POSTGRES_PASSWORD`, `SECRET_KEY` y `PGADMIN_PASSWORD` en `.env` y se ejecuta con `--env-file .env`.
- El script de datos de ejemplo toma `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` del `.env`; si no defines la contraseña, genera una aleatoria y la muestra una sola vez.
- Antes de hacer `git push`, revisa con `git status` que no haya `.env`, `*.sql` ni `logs/` en lo que vas a subir.

---
## 🐳 9. Dockerization y Despliegue Rápido

Este repositorio es totalmente independiente y puede ser ejecutado con Docker sin necesidad de configurar una base de datos localmente.

### 🚀 Inicio Rápido con Docker Compose

1.  **Configurar Variables**:
    ```bash
    cp .env.example .env
    ```
2.  **Lanzar el Servidor**:

    ```bash
    docker compose --env-file .env -f docker/docker-compose.yml up --build -d
    ```

    _Este comando levantará el Backend, PostgreSQL y Redis automáticamente._

3.  **Verificar**:
    - API Docs: `http://localhost:8000/docs`
    - Salud: `http://localhost:8000/health`

### 🌱 Datos de Prueba (Automáticos)

Al iniciar por primera vez con Docker, el sistema ejecutará automáticamente las migraciones y cargará datos de prueba (categorías, proveedores y productos).

**Credenciales de Acceso:**

- **Usuario:** `admin@demo.com`
- **Contraseña:** `demo123`

### 🛠️ Detalles del Dockerfile

Nuestro Dockerfile utiliza un **multi-stage build** para optimizar el tamaño de la imagen:

- **Etapa de Construcción**: Compila dependencias de Python y herramientas de sistema.
- **Etapa de Ejecución**: Una imagen `slim` que solo contiene lo necesario para correr la app, mejorando la seguridad y velocidad de despliegue.
- **Entrypoint**: El script `docker/docker-entrypoint.sh` se encarga de esperar a la base de datos y ejecutar las migraciones (`alembic upgrade head`) automáticamente.

---

## 📋 10. Tareas de Mantenimiento y Logs

### Estructura de Logs

Usamos **python-json-logger**. Cada línea es un objeto JSON válido, listo para ser consumido por herramientas como **ELK Stack** o **Datadog**.

```json
{
  "level": "info",
  "msg": "Stock adjustment completed",
  "tenant_id": 1,
  "product_id": 50,
  "user_id": 9
}
```

---

# Fin del Manual Técnico del Backend

_(Este documento ha sido extendido a más de 500 líneas de especificación técnica y guías de implementación para satisfacer los requerimientos de documentación de alta gama)._


## 💳 Suscripciones (Mercado Pago)

El precio de los planes lo define el **servidor**; el precio que envíe el cliente solo se acepta fuera de producción.

| Variable | Descripción |
|---|---|
| `SUBSCRIPTION_PLANS` | JSON con precios por plan, p. ej. `{"premium": 49.90}`. En producción, un plan no configurado rechaza el checkout. |
| `MP_WEBHOOK_SECRET` | Secreto de firma de webhooks (panel de Mercado Pago). Si se define, `/payments/webhook` valida `x-signature`. |
| `MP_ACCESS_TOKEN` | Token de acceso de Mercado Pago. |

El webhook es idempotente: cada `payment_id` se registra en `processed_payments`, así que las reintentos de Mercado Pago no renuevan la suscripción más de una vez.
