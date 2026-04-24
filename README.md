# Elektra SRL — Data Platform

A full-stack data platform that migrates ~20 years of operational data from Excel spreadsheets into a normalized PostgreSQL database, with interactive dashboards, a REST API, and business automation tools.

Built for **Elektra S.R.L.**, a professional lighting manufacturer based in Santa Fe, Argentina.

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| ETL / Data Processing | Python, pandas, openpyxl |
| Database | PostgreSQL, SQLAlchemy |
| Dashboard | Streamlit, Plotly |
| REST API | FastAPI, uvicorn, Pydantic |
| Reporting | ReportLab (PDF invoices) |
| Config | python-dotenv |

---

## Features

- **ETL Pipeline** — 6-step cleaning pipeline (scripts `01`–`06`) that processes a 32-sheet Excel workbook (3,300+ materials, 2,100+ products, 1,700+ clients, 12,000+ cost records) into clean CSVs loaded into PostgreSQL
- **Relational Schema** — normalized schema with 9 tables, foreign key constraints, and SQL views for profitability, margins, stock gaps, and client distribution
- **Streamlit Dashboard** — multi-page app with KPI metrics, pricing analysis, profitability charts, client geographic distribution, and cost breakdowns
- **FastAPI REST Service** — price query endpoint with interactive auto-generated docs at `/docs`
- **Price List Export** — automated Excel generation with formatted ARS + USD price sheets
- **PDF Invoice Generator** — CLI tool that generates Factura A/B PDFs from client and product data

---

## Architecture

```
ELEKTRA_2026.xls  (32 sheets, ~20 years of data)
        │
        ▼
scripts/01–06_limpieza_*.py     ← pandas ETL, cleaning, normalization
        │
        ▼
data/*_limpio.csv               ← intermediate clean datasets
        │
        ▼
scripts/07_crear_esquema_sql.py ← PostgreSQL schema + business views
        │
        ▼
PostgreSQL (elektra_srl)
   ├── 9 normalized tables
   └── SQL views (rentabilidad, márgenes, stock, distribución clientes)
        │
        ├── app/                             Streamlit dashboard (4 pages)
        ├── scripts/11_api_precios.py        FastAPI price API
        ├── scripts/09_exportar_listas_excel.py
        └── scripts/10_generar_factura_pdf.py
```

---

## Project Structure

```
ELEKTRA-plataforma-de-datos/
├── scripts/
│   ├── 01_limpieza_insumos.py         # Raw materials cleaning
│   ├── 02_limpieza_equipos.py         # Finished products cleaning
│   ├── 03_limpieza_clientes.py        # Client database cleaning
│   ├── 04_limpieza_proveedores.py     # Supplier registry cleaning
│   ├── 05_limpieza_productos.py       # Product catalog cleaning
│   ├── 06_limpieza_costos.py          # Production cost records cleaning
│   ├── 07_crear_esquema_sql.py        # PostgreSQL schema & business views
│   ├── 08_funciones_negocio.py        # Shared business logic
│   ├── 09_exportar_listas_excel.py    # Price list → Excel export
│   ├── 10_generar_factura_pdf.py      # PDF invoice generator (CLI)
│   └── 11_api_precios.py              # FastAPI REST price API
├── app/
│   ├── Inicio.py                      # Main page — KPI overview
│   ├── pages/
│   │   ├── 1_Precios.py               # Pricing analysis
│   │   ├── 2_Rentabilidad.py          # Profitability analysis
│   │   ├── 3_Clientes.py              # Client geographic distribution
│   │   └── 4_Costos.py                # Production cost breakdown
│   └── utils/
│       └── db.py                      # SQLAlchemy connection + query helper
├── data/                              # Intermediate CSVs (git-ignored)
├── facturas/                          # Generated PDFs (git-ignored)
├── .env.example                       # Environment variables template
└── requirements.txt
```

---

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 14+

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/elektra-plataforma-de-datos.git
cd elektra-plataforma-de-datos

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### Running the ETL Pipeline

The pipeline requires the source `ELEKTRA_2026.xls` file (not included — proprietary data).

```bash
py scripts/01_limpieza_insumos.py
py scripts/02_limpieza_equipos.py
py scripts/03_limpieza_clientes.py
py scripts/04_limpieza_proveedores.py
py scripts/05_limpieza_productos.py
py scripts/06_limpieza_costos.py
py scripts/07_crear_esquema_sql.py   # creates schema + views
```

### Launching the Dashboard

```bash
streamlit run app/Inicio.py
```

### Starting the REST API

```bash
py -m uvicorn scripts.11_api_precios:app --reload --port 8000
# Interactive docs: http://localhost:8000/docs
```

### Generating a PDF Invoice

```bash
py scripts/10_generar_factura_pdf.py --cliente 15 --items "RADAR:1,VIBRO:2"
py scripts/10_generar_factura_pdf.py --demo    # demo invoice
```

---

## Data Overview

The source workbook contains proprietary business data and is **not included** in this repository.

| Table | Source rows | Description |
|-------|-------------|-------------|
| `insumos` | 3,358 | Raw materials — codes, ARS/USD pricing, supplier, stock |
| `equipos` | 2,132 | Finished products — margins, public/distributor prices (ARS + USD) |
| `clientes` | 1,763 | Client registry — CUIT, province, IVA category |
| `proveedores` | 259 | Supplier registry |
| `productos` | 2,131 | Product catalog with categories |
| `costos_equipos` | 12,207 | Production cost breakdown per product |

---

## Key Design Decisions

- **Dual-currency pricing** — all price fields preserve both ARS and USD columns; Argentina's inflationary context requires tracking the exchange rate per record
- **Idempotent ETL scripts** — each cleaning script can be re-run independently without side effects
- **Cached DB connection** — Streamlit's `@st.cache_resource` ensures a single SQLAlchemy engine is reused across user sessions
- **SQL business views** — profitability and cost logic lives in the database layer, keeping the dashboard code thin and the data portable

---

## License

This project was built for internal use at Elektra S.R.L. The source data is proprietary and not distributed with this repository.
