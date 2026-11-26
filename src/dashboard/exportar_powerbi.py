"""Exporta el modelo de datos (tablas CSV) para el dashboard de Power BI.

Esquema en estrella:
  dim_estacion, dim_fecha, dim_alerta, dim_modelo          (dimensiones)
  hechos_hidrologia      nivel/lluvia horario de La Lindosa y Los Micos (limpio)
  hechos_pronostico      pronóstico vs real en test 2024-2025, todos los modelos
  calidad_anual          completitud por estación y año (6 estaciones, datos crudos)
  calidad_limpieza       qué hizo el ETL (antes/después y bitácora)
  metricas_modelos       métricas de test por modelo y horizonte
  pruebas_estadisticas   Shapiro-Wilk / Wilcoxon / Holm
  eventos_crecientes     lista de crecientes detectadas (anomalía >= 0.5 m)

Salida: dashboard/datos/*.csv  (UTF-8, separador coma, punto decimal)
Uso:    python src/dashboard/exportar_powerbi.py
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src" / "models"))
import features as F  # noqa: E402

PROC = RAIZ / "data" / "processed"
REP = RAIZ / "reports"
OUT = RAIZ / "dashboard" / "datos"

ESTACIONES = pd.DataFrame([
    # estacion, nombre, municipio, corriente, lat, lon, km a Neiva, en cuenca, rol
    ("La_Lindosa", "La Lindosa", "Neiva", "Río Las Ceibas", 2.8772, -75.1478, 15.9, True, "Objetivo (se pronostica)"),
    ("Los_Micos", "Los Micos", "Neiva", "Quebrada Los Micos", 2.9153, -75.1325, 16.6, True, "Apoyo (variables de entrada)"),
    ("El_Batan", "El Batán", "Neiva", "Río Las Ceibas (parte alta)", 2.7967, -75.0750, 27.2, True, "Experimental"),
    ("Las_Juntas", "Las Juntas", "Rivera", "Río Frío", 2.7581, -75.2119, 20.4, False, "Descartada (otra cuenca)"),
    ("San_Benito", "San Benito", "Garzón", "Quebrada Garzón", 2.1828, -75.5994, 90.0, False, "Descartada (otra cuenca)"),
    ("Puente_Bruselas", "Puente Bruselas", "Pitalito", "Quebrada Guachicos", 1.7850, -76.1639, 160.4, False, "Descartada (otra cuenca)"),
], columns=["estacion", "nombre", "municipio", "corriente", "latitud", "longitud", "distancia_neiva_km",
            "en_cuenca_ceibas", "rol"])

ALERTAS = pd.DataFrame({
    "clase_alerta": [0, 1, 2, 3],
    "alerta": ["Normal", "Amarilla", "Naranja", "Roja"],
    "anomalia_minima_m": [-np.inf, *F.UMBRALES_ALERTA.values()],
    "color_hex": ["#2E7D32", "#F9A825", "#EF6C00", "#C62828"],
    "orden": [0, 1, 2, 3],
})
ALERTAS["anomalia_minima_m"] = ALERTAS["anomalia_minima_m"].replace(-np.inf, np.nan)

MODELOS = pd.DataFrame([
    ("persistencia", "Persistencia", "Referencia", False),
    ("ridge", "Ridge", "Regresión lineal", False),
    ("random_forest", "Random Forest", "Machine learning", True),
    ("xgboost", "XGBoost", "Machine learning", False),
    ("xgboost_ponderado", "XGBoost ponderado", "Machine learning", False),
    ("lstm", "LSTM", "Deep learning", False),
], columns=["modelo", "nombre_modelo", "familia", "seleccionado"])


def hidrologia():
    d = pd.read_parquet(PROC / "dataset_modelo.parquet")
    filas = []
    for est, suf in [("La_Lindosa", "lindosa"), ("Los_Micos", "micos")]:
        n = d[f"nivel_{suf}_m"]
        base = F.linea_base(n)
        t = pd.DataFrame({
            "fecha_hora": d.index, "estacion": est,
            "nivel_m": n.values, "lluvia_mm": d[f"lluvia_{suf}_mm"].values,
            "temperatura_c": d[f"temperatura_{suf}_c"].values,
            "nivel_imputado": d[f"nivel_{suf}_imputado"].values,
            "linea_base_m": base.values, "anomalia_m": (n - base).values,
        })
        t["nivel_max_m"] = d["nivel_max_lindosa_m"].values if est == "La_Lindosa" else np.nan
        t["clase_alerta"] = np.where(t.anomalia_m.notna(), F.clase_alerta(t.anomalia_m.fillna(-9)), np.nan)
        filas.append(t)
    h = pd.concat(filas, ignore_index=True)
    h["fecha"] = h.fecha_hora.dt.date
    return h


def eventos(h):
    L = h[h.estacion == "La_Lindosa"].set_index("fecha_hora")
    ex = (L.anomalia_m >= F.UMBRALES_ALERTA["amarilla"]).fillna(False)
    grupo = (ex != ex.shift()).cumsum()
    ev = []
    for _, g in L[ex].groupby(grupo[ex]):
        pico = g.anomalia_m.idxmax()
        ev.append({"inicio": g.index[0], "fin": g.index[-1], "duracion_h": len(g),
                   "fecha_pico": pico, "nivel_pico_m": g.nivel_m.max(),
                   "nivel_max_instantaneo_m": g.nivel_max_m.max(), "anomalia_pico_m": g.anomalia_m.max(),
                   "lluvia_evento_mm": g.lluvia_mm.sum(),
                   "lluvia_6h_previas_mm": L.lluvia_mm.loc[g.index[0] - pd.Timedelta("6h"):g.index[0]].sum()})
    e = pd.DataFrame(ev)
    e["clase_alerta"] = F.clase_alerta(e.anomalia_pico_m)
    e["anio"] = e.inicio.dt.year
    e["fecha"] = e.inicio.dt.date
    e.insert(0, "id_evento", range(1, len(e) + 1))
    return e


def pronosticos():
    p = pd.read_parquet(REP / "predicciones_test.parquet")
    p["anomalia_real_m"] = p.nivel_real_m - p.base_m
    p["anomalia_pred_m"] = p.nivel_pred_m - p.base_m
    p["clase_alerta_real"] = F.clase_alerta(p.anomalia_real_m)
    p["clase_alerta_pred"] = F.clase_alerta(p.anomalia_pred_m)
    p["error_m"] = p.nivel_pred_m - p.nivel_real_m
    p["error_abs_cm"] = 100 * p.error_m.abs()
    p["horizonte"] = p.h.astype(str) + " h"
    p["fecha"] = p.fecha_hora_objetivo.dt.date
    return p


def dim_fecha(h):
    f = pd.DataFrame({"fecha": pd.date_range(h.fecha_hora.min().normalize(), h.fecha_hora.max().normalize(), freq="D")})
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    f["anio"] = f.fecha.dt.year
    f["mes"] = f.fecha.dt.month
    f["nombre_mes"] = f.mes.map(lambda m: meses[m - 1])
    f["anio_mes"] = f.fecha.dt.strftime("%Y-%m")
    # temporadas de lluvia en el Huila: bimodal (mar-may y oct-dic)
    f["temporada"] = np.where(f.mes.isin([3, 4, 5, 10, 11, 12]), "Lluviosa", "Seca")
    f["periodo_modelo"] = np.select([f.anio <= 2017, f.anio <= 2022, f.anio == 2023],
                                    ["Excluido (2017)", "Entrenamiento", "Validación"], "Prueba")
    f["fecha"] = f.fecha.dt.date
    return f


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h = hidrologia()
    tablas = {
        "dim_estacion": ESTACIONES, "dim_alerta": ALERTAS, "dim_modelo": MODELOS, "dim_fecha": dim_fecha(h),
        "hechos_hidrologia": h, "hechos_pronostico": pronosticos(), "eventos_crecientes": eventos(h),
        "calidad_anual": pd.read_csv(REP / "calidad_por_anio.csv"),
        "calidad_antes_despues": pd.read_csv(REP / "calidad_antes_despues.csv"),
        "calidad_bitacora": pd.read_csv(REP / "bitacora_limpieza.csv"),
        "metricas_modelos": pd.read_csv(REP / "modelos_test.csv"),
        "pruebas_estadisticas": pd.read_csv(REP / "pruebas_estadisticas.csv"),
    }
    for nombre, t in tablas.items():
        t.to_csv(OUT / f"{nombre}.csv", index=False, float_format="%.4f", encoding="utf-8")
        print(f"{nombre:24s} {len(t):>8,} filas  {t.shape[1]} columnas")


if __name__ == "__main__":
    main()
