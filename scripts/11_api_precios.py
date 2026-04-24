"""
API REST con FastAPI para consulta de precios de Elektra SRL.
Levantar con:
    py -m uvicorn 11_api_precios:app --reload --port 8000

Documentación interactiva en: http://localhost:8000/docs
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus
from pydantic import BaseModel
from typing import Optional
import os, datetime

load_dotenv()
password = quote_plus(os.getenv('DB_PASSWORD'))
engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{password}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

app = FastAPI(
    title="Elektra SRL — API de Precios",
    description="Consulta de precios, insumos, clientes y costos de producción.",
    version="1.0.0",
    contact={"name": "Elektra S.R.L.", "email": "ventas@elektrasrl.com.ar"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def db_query(sql, params=None):
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        cols = list(result.keys())
        rows = [dict(zip(cols, row)) for row in result.fetchall()]
    return rows

# ── Modelos de respuesta ──────────────────────────────────────────────────────
class Producto(BaseModel):
    id: int
    nombre: str
    categoria: Optional[str]
    precio_sin_iva: Optional[float]
    iva_pct: Optional[float]
    precio_con_iva: Optional[float]
    precio_usd: Optional[float]
    descuento_dist_pct: Optional[int]

class Insumo(BaseModel):
    codigo: int
    descripcion: str
    rubro: Optional[str]
    proveedor: Optional[str]
    precio_ars: Optional[float]
    precio_usd: Optional[float]
    stock: Optional[float]

class CostoEquipo(BaseModel):
    equipo_nombre: str
    costo_total: Optional[float]

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def raiz():
    return {
        "api": "Elektra SRL — API de Precios",
        "version": "1.0.0",
        "fecha": datetime.date.today().isoformat(),
        "endpoints": [
            "/productos", "/productos/{nombre}",
            "/insumos",   "/insumos/{codigo}",
            "/equipos",   "/equipos/{nombre}/costo",
            "/clientes",  "/clientes/{codigo}",
            "/categorias",
            "/cotizacion",
            "/docs",
        ]
    }

@app.get("/productos", tags=["Precios"])
def listar_productos(
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    buscar:    Optional[str] = Query(None, description="Buscar por nombre"),
    limit:     int           = Query(50,   ge=1, le=500),
):
    """Lista de precios al público. Soporta filtro por categoría y búsqueda por nombre."""
    sql = "SELECT * FROM v_lista_precios_publica WHERE 1=1"
    params = {}
    if categoria:
        sql += " AND UPPER(categoria) = UPPER(:cat)"
        params["cat"] = categoria
    if buscar:
        sql += " AND nombre ILIKE :buscar"
        params["buscar"] = f"%{buscar}%"
    sql += f" LIMIT {limit}"
    return db_query(sql, params)

@app.get("/productos/{nombre}", tags=["Precios"])
def precio_producto(nombre: str):
    """Precio de un producto específico (público y distribuidor)."""
    rows = db_query(
        "SELECT p.*, d.precio_dist_sin_iva, d.precio_dist_con_iva "
        "FROM v_lista_precios_publica p "
        "LEFT JOIN v_lista_precios_distribuidor d USING (id) "
        "WHERE UPPER(p.nombre) = UPPER(:n) LIMIT 1",
        {"n": nombre}
    )
    if not rows:
        raise HTTPException(404, f"Producto '{nombre}' no encontrado.")
    return rows[0]

@app.get("/insumos", tags=["Insumos"])
def listar_insumos(
    rubro:  Optional[str] = Query(None),
    buscar: Optional[str] = Query(None),
    limit:  int           = Query(50, ge=1, le=500),
):
    """Lista de insumos con precios ARS y USD."""
    sql = """
        SELECT codigo, descripcion, rubro, proveedor,
               precio_ars, precio_usd, precio_ars_iva, stock
        FROM insumos WHERE precio_ars IS NOT NULL
    """
    params = {}
    if rubro:
        sql += " AND UPPER(rubro) = UPPER(:rubro)"
        params["rubro"] = rubro
    if buscar:
        sql += " AND descripcion ILIKE :buscar"
        params["buscar"] = f"%{buscar}%"
    sql += f" ORDER BY descripcion LIMIT {limit}"
    return db_query(sql, params)

@app.get("/insumos/{codigo}", tags=["Insumos"])
def detalle_insumo(codigo: int):
    """Detalle completo de un insumo por código."""
    rows = db_query("SELECT * FROM insumos WHERE codigo = :c", {"c": codigo})
    if not rows:
        raise HTTPException(404, f"Insumo {codigo} no encontrado.")
    return rows[0]

@app.get("/equipos", tags=["Equipos"])
def listar_equipos(
    clasificacion: Optional[str] = Query(None),
    limit:         int           = Query(50, ge=1, le=500),
):
    """Lista de equipos con precios y márgenes."""
    sql = "SELECT * FROM v_equipos_rentabilidad WHERE 1=1"
    params = {}
    if clasificacion:
        sql += " AND UPPER(clasificacion) = UPPER(:cl)"
        params["cl"] = clasificacion
    sql += f" LIMIT {limit}"
    return db_query(sql, params)

@app.get("/equipos/{nombre}/costo", tags=["Equipos"])
def costo_equipo(nombre: str):
    """Costo de producción detallado de un equipo."""
    costo = db_query(
        "SELECT fn_costo_total_equipo(:n) AS costo_total", {"n": nombre}
    )
    detalle = db_query(
        "SELECT * FROM fn_detalle_costo_equipo(:n)", {"n": nombre}
    )
    if not detalle:
        raise HTTPException(404, f"Equipo '{nombre}' no encontrado en costos.")
    return {
        "equipo":      nombre.upper(),
        "costo_total": float(costo[0]["costo_total"]) if costo[0]["costo_total"] else 0,
        "cant_materiales": len(detalle),
        "detalle":     detalle,
    }

@app.get("/clientes", tags=["Clientes"])
def listar_clientes(
    provincia: Optional[str] = Query(None),
    tipo_iva:  Optional[str] = Query(None),
    buscar:    Optional[str] = Query(None),
    limit:     int           = Query(50, ge=1, le=500),
):
    """Lista de clientes con filtros."""
    sql = "SELECT codigo, nombre, ciudad, provincia, tipo_iva, cuit FROM clientes WHERE nombre IS NOT NULL"
    params = {}
    if provincia:
        sql += " AND UPPER(provincia) = UPPER(:prov)"
        params["prov"] = provincia
    if tipo_iva:
        sql += " AND UPPER(tipo_iva) ILIKE :iva"
        params["iva"] = f"%{tipo_iva}%"
    if buscar:
        sql += " AND nombre ILIKE :buscar"
        params["buscar"] = f"%{buscar}%"
    sql += f" ORDER BY nombre LIMIT {limit}"
    return db_query(sql, params)

@app.get("/clientes/{codigo}", tags=["Clientes"])
def detalle_cliente(codigo: int):
    """Detalle de un cliente por código."""
    rows = db_query("SELECT * FROM clientes WHERE codigo = :c", {"c": codigo})
    if not rows:
        raise HTTPException(404, f"Cliente {codigo} no encontrado.")
    return rows[0]

@app.get("/categorias", tags=["Precios"])
def listar_categorias():
    """Lista de categorías con estadísticas de precios."""
    return db_query("SELECT * FROM v_rentabilidad_por_categoria")

@app.get("/cotizacion", tags=["Info"])
def cotizaciones():
    """Cotizaciones de dólar registradas por proveedor."""
    return db_query("""
        SELECT empresa, cotizacion_dolar, rubro, ciudad
        FROM proveedores
        WHERE cotizacion_dolar IS NOT NULL
        ORDER BY cotizacion_dolar DESC
        LIMIT 20
    """)

@app.get("/stock-critico", tags=["Insumos"])
def stock_critico():
    """Insumos con stock = 0 o sin dato."""
    return db_query("SELECT * FROM v_insumos_sin_stock LIMIT 100")
