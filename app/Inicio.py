import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from utils.db import query

st.set_page_config(
    page_title="Elektra SRL — Plataforma de Datos",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Elektra S.R.L. — Plataforma de Datos")
st.caption("Santa Fe, Argentina · Iluminación Profesional")
st.divider()

# ── KPIs principales ──────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

df_insumos   = query("SELECT COUNT(*) AS n FROM insumos")
df_equipos   = query("SELECT COUNT(*) AS n FROM equipos")
df_clientes  = query("SELECT COUNT(*) AS n FROM clientes")
df_proveed   = query("SELECT COUNT(*) AS n FROM proveedores")
df_costos    = query("SELECT COUNT(DISTINCT equipo_nombre) AS n FROM costos_equipos")

col1.metric("Insumos",     f"{df_insumos['n'][0]:,}")
col2.metric("Equipos",     f"{df_equipos['n'][0]:,}")
col3.metric("Clientes",    f"{df_clientes['n'][0]:,}")
col4.metric("Proveedores", f"{df_proveed['n'][0]:,}")
col5.metric("Equipos c/ costo", f"{df_costos['n'][0]:,}")

st.divider()

# ── Fila de resumen ───────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Top 5 categorías por precio promedio")
    df_cat = query("""
        SELECT categoria,
               cant_productos,
               precio_publico_promedio,
               precio_usd_promedio,
               margen_distribuidor_pct
        FROM v_rentabilidad_por_categoria
        LIMIT 5
    """)
    df_cat.columns = ["Categoría", "Productos", "Precio público ($)", "Precio (u$s)", "Margen dist. (%)"]
    df_cat["Precio público ($)"] = df_cat["Precio público ($)"].apply(lambda x: f"${x:,.0f}")
    df_cat["Precio (u$s)"]       = df_cat["Precio (u$s)"].apply(lambda x: f"u$s {x:,.0f}")
    st.dataframe(df_cat, use_container_width=True, hide_index=True)

with col_b:
    st.subheader("Top 5 equipos por margen real")
    df_eq = query("""
        SELECT nombre, clasificacion, costo_produccion,
               precio_publico, margen_real_pct
        FROM v_equipos_rentabilidad
        LIMIT 5
    """)
    df_eq.columns = ["Equipo", "Clase", "Costo ($)", "Precio ($)", "Margen (%)"]
    df_eq["Costo ($)"]  = df_eq["Costo ($)"].apply(lambda x: f"${x:,.0f}")
    df_eq["Precio ($)"] = df_eq["Precio ($)"].apply(lambda x: f"${x:,.0f}")
    st.dataframe(df_eq, use_container_width=True, hide_index=True)

st.divider()

col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Clientes por provincia")
    df_prov = query("""
        SELECT provincia, COUNT(*) AS cantidad
        FROM clientes
        WHERE provincia IS NOT NULL
        GROUP BY provincia
        ORDER BY cantidad DESC
    """)
    st.bar_chart(df_prov.set_index("provincia")["cantidad"])

with col_d:
    st.subheader("Materiales más usados en producción")
    df_mat = query("""
        SELECT material_descripcion AS material,
               cant_equipos_que_lo_usan AS equipos
        FROM v_materiales_mas_usados
        LIMIT 10
    """)
    st.bar_chart(df_mat.set_index("material")["equipos"])

st.divider()
st.caption("Usá el menú de la izquierda para navegar entre secciones.")
