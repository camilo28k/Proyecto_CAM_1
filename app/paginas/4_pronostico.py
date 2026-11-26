"""Página 4: pronóstico frente a la realidad en el periodo de prueba 2024-2025."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import comun as C

st.title("🎯 Pronóstico vs real (prueba 2024-2025)")
st.caption("¿Qué tan bien pronostica el modelo? Datos que el modelo **no vio** al entrenar.")

p = C.pronosticos()
c1, c2, c3 = st.columns([1, 2, 2])
hz = c1.radio("Horizonte", [1, 3, 6], format_func=lambda x: f"{x} h", horizontal=True)
modelo = c2.selectbox("Modelo", list(C.NOMBRE_MODELO), index=2, format_func=C.NOMBRE_MODELO.get)
rango = c3.date_input("Periodo", value=(pd.Timestamp("2024-11-10").date(), pd.Timestamp("2024-11-25").date()),
                      min_value=pd.Timestamp("2024-01-01").date(), max_value=pd.Timestamp("2025-12-31").date())

g = p[(p.h == hz) & (p.modelo == modelo)]
if isinstance(rango, tuple) and len(rango) == 2:
    sel = g[g.fecha_hora_objetivo.between(pd.Timestamp(rango[0]), pd.Timestamp(rango[1]) + pd.Timedelta("23h"))]
else:
    sel = g


def metricas(x):
    err = x.nivel_pred_m - x.nivel_real_m
    ra = (x.nivel_real_m - x.base_m) >= 0.5
    pa = (x.nivel_pred_m - x.base_m) >= 0.5
    tp, fp, fn = (ra & pa).sum(), (~ra & pa).sum(), (ra & ~pa).sum()
    return {"RMSE (cm)": 100 * np.sqrt((err ** 2).mean()), "MAE (cm)": 100 * err.abs().mean(),
            "POD": tp / (tp + fn) if tp + fn else np.nan, "FAR": fp / (tp + fp) if tp + fp else np.nan,
            "CSI": tp / (tp + fp + fn) if tp + fp + fn else np.nan}


st.markdown(f"**Todo el periodo de prueba** – {C.NOMBRE_MODELO[modelo]}, {hz} h")
mt = metricas(g)
cols = st.columns(5)
for col, (k, v) in zip(cols, mt.items()):
    col.metric(k, "—" if pd.isna(v) else (f"{v:.2f}" if "cm" in k else f"{v:.2f}"),
               help={"POD": "Proporción de horas en alerta que el modelo detectó",
                     "FAR": "Proporción de alertas del modelo que fueron falsas",
                     "CSI": "Índice crítico de éxito: combina POD y FAR (1 = perfecto)"}.get(k))

fig = go.Figure()
fig.add_trace(go.Scatter(x=sel.fecha_hora_objetivo, y=sel.nivel_real_m, name="Real", line=dict(color="black", width=2)))
fig.add_trace(go.Scatter(x=sel.fecha_hora_objetivo, y=sel.nivel_pred_m, name=f"Pronóstico {hz} h",
                         line=dict(color="#1565C0", width=1.5)))
fig.add_trace(go.Scatter(x=sel.fecha_hora_objetivo, y=sel.base_m + 0.5, name="Umbral amarilla",
                         line=dict(color=C.COLORES_ALERTA["Amarilla"], dash="dash", width=1)))
fig.update_layout(height=420, margin=dict(t=10), yaxis_title="Nivel (m)", legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, width="stretch")

a, b = st.columns(2)
with a:
    st.markdown("**Real vs pronosticado** (cada punto es una hora)")
    mx = max(g.nivel_real_m.max(), g.nivel_pred_m.max())
    fd = px.scatter(g, x="nivel_real_m", y="nivel_pred_m", opacity=0.35,
                    labels={"nivel_real_m": "Nivel real (m)", "nivel_pred_m": "Nivel pronosticado (m)"})
    fd.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", line=dict(color="red", dash="dash"), name="y = x"))
    fd.update_layout(height=380, margin=dict(t=10), showlegend=False)
    st.plotly_chart(fd, width="stretch")
with b:
    st.markdown("**Matriz de alertas** (horas): real en filas, pronosticada en columnas")
    nombres = C.NOMBRES_ALERTA
    cm = pd.crosstab(g.clase_alerta_real.map(lambda c: nombres[c]), g.clase_alerta_pred.map(lambda c: nombres[c]))
    cm = cm.reindex(index=nombres, columns=nombres, fill_value=0)
    fc = px.imshow(cm, text_auto="d", color_continuous_scale="Blues", aspect="auto",
                   labels=dict(x="Pronosticada", y="Real", color="Horas"))
    fc.update_layout(height=380, margin=dict(t=10))
    st.plotly_chart(fc, width="stretch")

st.info("**Interpretación (fase 2):** el modelo sigue bien la evolución de una creciente que ya empezó, "
        "pero anticipa poco su inicio: en La Lindosa la creciente llega en menos de 1 hora y en ~18 % de "
        "los casos la lluvia cae en la parte alta de la cuenca, donde no hay pluviómetro en los datos.")
C.pie()
