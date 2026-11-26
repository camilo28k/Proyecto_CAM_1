"""Enfoque de ALERTA: clasificador de probabilidad de creciente.

Pregunta que responde: "¿la anomalía del nivel en La Lindosa superará 0.5 m
(alerta amarilla) en algún momento de las próximas h horas?"

Experimento A (2018-2025, sin El Batán):
  train 2018-2022, val 2023 (elige umbral de probabilidad que maximiza CSI), test 2024-2025.
Experimento B (2023-2025, efecto de la lluvia de El Batán - parte alta de la cuenca):
  El Batán solo tiene lluvia confiable desde 2023, así que se comparan dos modelos
  idénticos con y sin sus variables: train 2023-01..2024-06 (umbral por validación
  cruzada temporal interna), test 2024-07..2025-12.

Métricas: POD, FAR, CSI sobre todas las horas y sobre los INICIOS (ahora sin alerta).
Referencia: persistencia (alerta si ya hay alerta ahora).

Salidas: reports/alerta_clasificador.csv, reports/alerta_probabilidades_test.parquet,
         models/alerta_xgb_<h>h.json
Uso: python src/models/alerta_clasificador.py
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import features as F  # noqa: E402
import metricas as M  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
REP = RAIZ / "reports"
MOD = RAIZ / "models"
SEMILLA = 42
U = F.UMBRALES_ALERTA["amarilla"]
PARAMS = dict(n_estimators=600, learning_rate=0.03, max_depth=5, subsample=0.8, colsample_bytree=0.8,
              min_child_weight=5, random_state=SEMILLA, eval_metric="aucpr")


def objetivo(f, h):
    """1 si la anomalía (respecto a la base de AHORA) llega a >= U en (t, t+h]."""
    futuros = pd.concat([f["nivel"].shift(-k) for k in range(1, h + 1)], axis=1).max(axis=1)
    y = (futuros - f["base"] >= U).astype(float)
    return y.where(futuros.notna())


def variables_batan(idx):
    B = pd.read_parquet(RAIZ / "data" / "interim" / "El_Batan_horario.parquet")["lluvia_mm"].reindex(idx)
    return pd.DataFrame({f"lluvia_B_{k}h": B.rolling(k, min_periods=k).sum() for k in [1, 3, 6, 12, 24]})


def elegir_umbral(y, p):
    mejor = (-1, 0.5)
    for u in np.arange(0.05, 0.95, 0.01):
        csi = M.contingencia(y, p >= u)[2]
        if csi > mejor[0]:
            mejor = (csi, u)
    return mejor[1]


def medir(nombre, exp, h, y, alerta, actual):
    pod, far, csi, n = M.contingencia(y == 1, alerta)
    ini = actual < U
    pod_i, far_i, csi_i, n_i = M.contingencia(y[ini] == 1, alerta[ini])
    return {"experimento": exp, "h": h, "modelo": nombre, "pod": pod, "far": far, "csi": csi, "horas_alerta": n,
            "pod_inicio": pod_i, "far_inicio": far_i, "csi_inicio": csi_i, "horas_inicio": n_i}


def entrenar(Xtr, ytr, Xva, yva):
    spw = (ytr == 0).sum() / max(1, (ytr == 1).sum())
    m = xgb.XGBClassifier(**PARAMS, scale_pos_weight=spw)
    m.fit(Xtr, ytr, verbose=False)
    return m, elegir_umbral(yva.to_numpy() == 1, m.predict_proba(Xva)[:, 1])


def main():
    MOD.mkdir(exist_ok=True)
    f = F.cargar()
    cols = F.variables(f)
    fb = pd.concat([f, variables_batan(f.index)], axis=1)
    cols_b = cols + [c for c in fb.columns if c.startswith("lluvia_B_")]
    filas, probs = [], []
    for h in F.HORIZONTES:
        y = objetivo(f, h)
        # ---------------- Experimento A
        v = f.assign(y=y).dropna(subset=cols + ["y", "base"])
        tr, va, te = (F.particion(v, k) for k in ["train", "val", "test"])
        m, umbral = entrenar(tr[cols], tr.y, va[cols], va.y)
        trva = pd.concat([tr, va])
        spw = (trva.y == 0).sum() / (trva.y == 1).sum()
        final = xgb.XGBClassifier(**PARAMS, scale_pos_weight=spw).fit(trva[cols], trva.y, verbose=False)
        final.save_model(MOD / f"alerta_xgb_{h}h.json")
        p = final.predict_proba(te[cols])[:, 1]
        filas.append(medir("persistencia", "A", h, te.y.to_numpy(), te.anomalia.to_numpy() >= U, te.anomalia.to_numpy()))
        filas.append(medir(f"xgb_clasificador(u={umbral:.2f})", "A", h, te.y.to_numpy(), p >= umbral, te.anomalia.to_numpy()))
        probs.append(pd.DataFrame({"fecha_hora": te.index, "h": h, "probabilidad": p, "umbral": umbral,
                                   "alerta_pred": p >= umbral, "alerta_real": te.y.to_numpy() == 1,
                                   "anomalia_actual_m": te.anomalia.to_numpy()}))
        # ---------------- Experimento B (con / sin El Batán, mismas filas)
        vb = fb.assign(y=y).dropna(subset=cols_b + ["y", "base"]).loc["2023-01-01":"2025-12-31"]
        trb, teb = vb.loc[:"2024-06-30 23:00"], vb.loc["2024-07-01":]
        corte = trb.index[int(len(trb) * 0.75)]
        for nombre, cc in [("xgb_sin_batan", cols), ("xgb_con_batan", cols_b)]:
            a, b = trb.loc[:corte], trb.loc[corte:]
            _, umbral = entrenar(a[cc], a.y, b[cc], b.y)
            spw = (trb.y == 0).sum() / max(1, (trb.y == 1).sum())
            mb = xgb.XGBClassifier(**PARAMS, scale_pos_weight=spw).fit(trb[cc], trb.y, verbose=False)
            pb = mb.predict_proba(teb[cc])[:, 1]
            filas.append(medir(f"{nombre}(u={umbral:.2f})", "B", h, teb.y.to_numpy(), pb >= umbral,
                               teb.anomalia.to_numpy()))
        filas.append(medir("persistencia", "B", h, teb.y.to_numpy(), teb.anomalia.to_numpy() >= U, teb.anomalia.to_numpy()))
        print(f"h={h} listo (filas B: train {len(trb)}, test {len(teb)})")
    r = pd.DataFrame(filas)
    r.to_csv(REP / "alerta_clasificador.csv", index=False)
    pd.concat(probs).to_parquet(REP / "alerta_probabilidades_test.parquet", index=False)
    pd.set_option("display.width", 250)
    print(r.round(3).to_string())


if __name__ == "__main__":
    main()
