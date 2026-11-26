"""Métricas de evaluación de los pronósticos."""
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import features as F  # noqa: E402


def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def mae(a, b):
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def nse(obs, sim):
    """Nash-Sutcliffe: 1 = perfecto, 0 = igual que predecir la media, < 0 = peor que la media."""
    obs, sim = np.asarray(obs), np.asarray(sim)
    return float(1 - np.sum((obs - sim) ** 2) / np.sum((obs - obs.mean()) ** 2))


def contingencia(real_alerta, pred_alerta):
    """POD (probabilidad de detección), FAR (tasa de falsas alarmas), CSI (índice crítico de éxito)."""
    r, p = np.asarray(real_alerta, bool), np.asarray(pred_alerta, bool)
    tp, fp, fn = int((r & p).sum()), int((~r & p).sum()), int((r & ~p).sum())
    pod = tp / (tp + fn) if tp + fn else np.nan
    far = fp / (tp + fp) if tp + fp else np.nan
    csi = tp / (tp + fp + fn) if tp + fp + fn else np.nan
    return pod, far, csi, tp + fn


def evaluar(y_delta, p_delta, nivel_real, nivel_pred, base, anomalia_actual):
    an_real = nivel_real - base
    an_pred = nivel_pred - base
    umbral = F.UMBRALES_ALERTA["amarilla"]
    ra, pa = an_real >= umbral, an_pred >= umbral
    pod, far, csi, n_al = contingencia(ra, pa)
    # inicio de crecientes: ahora NO hay alerta, en h horas SÍ -> lo que realmente sirve para avisar
    ini = anomalia_actual < umbral
    pod_i, far_i, csi_i, n_ini = contingencia(ra[ini], pa[ini])
    ev = ra
    return {
        "rmse_cm": 100 * rmse(nivel_real, nivel_pred),
        "mae_cm": 100 * mae(nivel_real, nivel_pred),
        "nse_nivel": nse(nivel_real, nivel_pred),
        "nse_delta": nse(y_delta, p_delta),
        "rmse_crecientes_cm": 100 * rmse(nivel_real[ev], nivel_pred[ev]) if ev.any() else np.nan,
        "pod": pod, "far": far, "csi": csi, "horas_alerta": n_al,
        "pod_inicio": pod_i, "far_inicio": far_i, "csi_inicio": csi_i, "horas_inicio": n_ini,
    }
