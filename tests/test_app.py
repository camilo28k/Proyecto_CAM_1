"""Pruebas del dashboard Streamlit: cada página se ejecuta sin errores.
Se omiten si no existen los datos (ejecute src/pipeline.py)."""
import sys
from pathlib import Path
import pytest

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "app"
sys.path.insert(0, str(APP))

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

requiere_datos = pytest.mark.skipif(not (RAIZ / "dashboard" / "datos" / "hechos_hidrologia.csv").exists(),
                                    reason="ejecute primero src/pipeline.py")
PAGINAS = sorted((APP / "paginas").glob("*.py"))


@requiere_datos
@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.stem)
def test_pagina_sin_errores(pagina):
    at = AppTest.from_file(str(pagina), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.title) == 1


@requiere_datos
def test_estado_noviembre_2024_es_naranja():
    at = AppTest.from_file(str(APP / "paginas" / "1_estado.py"), default_timeout=120).run()
    textos = " ".join(m.body for m in at.markdown)
    assert "NARANJA" in textos
    assert at.metric[0].value == "2.09 m"


@requiere_datos
def test_hora_sin_datos_muestra_aviso():
    at = AppTest.from_file(str(APP / "paginas" / "1_estado.py"), default_timeout=120).run()
    at.date_input[0].set_value(__import__("datetime").date(2024, 1, 11)).run()
    at.selectbox[0].select(__import__("datetime").time(10)).run()
    assert not at.exception
    assert at.warning, "debería avisar que no hay pronóstico para esa hora"
