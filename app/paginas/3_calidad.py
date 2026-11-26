"""Página 3: calidad de los datos y selección de la estación."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import comun as C

st.title("🧹 Calidad de los datos")
st.caption("¿Qué tan confiables son los datos y por qué se eligió La Lindosa?")

est = C.tabla("dim_estacion")
cal = C.tabla("calidad_anual")
ad = C.tabla("calidad_antes_despues")
bit = C.tabla("calidad_bitacora")

a, b = st.columns([3, 2])
with a:
    st.subheader("Ubicación de las estaciones")
    m = est.copy()
    m["Estación"] = m.nombre
    fig = px.scatter_map(m, lat="latitud", lon="longitud", color="rol", hover_name="Estación",
                         hover_data={"municipio": True, "corriente": True, "distancia_neiva_km": True,
                                     "latitud": False, "longitud": False, "rol": False},
                         zoom=7.1, height=430, size=[14] * len(m), size_max=14,
                         color_discrete_map={"Objetivo (se pronostica)": "#C62828",
                                             "Apoyo (variables de entrada)": "#1565C0",
                                             "Experimental": "#F9A825",
                                             "Descartada (otra cuenca)": "#9E9E9E"})
    fig.add_trace(go.Scattermap(lat=[2.9273], lon=[-75.2819], mode="markers+text", text=["Neiva"],
                                textposition="top right", marker=dict(size=16, color="black"), name="Neiva"))
    fig.update_layout(map_style="open-street-map", margin=dict(t=0, b=0, l=0, r=0),
                      map_center=dict(lat=2.35, lon=-75.7), legend=dict(orientation="h", y=-0.05))
    st.plotly_chart(fig, width="stretch", config={"scrollZoom": False})
with b:
    st.subheader("¿Por qué La Lindosa?")
    st.markdown("""
- **Mejores datos:** 94.9 % de las horas con nivel (2021-2025), > 88 % todos los años desde 2018.
- **La más cercana a Neiva:** ~16 km, sobre el **cauce principal** del río Las Ceibas.
- **Registra el riesgo:** nivel normal ~0.8 m, crecientes de hasta **3.7 m** (feb. 2022).
- **Los Micos** (afluente, 95.8 % de datos) aporta variables de apoyo.
- **Las Juntas, San Benito y Puente Bruselas** están en **otras cuencas** (Rivera, Garzón y Pitalito): se descartaron.
""")
    st.dataframe(est[["nombre", "municipio", "corriente", "distancia_neiva_km", "rol"]].rename(
        columns={"nombre": "Estación", "municipio": "Municipio", "corriente": "Corriente",
                 "distancia_neiva_km": "km a Neiva", "rol": "Rol"}), hide_index=True, width="stretch")

st.subheader("Completitud por estación y año (% de horas con dato, datos crudos)")
var = st.radio("Variable", ["nivel_pct", "lluvia_pct", "ambos_pct"], horizontal=True,
               format_func={"nivel_pct": "Nivel", "lluvia_pct": "Lluvia", "ambos_pct": "Nivel y lluvia"}.get)
mat = cal.pivot(index="estacion", columns="anio", values=var).rename(index=C.ESTACION)
fh = px.imshow(mat, text_auto=".0f", color_continuous_scale="RdYlGn", zmin=0, zmax=100, aspect="auto",
               labels=dict(x="Año", y="", color="%"))
fh.update_layout(height=330, margin=dict(t=10))
st.plotly_chart(fh, width="stretch")

st.subheader("Qué hizo el sistema de limpieza (La Lindosa y Los Micos)")
c1, c2 = st.columns(2)
with c1:
    t = bit.set_index("estacion").rename(index=C.ESTACION)[
        ["rangos_quitados", "picos_quitados", "pegado_registros", "mesetas_rellenadas", "horas_imputadas"]].T
    t.index = ["Fuera de rango eliminados", "Picos aislados eliminados", "Sensor pegado (registros eliminados)",
               "Registros recuperados (mesetas)", "Horas imputadas (huecos ≤ 6 h)"]
    st.dataframe(t, width="stretch")
    st.caption("La regla de la CAM (> 20 valores idénticos = sensor pegado) borraba datos válidos de un río "
               "estable; el sistema los recupera cuando el valor antes y después del hueco es el mismo.")
with c2:
    x = ad.assign(estacion=ad.estacion.map(C.ESTACION))
    fa = px.bar(x, x="estacion", y="n_huecos_nivel", color="etapa", barmode="group",
                color_discrete_map={"antes": "#B0BEC5", "despues": "#1565C0"},
                labels={"estacion": "", "n_huecos_nivel": "Número de huecos en el nivel", "etapa": ""})
    fa.update_layout(height=320, margin=dict(t=10))
    st.plotly_chart(fa, width="stretch")
    st.caption("Los huecos cortos (≤ 6 h) pasaron de 54 a 1 en La Lindosa y de 449 a 1 en Los Micos.")
C.pie()
