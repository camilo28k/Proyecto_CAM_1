"""Comparación estadística del mejor modelo contra los demás (test 2024-2025).

Los errores horarios están autocorrelacionados (una hora se parece a la siguiente),
lo que viola la independencia que exigen las pruebas. Por eso se usa el ERROR
ABSOLUTO MEDIO DIARIO de cada modelo como unidad de análisis (muestras pareadas
por día).

Para cada horizonte y cada par (mejor, otro):
  1. Shapiro-Wilk sobre las diferencias diarias (normalidad, alfa = 0.05).
  2. Si son normales -> t de Student pareada; si no -> Wilcoxon de rangos con signo.
  3. Corrección de Holm por comparaciones múltiples.

El "mejor" modelo de cada horizonte es el de menor error absoluto medio diario en test.
(Los modelos ponderados reducen el error en crecientes pero empeoran mucho el resto
del tiempo; ese compromiso se discute aparte en el informe de la fase 2.)

Salida: reports/pruebas_estadisticas.csv
Uso:    python src/models/pruebas_estadisticas.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parents[2]
REP = RAIZ / "reports"
ALFA = 0.05


def holm(p):
    p = np.asarray(p)
    orden = np.argsort(p)
    ajustado = np.empty_like(p)
    acum = 0
    for rango, i in enumerate(orden):
        acum = max(acum, min(1, (len(p) - rango) * p[i]))
        ajustado[i] = acum
    return ajustado


def main():
    pr = pd.read_parquet(REP / "predicciones_test.parquet")

    pr["error_abs_cm"] = 100 * (pr.nivel_real_m - pr.nivel_pred_m).abs()
    pr["dia"] = pr.fecha_hora_objetivo.dt.floor("D")
    filas = []
    for h, g in pr.groupby("h"):
        diario = g.pivot_table(index="dia", columns="modelo", values="error_abs_cm", aggfunc="mean").dropna()
        mejor = diario.mean().idxmin()
        bloque = []
        for otro in diario.columns.drop(mejor):
            dif = diario[otro] - diario[mejor]          # > 0 => el mejor se equivoca menos
            w, p_sw = stats.shapiro(dif)
            normal = p_sw > ALFA
            if normal:
                est, p = stats.ttest_rel(diario[otro], diario[mejor])
                prueba = "t pareada"
            else:
                est, p = stats.wilcoxon(diario[otro], diario[mejor])
                prueba = "Wilcoxon"
            bloque.append({"h": h, "mejor": mejor, "comparado_con": otro, "dias": len(dif),
                           "mae_diario_mejor_cm": diario[mejor].mean(), "mae_diario_otro_cm": diario[otro].mean(),
                           "shapiro_W": w, "shapiro_p": p_sw, "normal": normal, "prueba": prueba,
                           "estadistico": est, "p_valor": p})
        p_aj = holm([b["p_valor"] for b in bloque])
        for b, pa in zip(bloque, p_aj):
            b["p_holm"] = pa
            b["diferencia_significativa"] = pa < ALFA
        filas += bloque
    r = pd.DataFrame(filas)
    r.to_csv(REP / "pruebas_estadisticas.csv", index=False)
    pd.set_option("display.width", 250)
    print(r.round(4).to_string())


if __name__ == "__main__":
    main()
