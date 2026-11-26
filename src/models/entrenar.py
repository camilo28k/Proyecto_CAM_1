"""Entrenamiento y evaluación de modelos de pronóstico del nivel en La Lindosa.

Modelos: persistencia, ridge, random_forest, xgboost, xgboost_ponderado, lstm.
Para cada horizonte h (1, 3, 6 h):
  1. Selección de hiperparámetros con train (2018-2022) evaluando en val (2023).
  2. Reentrenamiento con train+val (excepto LSTM: usa val para early stopping).
  3. Evaluación en test (2024-2025), sobre las MISMAS filas para todos los modelos.

Salidas:
  reports/modelos_validacion.csv      desempeño de cada configuración en val
  reports/modelos_test.csv            métricas finales en test
  reports/predicciones_test.parquet   predicciones horarias en test (para el dashboard)
  models/                             modelos entrenados

Uso: python src/models/entrenar.py
"""
from pathlib import Path
import sys
import json
import time
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import features as F  # noqa: E402
import metricas as M  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
REP = RAIZ / "reports"
MOD = RAIZ / "models"
SEMILLA = 42
SEQ = 24  # horas de historia que ve la LSTM
np.random.seed(SEMILLA)
torch.manual_seed(SEMILLA)
torch.set_num_threads(4)


# ---------------------------------------------------------------- modelos tabulares
def grilla():
    return {
        "ridge": [{"alpha": a} for a in [0.1, 1, 10, 100]],
        "random_forest": [{"n_estimators": 300, "max_depth": md, "min_samples_leaf": ml, "n_jobs": -1,
                           "random_state": SEMILLA} for md in [10, 20] for ml in [5, 20]],
        "xgboost": [{"n_estimators": 2000, "learning_rate": 0.03, "max_depth": md, "subsample": 0.8,
                     "colsample_bytree": 0.8, "min_child_weight": mcw, "random_state": SEMILLA,
                     "early_stopping_rounds": 100} for md in [4, 6, 8] for mcw in [1, 10]],
    }


def peso(y):
    """Más peso a las horas en que el nivel cambia > 10 cm (crecientes y recesiones)."""
    return 1 + 20 * (np.abs(y) > 0.10)


def crear(nombre, p):
    if nombre == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=p["alpha"]))
    if nombre == "random_forest":
        return RandomForestRegressor(**p)
    return xgb.XGBRegressor(**p)


def ajustar(nombre, p, Xtr, ytr, Xva=None, yva=None, ponderado=False):
    mod = crear(nombre, p)
    w = peso(ytr) if ponderado else None
    if nombre == "xgboost":
        if Xva is not None:
            mod.fit(Xtr, ytr, sample_weight=w, eval_set=[(Xva, yva)],
                    sample_weight_eval_set=[peso(yva)] if ponderado else None, verbose=False)
        else:
            mod.fit(Xtr, ytr, sample_weight=w, verbose=False)
    elif nombre == "ridge":
        mod.fit(Xtr, ytr, ridge__sample_weight=w)
    else:
        mod.fit(Xtr, ytr, sample_weight=w)
    return mod


# ---------------------------------------------------------------- LSTM
class RedLSTM(nn.Module):
    def __init__(self, n_in, oculto=64, capas=2, drop=0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_in, oculto, capas, batch_first=True, dropout=drop)
        self.cabeza = nn.Sequential(nn.Linear(oculto, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.cabeza(out[:, -1, :]).squeeze(-1)


def ventanas(X_todo: np.ndarray, posiciones: np.ndarray) -> np.ndarray:
    idx = posiciones[:, None] + np.arange(-SEQ + 1, 1)[None, :]
    return X_todo[idx]


def posiciones_lstm(f, filas_idx):
    """Posiciones (en f) de filas cuyas SEQ horas previas tienen todas las variables."""
    completo = f[F.variables(f)].notna().all(axis=1).to_numpy()
    ok_ventana = pd.Series(completo).rolling(SEQ).sum().to_numpy() == SEQ
    pos = f.index.get_indexer(filas_idx)
    return pos[ok_ventana[pos]]


def entrenar_lstm(Xs, ytr_pos, ytr, yva_pos, yva, epocas=60, paciencia=8, ponderado=True):
    red = RedLSTM(Xs.shape[1])
    opt = torch.optim.Adam(red.parameters(), lr=1e-3)
    Xva_t = torch.tensor(ventanas(Xs, yva_pos), dtype=torch.float32)
    yva_t = torch.tensor(yva, dtype=torch.float32)
    wtr = torch.tensor(peso(ytr) if ponderado else np.ones_like(ytr), dtype=torch.float32)
    mejor, mejor_estado, sin_mejora = np.inf, None, 0
    rng = np.random.default_rng(SEMILLA)
    for ep in range(epocas):
        red.train()
        orden = rng.permutation(len(ytr_pos))
        for i in range(0, len(orden), 256):
            b = orden[i:i + 256]
            xb = torch.tensor(ventanas(Xs, ytr_pos[b]), dtype=torch.float32)
            yb = torch.tensor(ytr[b], dtype=torch.float32)
            opt.zero_grad()
            perdida = (wtr[b] * (red(xb) - yb) ** 2).mean()
            perdida.backward()
            nn.utils.clip_grad_norm_(red.parameters(), 1.0)
            opt.step()
        red.eval()
        with torch.no_grad():
            pv = red(Xva_t)
            val = torch.sqrt(((pv - yva_t) ** 2).mean()).item()
        if val < mejor - 1e-5:
            mejor, sin_mejora = val, 0
            mejor_estado = {k: v.clone() for k, v in red.state_dict().items()}
        else:
            sin_mejora += 1
            if sin_mejora >= paciencia:
                break
    red.load_state_dict(mejor_estado)
    red.eval()
    return red, mejor, ep + 1


def predecir_lstm(red, Xs, pos):
    with torch.no_grad():
        out = []
        for i in range(0, len(pos), 4096):
            out.append(red(torch.tensor(ventanas(Xs, pos[i:i + 4096]), dtype=torch.float32)).numpy())
    return np.concatenate(out)


# ---------------------------------------------------------------- principal
def main():
    MOD.mkdir(exist_ok=True)
    f = F.cargar()
    cols = F.variables(f)
    # estandarización para la LSTM con estadísticos SOLO de train
    tr_all = F.particion(f, "train")[cols]
    mu, sd = tr_all.mean(), tr_all.std().replace(0, 1)
    Xs = ((f[cols] - mu) / sd).to_numpy(dtype=np.float32)

    res_val, res_test, preds = [], [], []
    for h in F.HORIZONTES:
        t0 = time.time()
        y = f"y_delta_{h}h"
        v = F.filas_validas(f, h)
        tr, va, te = (F.particion(v, k) for k in ["train", "val", "test"])
        # filas de test comunes a todos los modelos (las que la LSTM puede ver)
        te_pos = posiciones_lstm(f, te.index)
        te = te.loc[f.index[te_pos]]
        trva = pd.concat([tr, va])

        pred_test = {"persistencia": np.zeros(len(te))}
        res_val.append({"h": h, "modelo": "persistencia", "config": "-",
                        "rmse_delta_cm": 100 * M.rmse(va[y], 0 * va[y])})

        for nombre, configs in grilla().items():
            for ponderado in ([False, True] if nombre == "xgboost" else [False]):
                etiqueta = nombre + ("_ponderado" if ponderado else "")
                mejor = (np.inf, None, None)
                for p in configs:
                    mod = ajustar(nombre, p, tr[cols], tr[y], va[cols], va[y], ponderado)
                    e = M.rmse(va[y], mod.predict(va[cols]))
                    extra = {"best_iteration": int(mod.best_iteration)} if nombre == "xgboost" else {}
                    res_val.append({"h": h, "modelo": etiqueta, "config": json.dumps({**p, **extra}),
                                    "rmse_delta_cm": 100 * e})
                    if e < mejor[0]:
                        mejor = (e, p, extra)
                p = dict(mejor[1])
                if nombre == "xgboost":
                    p.pop("early_stopping_rounds")
                    p["n_estimators"] = mejor[2]["best_iteration"] + 1
                final = ajustar(nombre, p, trva[cols], trva[y], ponderado=ponderado)
                joblib.dump(final, MOD / f"{etiqueta}_{h}h.joblib")
                pred_test[etiqueta] = final.predict(te[cols])

        # LSTM (ponderada igual que xgboost_ponderado)
        tr_pos = posiciones_lstm(f, tr.index)
        va_pos = posiciones_lstm(f, va.index)
        red, e_val, ep = entrenar_lstm(Xs, tr_pos, f[y].to_numpy()[tr_pos].astype(np.float32),
                                       va_pos, f[y].to_numpy()[va_pos].astype(np.float32))
        res_val.append({"h": h, "modelo": "lstm", "config": json.dumps({"seq": SEQ, "oculto": 64, "capas": 2,
                                                                         "epocas": ep}),
                        "rmse_delta_cm": 100 * e_val})
        torch.save(red.state_dict(), MOD / f"lstm_{h}h.pt")
        pred_test["lstm"] = predecir_lstm(red, Xs, te_pos)

        # evaluación en test
        real_nivel = te["nivel"] + te[y]
        for nombre, pdelta in pred_test.items():
            pnivel = te["nivel"] + pdelta
            met = M.evaluar(te[y].to_numpy(), np.asarray(pdelta), real_nivel.to_numpy(), pnivel.to_numpy(),
                            te["base"].to_numpy(), te["anomalia"].to_numpy())
            res_test.append({"h": h, "modelo": nombre, **met})
            preds.append(pd.DataFrame({"fecha_hora_origen": te.index, "h": h, "modelo": nombre,
                                       "fecha_hora_objetivo": te.index + pd.Timedelta(hours=h),
                                       "nivel_actual_m": te["nivel"].to_numpy(),
                                       "nivel_real_m": real_nivel.to_numpy(), "nivel_pred_m": pnivel.to_numpy(),
                                       "base_m": te["base"].to_numpy()}))
        print(f"h={h}: listo en {time.time() - t0:.0f}s")

    pd.DataFrame(res_val).to_csv(REP / "modelos_validacion.csv", index=False)
    rt = pd.DataFrame(res_test)
    rt.to_csv(REP / "modelos_test.csv", index=False)
    pd.concat(preds).to_parquet(REP / "predicciones_test.parquet", index=False)
    json.dump({"variables": cols, "media": mu.to_dict(), "desv": sd.to_dict()},
              open(MOD / "escalado_lstm.json", "w"), indent=1)
    pd.set_option("display.width", 250)
    print(rt.round(3).to_string())


if __name__ == "__main__":
    main()
