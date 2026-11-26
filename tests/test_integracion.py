"""Pruebas de integración: usan los datos y modelos reales.
Se omiten si aún no se ha ejecutado el flujo (python src/pipeline.py)."""
import sys
from pathlib import Path
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

requiere_flujo = pytest.mark.skipif(
    not (RAIZ / "models" / "operativo_rf_1h.joblib").exists()
    or not (RAIZ / "data" / "processed" / "dataset_modelo.parquet").exists(),
    reason="ejecute primero src/pipeline.py")


@requiere_flujo
def test_pronostico_creciente_noviembre_2024():
    import pronosticar
    s = pronosticar.pronosticar("2024-11-14 06:00", guardar=False)
    assert s["alerta_actual"] == "NARANJA"
    assert s["nivel_m"] == pytest.approx(2.091, abs=0.01)
    assert [p["horizonte_h"] for p in s["pronostico"]] == [1, 3, 6]
    for p in s["pronostico"]:
        assert 0 < p["nivel_pronosticado_m"] < 10
        assert p["nivel_real_m"] is not None


@requiere_flujo
def test_pronostico_fecha_sin_datos_falla_con_mensaje():
    import pronosticar
    with pytest.raises(SystemExit, match="No hay datos completos"):
        pronosticar.pronosticar("2030-01-01 00:00", guardar=False)


@requiere_flujo
def test_dataset_final_consistente():
    d = pd.read_parquet(RAIZ / "data" / "processed" / "dataset_modelo.parquet")
    assert d.index.is_monotonic_increasing and not d.index.has_duplicates
    assert (d.index.to_series().diff().dropna() == pd.Timedelta("1h")).all()
    assert d.loc["2018":, "nivel_lindosa_m"].notna().mean() > 0.85
    # lo imputado nunca es más del 1 % del nivel disponible
    assert d.nivel_lindosa_imputado.sum() / d.nivel_lindosa_m.notna().sum() < 0.01
