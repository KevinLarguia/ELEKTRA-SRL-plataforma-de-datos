# Elektra SRL — Plataforma de Datos

Plataforma de datos full-stack que migra ~20 años de datos operativos desde planillas Excel a una base de datos PostgreSQL normalizada, con dashboards interactivos, una API REST y herramientas de automatización de negocio.

Desarrollada para **Elektra S.R.L.**, fabricante de iluminación profesional con sede en Santa Fe, Argentina.

<img width="1910" height="962" alt="image" src="https://github.com/user-attachments/assets/a31ecc18-015c-49c9-b166-a77304a8f21c" />
<img width="1910" height="970" alt="image" src="https://github.com/user-attachments/assets/9e6080df-da9f-42a2-93cf-ce89530b87d5" />
<img width="1910" height="971" alt="image" src="https://github.com/user-attachments/assets/263cbcaa-f4c1-416d-9c1b-98c8525d937b" />
<img width="1913" height="972" alt="image" src="https://github.com/user-attachments/assets/8f72587b-7d04-4196-a06b-dc092a9221f2" />
<img width="1914" height="973" alt="image" src="https://github.com/user-attachments/assets/9aeb3a61-ce13-42d2-be52-af940a7664dc" />


---

## Stack tecnológico

| Capa | Tecnologías |
|------|-------------|
| ETL / Procesamiento de datos | Python, pandas, openpyxl |
| Base de datos | PostgreSQL, SQLAlchemy |
| Dashboard | Streamlit, Plotly |
| API REST | FastAPI, uvicorn, Pydantic |
| Reportes | ReportLab (facturas PDF) |
| Configuración | python-dotenv |

---

## Funcionalidades

- **Pipeline ETL** — 6 scripts de limpieza (`01`–`06`) que procesan un Excel de 32 hojas (3.300+ insumos, 2.100+ equipos, 1.700+ clientes, 12.000+ registros de costos) y los cargan en PostgreSQL
- **Esquema relacional** — 9 tablas normalizadas con claves foráneas y vistas SQL para rentabilidad, márgenes, stock faltante y distribución de clientes
- **Dashboard Streamlit** — app multipágina con métricas KPI, análisis de precios, gráficos de rentabilidad, distribución geográfica de clientes y desglose de costos de producción
- **API REST con FastAPI** — endpoint de consulta de precios con documentación interactiva automática en `/docs`
- **Exportación de listas de precios** — generación automática de Excel con precios en ARS y USD
- **Generador de facturas PDF** — herramienta CLI que genera Facturas A/B en PDF a partir de datos de clientes y productos

---

## Arquitectura

```
ELEKTRA_2026.xls  (32 hojas, ~20 años de datos)
        │
        ▼
scripts/01–06_limpieza_*.py     ← ETL con pandas: limpieza y normalización
        │
        ▼
data/*_limpio.csv               ← datasets intermedios limpios
        │
        ▼
scripts/07_crear_esquema_sql.py ← esquema PostgreSQL + vistas de negocio
        │
        ▼
PostgreSQL (elektra_srl)
   ├── 9 tablas normalizadas
   └── vistas SQL (rentabilidad, márgenes, stock, distribución clientes)
        │
        ├── app/                               Dashboard Streamlit (4 páginas)
        ├── scripts/11_api_precios.py          API de precios FastAPI
        ├── scripts/09_exportar_listas_excel.py
        └── scripts/10_generar_factura_pdf.py
```

---

## Estructura del proyecto

```
ELEKTRA-plataforma-de-datos/
├── scripts/
│   ├── 01_limpieza_insumos.py         # Limpieza de insumos/materiales
│   ├── 02_limpieza_equipos.py         # Limpieza de equipos/productos terminados
│   ├── 03_limpieza_clientes.py        # Limpieza de base de clientes
│   ├── 04_limpieza_proveedores.py     # Limpieza de proveedores
│   ├── 05_limpieza_productos.py       # Limpieza de catálogo de productos
│   ├── 06_limpieza_costos.py          # Limpieza de costos de producción
│   ├── 07_crear_esquema_sql.py        # Esquema PostgreSQL y vistas de negocio
│   ├── 08_funciones_negocio.py        # Lógica de negocio compartida
│   ├── 09_exportar_listas_excel.py    # Exportación de listas de precios a Excel
│   ├── 10_generar_factura_pdf.py      # Generador de facturas PDF (CLI)
│   └── 11_api_precios.py              # API REST de precios con FastAPI
├── app/
│   ├── Inicio.py                      # Página principal — resumen KPIs
│   ├── pages/
│   │   ├── 1_Precios.py               # Análisis de precios
│   │   ├── 2_Rentabilidad.py          # Análisis de rentabilidad
│   │   ├── 3_Clientes.py              # Distribución geográfica de clientes
│   │   └── 4_Costos.py                # Desglose de costos de producción
│   └── utils/
│       └── db.py                      # Conexión SQLAlchemy + helper de consultas
├── data/                              # CSVs intermedios (ignorados por git)
├── facturas/                          # PDFs generados (ignorados por git)
├── .env.example                       # Plantilla de variables de entorno
└── requirements.txt
```

---

## Instalación

### Requisitos previos

- Python 3.10+
- PostgreSQL 14+

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/KevinLarguia/ELEKTRA-SRL-plataforma-de-datos.git
cd ELEKTRA-SRL-plataforma-de-datos

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con las credenciales de PostgreSQL
```

### Ejecutar el pipeline ETL

El pipeline requiere el archivo fuente `ELEKTRA_2026.xls` (no incluido — datos propietarios).

```bash
py scripts/01_limpieza_insumos.py
py scripts/02_limpieza_equipos.py
py scripts/03_limpieza_clientes.py
py scripts/04_limpieza_proveedores.py
py scripts/05_limpieza_productos.py
py scripts/06_limpieza_costos.py
py scripts/07_crear_esquema_sql.py   # crea el esquema y las vistas
```

### Levantar el dashboard

```bash
streamlit run app/Inicio.py
```

### Iniciar la API REST

```bash
py -m uvicorn scripts.11_api_precios:app --reload --port 8000
# Documentación interactiva: http://localhost:8000/docs
```

### Generar una factura PDF

```bash
py scripts/10_generar_factura_pdf.py --cliente 15 --items "RADAR:1,VIBRO:2"
py scripts/10_generar_factura_pdf.py --demo    # factura de prueba
```

---

## Datos

El archivo fuente contiene datos propietarios de la empresa y **no está incluido** en este repositorio.

| Tabla | Filas | Descripción |
|-------|-------|-------------|
| `insumos` | 3.358 | Materiales — códigos, precios ARS/USD, proveedor, stock |
| `equipos` | 2.132 | Productos terminados — márgenes, precios público/distribuidor (ARS + USD) |
| `clientes` | 1.763 | Base de clientes — CUIT, provincia, categoría IVA |
| `proveedores` | 259 | Registro de proveedores |
| `productos` | 2.131 | Catálogo de productos con categorías |
| `costos_equipos` | 12.207 | Desglose de costos de producción por equipo |

---

## Decisiones de diseño

- **Precios en doble moneda** — todos los campos de precio conservan columnas ARS y USD; el contexto inflacionario argentino requiere registrar el tipo de cambio por registro
- **Scripts ETL idempotentes** — cada script de limpieza puede ejecutarse de forma independiente sin efectos secundarios
- **Conexión cacheada a la DB** — `@st.cache_resource` de Streamlit garantiza que se reutilice un único engine SQLAlchemy entre sesiones
- **Lógica de negocio en vistas SQL** — rentabilidad y costos viven en la capa de base de datos, manteniendo el código del dashboard simple y los datos portables

---

## Licencia

Proyecto desarrollado para uso interno de Elektra S.R.L. Los datos fuente son propietarios y no se distribuyen con este repositorio.
