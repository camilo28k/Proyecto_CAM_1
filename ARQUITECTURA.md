# Arquitectura técnica del sistema

Este documento describe cómo encajan las piezas del sistema. Las decisiones y los resultados de cada parte están en [`bitacora/`](bitacora/README.md).

## 1. Vista general

```
                    ┌──────────────────────────────────────────────┐
  Datos_CAM/        │  SISTEMA DE CALIDAD DE DATOS (src/etl)       │
  6 estaciones      │                                              │
  Excel (MAIGRAI)   │  cargar_crudos ──► diagnostico_calidad       │
  CSV (MeerKAD) ───►│       │                                      │
  2017-2025         │       ▼                                      │
                    │  procesar (calidad.py):                      │
                    │   rangos CAM → picos → sensor pegado →       │
                    │   mesetas → paso horario → imputación ≤6 h   │
                    └───────┬──────────────────────────────────────┘
                            │ data/processed/dataset_modelo.parquet
                            ▼
                    ┌──────────────────────────────────────────────┐
                    │  MODELOS PREDICTIVOS (src/models)            │
                    │  features → entrenar (6 modelos × 1/3/6 h)   │
                    │  → pruebas_estadisticas → Random Forest      │
                    │  alerta_clasificador (experimento)           │
                    └───────┬───────────────────────┬──────────────┘
                            │ reports/*.csv          │ models/operativo_rf_*.joblib
                            ▼                        ▼
                    ┌────────────────────┐   ┌──────────────────────────┐
                    │ exportar_powerbi   │   │ pronosticar.py           │
                    │ (src/dashboard)    │   │ estado actual + alerta   │
                    └───────┬────────────┘   │ a 1/3/6 h → JSON y CSV   │
                            │                └────────────┬─────────────┘
                            ▼ dashboard/datos/*.csv       │
                    ┌──────────────────────────────────────▼───────────┐
                    │  DASHBOARD POWER BI (5 páginas)                   │
                    └──────────────────────────────────────────────────┘

        src/pipeline.py ejecuta todo en orden y valida cada etapa
```

## 2. Componentes

| Componente | Archivo | Entrada | Salida |
|---|---|---|---|
| Carga | `src/etl/cargar_crudos.py` | `Datos_CAM/**/*.xlsx, *.csv` | `data/interim/<estación>_crudo.parquet` y `_horario.parquet` |
| Diagnóstico | `src/etl/diagnostico_calidad.py` | `data/interim/*_horario` | `reports/calidad_*.csv` y figuras |
| Reglas de calidad | `src/etl/calidad.py` | (librería) | funciones puras y probadas |
| Limpieza | `src/etl/procesar.py` | `data/interim/*_crudo` | `data/processed/dataset_modelo.parquet` (y `.csv`) |
| Variables | `src/models/features.py` | dataset | 25 variables sin fuga de futuro y el objetivo delta a 1/3/6 h |
| Entrenamiento | `src/models/entrenar.py` | variables | `reports/modelos_*.csv`, `predicciones_test.parquet`, `models/` |
| Estadística | `src/models/pruebas_estadisticas.py` | predicciones | `reports/pruebas_estadisticas.csv` |
| Modelo operativo | `src/pronosticar.py entrenar` | variables 2018 en adelante | `models/operativo_rf_<h>h.joblib` y su ficha |
| Pronóstico | `src/pronosticar.py pronosticar` | dataset y modelo operativo | `reports/pronostico_actual.json` y `dashboard/datos/pronostico_actual.csv` |
| Exportación a BI | `src/dashboard/exportar_powerbi.py` | todo lo anterior | `dashboard/datos/*.csv` (12 tablas) |
| Orquestador | `src/pipeline.py` | — | ejecuta y valida todo; log en `logs/` |

## 3. Cómo ejecutarlo

Desde `Proyecto Grado`, en PowerShell.

**Instalación** (una sola vez):
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

**Todo desde cero** (unos 15 minutos):
```powershell
.venv\Scripts\python src\pipeline.py
```

**Datos nuevos de la CAM, sin reentrenar la comparación de modelos** (unos 2 minutos):
```powershell
.venv\Scripts\python src\pipeline.py --rapido
```

**Pronóstico para un momento dado:**
```powershell
.venv\Scripts\python src\pronosticar.py pronosticar --fecha "2024-11-14 06:00"
```

**Pruebas automáticas:**
```powershell
.venv\Scripts\python -m pytest tests
```

## 4. Cómo agregar datos nuevos de la CAM

1. Copia el archivo nuevo en la carpeta de su estación, por ejemplo `Datos_CAM/La_Lindosa/La_Lindosa_2026.csv`. Debe tener el mismo formato de MeerKAD: separador `;`, coma decimal y fechas día/mes/año.
2. Ejecuta `.venv\Scripts\python src\pipeline.py --rapido`. Esto vuelve a cargar y limpiar los datos, reentrena el modelo operativo con los datos nuevos, regenera las tablas de Power BI y calcula el pronóstico para la última hora disponible.
3. En Power BI, pulsa **Inicio → Actualizar**.

Si el archivo trae una columna con un nombre nuevo, la carga **se detiene con un error que nombra la columna**. Así no se pierden datos en silencio. Para resolverlo, agrega la columna a `MAPA_COLUMNAS` en `src/etl/cargar_crudos.py`.

## 5. Qué se versiona y qué no

| Se sube a GitHub | No se sube (se regenera) |
|---|---|
| código (`src/`, `tests/`), bitácora y guías | `.venv/` (entorno) |
| `reports/` (tablas y figuras de resultados) | `data/` (datos intermedios y procesados) |
| `Datos_CAM/` y `Docs/` (originales) | `models/` (modelos entrenados) |
| `requirements.txt` (versiones exactas) | `dashboard/datos/` (unos 36 MB) y `logs/` |

## 6. Reproducibilidad

- Las versiones exactas de las librerías están en `requirements.txt` (Python 3.14).
- Todas las semillas aleatorias están fijadas en 42.
- `src/pipeline.py` regenera todos los resultados desde los datos crudos.
- **Verificación:** el flujo se ejecutó desde cero, sin `data/` ni `models/`, y se compararon sus resultados con los ya publicados (ver el informe de la fase 4).

## 7. Limitaciones de la arquitectura actual

- Los datos se procesan **por lotes**. No hay conexión en tiempo real con la transmisión satelital de la CAM.
- El dashboard se actualiza a mano en Power BI Desktop. Para que se actualice solo haría falta Power BI Service con una puerta de enlace (gateway).
- El modelo operativo se reentrena completo cada vez. Con datos de varios años sigue tardando menos de 2 minutos, así que por ahora no es un problema.
