"""Dashboard de alertas tempranas – río Las Ceibas.

Ejecutar desde la carpeta del proyecto:
    .venv\\Scripts\\streamlit run app\\app.py
"""
import streamlit as st

st.set_page_config(page_title="Alertas Las Ceibas", page_icon="🌊", layout="wide")

paginas = [
    st.Page("paginas/1_estado.py", title="Estado del río", icon="🚨", default=True),
    st.Page("paginas/2_historico.py", title="Histórico y crecientes", icon="📈"),
    st.Page("paginas/3_calidad.py", title="Calidad de datos", icon="🧹"),
    st.Page("paginas/4_pronostico.py", title="Pronóstico vs real", icon="🎯"),
    st.Page("paginas/5_modelos.py", title="Comparación de modelos", icon="🏆"),
]
st.sidebar.markdown("### 🌊 Río Las Ceibas\nSistema de calidad de datos y alertas tempranas – estación **La Lindosa** (Neiva, Huila)")
st.navigation(paginas).run()
