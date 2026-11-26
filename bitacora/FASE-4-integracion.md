# Fase 4: integración de la solución

**Proyecto:** Desarrollo de un sistema de calidad de datos y modelos predictivos para alertas tempranas de inundaciones en la cuenca del río Las Ceibas
**Responsable:** Harold Camilo Barrera Giraldo
**Fecha de cierre:** 2026-11-26
**Estado:** terminada
**Sección de la propuesta que cubre:** "Integración de la solución": un flujo desde el procesamiento y la validación de los datos hasta la generación y visualización de la información.

---

## 1. Objetivo de la fase

Unir las piezas de las fases 1 a 3 en **un solo flujo reproducible**: datos crudos → calidad → modelos → pronóstico y alerta → tablas del dashboard. Además:
- dejar un **pronóstico operativo** que se pueda ejecutar para cualquier momento;
- documentar la arquitectura técnica;
- verificar que todo se reconstruye desde cero con los mismos resultados.

## 2. Punto de partida

- Cada fase tenía sus propios scripts y había que ejecutarlos a mano y en el orden correcto.
- Los modelos de la fase 2 se entrenaron solo hasta 2023, porque 2024-2025 se reservó para la prueba. No había un modelo listo para pronosticar con todos los datos.

## 3. Qué se hizo

### 3.1 Modelo operativo y pronóstico (`src/pronosticar.py`)

- **`entrenar`:** ajusta el modelo seleccionado en la fase 2 (Random Forest con profundidad 20, 20 muestras por hoja y 300 árboles) con **todos** los datos válidos desde 2018, unas 52,700 horas por horizonte. Guarda una ficha con la fecha de entrenamiento, el periodo y las variables usadas (`models/operativo_ficha.json`).
  - **Por qué:** en la fase 2 se reservaron 2024-2025 para evaluar con honestidad. Una vez elegido el modelo, conviene que aprenda también de las crecientes más recientes, como las de noviembre de 2024.
- **`pronosticar [--fecha]`:** para la última hora con datos completos, o para la fecha indicada, calcula:
  - el nivel, la línea base, la anomalía y la **alerta actual**;
  - el nivel y la alerta pronosticados a **+1, +3 y +6 h**;
  - el nivel real, si ese momento ya ocurrió (útil para revisar eventos pasados).

  Escribe `reports/pronostico_actual.json` y agrega una fila a `dashboard/datos/pronostico_actual.csv`, que se puede usar como historial en Power BI.

**Ejemplo con la creciente del 14/11/2024 a las 06:00:**

```
Nivel 2.09 m | línea base 0.68 m | anomalía +1.41 m | ALERTA ACTUAL: NARANJA
  +1 h -> 2.20 m  ROJA     (real: 2.37 m)
  +3 h -> 1.93 m  NARANJA  (real: 2.50 m)
  +6 h -> 1.63 m  AMARILLA (real: 2.00 m)
```

El ejemplo confirma lo que encontró la fase 2: el modelo sigue bien la creciente en curso, pero subestima el segundo pico. Para esta fecha el modelo operativo **ya vio** ese evento al entrenar, así que el ejemplo ilustra el funcionamiento y **no** sirve como evaluación. La evaluación honesta es la de la fase 2.

### 3.2 Orquestador (`src/pipeline.py`)

Un solo comando ejecuta las 10 etapas en orden. **Después de cada etapa valida sus salidas** y, si algo falla, se detiene indicando dónde:

| # | Etapa | Validación |
|---|---|---|
| 1 | carga | 6 estaciones, todas con más de 100 mil registros |
| 2 | diagnóstico | existen las tablas y figuras de calidad |
| 3 | limpieza | completitud del nivel de La Lindosa desde 2018 mayor al 85%, niveles entre 0 y 10 m, índice horario sin duplicados |
| 4 | imputación (experimento) | existe la evaluación |
| 5 | modelos | están los modelos clave y **Random Forest supera a la persistencia en los 3 horizontes** |
| 6 | estadística | existen las pruebas |
| 7 | alerta (experimento) | existe el resultado |
| 8 | operativo | existen los 3 modelos operativos |
| 9 | Power BI | 12 tablas o más y más de 50 crecientes exportadas |
| 10 | pronóstico | existe el JSON |

**Opciones:**
- `--rapido`: se salta las etapas 4 a 7 (comparación de modelos y experimentos). Es para cuando llegan **datos nuevos de la CAM** y solo hace falta limpiar, reentrenar el modelo operativo, exportar y pronosticar. Tarda unos 2.5 minutos.
- `--desde <etapa>` y `--solo <etapa>`.
- El log completo de cada ejecución queda en `logs/pipeline_<fecha>.log`.

### 3.3 Documentación técnica (`ARQUITECTURA.md`)

Incluye:
- el diagrama del flujo;
- la tabla de componentes con la entrada y la salida de cada uno;
- cómo ejecutar el sistema;
- **cómo agregar datos nuevos de la CAM**;
- qué se versiona en Git y qué no;
- las limitaciones de la arquitectura.

### 3.4 Pruebas de integración (`tests/test_integracion.py`)

Hay 3 pruebas nuevas, que usan los datos y modelos reales:
- el pronóstico del 14/11/2024 da alerta NARANJA, nivel de 2.09 m y los 3 horizontes;
- una fecha sin datos produce un error con un mensaje claro;
- el dataset final tiene paso horario exacto, sin duplicados, completitud mayor al 85% y menos del 1% de datos imputados.

Si todavía no se ha ejecutado el flujo, estas pruebas se omiten.

## 4. Resultados

### 4.1 Verificación de reproducibilidad

Se borraron `data/`, `models/` y `dashboard/datos/`, y se ejecutó `python src/pipeline.py` desde cero:

```
[1/10] carga ... ok (12 s)
[2/10] diagnostico ... ok (2 s)
[3/10] limpieza ... ok (18 s)
[4/10] imputacion ... ok (3 s)
[5/10] modelos ... ok (679 s)
[6/10] estadistica ... ok (4 s)
[7/10] alerta ... ok (49 s)
[8/10] operativo ... ok (113 s)
[9/10] powerbi ... ok (8 s)
[10/10] pronostico ... ok (5 s)
Flujo completo en 14.9 min.
```

**Comparación con los resultados ya publicados en Git:**
- Datos, métricas, predicciones y pruebas estadísticas son **idénticos**.
- La única diferencia está en el **decimal 15** de algunos valores (por ejemplo, un W de Shapiro de 0.7941766083403506 frente a 0.7941766083403509), por redondeo de coma flotante. No cambia ninguna conclusión.

**Conclusión: el proyecto es completamente reproducible desde los datos crudos.**

### 4.2 Pruebas automáticas

**Pasan las 25:** 14 del ETL, 8 de los modelos y 3 de integración.

## 5. Cómo reproducirlo

Desde `Proyecto Grado`, en PowerShell:

```powershell
.venv\Scripts\python src\pipeline.py
.venv\Scripts\python -m pytest tests
.venv\Scripts\python src\pronosticar.py pronosticar --fecha "2024-11-14 06:00"
```

## 6. Limitaciones

- **Procesamiento por lotes, no en tiempo real:** el sistema trabaja con los archivos que entrega la CAM. Conectarlo a la transmisión satelital de la CAM requiere un acuerdo de acceso a esos datos (trabajo futuro).
- **Actualización del dashboard:** se hace a mano con "Actualizar" en Power BI Desktop. La actualización automática requiere Power BI Service y una puerta de enlace.
- **La última hora disponible es el 28/11/2025 a las 22:00**, y no el 31/12/2025. Después de esa fecha faltan datos de alguna variable de entrada (Los Micos o la lluvia), así que no hay filas completas para pronosticar.

## 7. Siguiente fase

**Fase 5: artículo y documento final.**
- Artículo científico: introducción, métodos (fases 1 y 2), resultados y discusión sobre el límite de predictibilidad. Elegir la revista o el evento.
- Documento final de grado y presentación para la sustentación.
- Incorporar los resultados de las pruebas de usabilidad de la fase 3 cuando estén listos.
