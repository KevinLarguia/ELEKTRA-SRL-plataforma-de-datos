from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

load_dotenv()

password = quote_plus(os.getenv('DB_PASSWORD'))
engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{password}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

schema_sql = """
-- ============================================================
-- ELEKTRA SRL - Esquema relacional
-- ============================================================

-- Tablas maestras (sin dependencias)

CREATE TABLE IF NOT EXISTS categorias (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tipos_iva (
    id          SERIAL PRIMARY KEY,
    descripcion VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS provincias (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL UNIQUE
);

-- Proveedores

CREATE TABLE IF NOT EXISTS proveedores (
    codigo              INTEGER PRIMARY KEY,
    empresa             VARCHAR(200) NOT NULL,
    cotizacion_dolar    NUMERIC(12,2),
    telefono            VARCHAR(100),
    direccion           VARCHAR(200),
    codigo_postal       VARCHAR(20),
    ciudad              VARCHAR(100),
    provincia           VARCHAR(100),
    rubro               VARCHAR(100),
    email               VARCHAR(150),
    contacto            VARCHAR(100),
    cuit                VARCHAR(30),
    sitio_web           VARCHAR(200),
    fecha_modificacion  DATE,
    ultimo_aumento_pct  NUMERIC(8,2)
);

-- Clientes

CREATE TABLE IF NOT EXISTS clientes (
    codigo          INTEGER PRIMARY KEY,
    nombre          VARCHAR(200) NOT NULL,
    fantasia        VARCHAR(200),
    contacto        VARCHAR(150),
    direccion       VARCHAR(200),
    codigo_postal   VARCHAR(20),
    ciudad          VARCHAR(100),
    telefono        VARCHAR(60),
    telefono2       VARCHAR(60),
    cuit            VARCHAR(30),
    tipo_iva        VARCHAR(100),
    provincia       VARCHAR(100)
);

-- Insumos (materiales)

CREATE TABLE IF NOT EXISTS insumos (
    codigo              INTEGER PRIMARY KEY,
    descripcion         VARCHAR(300) NOT NULL,
    unidad              NUMERIC(10,4),
    tipo_unidad         VARCHAR(20),
    precio_usd          NUMERIC(14,4),
    precio_ars          NUMERIC(14,4),
    precio_ars_iva      NUMERIC(14,4),
    oferta_dto          NUMERIC(10,4),
    precio_final_iva    NUMERIC(14,4),
    proveedor_codigo    INTEGER REFERENCES proveedores(codigo) ON DELETE SET NULL,
    rubro               VARCHAR(100),
    sup_pintura         NUMERIC(12,4),
    medidas             VARCHAR(100),
    sup_chapa           NUMERIC(12,4),
    fecha_actualizacion DATE,
    proveedor           VARCHAR(200),
    cotizacion_dolar    NUMERIC(12,2),
    stock               NUMERIC(14,4),
    us_tot              NUMERIC(14,4)
);

-- Productos (catálogo con categorías)

CREATE TABLE IF NOT EXISTS productos (
    id                      INTEGER PRIMARY KEY,
    nombre                  VARCHAR(200) NOT NULL,
    precio_base             NUMERIC(14,4),
    tasa_iva                NUMERIC(6,4),
    precio_iva              NUMERIC(14,4),
    precio_dolares          NUMERIC(14,4),
    precio_distribuidor     NUMERIC(14,4),
    precio_distribuidor_iva NUMERIC(14,4),
    categoria_id            INTEGER REFERENCES categorias(id) ON DELETE SET NULL,
    categoria               VARCHAR(100),
    descuento               NUMERIC(8,4)
);

-- Equipos (productos terminados)

CREATE TABLE IF NOT EXISTS equipos (
    codigo                      INTEGER PRIMARY KEY,
    nombre                      VARCHAR(200) NOT NULL,
    clasificacion               VARCHAR(100),
    costo_iva_inc               NUMERIC(14,4),
    margen                      NUMERIC(8,4),
    precio_publico_iva_cdo      NUMERIC(14,4),
    precio_publico_iva_cc       NUMERIC(14,4),
    precio_publico_usd_cdo      NUMERIC(14,4),
    precio_publico_usd_cc       NUMERIC(14,4),
    dto_distribuidor            NUMERIC(8,4),
    precio_distribuidor_iva_cdo NUMERIC(14,4),
    precio_distribuidor_iva_cc  NUMERIC(14,4),
    precio_distribuidor_usd_cdo NUMERIC(14,4),
    precio_distribuidor_usd_cc  NUMERIC(14,4),
    dolar_compra                NUMERIC(12,2),
    tasa_iva                    NUMERIC(6,4)
);

-- Costos de producción por equipo

CREATE TABLE IF NOT EXISTS costos_equipos (
    id                  SERIAL PRIMARY KEY,
    equipo_nombre       VARCHAR(200) NOT NULL,
    material_codigo     INTEGER,
    material_descripcion VARCHAR(300),
    cantidad            NUMERIC(14,6),
    costo_unitario      NUMERIC(14,6),
    costo_total         NUMERIC(14,6)
);

-- ============================================================
-- VISTAS de negocio
-- ============================================================

CREATE OR REPLACE VIEW v_costo_por_equipo AS
SELECT
    equipo_nombre,
    COUNT(*)                    AS cant_materiales,
    SUM(costo_total)            AS costo_produccion_total
FROM costos_equipos
GROUP BY equipo_nombre
ORDER BY costo_produccion_total DESC;

CREATE OR REPLACE VIEW v_margen_equipos AS
SELECT
    e.codigo,
    e.nombre,
    e.clasificacion,
    e.costo_iva_inc,
    e.precio_publico_iva_cdo                                        AS precio_publico,
    e.precio_distribuidor_iva_cdo                                   AS precio_distribuidor,
    ROUND((e.margen * 100)::NUMERIC, 2)                             AS margen_pct,
    ROUND(((e.precio_publico_iva_cdo - e.costo_iva_inc)
          / NULLIF(e.precio_publico_iva_cdo, 0) * 100)::NUMERIC, 2) AS margen_real_pct,
    e.dolar_compra,
    e.precio_publico_usd_cdo                                        AS precio_publico_usd
FROM equipos e
WHERE e.costo_iva_inc > 0;

CREATE OR REPLACE VIEW v_insumos_sin_stock AS
SELECT
    codigo, descripcion, rubro, proveedor,
    precio_ars, precio_usd, fecha_actualizacion
FROM insumos
WHERE stock IS NULL OR stock = 0
ORDER BY descripcion;

CREATE OR REPLACE VIEW v_clientes_por_provincia AS
SELECT
    provincia,
    tipo_iva,
    COUNT(*) AS cantidad
FROM clientes
WHERE provincia IS NOT NULL
GROUP BY provincia, tipo_iva
ORDER BY provincia, cantidad DESC;
"""

print("Aplicando esquema SQL...")
with engine.connect() as conn:
    for statement in schema_sql.split(';'):
        stmt = statement.strip()
        if stmt:
            conn.execute(text(stmt))
    conn.commit()

print("Esquema creado correctamente.")
print()
print("Tablas: categorias, tipos_iva, provincias, proveedores, clientes,")
print("        insumos, productos, equipos, costos_equipos")
print()
print("Vistas: v_costo_por_equipo, v_margen_equipos,")
print("        v_insumos_sin_stock, v_clientes_por_provincia")

# Verificar tablas creadas
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    tablas = [r[0] for r in result]
    print(f"\nObjetos en la base ({len(tablas)}):")
    for t in tablas:
        print(f"  - {t}")
