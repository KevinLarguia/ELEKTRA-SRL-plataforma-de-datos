import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import query

st.set_page_config(page_title="Costos — Elektra", page_icon="🔩", layout="wide")
st.title("🔩 Análisis de Costos de Producción")

tab1, tab2, tab3 = st.tabs(["Insumos", "Equipos", "Actualizar precios"])

# ── Tab 1: Insumos ────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Insumos y materiales")

    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        busq = st.text_input("Buscar insumo", "")
    with col_f2:
        df_rubros = query("SELECT DISTINCT rubro FROM insumos WHERE rubro IS NOT NULL ORDER BY rubro")
        rubros = ["Todos"] + df_rubros["rubro"].tolist()
        rubro_sel = st.selectbox("Rubro", rubros)

    sql_ins = "SELECT codigo, descripcion, rubro, proveedor, precio_ars, precio_usd, precio_ars_iva, stock FROM insumos WHERE precio_ars IS NOT NULL"
    if busq:
        sql_ins += f" AND descripcion ILIKE '%{busq}%'"
    if rubro_sel != "Todos":
        sql_ins += f" AND rubro = '{rubro_sel}'"
    sql_ins += " ORDER BY descripcion LIMIT 200"
    df_ins = query(sql_ins)

    col1, col2, col3 = st.columns(3)
    col1.metric("Insumos mostrados", len(df_ins))
    col2.metric("Precio ARS promedio", f"${df_ins['precio_ars'].mean():,.0f}" if len(df_ins) else "—")
    col3.metric("Con stock = 0 o sin dato",
                int((df_ins["stock"].isna() | (df_ins["stock"] == 0)).sum()))

    df_ins_show = df_ins.copy()
    df_ins_show["precio_ars"]     = df_ins_show["precio_ars"].apply(lambda x: f"${x:,.2f}" if x else "—")
    df_ins_show["precio_ars_iva"] = df_ins_show["precio_ars_iva"].apply(lambda x: f"${x:,.2f}" if x else "—")
    df_ins_show["precio_usd"]     = df_ins_show["precio_usd"].apply(lambda x: f"u$s {x:,.2f}" if x else "—")
    df_ins_show["stock"]          = df_ins_show["stock"].apply(lambda x: f"{x:,.0f}" if x else "sin dato")
    df_ins_show.columns = ["Código", "Descripción", "Rubro", "Proveedor", "Precio ARS", "Precio USD", "Precio c/IVA", "Stock"]
    st.dataframe(df_ins_show, use_container_width=True, hide_index=True, height=400)

    st.divider()
    st.subheader("Precio promedio por rubro")
    df_rubro_avg = query("""
        SELECT rubro, COUNT(*) AS cantidad,
               ROUND(AVG(precio_ars)::NUMERIC, 0) AS precio_promedio
        FROM insumos
        WHERE rubro IS NOT NULL AND precio_ars > 0
        GROUP BY rubro ORDER BY precio_promedio DESC
    """)
    fig = px.bar(
        df_rubro_avg, x="rubro", y="precio_promedio",
        title="Precio promedio ARS por rubro de insumo",
        labels={"rubro": "", "precio_promedio": "Precio ($)"},
        color="precio_promedio", color_continuous_scale="Oranges",
        text="precio_promedio",
    )
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig.update_layout(xaxis_tickangle=-40, coloraxis_showscale=False, height=450)
    st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Equipos ────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Costo de producción por equipo")

    df_costos_res = query("""
        SELECT equipo_nombre,
               COUNT(*) AS cant_materiales,
               ROUND(SUM(costo_total)::NUMERIC, 2) AS costo_total
        FROM costos_equipos
        GROUP BY equipo_nombre
        ORDER BY costo_total DESC
    """)

    col1, col2, col3 = st.columns(3)
    col1.metric("Equipos con costo calculado", len(df_costos_res))
    col2.metric("Equipo más caro", df_costos_res.iloc[0]["equipo_nombre"] if len(df_costos_res) else "—")
    col3.metric("Costo máximo", f"${float(df_costos_res.iloc[0]['costo_total']):,.0f}" if len(df_costos_res) else "—")

    top_n = st.slider("Mostrar top N equipos por costo", 5, 50, 20)

    fig2 = px.bar(
        df_costos_res.head(top_n).sort_values("costo_total"),
        x="costo_total", y="equipo_nombre",
        orientation="h",
        title=f"Top {top_n} equipos por costo de producción",
        labels={"costo_total": "Costo total ($)", "equipo_nombre": ""},
        color="costo_total", color_continuous_scale="Reds",
        text="costo_total",
    )
    fig2.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig2.update_layout(coloraxis_showscale=False, height=max(400, top_n * 22))
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Detalle de un equipo")
    equipo_sel = st.selectbox(
        "Seleccioná un equipo",
        df_costos_res["equipo_nombre"].tolist(),
        key="eq_costos"
    )
    if equipo_sel:
        df_det = query(
            "SELECT material, cantidad, costo_unitario, costo_total, pct_sobre_total "
            "FROM fn_detalle_costo_equipo(:eq)",
            {"eq": equipo_sel}
        )
        costo_tot = query("SELECT fn_costo_total_equipo(:eq) AS t", {"eq": equipo_sel})["t"][0]
        st.metric("Costo total de producción", f"${float(costo_tot):,.2f}")

        col_p, col_q = st.columns([1, 2])
        with col_p:
            fig_pie = px.pie(
                df_det.head(12), names="material", values="costo_total",
                title="Distribución del costo", hole=0.3,
            )
            fig_pie.update_traces(textinfo="percent")
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_q:
            df_det_show = df_det.copy()
            df_det_show["costo_unitario"] = df_det_show["costo_unitario"].apply(lambda x: f"${x:,.4f}")
            df_det_show["costo_total"]    = df_det_show["costo_total"].apply(lambda x: f"${x:,.2f}")
            df_det_show["pct_sobre_total"] = df_det_show["pct_sobre_total"].apply(lambda x: f"{x:.1f}%")
            df_det_show.columns = ["Material", "Cantidad", "C. Unitario", "Costo Total", "% del Total"]
            st.dataframe(df_det_show, use_container_width=True, hide_index=True, height=380)

# ── Tab 3: Actualizar precios ─────────────────────────────────────────────────
with tab3:
    st.subheader("Simulador y aplicador de aumentos de precios")
    st.warning("**Atención:** Los procedimientos de actualización modifican los precios en la base de datos. "
               "Usá primero la simulación para verificar antes de aplicar.")

    st.divider()
    col_sim, col_apl = st.columns(2)

    with col_sim:
        st.markdown("### Simular aumento (sin modificar)")
        pct_sim = st.number_input("Porcentaje de aumento (%)", min_value=0.1, max_value=500.0,
                                   value=15.0, step=0.5, key="pct_sim")
        tabla_sim = st.radio("Simular sobre", ["Insumos", "Equipos"], key="tabla_sim")

        if st.button("Simular"):
            if tabla_sim == "Insumos":
                df_prev = query(
                    "SELECT descripcion, precio_ars_actual, precio_ars_nuevo, diferencia "
                    "FROM fn_simular_aumento_insumos(:p) LIMIT 100",
                    {"p": float(pct_sim)}
                )
                df_prev.columns = ["Insumo", "Precio actual", "Precio nuevo", "Diferencia ($)"]
            else:
                df_prev = query(
                    "SELECT nombre, clasificacion, precio_publico_actual, precio_publico_nuevo, diferencia_publico "
                    "FROM fn_simular_aumento_equipos(:p) LIMIT 100",
                    {"p": float(pct_sim)}
                )
                df_prev.columns = ["Equipo", "Clase", "Precio actual", "Precio nuevo", "Diferencia ($)"]

            for col in ["Precio actual", "Precio nuevo", "Diferencia ($)"]:
                df_prev[col] = df_prev[col].apply(lambda x: f"${float(x):,.2f}")

            st.success(f"Simulación de +{pct_sim}% sobre {len(df_prev)} registros (mostrando hasta 100)")
            st.dataframe(df_prev, use_container_width=True, hide_index=True, height=400)

    with col_apl:
        st.markdown("### Aplicar aumento (modifica la base)")
        pct_apl = st.number_input("Porcentaje de aumento (%)", min_value=0.1, max_value=500.0,
                                   value=15.0, step=0.5, key="pct_apl")
        tabla_apl = st.radio("Aplicar sobre", ["Insumos", "Equipos", "Productos", "Todo"], key="tabla_apl")

        confirmar = st.checkbox(f"Confirmo que quiero aplicar un aumento del {pct_apl}% sobre {tabla_apl}")

        if st.button("Aplicar aumento", disabled=not confirmar, type="primary"):
            from sqlalchemy import create_engine, text as sa_text
            from dotenv import load_dotenv
            from urllib.parse import quote_plus
            import os
            load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
            password = quote_plus(os.getenv('DB_PASSWORD'))
            engine = create_engine(
                f"postgresql://{os.getenv('DB_USER')}:{password}@"
                f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
            )
            proc_map = {
                "Insumos":   "CALL sp_aumento_insumos(:p)",
                "Equipos":   "CALL sp_aumento_equipos(:p)",
                "Productos": "CALL sp_aumento_productos(:p)",
                "Todo":      "CALL sp_aumento_general(:p)",
            }
            try:
                with engine.connect() as conn:
                    conn.execute(sa_text(proc_map[tabla_apl]), {"p": float(pct_apl)})
                    conn.commit()
                st.success(f"Aumento del {pct_apl}% aplicado correctamente sobre {tabla_apl}.")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Error al aplicar el aumento: {e}")
