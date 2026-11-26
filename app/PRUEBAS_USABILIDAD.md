# Protocolo de pruebas del dashboard

La propuesta plantea un componente cualitativo: requerimientos y evaluación de la herramienta de visualización, incluyendo su funcionamiento y su facilidad de uso. Este protocolo lo cubre en dos partes.

Para abrir el dashboard, desde la carpeta del proyecto:

```powershell
.venv\Scripts\streamlit run app\app.py
```

## A. Pruebas funcionales

Se ejecutaron el 2026-11-26 en el navegador y con `streamlit.testing`.

| ID | Prueba | Resultado esperado | ¿Pasa? |
|---|---|---|---|
| PF1 | "Estado del río": 14/11/2024 a las 06:00 | estado NARANJA, nivel 2.09 m, anomalía +1.41 m. Pronóstico RF: 2.19 m a 1 h (real 2.37 m) | ✅ |
| PF2 | "Estado del río": 01/02/2024 a las 12:00 | estado NORMAL, nivel 0.57 m | ✅ |
| PF3 | "Pronóstico vs real": Random Forest a 1 h | RMSE 3.01 cm, POD 0.78, FAR 0.15, CSI 0.69 | ✅ |
| PF4 | "Pronóstico vs real": Persistencia a 1 h | RMSE 3.29 cm | ✅ |
| PF5 | "Histórico": años 2022 a 2022 | 20 crecientes, 3 rojas y nivel máximo instantáneo de 3.70 m | ✅ |
| PF6 | "Calidad": matriz de completitud | La Lindosa 2021 = 100 (99.8%) y San Benito 2021 = 0 | ✅ |
| PF7 | Hora sin datos (11/01/2024 a las 10:00) | aviso "No hay pronóstico…" sin error | ✅ (prueba automática) |
| PF8 | Menú lateral y pie de página | las 5 páginas abren y todas muestran el aviso de herramienta de apoyo | ✅ |

**Pruebas automáticas:** `tests/test_app.py` (7 pruebas). Verifican que las 5 páginas se ejecutan sin errores, además de PF1 y PF7.

## B. Pruebas de usabilidad con usuarios

**Participantes:** 5 personas. Según Nielsen, 5 usuarios detectan alrededor del 85% de los problemas de usabilidad. Combinación sugerida:
- 2 estudiantes o docentes de Ingeniería de Sistemas;
- 1 persona de otra carrera, como usuario no técnico;
- el director del proyecto;
- si se puede, 1 persona de la CAM o de Gestión del Riesgo.

**Procedimiento (unos 20 minutos por persona):**
1. Explicar en un minuto qué es la herramienta, sin mostrar cómo se usa.
2. Pedir que realice las 5 tareas mientras piensa en voz alta. Anotar el tiempo de cada tarea, si la completó y los comentarios.
3. Aplicar el cuestionario SUS.
4. Preguntar: "¿Qué cambiarías?"

### Tareas

| # | Tarea | Éxito si… | Tiempo objetivo |
|---|---|---|---|
| T1 | "¿En qué estado de alerta estaba el río el 14 de noviembre de 2024 a las 6 de la mañana?" | responde naranja | 60 s o menos |
| T2 | "¿Cuál fue la creciente más alta de 2022 y cuándo ocurrió?" | 20/02/2022 (3.70 m de nivel máximo) o 28/10/2022 (mayor anomalía, 3.50 m) | 90 s o menos |
| T3 | "¿Qué estación tiene los datos más completos?" | La Lindosa o Los Micos | 60 s o menos |
| T4 | "¿Qué modelo se eligió y por qué?" | Random Forest, con una razón válida | 90 s o menos |
| T5 | "¿Qué tan bien anticipa el modelo una creciente a 3 horas?" | menciona que la anticipa poco o algún indicador (CSI/POD) | 120 s o menos |

### Cuestionario SUS (System Usability Scale, Brooke 1996)

Cada afirmación se responde de 1 a 5: 1 = totalmente en desacuerdo, 5 = totalmente de acuerdo.

1. Creo que me gustaría usar esta herramienta con frecuencia.
2. Encontré la herramienta innecesariamente compleja.
3. Pensé que la herramienta era fácil de usar.
4. Creo que necesitaría el apoyo de un técnico para poder usar esta herramienta.
5. Encontré que las diversas funciones de la herramienta estaban bien integradas.
6. Pensé que había demasiada inconsistencia en la herramienta.
7. Imagino que la mayoría de las personas aprendería a usar esta herramienta muy rápidamente.
8. Encontré la herramienta muy engorrosa de usar.
9. Me sentí muy seguro(a) usando la herramienta.
10. Necesité aprender muchas cosas antes de poder empezar a usar la herramienta.

**Cálculo del puntaje:**
- En los ítems impares, el aporte es la respuesta menos 1.
- En los ítems pares, el aporte es 5 menos la respuesta.
- Se suman los 10 aportes y el resultado se multiplica por 2.5.
- El puntaje va de 0 a 100. **Por encima de 68 se considera sobre el promedio y por encima de 80 es excelente.**

### Plantilla de resultados

Copiar esta tabla en el informe de la fase 3 cuando se hagan las pruebas:

| Participante | Perfil | T1 | T2 | T3 | T4 | T5 | SUS | Comentarios principales |
|---|---|---|---|---|---|---|---|---|
| P1 | | ✅/❌ (s) | | | | | | |
| P2 | | | | | | | | |
| P3 | | | | | | | | |
| P4 | | | | | | | | |
| P5 | | | | | | | | |
| **Promedio** | | % de éxito | | | | | | |

**Criterio de aceptación:** SUS promedio de 68 o más, y al menos el 80% de las tareas completadas. Si no se cumple, se ajusta el dashboard según los comentarios y se repite la prueba con 2 o 3 personas nuevas.
