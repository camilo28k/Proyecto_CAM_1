"""Etapa 1 del ETL: carga de los datos crudos de la CAM a un formato unificado.

Lee los Excel (MAIGRAI, 2017-2020, horarios) y los CSV (MeerKAD, 2020-2025, ~5 min)
de Datos_CAM/, normaliza nombres de columnas, tipos y fechas, y guarda por estación:
  data/interim/<estacion>_crudo.parquet   -> registros originales unificados
  data/interim/<estacion>_horario.parquet -> serie a paso horario regular

Los archivos originales NO se modifican.

Uso:  python src/etl/cargar_crudos.py
"""
from pathlib import Path
import re
import pandas as pd
import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
CRUDOS = RAIZ / "Datos_CAM"
SALIDA = RAIZ / "data" / "interim"

# Nombre original (normalizado sin tildes/símbolos) -> nombre estándar
MAPA_COLUMNAS = {
    "fecha_hora": "fecha_hora",
    "nivel_m": "nivel_m",
    "temperatura_c": "temperatura_c",
    "humedad": "humedad_pct",
    "radiacion_solar_w_m2": "radiacion_wm2",
    "lluvia_mm": "lluvia_mm",
    "direccion_viento": "dir_viento_grados",
    "velocidad_viento_m_s": "vel_viento_ms",
    "velocidad_agua_m_s": "vel_agua_ms",
    "presion_atmosferica_hpa": "presion_hpa",
}
# Columnas que se descartan a propósito (ver informe FASE-0)
DESCARTAR = {"rad_u_w_m2"}  # canal auxiliar de El Batán sin documentación

# Archivos duplicados exactos que se omiten
OMITIR = {"Las Juntas_2019(1).xlsx"}

# Cómo agregar cada variable al pasar a paso horario
AGREGACION = {
    "nivel_m": "mean",
    "temperatura_c": "mean",
    "humedad_pct": "mean",
    "radiacion_wm2": "mean",
    "lluvia_mm": "sum",
    "dir_viento_grados": "mean",  # aproximación; no se usa en modelos
    "vel_viento_ms": "mean",
    "vel_agua_ms": "mean",
    "presion_hpa": "mean",
}


def normalizar(nombre: str) -> str:
    n = str(nombre).lower()
    n = n.replace("°", "").replace("�", "").replace("%", "")
    n = re.sub(r"[^a-z0-9]+", "_", n).strip("_")
    return n


def estandarizar(df: pd.DataFrame, archivo: Path) -> pd.DataFrame:
    nuevas = {}
    for c in df.columns:
        n = normalizar(c)
        if n in DESCARTAR or n.startswith("unnamed") or n == "":
            continue
        if n not in MAPA_COLUMNAS:
            raise ValueError(f"Columna desconocida '{c}' en {archivo.name}")
        nuevas[c] = MAPA_COLUMNAS[n]
    df = df[list(nuevas)].rename(columns=nuevas)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], dayfirst=True, errors="coerce")
    for c in df.columns:
        if c != "fecha_hora":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["fecha_hora"])


def leer_archivo(archivo: Path) -> pd.DataFrame:
    if archivo.suffix == ".xlsx":
        df = pd.read_excel(archivo)
        fuente = "MAIGRAI"
    else:
        df = pd.read_csv(archivo, sep=";", decimal=",", encoding="cp1252")
        fuente = "MeerKAD"
    df = estandarizar(df, archivo)
    df["fuente"] = fuente
    df["archivo"] = archivo.name
    return df


def a_horario(df: pd.DataFrame) -> pd.DataFrame:
    """Serie horaria regular. La hora h agrupa registros en [h, h+1).
    Si en una hora no hay ningún registro válido de una variable, queda NaN
    (también la lluvia: no se asume 0 cuando no hubo datos)."""
    vars_ = [c for c in AGREGACION if c in df.columns]
    g = df.set_index("fecha_hora")[vars_].resample("1h")
    agg = {}
    for v in vars_:
        if AGREGACION[v] == "sum":
            agg[v] = g[v].sum(min_count=1)
        else:
            agg[v] = g[v].mean()
    out = pd.DataFrame(agg)
    if "nivel_m" in vars_:
        out["nivel_max_m"] = g["nivel_m"].max()
    out["n_registros"] = g["nivel_m" if "nivel_m" in vars_ else vars_[0]].count()
    return out


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    resumen = []
    for carpeta in sorted(p for p in CRUDOS.iterdir() if p.is_dir()):
        estacion = carpeta.name
        partes = []
        for a in sorted(list(carpeta.glob("*.xlsx")) + list(carpeta.glob("*.csv"))):
            if a.name in OMITIR:
                continue
            partes.append(leer_archivo(a))
        df = pd.concat(partes, ignore_index=True)
        # Solape MAIGRAI/MeerKAD (p. ej. La Lindosa 2020): se prefiere MeerKAD
        df = df.sort_values(["fecha_hora", "fuente"], ascending=[True, False])
        antes = len(df)
        df = df.drop_duplicates(subset="fecha_hora", keep="first")
        dup = antes - len(df)
        df = df.sort_values("fecha_hora").reset_index(drop=True)
        df.to_parquet(SALIDA / f"{estacion}_crudo.parquet", index=False)
        h = a_horario(df)
        h.to_parquet(SALIDA / f"{estacion}_horario.parquet")
        resumen.append({
            "estacion": estacion, "registros": len(df), "duplicados_quitados": dup,
            "inicio": df.fecha_hora.min(), "fin": df.fecha_hora.max(),
            "variables": ", ".join(c for c in df.columns if c not in ("fecha_hora", "fuente", "archivo")),
        })
        print(f"{estacion}: {len(df):,} registros, {dup} duplicados quitados")
    pd.DataFrame(resumen).to_csv(SALIDA / "resumen_carga.csv", index=False)


if __name__ == "__main__":
    main()
