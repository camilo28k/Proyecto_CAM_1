"""Página 5: comparación de modelos y pruebas estadísticas."""
import plotly.express as px
import streamlit as st
import comun as C

st.title("🏆 Comparación de modelos")
st.caption("¿Por qué se eligió Random Forest?")

m = C.tabla("metricas_modelos")
pe = C.tabla("pruebas_estadisticas")
m["Modelo"] = m.modelo.map(C.NOMBRE_MODELO)
m["Horizonte"] = m.h.astype(str) + " h"

rf = m[m.modelo == "random_forest"].set_index("h")
pers = m[m.modelo == "persistencia"].set_index("h")
k = st.columns(4)
k[0].metric("Modelo seleccionado", "Random Forest")
for col, h in zip(k[1:], [1, 3, 6]):
    mejora = 1 - rf.loc[h, "rmse_cm"] / pers.loc[h, "rmse_cm"]
    col.metric(f"RMSE a {h} h", f"{rf.loc[h, 'rmse_cm']:.2f} cm", f"{mejora:.0%} mejor que persistencia")

orden = list(C.NOMBRE_MODELO.values())
a, b = st.columns(2)
fa = px.bar(m, x="Modelo", y="rmse_cm", color="Horizonte", barmode="group", category_orders={"Modelo": orden},
            labels={"rmse_cm": "RMSE (cm) – menor es mejor"}, color_discrete_sequence=["#1565C0", "#26A69A", "#6A1B9A"])
fa.update_layout(height=380, margin=dict(t=30), title="Error del nivel")
a.plotly_chart(fa, width="stretch")
fb = px.bar(m, x="Modelo", y="csi", color="Horizonte", barmode="group", category_orders={"Modelo": orden},
            labels={"csi": "CSI – mayor es mejor"}, color_discrete_sequence=["#1565C0", "#26A69A", "#6A1B9A"])
fb.update_layout(height=380, margin=dict(t=30), title="Detección de alerta amarilla")
b.plotly_chart(fb, width="stretch")

st.subheader("Métricas en prueba (2024-2025)")
t = m[["Horizonte", "Modelo", "rmse_cm", "mae_cm", "nse_delta", "rmse_crecientes_cm", "csi", "pod_inicio"]].rename(
    columns={"rmse_cm": "RMSE (cm)", "mae_cm": "MAE (cm)", "nse_delta": "NSE del cambio",
             "rmse_crecientes_cm": "RMSE crecientes (cm)", "csi": "CSI", "pod_inicio": "POD inicio"})
st.dataframe(t.style.format(precision=3).highlight_min(subset=["RMSE (cm)", "MAE (cm)"], color="#C8E6C9")
             .highlight_max(subset=["CSI", "NSE del cambio"], color="#C8E6C9"),
             hide_index=True, width="stretch")
st.caption("NSE del cambio: 0 = igual que la persistencia; > 0 = mejor. "
           "POD inicio: proporción de inicios de creciente anticipados.")

st.subheader("Pruebas estadísticas")
st.markdown("Error absoluto medio **diario** (≈ 470 días pareados). Shapiro-Wilk rechazó la normalidad en "
            "todos los casos (p < 0.001), por eso se usó **Wilcoxon** de rangos con signo con corrección de **Holm**.")
s = pe[["h", "mejor", "comparado_con", "mae_diario_mejor_cm", "mae_diario_otro_cm", "prueba", "p_holm",
        "diferencia_significativa"]].copy()
s["mejor"] = s.mejor.map(C.NOMBRE_MODELO)
s["comparado_con"] = s.comparado_con.map(C.NOMBRE_MODELO)
s = s.rename(columns={"h": "h", "mejor": "Mejor", "comparado_con": "Comparado con",
                      "mae_diario_mejor_cm": "MAE mejor (cm)", "mae_diario_otro_cm": "MAE otro (cm)",
                      "prueba": "Prueba", "p_holm": "p (Holm)", "diferencia_significativa": "¿Diferencia?"})
st.dataframe(s.style.format({"MAE mejor (cm)": "{:.3f}", "MAE otro (cm)": "{:.3f}", "p (Holm)": "{:.2e}"})
             .apply(lambda r: ["background-color:#FFF9C4" if not r["¿Diferencia?"] else "" for _ in r], axis=1),
             hide_index=True, width="stretch")
st.success("**Decisión:** Random Forest es el mejor a 1 h con diferencia significativa frente a todos; a 3 y 6 h "
           "está estadísticamente empatado con XGBoost (filas amarillas) y tiene el mayor CSI en los tres "
           "horizontes. La LSTM fue la peor: con solo 64 crecientes de entrenamiento los árboles aprovechan "
           "mejor los datos.")
C.pie()
