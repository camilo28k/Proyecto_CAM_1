"""Orquestador: ejecuta el flujo completo del proyecto con un solo comando.

  datos crudos (Datos_CAM/)
     -> 1 carga          src/etl/cargar_crudos.py
     -> 2 diagnostico    src/etl/diagnostico_calidad.py
     -> 3 limpieza       src/etl/procesar.py
     -> 4 imputacion     src/etl/evaluar_imputacion.py      (experimento, opcional)
     -> 5 modelos        src/models/entrenar.py             (~10 min)
     -> 6 estadistica    src/models/pruebas_estadisticas.py
     -> 7 alerta         src/models/alerta_clasificador.py
     -> 8 operativo      src/pronosticar.py entrenar
     -> 9 powerbi        src/dashboard/exportar_powerbi.py
     -> 10 pronostico    src/pronosticar.py pronosticar

Después de cada etapa se validan sus salidas (existen y tienen contenido sensato).
Si una etapa o validación falla, el flujo se detiene y lo indica.
Log completo en logs/pipeline_<fecha>.log

Uso:
  python src/pipeline.py                     # todo
  python src/pipeline.py --rapido            # sin reentrenar ni experimentos (usa modelos existentes)
  python src/pipeline.py --desde limpieza    # desde una etapa
  python src/pipeline.py --solo powerbi      # una sola etapa
"""
from pathlib import Path
import argparse
import subprocess
import sys
import time
from datetime import datetime
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PY = sys.executable
LOGS = RAIZ / "logs"


# ------------------------------------------------------------------ validaciones
def _existe(*rutas):
    faltan = [str(r.relative_to(RAIZ)) for r in rutas if not r.exists() or r.stat().st_size == 0]
    assert not faltan, f"faltan salidas: {faltan}"


def v_carga():
    r = pd.read_csv(RAIZ / "data/interim/resumen_carga.csv")
    assert len(r) == 6, f"se esperaban 6 estaciones, hay {len(r)}"
    assert (r.registros > 100_000).all(), "alguna estación tiene muy pocos registros"


def v_diagnostico():
    _existe(RAIZ / "reports/calidad_por_anio.csv", RAIZ / "reports/figures/completitud_nivel.png")


def v_limpieza():
    d = pd.read_parquet(RAIZ / "data/processed/dataset_modelo.parquet")
    comp = d.loc["2018":, "nivel_lindosa_m"].notna().mean()
    assert comp > 0.85, f"completitud del nivel de La Lindosa 2018+ = {comp:.1%} (< 85%)"
    assert d.nivel_lindosa_m.dropna().between(0, 10).all(), "niveles fuera de [0, 10] m"
    assert d.index.is_monotonic_increasing and not d.index.has_duplicates


def v_imputacion():
    _existe(RAIZ / "reports/evaluacion_imputacion.csv")


def v_modelos():
    m = pd.read_csv(RAIZ / "reports/modelos_test.csv")
    assert set(m.modelo) >= {"persistencia", "random_forest", "xgboost", "lstm"}
    rf = m[m.modelo == "random_forest"].set_index("h").rmse_cm
    pe = m[m.modelo == "persistencia"].set_index("h").rmse_cm
    assert (rf < pe).all(), "Random Forest no supera a la persistencia en algún horizonte"


def v_estadistica():
    _existe(RAIZ / "reports/pruebas_estadisticas.csv")


def v_alerta():
    _existe(RAIZ / "reports/alerta_clasificador.csv")


def v_operativo():
    _existe(*[RAIZ / f"models/operativo_rf_{h}h.joblib" for h in (1, 3, 6)])


def v_powerbi():
    archivos = list((RAIZ / "dashboard/datos").glob("*.csv"))
    assert len(archivos) >= 12, f"se esperaban 12 tablas, hay {len(archivos)}"
    e = pd.read_csv(RAIZ / "dashboard/datos/eventos_crecientes.csv")
    assert len(e) > 50, "muy pocas crecientes exportadas"


def v_pronostico():
    _existe(RAIZ / "reports/pronostico_actual.json")


ETAPAS = [
    # nombre, comando, validación, pesada (se omite con --rapido)
    ("carga", ["src/etl/cargar_crudos.py"], v_carga, False),
    ("diagnostico", ["src/etl/diagnostico_calidad.py"], v_diagnostico, False),
    ("limpieza", ["src/etl/procesar.py"], v_limpieza, False),
    ("imputacion", ["src/etl/evaluar_imputacion.py"], v_imputacion, True),
    ("modelos", ["src/models/entrenar.py"], v_modelos, True),
    ("estadistica", ["src/models/pruebas_estadisticas.py"], v_estadistica, True),
    ("alerta", ["src/models/alerta_clasificador.py"], v_alerta, True),
    ("operativo", ["src/pronosticar.py", "entrenar"], v_operativo, False),
    ("powerbi", ["src/dashboard/exportar_powerbi.py"], v_powerbi, False),
    ("pronostico", ["src/pronosticar.py", "pronosticar"], v_pronostico, False),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    nombres = [e[0] for e in ETAPAS]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", choices=nombres)
    ap.add_argument("--solo", choices=nombres)
    ap.add_argument("--rapido", action="store_true", help="omite reentrenamiento de la fase 2 y experimentos")
    a = ap.parse_args()

    etapas = ETAPAS
    if a.solo:
        etapas = [e for e in ETAPAS if e[0] == a.solo]
    elif a.desde:
        etapas = ETAPAS[nombres.index(a.desde):]
    if a.rapido:
        etapas = [e for e in etapas if not e[3]]

    LOGS.mkdir(exist_ok=True)
    log = LOGS / f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
    t_total = time.time()
    with open(log, "w", encoding="utf-8") as fl:
        for i, (nombre, cmd, validar, _) in enumerate(etapas, 1):
            print(f"[{i}/{len(etapas)}] {nombre} ...", end=" ", flush=True)
            fl.write(f"\n===== {nombre}: {' '.join(cmd)} =====\n")
            t0 = time.time()
            r = subprocess.run([PY, *cmd], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
            fl.write(r.stdout + r.stderr)
            if r.returncode != 0:
                print("ERROR")
                print(r.stderr[-2000:])
                print(f"Flujo detenido en '{nombre}'. Log: {log.relative_to(RAIZ)}")
                sys.exit(1)
            try:
                validar()
            except AssertionError as e:
                print(f"VALIDACIÓN FALLIDA: {e}")
                fl.write(f"VALIDACIÓN FALLIDA: {e}\n")
                print(f"Flujo detenido en '{nombre}'. Log: {log.relative_to(RAIZ)}")
                sys.exit(1)
            print(f"ok ({time.time() - t0:.0f} s)")
            fl.write(f"-- ok en {time.time() - t0:.0f} s\n")
    print(f"\nFlujo completo en {(time.time() - t_total) / 60:.1f} min. Log: {log.relative_to(RAIZ)}")
    if any(e[0] == "pronostico" for e in etapas):
        print((RAIZ / "reports/pronostico_actual.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
