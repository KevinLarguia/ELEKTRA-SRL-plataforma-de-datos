import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import query
import io

st.set_page_config(page_title="Precios — Elektra", page_icon="💲", layout="wide")
st.title("💲 Lista de Precios")
st.caption("Precios al público y distribuidores en ARS y USD")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Filtros")
cotizacion = st.sidebar.number_input(
    "Cotización dólar (ARS)", min_value=100.0, max_value=99999.0,
    value=1500.0, step=50.0, format="%.0f"
)
lista = st.sidebar.radio("Lista de precios", ["Público", "Distribuidor"])

df_cat = query("SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL ORDER BY categoria")
categorias = ["Todas"] + df_cat["categoria"].tolist()
cat_sel = st.sidebar.multiselect("Categoría", categorias, default=["Todas"])

busqueda = st.sidebar.text_input("Buscar producto", "")

# ── Cargar datos ──────────────────────────────────────────────────────────────
if lista == "Público":
    df = query("SELECT * FROM v_lista_precios_publica")
    col_precio   = "precio_con_iva"
    col_sin_iva  = "precio_sin_iva"
    label_precio = "Precio c/IVA ($)"
else:
    df = query("SELECT * FROM v_lista_precios_distribuidor")
    col_precio   = "precio_dist_con_iva"
    col_sin_iva  = "precio_dist_sin_iva"
    label_precio = "Precio dist. c/IVA ($)"

# ── Filtros ───────────────────────────────────────────────────────────────────
if "Todas" not in cat_sel and cat_sel:
    df = df[df["categoria"].isin(cat_sel)]
if busqueda:
    df = df[df["nombre"].str.contains(busqueda.upper(), na=False)]

# ── Calcular USD con cotización ajustable ─────────────────────────────────────
df = df.copy()
df["precio_usd_calculado"] = (df[col_sin_iva] / cotizacion).round(2)

# ── Métricas ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Productos mostrados",  len(df))
col2.metric("Cotización usada",     f"${cotizacion:,.0f}")
col3.metric("Precio promedio ARS",  f"${df[col_precio].mean():,.0f}" if len(df) else "—")
col4.metric("Precio promedio USD",  f"u$s {df['precio_usd_calculado'].mean():,.0f}" if len(df) else "—")

st.divider()

# ── Tabla principal ───────────────────────────────────────────────────────────
cols_mostrar = {
    "nombre": "Producto",
    "categoria": "Categoría",
    col_sin_iva: "Sin IVA ($)",
    col_precio: label_precio,
    "precio_usd_calculado": f"USD (cot. ${cotizacion:,.0f})",
}
if lista == "Público" and "iva_pct" in df.columns:
    cols_mostrar["iva_pct"] = "IVA (%)"
if "descuento_dist_pct" in df.columns or "descuento_pct" in df.columns:
    dcol = "descuento_dist_pct" if "descuento_dist_pct" in df.columns else "descuento_pct"
    cols_mostrar[dcol] = "Dto. dist. (%)"

df_display = df[[c for c in cols_mostrar if c in df.columns]].copy()
df_display.columns = [cols_mostrar[c] for c in cols_mostrar if c in df.columns]

# Formatear columnas de pesos
for col in df_display.columns:
    if "($)" in col:
        df_display[col] = df_display[col].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
        )
    elif "USD" in col:
        df_display[col] = df_display[col].apply(
            lambda x: f"u$s {x:,.2f}" if pd.notna(x) else "—"
        )

st.dataframe(df_display, use_container_width=True, hide_index=True, height=500)

# ── Exportar a Excel ──────────────────────────────────────────────────────────
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_display.to_excel(writer, index=False, sheet_name='Precios')
st.download_button(
    label="Descargar como Excel",
    data=buffer.getvalue(),
    file_name=f"lista_precios_{lista.lower()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
