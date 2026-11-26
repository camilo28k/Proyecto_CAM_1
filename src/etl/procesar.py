"""Etapa 3 del ETL: aplica el control de calidad a las estaciones seleccionadas y
produce el dataset final horario.

Entradas : data/interim/<estacion>_crudo.parquet   (de cargar_crudos.py)
Salidas  : data/processed/<estacion>_procesado.parquet
           data/processed/dataset_modelo.parquet  (La Lindosa + Los Micos, alineados)
           data/processed/dataset_modelo.csv      (mismo contenido, para Power BI)
           reports/calidad_antes_despues.csv, reports/bitacora_limpieza.csv
           reports/figures/limpieza_<estacion>.png

Uso: python src/etl/procesar.py
"""
from pathlib import Path
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calidad as cq  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
INTERIM = RAIZ / "data" / "interim"
PROC = RAIZ / "data" / "processed"
REP = RAIZ / "reports"
FIG = REP / "figures"
ESTACIONES = ["La_Lindosa", "Los_Micos"]
INICIO, FIN = "2017-01-01", "2025-12-31 23:00"
REGISTROS_HORA = {"MAIGRAI": 1, "MeerKAD": 12}
COBERTURA_MIN_LLUVIA = 0.5   # una hora con < 50 % de los registros esperados no tiene lluvia confiable


def horario(df: pd.DataFrame) -> pd.DataFrame:
    g = df.set_index("fecha_hora").resample("1h")
    h = pd.DataFrame({
        "nivel_m": g["nivel_m"].mean(),
        "nivel_max_m": g["nivel_m"].max(),
        "lluvia_mm": g["lluvia_mm"].sum(min_count=1),
    })
    if "temperatura_c" in df:
        h["temperatura_c"] = g["temperatura_c"].mean()
    esperados = g["fuente"].first().map(REGISTROS_HORA)
    cobertura = g["lluvia_mm"].count() / esperados
    h.loc[cobertura < COBERTURA_MIN_LLUVIA, "lluvia_mm"] = np.nan
    h["fuente"] = g["fuente"].first()
    return h.reindex(pd.date_range(INICIO, FIN, freq="h", name="fecha_hora"))


def metricas(h: pd.DataFrame, etapa: str, estacion: str) -> dict:
    n = h["nivel_m"]
    na = n.isna()
    g = (na != na.shift()).cumsum()
    hu = na.groupby(g).sum()[na.groupby(g).first()]
    return {"estacion": estacion, "etapa": etapa,
            "nivel_completitud_pct": round(100 * n.notna().mean(), 2),
            "lluvia_completitud_pct": round(100 * h["lluvia_mm"].notna().mean(), 2),
            "n_huecos_nivel": int(len(hu)), "huecos_<=6h": int((hu <= 6).sum()),
            "nivel_min": round(n.min(), 3), "nivel_max": round(n.max(), 3),
            "nivel_media": round(n.mean(), 3)}


def procesar_estacion(e: str):
    crudo = pd.read_parquet(INTERIM / f"{e}_crudo.parquet")
    crudo = crudo[(crudo.fecha_hora >= INICIO) & (crudo.fecha_hora <= FIN + ":59")].reset_index(drop=True)
    bit = {"estacion": e, "registros_crudos": len(crudo),
           "nivel_nulos_crudos": int(crudo.nivel_m.isna().sum())}
    antes = horario(crudo)

    df, c = cq.control_rangos(crudo)
    bit["rangos_quitados"] = sum(c.values())
    df, c = cq.quitar_picos_aislados(df)
    bit["picos_quitados"] = c
    df, c = cq.quitar_sensor_pegado(df)
    bit["pegado_tramos"], bit["pegado_registros"] = c["tramos"], c["registros"]
    df, c = cq.rellenar_mesetas(df)
    bit["mesetas_rellenadas"] = c

    h = horario(df)
    h, c = cq.imputar_huecos_cortos(h)
    bit["horas_imputadas"] = c
    h.to_parquet(PROC / f"{e}_procesado.parquet")
    return antes, h, bit


def figura(e, antes, despues):
    fig, axs = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
    axs[0].plot(antes.index, antes.nivel_m, lw=.4, color="gray")
    axs[0].set_title(f"{e}: nivel horario ANTES de la limpieza")
    axs[1].plot(despues.index, despues.nivel_m, lw=.4)
    imp = despues[despues.nivel_m_imputado]
    axs[1].scatter(imp.index, imp.nivel_m, s=3, color="red", label="imputado")
    axs[1].set_title(f"{e}: nivel horario DESPUÉS (rojo = imputado)")
    axs[1].legend(loc="upper right")
    for a in axs:
        a.set_ylabel("m")
    fig.tight_layout()
    fig.savefig(FIG / f"limpieza_{e}.png", dpi=110)
    plt.close(fig)


def main():
    PROC.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    comp, bits, finales = [], [], {}
    for e in ESTACIONES:
        antes, h, bit = procesar_estacion(e)
        comp += [metricas(antes, "antes", e), metricas(h, "despues", e)]
        bits.append(bit)
        finales[e] = h
        figura(e, antes, h)
        print(bit)
    pd.DataFrame(comp).to_csv(REP / "calidad_antes_despues.csv", index=False)
    pd.DataFrame(bits).to_csv(REP / "bitacora_limpieza.csv", index=False)
    print(pd.DataFrame(comp).to_string())

    L, M = finales["La_Lindosa"], finales["Los_Micos"]
    ds = pd.DataFrame({
        "nivel_lindosa_m": L.nivel_m, "nivel_max_lindosa_m": L.nivel_max_m,
        "nivel_lindosa_imputado": L.nivel_m_imputado,
        "lluvia_lindosa_mm": L.lluvia_mm, "temperatura_lindosa_c": L.temperatura_c,
        "nivel_micos_m": M.nivel_m, "nivel_micos_imputado": M.nivel_m_imputado,
        "lluvia_micos_mm": M.lluvia_mm, "temperatura_micos_c": M.temperatura_c,
    })
    ds.to_parquet(PROC / "dataset_modelo.parquet")
    ds.to_csv(PROC / "dataset_modelo.csv", float_format="%.3f")
    print("dataset_modelo:", ds.shape, "| filas con nivel Lindosa:", int(ds.nivel_lindosa_m.notna().sum()))


if __name__ == "__main__":
    main()
