import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import query

st.set_page_config(page_title="Rentabilidad — Elektra", page_icon="📈", layout="wide")
st.title("📈 Análisis de Rentabilidad")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Por categoría", "Por equipo", "Costo vs Precio"])

# ── Tab 1: por categoría ──────────────────────────────────────────────────────
with tab1:
    df_cat = query("SELECT * FROM v_rentabilidad_por_categoria")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            df_cat.sort_values("precio_publico_promedio"),
            x="precio_publico_promedio", y="categoria",
            orientation="h",
            title="Precio público promedio por categoría (ARS c/IVA)",
            labels={"precio_publico_promedio": "Precio ($)", "categoria": ""},
            color="precio_publico_promedio",
            color_continuous_scale="Blues",
            text="precio_publico_promedio",
        )
        fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        fig.update_layout(coloraxis_showscale=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.bar(
            df_cat.sort_values("margen_distribuidor_pct"),
            x="margen_distribuidor_pct", y="categoria",
            orientation="h",
            title="Margen al distribuidor por categoría (%)",
            labels={"margen_distribuidor_pct": "Margen (%)", "categoria": ""},
            color="margen_distribuidor_pct",
            color_continuous_scale="Greens",
            text="margen_distribuidor_pct",
        )
        fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig2.update_layout(coloraxis_showscale=False, height=500)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Tabla completa por categoría")
    df_show = df_cat.copy()
    df_show["precio_base_promedio"]    = df_show["precio_base_promedio"].apply(lambda x: f"${x:,.0f}")
    df_show["precio_publico_promedio"] = df_show["precio_publico_promedio"].apply(lambda x: f"${x:,.0f}")
    df_show["precio_dist_promedio"]    = df_show["precio_dist_promedio"].apply(lambda x: f"${x:,.0f}")
    df_show["precio_usd_promedio"]     = df_show["precio_usd_promedio"].apply(lambda x: f"u$s {x:,.0f}")
    df_show.columns = ["Categoría", "Productos", "Precio base", "Precio público", "Precio dist.", "USD ref.", "Margen dist. (%)", "Dto. (%)"]
    st.dataframe(df_show, use_container_width=True, hide_index=True)

# ── Tab 2: por equipo ─────────────────────────────────────────────────────────
with tab2:
    st.sidebar.header("Filtros rentabilidad")
    df_clases = query("SELECT DISTINCT clasificacion FROM equipos WHERE clasificacion IS NOT NULL ORDER BY clasificacion")
    clases = ["Todas"] + df_clases["clasificacion"].tolist()
    clase_sel = st.sidebar.selectbox("Clasificación", clases)

    sql = "SELECT * FROM v_equipos_rentabilidad"
    if clase_sel != "Todas":
        sql += f" WHERE clasificacion = '{clase_sel}'"
    sql += " LIMIT 50"
    df_eq = query(sql)

    if len(df_eq):
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Equipos analizados", len(df_eq))
        col_b.metric("Margen real promedio", f"{df_eq['margen_real_pct'].mean():.1f}%")
        col_c.metric("Margen dist. promedio", f"{df_eq['margen_distribuidor_pct'].mean():.1f}%")

        fig3 = px.scatter(
            df_eq,
            x="costo_produccion", y="precio_publico",
            color="clasificacion",
            size="margen_real_pct",
            hover_name="nombre",
            hover_data={"costo_produccion": ":,.0f", "precio_publico": ":,.0f",
                        "margen_real_pct": ":.1f", "clasificacion": True},
            title="Costo de producción vs Precio al público",
            labels={"costo_produccion": "Costo ($)", "precio_publico": "Precio público ($)"},
        )
        # Línea de break-even (precio = costo)
        max_val = max(df_eq["precio_publico"].max(), df_eq["costo_produccion"].max())
        fig3.add_trace(go.Scatter(
            x=[0, max_val], y=[0, max_val],
            mode="lines", name="Break-even",
            line=dict(color="red", dash="dash", width=1)
        ))
        fig3.update_layout(height=500)
        st.plotly_chart(fig3, use_container_width=True)

        st.subheader(f"Top 20 equipos por margen real ({clase_sel})")
        df_top = df_eq.head(20)[["nombre", "clasificacion", "costo_produccion",
                                  "precio_publico", "margen_real_pct", "margen_distribuidor_pct",
                                  "precio_publico_usd"]].copy()
        df_top["costo_produccion"] = df_top["costo_produccion"].apply(lambda x: f"${x:,.0f}")
        df_top["precio_publico"]   = df_top["precio_publico"].apply(lambda x: f"${x:,.0f}")
        df_top["precio_publico_usd"] = df_top["precio_publico_usd"].apply(lambda x: f"u$s {x:,.0f}")
        df_top.columns = ["Equipo", "Clase", "Costo", "Precio público", "Margen (%)", "Margen dist. (%)", "USD"]
        st.dataframe(df_top, use_container_width=True, hide_index=True)

# ── Tab 3: costo vs precio por equipo específico ──────────────────────────────
with tab3:
    st.subheader("Desglose de costo de un equipo específico")
    df_nombres = query("SELECT DISTINCT equipo_nombre FROM costos_equipos ORDER BY equipo_nombre")
    equipo_sel = st.selectbox("Seleccioná un equipo", df_nombres["equipo_nombre"].tolist())

    if equipo_sel:
        df_det = query(
            "SELECT material, cantidad, costo_unitario, costo_total, pct_sobre_total "
            "FROM fn_detalle_costo_equipo(:eq)",
            {"eq": equipo_sel}
        )
        costo_total = query(
            "SELECT fn_costo_total_equipo(:eq) AS total", {"eq": equipo_sel}
        )["total"][0]

        df_precio = query(
            "SELECT precio_publico, precio_distribuidor, precio_publico_usd "
            "FROM v_equipos_rentabilidad WHERE UPPER(nombre) = UPPER(:eq)",
            {"eq": equipo_sel}
        )

        col_x, col_y, col_z = st.columns(3)
        col_x.metric("Costo de producción", f"${float(costo_total):,.0f}")
        if len(df_precio):
            col_y.metric("Precio público", f"${df_precio['precio_publico'][0]:,.0f}")
            col_z.metric("Precio USD", f"u$s {df_precio['precio_publico_usd'][0]:,.0f}")

        if len(df_det):
            col_p, col_q = st.columns(2)
            with col_p:
                fig_pie = px.pie(
                    df_det.head(15),
                    names="material", values="costo_total",
                    title=f"Composición de costo — {equipo_sel}",
                    hole=0.3,
                )
                fig_pie.update_traces(textposition="inside", textinfo="percent")
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_q:
                df_det_show = df_det.copy()
                df_det_show["costo_unitario"] = df_det_show["costo_unitario"].apply(lambda x: f"${x:,.4f}")
                df_det_show["costo_total"]    = df_det_show["costo_total"].apply(lambda x: f"${x:,.2f}")
                df_det_show["pct_sobre_total"] = df_det_show["pct_sobre_total"].apply(lambda x: f"{x:.2f}%")
                df_det_show.columns = ["Material", "Cantidad", "Costo unit.", "Costo total", "% del total"]
                st.dataframe(df_det_show, use_container_width=True, hide_index=True, height=400)
