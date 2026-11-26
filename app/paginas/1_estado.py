"""Página 1: estado del río en un momento elegido y pronóstico a 1, 3 y 6 h."""
from datetime import time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import comun as C

st.title("🚨 Estado del río Las Ceibas – La Lindosa")
st.caption("Simulación de monitoreo: elige un momento del periodo de prueba (2024-2025) y mira qué "
           "pronosticaba el modelo seleccionado (Random Forest) y qué ocurrió realmente.")

h = C.hidrologia()
p = C.pronosticos()
L = h[h.estacion == "La_Lindosa"].set_index("fecha_hora")
M = h[h.estacion == "Los_Micos"].set_index("fecha_hora")
rf = p[p.modelo == "random_forest"]
origenes = rf.fecha_hora_origen.drop_duplicates().sort_values()

c1, c2, c3 = st.columns([2, 1, 3])
fecha = c1.date_input("Fecha", value=pd.Timestamp("2024-11-14").date(),
                      min_value=origenes.min().date(), max_value=origenes.max().date())
hora = c2.selectbox("Hora", [time(x) for x in range(24)], index=6, format_func=lambda t: t.strftime("%H:%M"))
with c3:
    st.markdown("**Eventos de ejemplo**")
    e1, e2, e3 = st.columns(3)
    for col, (txt, f, hh) in zip([e1, e2, e3], [("Nov 2024 (naranja)", "2024-11-14", 6),
                                              ("Mar 2024", "2024-03-26", 3), ("Normal", "2024-02-01", 12)]):
        col.caption(f"{txt}: {f} {hh:02d}:00")

t = pd.Timestamp.combine(fecha, hora)
if t not in set(origenes):
    st.warning(f"No hay pronóstico para {t:%Y-%m-%d %H:%M}: faltan datos de alguna variable en ese momento "
               "(estación apagada o hueco largo). Prueba otra hora.")
    C.pie()
    st.stop()

fila = L.loc[t]
anom = fila.anomalia_m
estado = C.alerta_de(anom)
pr = rf[rf.fecha_hora_origen == t].set_index("h")

k1, k2, k3, k4 = st.columns([1, 1, 1.2, 2.2])
k1.metric("Nivel actual", f"{fila.nivel_m:.2f} m")
k2.metric("Anomalía", f"{anom:+.2f} m", help="Nivel menos la línea base (mediana de los 30 días anteriores)")
with k3:
    st.caption("Estado actual")
    C.insignia(estado.upper(), C.COLORES_ALERTA.get(estado, "#9E9E9E"))
with k4:
    st.caption("Pronóstico Random Forest")
    cols = st.columns(3)
    for col, hz in zip(cols, [1, 3, 6]):
        if hz in pr.index:
            r = pr.loc[hz]
            a = C.alerta_de(r.nivel_pred_m - r.base_m)
            col.metric(f"+{hz} h", f"{r.nivel_pred_m:.2f} m", f"real {r.nivel_real_m:.2f} m", delta_color="off")
            col.markdown(f"<span style='color:{C.COLORES_ALERTA[a]};font-weight:700'>● {a}</span>",
                         unsafe_allow_html=True)

# ventana de 36 h antes y 12 h después
ini, fin = t - pd.Timedelta("36h"), t + pd.Timedelta("12h")
v = L.loc[ini:fin]
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.05)
fig.add_trace(go.Scatter(x=v.index, y=v.nivel_m, name="Nivel real", line=dict(color="black", width=2.5)), 1, 1)
for nombre, u in C.UMBRALES.items():
    fig.add_trace(go.Scatter(x=v.index, y=v.linea_base_m + u, name=f"Umbral {nombre.lower()}",
                             line=dict(color=C.COLORES_ALERTA[nombre], dash="dash", width=1)), 1, 1)
for hz, color in zip([1, 3, 6], ["#1565C0", "#26A69A", "#6A1B9A"]):
    s = rf[(rf.h == hz) & rf.fecha_hora_objetivo.between(ini, fin) & (rf.fecha_hora_origen <= t)]
    fig.add_trace(go.Scatter(x=s.fecha_hora_objetivo, y=s.nivel_pred_m, name=f"Pronóstico {hz} h",
                             line=dict(color=color, width=1.5)), 1, 1)
    if hz in pr.index:
        fig.add_trace(go.Scatter(x=[pr.loc[hz].fecha_hora_objetivo], y=[pr.loc[hz].nivel_pred_m],
                                 mode="markers", marker=dict(color=color, size=11, symbol="diamond"),
                                 showlegend=False, hovertemplate=f"+{hz} h: %{{y:.2f}} m"), 1, 1)
fig.add_vline(x=t, line=dict(color="gray", dash="dot"))
fig.add_trace(go.Bar(x=v.index, y=v.lluvia_mm, name="Lluvia La Lindosa", marker_color="#42A5F5"), 2, 1)
fig.add_trace(go.Bar(x=v.index, y=M.loc[ini:fin].lluvia_mm, name="Lluvia Los Micos", marker_color="#90CAF9"), 2, 1)
fig.update_yaxes(title_text="Nivel (m)", row=1, col=1)
fig.update_yaxes(title_text="Lluvia (mm/h)", row=2, col=1)
fig.update_layout(height=560, margin=dict(t=30, b=10), legend=dict(orientation="h", y=1.08), barmode="group")
st.plotly_chart(fig, width="stretch")
st.caption("Línea punteada vertical: momento elegido. Las líneas de color a la derecha de ese momento "
           "son lo que el modelo pronosticaba; la negra es lo que realmente pasó.")

with st.expander("¿Qué significa cada color?"):
    st.markdown("""
La **anomalía** es cuánto está el río por encima de su nivel normal reciente (mediana de los 30 días anteriores).

| Estado | Anomalía | Eventos 2018-2025 |
|---|---|---|
| 🟢 Normal | < 0.5 m | — |
| 🟡 Amarilla | ≥ 0.5 m | 107 |
| 🟠 Naranja | ≥ 1.0 m | 23 |
| 🔴 Roja | ≥ 1.5 m | 10 |

Umbrales técnicos del proyecto (no oficiales); deben validarse con la CAM o Gestión del Riesgo.
""")
C.pie()
