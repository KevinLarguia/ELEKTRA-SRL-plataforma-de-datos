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

# ─────────────────────────────────────────────────────────────────────────────
# Cada bloque SQL se ejecuta por separado para mensajes de error claros
# ─────────────────────────────────────────────────────────────────────────────

objetos = {}

# ═════════════════════════════════════════════════════════════════════════════
# VISTAS ANALÍTICAS
# ═════════════════════════════════════════════════════════════════════════════

objetos['v_rentabilidad_por_categoria'] = """
CREATE OR REPLACE VIEW v_rentabilidad_por_categoria AS
SELECT
    p.categoria,
    COUNT(*)                                                            AS cant_productos,
    ROUND(AVG(p.precio_base)::NUMERIC, 2)                              AS precio_base_promedio,
    ROUND(AVG(p.precio_iva)::NUMERIC, 2)                               AS precio_publico_promedio,
    ROUND(AVG(p.precio_distribuidor_iva)::NUMERIC, 2)                  AS precio_dist_promedio,
    ROUND(AVG(p.precio_dolares)::NUMERIC, 2)                           AS precio_usd_promedio,
    ROUND(AVG(
        (p.precio_base - p.precio_distribuidor)
        / NULLIF(p.precio_base, 0) * 100
    )::NUMERIC, 1)                                                      AS margen_distribuidor_pct,
    ROUND(AVG(p.descuento)::NUMERIC, 1)                                AS descuento_promedio
FROM productos p
WHERE p.precio_base > 0
GROUP BY p.categoria
ORDER BY precio_publico_promedio DESC
"""

objetos['v_lista_precios_publica'] = """
CREATE OR REPLACE VIEW v_lista_precios_publica AS
SELECT
    p.id,
    p.nombre,
    p.categoria,
    ROUND(p.precio_base::NUMERIC, 2)                AS precio_sin_iva,
    ROUND((p.tasa_iva * 100)::NUMERIC, 0)           AS iva_pct,
    ROUND(p.precio_iva::NUMERIC, 2)                 AS precio_con_iva,
    ROUND(p.precio_dolares::NUMERIC, 2)             AS precio_usd,
    p.descuento                                     AS descuento_dist_pct
FROM productos p
WHERE p.precio_base > 0
ORDER BY p.categoria, p.nombre
"""

objetos['v_lista_precios_distribuidor'] = """
CREATE OR REPLACE VIEW v_lista_precios_distribuidor AS
SELECT
    p.id,
    p.nombre,
    p.categoria,
    ROUND(p.precio_distribuidor::NUMERIC, 2)        AS precio_dist_sin_iva,
    ROUND(p.precio_distribuidor_iva::NUMERIC, 2)    AS precio_dist_con_iva,
    ROUND(p.precio_dolares::NUMERIC, 2)             AS precio_referencia_usd,
    p.descuento                                     AS descuento_pct
FROM productos p
WHERE p.precio_distribuidor > 0
ORDER BY p.categoria, p.nombre
"""

objetos['v_materiales_mas_usados'] = """
CREATE OR REPLACE VIEW v_materiales_mas_usados AS
SELECT
    ce.material_codigo,
    ce.material_descripcion,
    COUNT(DISTINCT ce.equipo_nombre)                    AS cant_equipos_que_lo_usan,
    ROUND(SUM(ce.cantidad)::NUMERIC, 3)                 AS cantidad_total_usada,
    ROUND(AVG(ce.costo_unitario)::NUMERIC, 4)           AS costo_unitario_promedio,
    ROUND(SUM(ce.costo_total)::NUMERIC, 2)              AS impacto_total_en_costos
FROM costos_equipos ce
WHERE ce.material_codigo IS NOT NULL
GROUP BY ce.material_codigo, ce.material_descripcion
ORDER BY cant_equipos_que_lo_usan DESC, impacto_total_en_costos DESC
"""

objetos['v_equipos_rentabilidad'] = """
CREATE OR REPLACE VIEW v_equipos_rentabilidad AS
SELECT
    e.codigo,
    e.nombre,
    e.clasificacion,
    ROUND(e.costo_iva_inc::NUMERIC, 2)                              AS costo_produccion,
    ROUND(e.precio_publico_iva_cdo::NUMERIC, 2)                     AS precio_publico,
    ROUND(e.precio_distribuidor_iva_cdo::NUMERIC, 2)                AS precio_distribuidor,
    ROUND((e.margen * 100)::NUMERIC, 1)                             AS margen_declarado_pct,
    ROUND(
        ((e.precio_publico_iva_cdo - e.costo_iva_inc)
         / NULLIF(e.precio_publico_iva_cdo, 0) * 100)::NUMERIC, 1
    )                                                               AS margen_real_pct,
    ROUND(
        ((e.precio_distribuidor_iva_cdo - e.costo_iva_inc)
         / NULLIF(e.precio_distribuidor_iva_cdo, 0) * 100)::NUMERIC, 1
    )                                                               AS margen_distribuidor_pct,
    ROUND(e.precio_publico_usd_cdo::NUMERIC, 2)                     AS precio_publico_usd,
    ROUND(e.precio_distribuidor_usd_cdo::NUMERIC, 2)                AS precio_distribuidor_usd,
    e.dolar_compra
FROM equipos e
WHERE e.costo_iva_inc > 0
  AND e.precio_publico_iva_cdo > 0
ORDER BY margen_real_pct DESC
"""

objetos['v_insumos_caros_sin_usd'] = """
CREATE OR REPLACE VIEW v_insumos_caros_sin_usd AS
SELECT
    i.codigo,
    i.descripcion,
    i.rubro,
    i.proveedor,
    ROUND(i.precio_ars::NUMERIC, 2)         AS precio_ars,
    ROUND(i.precio_ars_iva::NUMERIC, 2)     AS precio_ars_iva,
    i.cotizacion_dolar,
    ROUND(
        (i.precio_ars / NULLIF(i.cotizacion_dolar, 0))::NUMERIC, 2
    )                                       AS precio_usd_calculado
FROM insumos i
WHERE i.precio_usd IS NULL
  AND i.precio_ars IS NOT NULL
  AND i.precio_ars > 0
ORDER BY i.precio_ars DESC
"""

# ═════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CONSULTA
# ═════════════════════════════════════════════════════════════════════════════

objetos['fn_detalle_costo_equipo'] = """
CREATE OR REPLACE FUNCTION fn_detalle_costo_equipo(p_equipo TEXT)
RETURNS TABLE (
    material_codigo     BIGINT,
    material            TEXT,
    cantidad            DOUBLE PRECISION,
    costo_unitario      DOUBLE PRECISION,
    costo_total         DOUBLE PRECISION,
    pct_sobre_total     NUMERIC
)
LANGUAGE sql STABLE
AS $$
    WITH total AS (
        SELECT SUM(costo_total) AS suma
        FROM costos_equipos
        WHERE UPPER(equipo_nombre) = UPPER(p_equipo)
    )
    SELECT
        ce.material_codigo,
        ce.material_descripcion,
        ce.cantidad,
        ce.costo_unitario,
        ce.costo_total,
        ROUND((ce.costo_total / NULLIF(t.suma, 0) * 100)::NUMERIC, 2)
    FROM costos_equipos ce, total t
    WHERE UPPER(ce.equipo_nombre) = UPPER(p_equipo)
    ORDER BY ce.costo_total DESC
$$
"""

objetos['fn_costo_total_equipo'] = """
CREATE OR REPLACE FUNCTION fn_costo_total_equipo(p_equipo TEXT)
RETURNS NUMERIC
LANGUAGE sql STABLE
AS $$
    SELECT ROUND(SUM(costo_total)::NUMERIC, 2)
    FROM costos_equipos
    WHERE UPPER(equipo_nombre) = UPPER(p_equipo)
$$
"""

objetos['fn_ars_a_usd'] = """
CREATE OR REPLACE FUNCTION fn_ars_a_usd(
    p_monto_ars     DOUBLE PRECISION,
    p_cotizacion    DOUBLE PRECISION
)
RETURNS NUMERIC
LANGUAGE sql IMMUTABLE
AS $$
    SELECT ROUND((p_monto_ars / NULLIF(p_cotizacion, 0))::NUMERIC, 2)
$$
"""

objetos['fn_usd_a_ars'] = """
CREATE OR REPLACE FUNCTION fn_usd_a_ars(
    p_monto_usd     DOUBLE PRECISION,
    p_cotizacion    DOUBLE PRECISION
)
RETURNS NUMERIC
LANGUAGE sql IMMUTABLE
AS $$
    SELECT ROUND((p_monto_usd * p_cotizacion)::NUMERIC, 2)
$$
"""

objetos['fn_precio_con_iva'] = """
CREATE OR REPLACE FUNCTION fn_precio_con_iva(
    p_precio_base   DOUBLE PRECISION,
    p_tasa_iva      DOUBLE PRECISION
)
RETURNS NUMERIC
LANGUAGE sql IMMUTABLE
AS $$
    SELECT ROUND((p_precio_base * (1 + p_tasa_iva))::NUMERIC, 2)
$$
"""

objetos['fn_simular_aumento_insumos'] = """
CREATE OR REPLACE FUNCTION fn_simular_aumento_insumos(p_porcentaje DOUBLE PRECISION)
RETURNS TABLE (
    codigo              BIGINT,
    descripcion         TEXT,
    precio_ars_actual   NUMERIC,
    precio_ars_nuevo    NUMERIC,
    diferencia          NUMERIC,
    precio_iva_nuevo    NUMERIC
)
LANGUAGE sql STABLE
AS $$
    SELECT
        i.codigo,
        i.descripcion,
        ROUND(i.precio_ars::NUMERIC, 2),
        ROUND((i.precio_ars * (1 + p_porcentaje / 100))::NUMERIC, 2),
        ROUND((i.precio_ars * p_porcentaje / 100)::NUMERIC, 2),
        ROUND((i.precio_ars * (1 + p_porcentaje / 100) * (1 + COALESCE(
            (SELECT tasa_iva FROM productos LIMIT 1), 0.21
        )))::NUMERIC, 2)
    FROM insumos i
    WHERE i.precio_ars IS NOT NULL AND i.precio_ars > 0
    ORDER BY i.descripcion
$$
"""

objetos['fn_simular_aumento_equipos'] = """
CREATE OR REPLACE FUNCTION fn_simular_aumento_equipos(p_porcentaje DOUBLE PRECISION)
RETURNS TABLE (
    codigo                      BIGINT,
    nombre                      TEXT,
    clasificacion               TEXT,
    precio_publico_actual       NUMERIC,
    precio_publico_nuevo        NUMERIC,
    precio_distribuidor_actual  NUMERIC,
    precio_distribuidor_nuevo   NUMERIC,
    diferencia_publico          NUMERIC
)
LANGUAGE sql STABLE
AS $$
    SELECT
        e.codigo,
        e.nombre,
        e.clasificacion,
        ROUND(e.precio_publico_iva_cdo::NUMERIC, 2),
        ROUND((e.precio_publico_iva_cdo * (1 + p_porcentaje / 100))::NUMERIC, 2),
        ROUND(e.precio_distribuidor_iva_cdo::NUMERIC, 2),
        ROUND((e.precio_distribuidor_iva_cdo * (1 + p_porcentaje / 100))::NUMERIC, 2),
        ROUND((e.precio_publico_iva_cdo * p_porcentaje / 100)::NUMERIC, 2)
    FROM equipos e
    WHERE e.precio_publico_iva_cdo > 0
    ORDER BY e.clasificacion, e.nombre
$$
"""

# ═════════════════════════════════════════════════════════════════════════════
# PROCEDIMIENTOS DE ACTUALIZACIÓN (modifican datos)
# ═════════════════════════════════════════════════════════════════════════════

objetos['sp_aumento_insumos'] = """
CREATE OR REPLACE PROCEDURE sp_aumento_insumos(p_porcentaje DOUBLE PRECISION)
LANGUAGE plpgsql
AS $$
DECLARE
    v_factor        DOUBLE PRECISION := 1 + p_porcentaje / 100;
    v_filas_afect   INTEGER;
BEGIN
    IF p_porcentaje <= 0 OR p_porcentaje > 500 THEN
        RAISE EXCEPTION 'Porcentaje inválido: %. Debe estar entre 0 y 500.', p_porcentaje;
    END IF;

    UPDATE insumos SET
        precio_ars          = precio_ars          * v_factor,
        precio_ars_iva      = precio_ars_iva      * v_factor,
        precio_final_iva    = precio_final_iva    * v_factor
    WHERE precio_ars IS NOT NULL AND precio_ars > 0;

    GET DIAGNOSTICS v_filas_afect = ROW_COUNT;
    RAISE NOTICE 'Aumento de % pct aplicado a % insumos.', p_porcentaje, v_filas_afect;
END
$$
"""

objetos['sp_aumento_equipos'] = """
CREATE OR REPLACE PROCEDURE sp_aumento_equipos(p_porcentaje DOUBLE PRECISION)
LANGUAGE plpgsql
AS $$
DECLARE
    v_factor        DOUBLE PRECISION := 1 + p_porcentaje / 100;
    v_filas_afect   INTEGER;
BEGIN
    IF p_porcentaje <= 0 OR p_porcentaje > 500 THEN
        RAISE EXCEPTION 'Porcentaje inválido: %. Debe estar entre 0 y 500.', p_porcentaje;
    END IF;

    UPDATE equipos SET
        costo_iva_inc               = costo_iva_inc               * v_factor,
        precio_publico_iva_cdo      = precio_publico_iva_cdo      * v_factor,
        precio_publico_iva_cc       = precio_publico_iva_cc       * v_factor,
        precio_distribuidor_iva_cdo = precio_distribuidor_iva_cdo * v_factor,
        precio_distribuidor_iva_cc  = precio_distribuidor_iva_cc  * v_factor
    WHERE precio_publico_iva_cdo > 0;

    GET DIAGNOSTICS v_filas_afect = ROW_COUNT;
    RAISE NOTICE 'Aumento de % pct aplicado a % equipos.', p_porcentaje, v_filas_afect;
END
$$
"""

objetos['sp_aumento_productos'] = """
CREATE OR REPLACE PROCEDURE sp_aumento_productos(p_porcentaje DOUBLE PRECISION)
LANGUAGE plpgsql
AS $$
DECLARE
    v_factor        DOUBLE PRECISION := 1 + p_porcentaje / 100;
    v_filas_afect   INTEGER;
BEGIN
    IF p_porcentaje <= 0 OR p_porcentaje > 500 THEN
        RAISE EXCEPTION 'Porcentaje inválido: %. Debe estar entre 0 y 500.', p_porcentaje;
    END IF;

    UPDATE productos SET
        precio_base             = precio_base             * v_factor,
        precio_iva              = precio_iva              * v_factor,
        precio_distribuidor     = precio_distribuidor     * v_factor,
        precio_distribuidor_iva = precio_distribuidor_iva * v_factor
    WHERE precio_base > 0;

    GET DIAGNOSTICS v_filas_afect = ROW_COUNT;
    RAISE NOTICE 'Aumento de % pct aplicado a % productos.', p_porcentaje, v_filas_afect;
END
$$
"""

objetos['sp_aumento_general'] = """
CREATE OR REPLACE PROCEDURE sp_aumento_general(p_porcentaje DOUBLE PRECISION)
LANGUAGE plpgsql
AS $$
BEGIN
    CALL sp_aumento_insumos(p_porcentaje);
    CALL sp_aumento_equipos(p_porcentaje);
    CALL sp_aumento_productos(p_porcentaje);
    RAISE NOTICE 'Aumento general de % pct aplicado a toda la base.', p_porcentaje;
END
$$
"""

# ═════════════════════════════════════════════════════════════════════════════
# EJECUTAR TODO
# ═════════════════════════════════════════════════════════════════════════════

print("Creando objetos de la Fase 3...")
print()

with engine.connect() as conn:
    for nombre, sql in objetos.items():
        try:
            conn.execute(text(sql))
            conn.commit()
            tipo = 'Vista     ' if nombre.startswith('v_') else \
                   'Función   ' if nombre.startswith('fn_') else 'Procedure '
            print(f"  OK  {tipo}  {nombre}")
        except Exception as e:
            print(f"  ERROR  {nombre}: {e}")

print()
print("-" * 60)
print("Verificando con datos reales...")
print()

with engine.connect() as conn:

    # 1. Rentabilidad por categoría
    print(">> Rentabilidad por categoría (top 5):")
    res = conn.execute(text("""
        SELECT categoria, cant_productos, precio_publico_promedio,
               precio_usd_promedio, margen_distribuidor_pct
        FROM v_rentabilidad_por_categoria LIMIT 5
    """))
    for r in res:
        print(f"    {r[0]:20s}  {r[1]:3d} prods  "
              f"${r[2]:>12,.0f}  u$s{r[3]:>8,.0f}  margen dist {r[4]}%")

    print()

    # 2. Detalle de costo de un equipo
    print(">> Costo detallado del equipo RADAR (top 5 materiales):")
    res = conn.execute(text("""
        SELECT material, cantidad, costo_unitario, costo_total, pct_sobre_total
        FROM fn_detalle_costo_equipo('RADAR')
        LIMIT 5
    """))
    for r in res:
        print(f"    {r[0][:35]:35s}  cant:{r[1]}  u:{r[2]:>10,.2f}  total:{r[3]:>12,.2f}  ({r[4]}%)")

    print()

    # 3. Costo total de un equipo
    res = conn.execute(text("SELECT fn_costo_total_equipo('RADAR')"))
    costo = res.scalar()
    print(f">> Costo total de producción RADAR: ${costo:,.2f}")

    print()

    # 4. Conversión ARS -> USD
    res = conn.execute(text("SELECT fn_ars_a_usd(100000, 1500)"))
    usd = res.scalar()
    print(f">> fn_ars_a_usd(100.000 ARS, cotización 1.500): u$s {usd}")

    print()

    # 5. Simulación de aumento del 15%
    print(">> Simulación aumento 15% en insumos (primeros 5):")
    res = conn.execute(text("""
        SELECT descripcion, precio_ars_actual, precio_ars_nuevo, diferencia
        FROM fn_simular_aumento_insumos(15)
        LIMIT 5
    """))
    for r in res:
        print(f"    {r[0][:35]:35s}  actual: ${r[1]:>10,.2f}  nuevo: ${r[2]:>10,.2f}  (+${r[3]:,.2f})")

    print()

    # 6. Materiales más usados
    print(">> Materiales usados en más equipos (top 5):")
    res = conn.execute(text("""
        SELECT material_descripcion, cant_equipos_que_lo_usan, impacto_total_en_costos
        FROM v_materiales_mas_usados LIMIT 5
    """))
    for r in res:
        print(f"    {r[0][:40]:40s}  en {r[1]:4d} equipos  impacto total: ${r[2]:>12,.2f}")

    print()

    # 7. Top equipos por margen real
    print(">> Top 5 equipos por margen real:")
    res = conn.execute(text("""
        SELECT nombre, clasificacion, costo_produccion, precio_publico, margen_real_pct
        FROM v_equipos_rentabilidad LIMIT 5
    """))
    for r in res:
        print(f"    {r[0][:30]:30s}  [{r[1]:12s}]  costo: ${r[2]:>10,.0f}  precio: ${r[3]:>10,.0f}  margen: {r[4]}%")

print()
print("=" * 60)
print("Fase 3 completada.")
print()
print("Objetos disponibles en la base:")
print()
print("  VISTAS ANALÍTICAS")
print("    v_rentabilidad_por_categoria   — margen por familia de productos")
print("    v_lista_precios_publica        — lista de precios al público")
print("    v_lista_precios_distribuidor   — lista de precios para distribuidores")
print("    v_materiales_mas_usados        — materiales con mayor impacto en costos")
print("    v_equipos_rentabilidad         — margen real por equipo")
print("    v_insumos_caros_sin_usd        — insumos sin precio USD con estimación")
print()
print("  FUNCIONES DE CONSULTA")
print("    fn_detalle_costo_equipo(nombre)        — desglose completo de un equipo")
print("    fn_costo_total_equipo(nombre)           — costo total de producción")
print("    fn_ars_a_usd(monto, cotizacion)         — conversión ARS -> USD")
print("    fn_usd_a_ars(monto, cotizacion)         — conversión USD -> ARS")
print("    fn_precio_con_iva(precio, tasa)         — precio final con IVA")
print("    fn_simular_aumento_insumos(pct)         — previsualizar aumento sin aplicar")
print("    fn_simular_aumento_equipos(pct)         — previsualizar aumento sin aplicar")
print()
print("  PROCEDIMIENTOS (modifican la base)")
print("    sp_aumento_insumos(pct)    — aplica aumento a precios ARS de insumos")
print("    sp_aumento_equipos(pct)    — aplica aumento a precios ARS de equipos")
print("    sp_aumento_productos(pct)  — aplica aumento a precios ARS de productos")
print("    sp_aumento_general(pct)    — aplica aumento a los tres a la vez")
print()
print("  Ejemplo de uso en pgAdmin:")
print("    SELECT * FROM fn_detalle_costo_equipo('VIBRO');")
print("    SELECT * FROM fn_simular_aumento_insumos(20);")
print("    CALL sp_aumento_general(15.5);")
