import streamlit as st
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import query

st.set_page_config(page_title="Clientes — Elektra", page_icon="👥", layout="wide")
st.title("👥 Clientes")

df_all = query("SELECT * FROM clientes WHERE nombre IS NOT NULL")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Filtros")
provincias = ["Todas"] + sorted(df_all["provincia"].dropna().unique().tolist())
prov_sel   = st.sidebar.selectbox("Provincia", provincias)

tipos_iva = ["Todos"] + sorted(df_all["tipo_iva"].dropna().unique().tolist())
iva_sel   = st.sidebar.selectbox("Tipo de IVA", tipos_iva)

busqueda = st.sidebar.text_input("Buscar cliente", "")

# ── Filtrar ───────────────────────────────────────────────────────────────────
df = df_all.copy()
if prov_sel != "Todas":
    df = df[df["provincia"] == prov_sel]
if iva_sel != "Todos":
    df = df[df["tipo_iva"] == iva_sel]
if busqueda:
    df = df[df["nombre"].str.contains(busqueda.upper(), na=False)]

# ── KPIs ─────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Clientes filtrados",     len(df))
col2.metric("Provincias",             df["provincia"].nunique())
col3.metric("Con CUIT cargado",       df["cuit"].notna().sum())
col4.metric("Con teléfono",           df["telefono"].notna().sum())

st.divider()

# ── Gráficos ──────────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    df_prov = (
        df_all.groupby("provincia", dropna=True)
        .size().reset_index(name="cantidad")
        .sort_values("cantidad", ascending=False)
    )
    fig_prov = px.bar(
        df_prov,
        x="provincia", y="cantidad",
        title="Clientes por provincia",
        labels={"provincia": "", "cantidad": "Cantidad"},
        color="cantidad",
        color_continuous_scale="Blues",
        text="cantidad",
    )
    fig_prov.update_traces(textposition="outside")
    fig_prov.update_layout(coloraxis_showscale=False, xaxis_tickangle=-30)
    st.plotly_chart(fig_prov, use_container_width=True)

with col_b:
    df_iva = (
        df_all.groupby("tipo_iva", dropna=True)
        .size().reset_index(name="cantidad")
    )
    fig_iva = px.pie(
        df_iva,
        names="tipo_iva", values="cantidad",
        title="Distribución por tipo de IVA",
        hole=0.35,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_iva.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_iva, use_container_width=True)

# ── Mapa de calor provincia × tipo IVA ───────────────────────────────────────
st.subheader("Clientes por provincia y tipo de IVA")
df_cross = query("""
    SELECT provincia, tipo_iva, cantidad
    FROM v_clientes_por_provincia
    WHERE provincia IS NOT NULL AND tipo_iva IS NOT NULL
""")
if len(df_cross):
    pivot = df_cross.pivot_table(
        index="provincia", columns="tipo_iva",
        values="cantidad", fill_value=0
    ).reset_index()
    fig_heat = px.imshow(
        pivot.set_index("provincia"),
        text_auto=True,
        color_continuous_scale="Blues",
        title="Cantidad de clientes — Provincia × Tipo IVA",
        aspect="auto",
    )
    st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ── Tabla ─────────────────────────────────────────────────────────────────────
st.subheader(f"Lista de clientes ({len(df)} registros)")
cols = ["codigo", "nombre", "fantasia", "ciudad", "provincia", "tipo_iva", "cuit", "telefono"]
df_show = df[[c for c in cols if c in df.columns]].copy()
df_show.columns = ["Código", "Nombre", "Fantasía", "Ciudad", "Provincia", "Tipo IVA", "CUIT", "Teléfono"][:len(df_show.columns)]
st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)
