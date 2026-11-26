"""Página 2: histórico de nivel y lluvia, y lista de crecientes."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import comun as C

st.title("📈 Histórico y crecientes 2017-2025")
st.caption("¿Cuándo y con qué fuerza ha crecido el río Las Ceibas?")

h = C.hidrologia()
e = C.eventos()

c1, c2 = st.columns([1, 3])
est = c1.radio("Estación", ["La_Lindosa", "Los_Micos"], format_func=C.ESTACION.get, horizontal=True)
anios = c2.slider("Años", 2017, 2025, (2018, 2025))

d = h[(h.estacion == est) & h.fecha_hora.dt.year.between(*anios)].set_index("fecha_hora")
ev = e[e.anio.between(*anios)]

if est == "La_Lindosa":
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Crecientes (≥ 0.5 m)", len(ev))
    k2.metric("Crecientes rojas", int((ev.clase_alerta == 3).sum()))
    k3.metric("Nivel máximo instantáneo", f"{ev.nivel_max_instantaneo_m.max():.2f} m" if len(ev) else "—")
    sin_lluvia = (ev.lluvia_6h_previas_mm < 1).mean() if len(ev) else 0
    k4.metric("Sin lluvia local previa", f"{sin_lluvia:.0%}",
              help="Crecientes sin lluvia (< 1 mm) en La Lindosa en las 6 h previas: la tormenta "
                   "cayó en la parte alta de la cuenca.")

diario = pd.DataFrame({"nivel_max": d.nivel_max_m.resample("D").max() if est == "La_Lindosa" else d.nivel_m.resample("D").max(),
                       "nivel_medio": d.nivel_m.resample("D").mean()})
mensual = d.lluvia_mm.resample("MS").sum(min_count=1)
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
fig.add_trace(go.Scatter(x=diario.index, y=diario.nivel_max, name="Máximo diario",
                         line=dict(color="#90CAF9", width=1)), 1, 1)
fig.add_trace(go.Scatter(x=diario.index, y=diario.nivel_medio, name="Promedio diario",
                         line=dict(color="#1565C0", width=1.5)), 1, 1)
fig.add_trace(go.Bar(x=mensual.index, y=mensual.values, name="Lluvia mensual", marker_color="#26A69A"), 2, 1)
fig.update_yaxes(title_text="Nivel (m)", row=1, col=1)
fig.update_yaxes(title_text="Lluvia (mm/mes)", row=2, col=1)
fig.update_layout(height=480, margin=dict(t=20, b=10), legend=dict(orientation="h", y=1.08))
st.plotly_chart(fig, width="stretch")

if est == "La_Lindosa":
    st.subheader("Crecientes registradas")
    a, b = st.columns([1, 2])
    conteo = ev.groupby(["anio", "alerta"]).size().reset_index(name="n")
    fb = px.bar(conteo, x="anio", y="n", color="alerta", color_discrete_map=C.COLORES_ALERTA,
                category_orders={"alerta": C.NOMBRES_ALERTA}, labels={"anio": "Año", "n": "Crecientes"})
    fb.update_layout(height=360, margin=dict(t=10), legend_title_text="")
    a.plotly_chart(fb, width="stretch")
    mes = ev.inicio.dt.month.value_counts().reindex(range(1, 13), fill_value=0)
    fm = px.bar(x=["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"], y=mes.values,
                labels={"x": "Mes", "y": "Crecientes"}, color_discrete_sequence=["#1565C0"])
    fm.update_layout(height=360, margin=dict(t=10))
    b.plotly_chart(fm, width="stretch")

    tabla = ev.sort_values("anomalia_pico_m", ascending=False)[
        ["inicio", "duracion_h", "nivel_max_instantaneo_m", "anomalia_pico_m", "lluvia_evento_mm",
         "lluvia_6h_previas_mm", "alerta"]].rename(columns={
            "inicio": "Inicio", "duracion_h": "Duración (h)", "nivel_max_instantaneo_m": "Nivel máx. (m)",
            "anomalia_pico_m": "Anomalía pico (m)", "lluvia_evento_mm": "Lluvia evento (mm)",
            "lluvia_6h_previas_mm": "Lluvia 6 h previas (mm)", "alerta": "Alerta"})
    st.dataframe(tabla.style.map(lambda v: f"background-color:{C.COLORES_ALERTA.get(v, '')};color:white"
                                 if v in C.COLORES_ALERTA else "", subset=["Alerta"])
                 .format(precision=2), width="stretch", hide_index=True, height=380)
C.pie()
