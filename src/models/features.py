"""Construcción de variables (features), objetivo y partición temporal.

Idea central: por la deriva de la línea base del nivel (ver FASE-1) los modelos NO
predicen el nivel absoluto sino el CAMBIO de nivel en h horas:
    delta_h(t) = nivel(t+h) - nivel(t)
y el nivel pronosticado es nivel(t) + delta_pred. Las alertas se definen sobre la
ANOMALÍA = nivel - línea base (mediana móvil de los 30 días anteriores).

Todas las variables usan solo información disponible en el instante t (sin fuga de futuro).
"""
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DATASET = RAIZ / "data" / "processed" / "dataset_modelo.parquet"

HORIZONTES = [1, 3, 6]
BASE_VENTANA = "30D"
BASE_MIN_HORAS = 24 * 7

# Umbrales de alerta sobre la anomalía (m) - definidos por el proyecto, ver FASE-2
UMBRALES_ALERTA = {"amarilla": 0.5, "naranja": 1.0, "roja": 1.5}

PARTICION = {
    "train": ("2018-01-01", "2022-12-31 23:00"),
    "val": ("2023-01-01", "2023-12-31 23:00"),
    "test": ("2024-01-01", "2025-12-31 23:00"),
}


def linea_base(nivel: pd.Series) -> pd.Series:
    """Mediana de los 30 días ANTERIORES (excluye la hora actual)."""
    return nivel.shift(1).rolling(BASE_VENTANA, min_periods=BASE_MIN_HORAS).median()


def construir(d: pd.DataFrame) -> pd.DataFrame:
    n = d["nivel_lindosa_m"]
    m = d["nivel_micos_m"]
    f = pd.DataFrame(index=d.index)
    base = linea_base(n)
    f["nivel"] = n
    f["base"] = base
    f["anomalia"] = n - base
    f["pico_en_hora"] = d["nivel_max_lindosa_m"] - n
    for k in [1, 2, 3, 6, 12]:
        f[f"dnivel_{k}h"] = n - n.shift(k)
    for k in [1, 2, 3, 6, 12, 24, 72]:
        f[f"lluvia_L_{k}h"] = d["lluvia_lindosa_mm"].rolling(k, min_periods=k).sum()
    for k in [1, 3, 6, 24]:
        f[f"lluvia_M_{k}h"] = d["lluvia_micos_mm"].rolling(k, min_periods=k).sum()
    f["anomalia_micos"] = m - linea_base(m)
    for k in [1, 3]:
        f[f"dnivel_micos_{k}h"] = m - m.shift(k)
    hora = d.index.hour
    dia = d.index.day_of_year
    f["hora_sin"], f["hora_cos"] = np.sin(2 * np.pi * hora / 24), np.cos(2 * np.pi * hora / 24)
    f["dia_sin"], f["dia_cos"] = np.sin(2 * np.pi * dia / 365.25), np.cos(2 * np.pi * dia / 365.25)
    for h in HORIZONTES:
        futuro = n.shift(-h)
        imp_futuro = d["nivel_lindosa_imputado"].shift(-h).fillna(True).astype(bool)
        f[f"y_delta_{h}h"] = (futuro - n).where(~imp_futuro)   # objetivo solo con dato MEDIDO
    return f



_AUX = {"nivel", "base"}


def variables(f: pd.DataFrame) -> list:
    return [c for c in f.columns if not c.startswith("y_") and c not in _AUX]


def cargar() -> pd.DataFrame:
    d = pd.read_parquet(DATASET)
    return construir(d)


def particion(f: pd.DataFrame, nombre: str) -> pd.DataFrame:
    a, b = PARTICION[nombre]
    return f.loc[a:b]


def filas_validas(f: pd.DataFrame, h: int) -> pd.DataFrame:
    """Filas con todas las variables y el objetivo del horizonte h disponibles."""
    cols = variables(f) + ["nivel", "base", f"y_delta_{h}h"]
    return f.dropna(subset=cols)


def clase_alerta(anomalia) -> np.ndarray:
    a = np.asarray(anomalia)
    c = np.zeros(a.shape, dtype=int)
    for i, (_, u) in enumerate(UMBRALES_ALERTA.items(), start=1):
        c[a >= u] = i
    return c
