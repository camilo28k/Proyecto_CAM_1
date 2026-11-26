"""Experimento: ¿qué método de imputación del nivel horario de La Lindosa es mejor?

Se ocultan artificialmente tramos de nivel REAL (donde sí hay dato) de distintas
duraciones, se imputan con cada método y se compara contra el valor verdadero.

Métodos:
  lineal       interpolación lineal entre el último y el siguiente dato
  constante    repetir el último valor (forward fill)
  micos        regresión lineal desde el nivel de Los Micos, ajustada en una
               ventana de 7 días alrededor del hueco y anclada a los bordes

Salida: reports/evaluacion_imputacion.csv
Uso:    python src/etl/evaluar_imputacion.py   (requiere haber corrido procesar.py)
"""
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "data" / "processed"
REP = RAIZ / "reports"
DURACIONES = [1, 2, 3, 6, 12, 24]
N_POR_DURACION = 300
SEMILLA = 42


def imputar(y, x, i0, i1, metodo):
    """y, x: arrays numpy horarios; hueco = posiciones [i0, i1)."""
    a, b = y[i0 - 1], y[i1]
    k = i1 - i0
    if metodo == "constante":
        return np.full(k, a)
    lin = a + (b - a) * np.arange(1, k + 1) / (k + 1)
    if metodo == "lineal":
        return lin
    # micos: modelo y ~ x en ventana de +-84 h, corregido para empatar en los bordes
    lo, hi = max(0, i0 - 84), min(len(y), i1 + 84)
    ventana = np.r_[lo:i0, i1:hi]
    m = ~np.isnan(y[ventana]) & ~np.isnan(x[ventana])
    if m.sum() < 24 or np.isnan(x[i0 - 1:i1 + 1]).any():
        return lin
    pend, inter = np.polyfit(x[ventana][m], y[ventana][m], 1)
    pred = pend * x[i0 - 1:i1 + 1] + inter
    err_a, err_b = a - pred[0], b - pred[-1]
    corr = err_a + (err_b - err_a) * np.arange(1, k + 1) / (k + 1)
    return pred[1:-1] + corr


def main():
    L = pd.read_parquet(PROC / "La_Lindosa_procesado.parquet")
    M = pd.read_parquet(PROC / "Los_Micos_procesado.parquet").reindex(L.index)
    # solo datos medidos (no imputados) como verdad
    y = L["nivel_m"].where(~L["nivel_m_imputado"]).to_numpy()
    x = M["nivel_m"].where(~M["nivel_m_imputado"]).to_numpy()
    rng = np.random.default_rng(SEMILLA)
    filas = []
    for k in DURACIONES:
        # posiciones donde hay k+2 horas seguidas medidas (para tener bordes)
        ok = pd.Series(~np.isnan(y)).rolling(k + 2).sum().to_numpy() == k + 2
        candidatos = np.where(ok)[0] - (k + 1)  # índice del borde izquierdo
        candidatos = candidatos[candidatos >= 0]
        # muestreo estratificado: tramos normales y tramos que contienen creciente (>= 1.2 m)
        con_crec = np.array([np.nanmax(y[i + 1:i + 1 + k]) >= 1.2 for i in candidatos])
        elegidos = np.concatenate([
            rng.choice(candidatos[~con_crec], size=min(N_POR_DURACION, (~con_crec).sum()), replace=False),
            rng.choice(candidatos[con_crec], size=min(N_POR_DURACION, con_crec.sum()), replace=False),
        ])
        for i in elegidos:
            i0, i1 = i + 1, i + 1 + k
            real = y[i0:i1]
            evento = real.max() >= 1.2  # el tramo incluye nivel de creciente
            for met in ["constante", "lineal", "micos"]:
                p = imputar(y, x, i0, i1, met)
                filas.append({"duracion_h": k, "metodo": met, "evento": evento,
                              "mae": np.mean(np.abs(p - real)), "maxerr": np.max(np.abs(p - real))})
    r = pd.DataFrame(filas)
    tabla = r.groupby(["duracion_h", "metodo"]).agg(mae_cm=("mae", lambda v: 100 * v.mean()),
                                                     err_max_p95_cm=("maxerr", lambda v: 100 * v.quantile(.95))).round(2)
    tabla_ev = r[r.evento].groupby(["duracion_h", "metodo"]).mae.agg(lambda v: 100 * v.mean()).round(2).rename("mae_en_crecientes_cm")
    tabla_no = r[~r.evento].groupby(["duracion_h", "metodo"]).mae.agg(lambda v: 100 * v.mean()).round(2).rename("mae_sin_creciente_cm")
    tabla = tabla.join(tabla_no).join(tabla_ev)
    tabla["n_crecientes"] = r[r.evento & (r.metodo == "lineal")].groupby("duracion_h").size().reindex(tabla.index.get_level_values(0)).values
    tabla.to_csv(REP / "evaluacion_imputacion.csv")
    print(tabla.to_string())


if __name__ == "__main__":
    main()
