"""Pronóstico operativo: estado actual del río y alerta esperada en 1, 3 y 6 h.

Dos acciones:
  entrenar   ajusta el modelo seleccionado (Random Forest, hiperparámetros de la
             fase 2) con TODOS los datos válidos 2018 en adelante y lo guarda en
             models/operativo_rf_<h>h.joblib (+ ficha JSON con fecha y datos usados)
  pronosticar  para una fecha-hora (por defecto la última con datos completos),
             calcula nivel, anomalía, alerta actual y el pronóstico a 1/3/6 h.
             Escribe reports/pronostico_actual.json y agrega una fila a
             dashboard/datos/pronostico_actual.csv

Uso:
  python src/pronosticar.py entrenar
  python src/pronosticar.py pronosticar [--fecha "2024-11-14 06:00"]
"""
from pathlib import Path
import argparse
import json
import sys
from datetime import datetime
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src" / "models"))
import features as F  # noqa: E402

MOD = RAIZ / "models"
REP = RAIZ / "reports"
DASH = RAIZ / "dashboard" / "datos"
# Configuración elegida en validación (fase 2, reports/modelos_validacion.csv)
PARAMS_RF = dict(n_estimators=300, max_depth=20, min_samples_leaf=20, n_jobs=-1, random_state=42)
NOMBRES_ALERTA = ["NORMAL", "AMARILLA", "NARANJA", "ROJA"]


def ruta_modelo(h):
    return MOD / f"operativo_rf_{h}h.joblib"


def entrenar():
    MOD.mkdir(exist_ok=True)
    f = F.cargar().loc["2018-01-01":]
    cols = F.variables(f)
    ficha = {"modelo": "RandomForestRegressor", "parametros": PARAMS_RF, "variables": cols,
             "entrenado": datetime.now().isoformat(timespec="seconds"), "horizontes": {}}
    for h in F.HORIZONTES:
        v = F.filas_validas(f, h)
        m = RandomForestRegressor(**PARAMS_RF).fit(v[cols], v[f"y_delta_{h}h"])
        joblib.dump(m, ruta_modelo(h))
        ficha["horizontes"][f"{h}h"] = {"filas": len(v), "desde": str(v.index.min()), "hasta": str(v.index.max())}
        print(f"modelo operativo {h} h: {len(v):,} filas ({v.index.min():%Y-%m-%d} a {v.index.max():%Y-%m-%d})")
    json.dump(ficha, open(MOD / "operativo_ficha.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def pronosticar(fecha=None, guardar=True) -> dict:
    f = F.cargar()
    cols = F.variables(f)
    completas = f.dropna(subset=cols + ["base"])
    if fecha is None:
        t = completas.index.max()
    else:
        t = pd.Timestamp(fecha)
        if t not in completas.index:
            raise SystemExit(f"No hay datos completos para {t}. Última hora disponible: {completas.index.max()}")
    fila = completas.loc[[t]]
    nivel, base = float(fila["nivel"].iloc[0]), float(fila["base"].iloc[0])
    an = nivel - base
    salida = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "estacion": "La Lindosa (río Las Ceibas)",
        "fecha_hora": str(t),
        "nivel_m": round(nivel, 3), "linea_base_m": round(base, 3), "anomalia_m": round(an, 3),
        "alerta_actual": NOMBRES_ALERTA[int(F.clase_alerta([an])[0])],
        "umbrales_m": {k: round(base + u, 3) for k, u in F.UMBRALES_ALERTA.items()},
        "pronostico": [],
        "aviso": "Herramienta académica de apoyo. No reemplaza las alertas oficiales de la CAM ni de Gestión del Riesgo.",
    }
    for h in F.HORIZONTES:
        if not ruta_modelo(h).exists():
            raise SystemExit("Falta el modelo operativo. Ejecute primero: python src/pronosticar.py entrenar")
        m = joblib.load(ruta_modelo(h))
        p = nivel + float(m.predict(fila[cols])[0])
        real = f["nivel"].get(t + pd.Timedelta(hours=h), np.nan)
        salida["pronostico"].append({
            "horizonte_h": h, "fecha_hora": str(t + pd.Timedelta(hours=h)),
            "nivel_pronosticado_m": round(p, 3), "anomalia_pronosticada_m": round(p - base, 3),
            "alerta_pronosticada": NOMBRES_ALERTA[int(F.clase_alerta([p - base])[0])],
            "nivel_real_m": None if pd.isna(real) else round(float(real), 3),  # solo si ya ocurrió (histórico)
        })
    if not guardar:
        return salida
    REP.mkdir(exist_ok=True)
    json.dump(salida, open(REP / "pronostico_actual.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if DASH.exists():
        plano = {k: v for k, v in salida.items() if k not in ("pronostico", "umbrales_m", "aviso")}
        for p in salida["pronostico"]:
            plano[f"nivel_{p['horizonte_h']}h_m"] = p["nivel_pronosticado_m"]
            plano[f"alerta_{p['horizonte_h']}h"] = p["alerta_pronosticada"]
        archivo = DASH / "pronostico_actual.csv"
        pd.DataFrame([plano]).to_csv(archivo, mode="a", header=not archivo.exists(), index=False)
    return salida


def imprimir(s):
    print(f"\n{s['estacion']} - {s['fecha_hora']}")
    print(f"  Nivel {s['nivel_m']:.2f} m | línea base {s['linea_base_m']:.2f} m | anomalía {s['anomalia_m']:+.2f} m"
          f" | ALERTA ACTUAL: {s['alerta_actual']}")
    for p in s["pronostico"]:
        real = f" (real: {p['nivel_real_m']:.2f} m)" if p["nivel_real_m"] is not None else ""
        print(f"  +{p['horizonte_h']} h -> {p['nivel_pronosticado_m']:.2f} m  {p['alerta_pronosticada']}{real}")
    print(f"  {s['aviso']}\n")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=["entrenar", "pronosticar"])
    ap.add_argument("--fecha", help='fecha-hora a evaluar, p. ej. "2024-11-14 06:00"')
    a = ap.parse_args()
    if a.accion == "entrenar":
        entrenar()
    else:
        imprimir(pronosticar(a.fecha))


if __name__ == "__main__":
    main()
