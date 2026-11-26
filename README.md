# Alertas tempranas de inundación – río Las Ceibas (Neiva, Huila)

Proyecto de grado de Ingeniería de Sistemas en CORHUILA. Consta de tres partes: un sistema de calidad de datos hidrometeorológicos, modelos predictivos del nivel del río y un dashboard en Streamlit.

- **👉 Empiece aquí: [MANUAL.md](MANUAL.md)** (instalación, ejecución y recorrido del dashboard).
- **Estado y decisiones:** ver [bitacora/README.md](bitacora/README.md).
- **Datos originales:** `Datos_CAM/` (CAM, 6 estaciones, 2017-2025). No se modifican.

## Puesta en marcha (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python src\pipeline.py          # flujo completo (~15 min)
.venv\Scripts\python -m pytest tests            # 32 pruebas
.venv\Scripts\streamlit run app\app.py         # dashboard en http://localhost:8501
.venv\Scripts\python src\pronosticar.py pronosticar --fecha "2024-11-14 06:00"
```
- Arquitectura y cómo agregar datos nuevos: [ARQUITECTURA.md](ARQUITECTURA.md)
- Dashboard: `app/` (Streamlit); protocolo de pruebas en [app/PRUEBAS_USABILIDAD.md](app/PRUEBAS_USABILIDAD.md)
