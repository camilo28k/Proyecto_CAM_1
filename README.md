# Alertas tempranas de inundación – río Las Ceibas (Neiva, Huila)

Proyecto de grado de Ingeniería de Sistemas en CORHUILA. Consta de tres partes: un sistema de calidad de datos hidrometeorológicos, modelos predictivos del nivel del río y un dashboard en Power BI.

- **Estado y decisiones:** ver [docs/fases/README.md](docs/fases/README.md).
- **Datos originales:** `Datos_CAM/` (CAM, 6 estaciones, 2017-2025). No se modifican.

## Puesta en marcha (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python src\etl\cargar_crudos.py
.venv\Scripts\python src\etl\diagnostico_calidad.py
.venv\Scripts\python src\etl\procesar.py
.venv\Scripts\python -m pytest tests
```
Resultado final del ETL: `data/processed/dataset_modelo.parquet` (y `.csv`).
