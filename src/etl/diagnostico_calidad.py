"""Diagnóstico de calidad por estación (sobre series horarias de data/interim).

Genera en reports/:
  calidad_por_anio.csv      completitud % de nivel y lluvia por estación y año
  calidad_resumen.csv       indicadores globales por estación (huecos, rachas, estadísticos)
  figures/completitud_nivel.png, figures/series_nivel.png

Uso:  python src/etl/diagnostico_calidad.py
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[2]
INTERIM = RAIZ / "data" / "interim"
REP = RAIZ / "reports"
FIG = REP / "figures"
ESTACIONES = ["El_Batan", "La_Lindosa", "Las_Juntas", "Los_Micos", "Puente_Bruselas", "San_Benito"]


def huecos(s: pd.Series) -> pd.Series:
    """Longitudes (horas) de cada tramo consecutivo de NaN."""
    na = s.isna()
    grupos = (na != na.shift()).cumsum()
    return na.groupby(grupos).sum()[na.groupby(grupos).first()]


def rachas_constantes(s: pd.Series, minimo: int = 24) -> int:
    """Horas dentro de tramos >= `minimo` horas con exactamente el mismo valor (sensor pegado)."""
    v = s.dropna()
    g = (v != v.shift()).cumsum()
    largo = v.groupby(g).transform("size")
    return int((largo >= minimo).sum())


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    por_anio, resumen, series = [], [], {}
    for e in ESTACIONES:
        h = pd.read_parquet(INTERIM / f"{e}_horario.parquet")
        h = h.loc["2017-01-01":"2025-12-31 23:00"]
        h = h.reindex(pd.date_range("2017-01-01", "2025-12-31 23:00", freq="h"))
        series[e] = h["nivel_m"]
        for anio, g in h.groupby(h.index.year):
            por_anio.append({"estacion": e, "anio": anio,
                             "nivel_pct": round(100 * g.nivel_m.notna().mean(), 1),
                             "lluvia_pct": round(100 * g.lluvia_mm.notna().mean(), 1),
                             "ambos_pct": round(100 * (g.nivel_m.notna() & g.lluvia_mm.notna()).mean(), 1)})
        n = h["nivel_m"]
        hu = huecos(n)
        resumen.append({
            "estacion": e,
            "nivel_completitud_2017_2025_pct": round(100 * n.notna().mean(), 1),
            "nivel_completitud_2021_2025_pct": round(100 * n.loc["2021":].notna().mean(), 1),
            "lluvia_completitud_2021_2025_pct": round(100 * h.lluvia_mm.loc["2021":].notna().mean(), 1),
            "ambos_2021_2025_pct": round(100 * (n.notna() & h.lluvia_mm.notna()).loc["2021":].mean(), 1),
            "n_huecos": int(len(hu)),
            "huecos_<=6h": int((hu <= 6).sum()),
            "huecos_>7dias": int((hu > 168).sum()),
            "hueco_max_dias": round(hu.max() / 24, 1) if len(hu) else 0,
            "horas_nivel_constante_>=24h": rachas_constantes(n),
            "nivel_min": n.min(), "nivel_p50": n.median(), "nivel_p99": n.quantile(.99),
            "nivel_max": n.max(), "nivel_max_inst": h["nivel_max_m"].max(),
            "lluvia_total_mm_2021_2025": round(h.lluvia_mm.loc["2021":].sum(), 0),
            "lluvia_max_horaria_mm": h.lluvia_mm.max(),
        })
    pa = pd.DataFrame(por_anio)
    pa.to_csv(REP / "calidad_por_anio.csv", index=False)
    rs = pd.DataFrame(resumen)
    rs.to_csv(REP / "calidad_resumen.csv", index=False)
    print(pa.pivot(index="estacion", columns="anio", values="nivel_pct").to_string())
    print()
    print(pa.pivot(index="estacion", columns="anio", values="lluvia_pct").to_string())
    print()
    print(rs.T.to_string())

    # Mapa de calor de completitud mensual del nivel
    m = pd.DataFrame({e: s.notna().resample("MS").mean() * 100 for e, s in series.items()})
    fig, ax = plt.subplots(figsize=(14, 3.5))
    im = ax.imshow(m.T.values, aspect="auto", cmap="RdYlGn", vmin=0, vmax=100)
    ax.set_yticks(range(len(m.columns)), m.columns)
    xt = [i for i, d in enumerate(m.index) if d.month == 1]
    ax.set_xticks(xt, [m.index[i].year for i in xt])
    ax.set_title("Completitud mensual del nivel (% de horas con dato)")
    fig.colorbar(im, ax=ax, label="%")
    fig.tight_layout(); fig.savefig(FIG / "completitud_nivel.png", dpi=130); plt.close(fig)

    fig, axs = plt.subplots(len(series), 1, figsize=(14, 12), sharex=True)
    for ax, (e, s) in zip(axs, series.items()):
        ax.plot(s.index, s.values, lw=.4); ax.set_ylabel(e, rotation=0, ha="right")
    axs[0].set_title("Nivel horario (m) por estación, 2017-2025")
    fig.tight_layout(); fig.savefig(FIG / "series_nivel.png", dpi=110); plt.close(fig)


if __name__ == "__main__":
    main()
