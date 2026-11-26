"""Pruebas del módulo de calidad. Ejecutar: .venv\\Scripts\\python -m pytest tests"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "etl"))
import calidad as cq  # noqa: E402
from cargar_crudos import normalizar, estandarizar  # noqa: E402


def serie(niveles, paso="5min", lluvia=None):
    n = len(niveles)
    return pd.DataFrame({
        "fecha_hora": pd.date_range("2024-01-01", periods=n, freq=paso),
        "nivel_m": niveles,
        "lluvia_mm": lluvia if lluvia is not None else [0.0] * n,
    })


def test_normalizar_columnas_con_simbolos():
    assert normalizar("temperatura_(�C)") == "temperatura_c"
    assert normalizar("Presion Atmosferica (HPa)") == "presion_atmosferica_hpa"


def test_estandarizar_rechaza_columna_desconocida():
    df = pd.DataFrame({"fecha_hora": ["1/01/2024 0:00"], "columna_rara": [1]})
    with pytest.raises(ValueError):
        estandarizar(df, Path("x.csv"))


def test_estandarizar_fecha_dia_primero():
    df = pd.DataFrame({"fecha_hora": ["2/01/2024 0:05"], "nivel_(m)": ["0,5"]})
    out = estandarizar(df, Path("x.csv"))
    assert out.fecha_hora.iloc[0] == pd.Timestamp("2024-01-02 00:05")


def test_rangos_quita_lluvia_negativa_y_excesiva():
    df = serie([0.5, 0.5, 0.5], lluvia=[-1.0, 5.0, 150.0])
    out, c = cq.control_rangos(df)
    assert c["lluvia_mm"] == 2
    assert out.lluvia_mm.isna().tolist() == [True, False, True]


def test_rangos_limites_inclusivos():
    df = serie([0.0, 1.0], lluvia=[0.0, 100.0])
    out, _ = cq.control_rangos(df)
    assert out.nivel_m.notna().all() and out.lluvia_mm.notna().all()


def test_pico_aislado_se_quita():
    out, c = cq.quitar_picos_aislados(serie([0.8, 0.8, 2.0, 0.81, 0.8]))
    assert c == 1 and np.isnan(out.nivel_m.iloc[2])


def test_creciente_real_no_es_pico():
    # sube y se queda arriba: es una creciente, no un pico
    out, c = cq.quitar_picos_aislados(serie([0.8, 0.8, 2.0, 2.1, 1.9]))
    assert c == 0


def test_sensor_pegado_por_duracion():
    n = 73 * 12 + 1  # > 72 h a 5 min
    out, c = cq.quitar_sensor_pegado(serie([0.6] * n))
    assert c["tramos"] == 1 and out.nivel_m.isna().all()


def test_sensor_pegado_con_lluvia():
    n = 7 * 12  # 7 h
    lluvia = [0.2] * n  # 16.8 mm
    out, c = cq.quitar_sensor_pegado(serie([0.6] * n, lluvia=lluvia))
    assert c["tramos"] == 1


def test_nivel_estable_sin_lluvia_se_conserva():
    n = 10 * 12  # 10 h sin lluvia: río estable, válido
    out, c = cq.quitar_sensor_pegado(serie([0.6] * n))
    assert c["tramos"] == 0 and out.nivel_m.notna().all()


def test_meseta_corta_se_rellena():
    out, c = cq.rellenar_mesetas(serie([0.6, np.nan, np.nan, 0.6]))
    assert c == 2 and (out.nivel_m == 0.6).all()


def test_meseta_con_valores_distintos_no_se_rellena():
    out, c = cq.rellenar_mesetas(serie([0.6, np.nan, 0.9]))
    assert c == 0 and np.isnan(out.nivel_m.iloc[1])


def test_imputacion_solo_huecos_cortos():
    idx = pd.date_range("2024-01-01", periods=20, freq="h")
    v = np.linspace(1, 2, 20)
    v[2:4] = np.nan     # hueco de 2 h -> se imputa
    v[8:16] = np.nan    # hueco de 8 h -> no se imputa
    h = pd.DataFrame({"nivel_m": v}, index=idx)
    out, c = cq.imputar_huecos_cortos(h)
    assert c == 2
    assert out.nivel_m.iloc[2:4].notna().all() and out.nivel_m.iloc[8:16].isna().all()
    assert out.nivel_m_imputado.sum() == 2
    assert out.nivel_m.iloc[2] == pytest.approx(np.linspace(1, 2, 20)[2])


def test_no_se_imputan_bordes():
    idx = pd.date_range("2024-01-01", periods=5, freq="h")
    h = pd.DataFrame({"nivel_m": [np.nan, 1.0, 1.1, 1.2, np.nan]}, index=idx)
    out, c = cq.imputar_huecos_cortos(h)
    assert c == 0
