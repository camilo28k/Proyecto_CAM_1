"""Pruebas de variables y métricas de los modelos."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "models"))
import features as F  # noqa: E402
import metricas as M  # noqa: E402


def dataset_sintetico(n=24 * 40):
    idx = pd.date_range("2024-01-01", periods=n, freq="h", name="fecha_hora")
    rng = np.random.default_rng(0)
    nivel = 0.8 + 0.01 * rng.standard_normal(n)
    return pd.DataFrame({
        "nivel_lindosa_m": nivel, "nivel_max_lindosa_m": nivel + 0.01,
        "nivel_lindosa_imputado": False, "lluvia_lindosa_mm": rng.exponential(0.1, n),
        "temperatura_lindosa_c": 20.0, "nivel_micos_m": nivel / 2, "nivel_micos_imputado": False,
        "lluvia_micos_mm": rng.exponential(0.1, n), "temperatura_micos_c": 20.0,
    }, index=idx)


def test_variables_no_usan_el_futuro():
    """Cambiar datos FUTUROS no debe cambiar ninguna variable de entrada en t."""
    d = dataset_sintetico()
    f1 = F.construir(d)
    d2 = d.copy()
    t = d.index[600]
    d2.loc[d.index > t, ["nivel_lindosa_m", "lluvia_lindosa_mm", "nivel_micos_m", "lluvia_micos_mm"]] *= 5
    f2 = F.construir(d2)
    cols = F.variables(f1)
    pd.testing.assert_frame_equal(f1.loc[:t, cols], f2.loc[:t, cols])


def test_objetivo_es_cambio_futuro():
    d = dataset_sintetico()
    f = F.construir(d)
    i = 100
    esperado = d.nivel_lindosa_m.iloc[i + 3] - d.nivel_lindosa_m.iloc[i]
    assert f["y_delta_3h"].iloc[i] == pytest.approx(esperado)


def test_objetivo_excluye_valores_imputados():
    d = dataset_sintetico()
    d.iloc[103, d.columns.get_loc("nivel_lindosa_imputado")] = True
    f = F.construir(d)
    assert np.isnan(f["y_delta_3h"].iloc[100])


def test_linea_base_excluye_hora_actual():
    s = pd.Series([1.0] * 200 + [9.0], index=pd.date_range("2024-01-01", periods=201, freq="h"))
    base = F.linea_base(s.rename("n"))
    assert base.iloc[-1] == 1.0


def test_particiones_no_se_solapan():
    a = [pd.Timestamp(v) for k in ["train", "val", "test"] for v in F.PARTICION[k]]
    assert a == sorted(a)


def test_clase_alerta():
    assert F.clase_alerta([0.1, 0.5, 1.2, 2.0]).tolist() == [0, 1, 2, 3]


def test_nse_perfecto_y_media():
    obs = np.array([1.0, 2.0, 3.0])
    assert M.nse(obs, obs) == 1
    assert M.nse(obs, np.full(3, 2.0)) == pytest.approx(0)


def test_contingencia():
    pod, far, csi, n = M.contingencia([1, 1, 0, 0], [1, 0, 1, 0])
    assert (pod, far, csi, n) == (0.5, 0.5, pytest.approx(1 / 3), 2)
