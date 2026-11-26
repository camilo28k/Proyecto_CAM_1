"""Carga de datos (con caché) y elementos comunes del dashboard Streamlit.

Los datos salen de dashboard/datos/*.csv, que genera src/dashboard/exportar_powerbi.py
(o src/pipeline.py). Si no existen, la app lo indica.
"""
from pathlib import Path
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "dashboard" / "datos"

COLORES_ALERTA = {"Normal": "#2E7D32", "Amarilla": "#F9A825", "Naranja": "#EF6C00", "Roja": "#C62828"}
NOMBRES_ALERTA = ["Normal", "Amarilla", "Naranja", "Roja"]
UMBRALES = {"Amarilla": 0.5, "Naranja": 1.0, "Roja": 1.5}
NOMBRE_MODELO = {"persistencia": "Persistencia", "ridge": "Ridge", "random_forest": "Random Forest",
                 "xgboost": "XGBoost", "xgboost_ponderado": "XGBoost ponderado", "lstm": "LSTM"}
ESTACION = {"La_Lindosa": "La Lindosa", "Los_Micos": "Los Micos", "El_Batan": "El Batán",
            "Las_Juntas": "Las Juntas", "San_Benito": "San Benito", "Puente_Bruselas": "Puente Bruselas"}

AVISO = ("Herramienta académica de apoyo. **No reemplaza las alertas oficiales** "
         "de la CAM ni de Gestión del Riesgo de Neiva.")


def _leer(nombre, fechas=()):
    ruta = DATOS / f"{nombre}.csv"
    if not ruta.exists():
        st.error(f"Falta `{ruta.relative_to(RAIZ)}`. Ejecute primero: "
                 "`.venv\\Scripts\\python src\\pipeline.py --rapido`")
        st.stop()
    return pd.read_csv(ruta, parse_dates=list(fechas))


@st.cache_data(show_spinner="Cargando datos hidrológicos…")
def hidrologia():
    h = _leer("hechos_hidrologia", ["fecha_hora"])
    h["alerta"] = h.clase_alerta.map(lambda c: NOMBRES_ALERTA[int(c)] if pd.notna(c) else None)
    return h


@st.cache_data(show_spinner="Cargando pronósticos…")
def pronosticos():
    return _leer("hechos_pronostico", ["fecha_hora_origen", "fecha_hora_objetivo"])


@st.cache_data
def eventos():
    e = _leer("eventos_crecientes", ["inicio", "fin", "fecha_pico"])
    e["alerta"] = e.clase_alerta.map(lambda c: NOMBRES_ALERTA[int(c)])
    return e


@st.cache_data
def tabla(nombre):
    return _leer(nombre)


def alerta_de(anomalia):
    if anomalia is None or pd.isna(anomalia):
        return "Sin dato"
    nombre = "Normal"
    for k, u in UMBRALES.items():
        if anomalia >= u:
            nombre = k
    return nombre


def insignia(texto, color):
    st.markdown(
        f"<div style='background:{color};color:white;border-radius:10px;padding:14px 10px;"
        f"text-align:center;font-size:1.6rem;font-weight:700'>{texto}</div>",
        unsafe_allow_html=True)


def pie():
    st.divider()
    st.caption(AVISO + "  Datos: estaciones hidrometeorológicas de la CAM (2017-2025). "
               "Proyecto de grado – Ingeniería de Sistemas, CORHUILA.")
