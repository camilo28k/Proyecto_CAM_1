"""Etapa 2 del ETL: control de calidad e imputación (funciones puras, probadas en tests/).

Orden de aplicación sobre los registros crudos de una estación:
  1. control_rangos          rangos válidos oficiales de la CAM (PDF de observaciones)
  2. quitar_picos_aislados   un registro que se dispara y vuelve de inmediato
  3. quitar_sensor_pegado    nivel idéntico demasiado tiempo (o mientras llueve)
  4. rellenar_mesetas        restaura huecos cortos con el mismo valor a ambos lados
  5. a_horario               paso horario regular (en cargar_crudos)
  6. imputar_huecos_cortos   interpolación lineal de huecos horarios <= MAX_HUECO_IMPUTABLE_H

Cada función devuelve el DataFrame corregido y un conteo de lo que cambió,
para poder reportar el antes/después.
"""
import numpy as np
import pandas as pd

# Rangos válidos (límites inclusivos) - verificados en "Observaciones <estación>.pdf" de la CAM
RANGOS_CAM = {
    "temperatura_c": (0, 50),
    "humedad_pct": (0, 100),
    "lluvia_mm": (0, 100),
    "radiacion_wm2": (0, 2000),
    "dir_viento_grados": (0, 361),
    "vel_viento_ms": (0, 90),
    "nivel_m": (0, np.inf),
    "presion_hpa": (500, 1100),
}

# Umbrales propios del proyecto (justificados en bitacora/FASE-1)
PICO_DESVIO_M = 0.5            # desvío del registro respecto a sus dos vecinos
PICO_VECINOS_M = 0.15          # los vecinos deben parecerse entre sí
PICO_VENTANA = pd.Timedelta("20min")
PEGADO_HORAS_MAX = 72          # nivel idéntico >= 72 h -> sensor pegado
PEGADO_HORAS_LLUVIA = 6        # nivel idéntico >= 6 h con...
PEGADO_LLUVIA_MM = 10          # ...>= 10 mm de lluvia en el tramo -> sensor pegado
MESETA_MAX_MIN = 60            # hueco <= 60 min con igual valor a ambos lados -> se rellena
MESETA_TOL_M = 0.005
MAX_HUECO_IMPUTABLE_H = 6      # huecos horarios <= 6 h se interpolan


def control_rangos(df: pd.DataFrame):
    df = df.copy()
    conteo = {}
    for v, (lo, hi) in RANGOS_CAM.items():
        if v in df:
            malo = df[v].notna() & ((df[v] < lo) | (df[v] > hi))
            conteo[v] = int(malo.sum())
            df.loc[malo, v] = np.nan
    return df, conteo


def quitar_picos_aislados(df: pd.DataFrame, col: str = "nivel_m"):
    """Un registro que difiere > PICO_DESVIO_M de su anterior y su siguiente,
    cuando esos dos vecinos se parecen entre sí y están cerca en el tiempo."""
    df = df.copy()
    s = df[col].dropna()
    t = df.loc[s.index, "fecha_hora"]
    prev, nxt = s.shift(1), s.shift(-1)
    cerca = (t - t.shift(1) <= PICO_VENTANA) & (t.shift(-1) - t <= PICO_VENTANA)
    pico = (
        ((s - prev).abs() > PICO_DESVIO_M)
        & ((s - nxt).abs() > PICO_DESVIO_M)
        & ((prev - nxt).abs() <= PICO_VECINOS_M)
        & cerca
    )
    df.loc[pico[pico].index, col] = np.nan
    return df, int(pico.sum())


def quitar_sensor_pegado(df: pd.DataFrame, col: str = "nivel_m"):
    """Tramos de valores idénticos consecutivos que duran >= PEGADO_HORAS_MAX,
    o >= PEGADO_HORAS_LLUVIA mientras llovieron >= PEGADO_LLUVIA_MM en la estación
    (si llueve fuerte y el nivel no se mueve ni 1 cm, el sensor no está respondiendo)."""
    df = df.copy()
    s = df[col].dropna()
    t = df.loc[s.index, "fecha_hora"]
    grupo = (s != s.shift()).cumsum()
    quitados = 0
    tramos = 0
    for _, idx in s.groupby(grupo).groups.items():
        if len(idx) < 2:
            continue
        ini, fin = t.loc[idx[0]], t.loc[idx[-1]]
        horas = (fin - ini).total_seconds() / 3600
        if horas < PEGADO_HORAS_LLUVIA:
            continue
        pegado = horas >= PEGADO_HORAS_MAX
        if not pegado and "lluvia_mm" in df:
            en_tramo = (df["fecha_hora"] >= ini) & (df["fecha_hora"] <= fin)
            pegado = df.loc[en_tramo, "lluvia_mm"].sum() >= PEGADO_LLUVIA_MM
        if pegado:
            df.loc[idx, col] = np.nan
            quitados += len(idx)
            tramos += 1
    return df, {"tramos": tramos, "registros": quitados}


def rellenar_mesetas(df: pd.DataFrame, col: str = "nivel_m"):
    """La CAM borró (NaN) las rachas de >20 valores idénticos en MeerKAD. En un río
    estable con resolución de 1 cm eso elimina datos válidos. Si un hueco dura
    <= MESETA_MAX_MIN y el valor antes y después es el mismo, se rellena con ese valor."""
    df = df.copy()
    s = df[col]
    na = s.isna()
    grupo = (na != na.shift()).cumsum()
    rellenados = 0
    for _, idx in s[na].groupby(grupo[na]).groups.items():
        i0 = df.index.get_loc(idx[0])
        i1 = df.index.get_loc(idx[-1])
        if i0 == 0 or i1 == len(df) - 1:
            continue
        antes, despues = s.iloc[i0 - 1], s.iloc[i1 + 1]
        dur = df["fecha_hora"].iloc[i1 + 1] - df["fecha_hora"].iloc[i0 - 1]
        if (pd.notna(antes) and pd.notna(despues) and abs(antes - despues) <= MESETA_TOL_M
                and dur <= pd.Timedelta(minutes=MESETA_MAX_MIN)):
            df.loc[idx, col] = antes
            rellenados += len(idx)
    return df, rellenados


def imputar_huecos_cortos(h: pd.DataFrame, col: str = "nivel_m", max_h: int = MAX_HUECO_IMPUTABLE_H):
    """Interpolación lineal (en el tiempo) solo de huecos internos <= max_h horas.
    Agrega la columna <col>_imputado (bool)."""
    h = h.copy()
    s = h[col]
    na = s.isna()
    grupo = (na != na.shift()).cumsum()
    largo = na.groupby(grupo).transform("sum")
    interp = s.interpolate(method="time", limit_area="inside")
    usar = na & (largo <= max_h) & interp.notna()
    h[col] = s.where(~usar, interp)
    h[f"{col}_imputado"] = usar
    return h, int(usar.sum())
