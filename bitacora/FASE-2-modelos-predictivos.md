# Fase 2: modelos predictivos

**Proyecto:** Desarrollo de un sistema de calidad de datos y modelos predictivos para alertas tempranas de inundaciones en la cuenca del río Las Ceibas
**Responsable:** Harold Camilo Barrera Giraldo
**Fecha de cierre:** 2026-11-26
**Estado:** terminada
**Objetivo de la propuesta que cubre:** objetivo específico 2, "Desarrollar los modelos predictivos". Incluye el diseño cuasiexperimental, la comparación de arquitecturas, las pruebas de Shapiro-Wilk y t pareada (o su alternativa no paramétrica) y la selección del mejor modelo.

---

## 1. Objetivo de la fase

Pronosticar el nivel del río Las Ceibas en **La Lindosa** (la estación más cercana a Neiva) a **1, 3 y 6 horas**, a partir del dataset limpio de la fase 1. Para eso se comparan varias arquitecturas de modelos y se elige la mejor con evidencia estadística.

## 2. Punto de partida

- Dataset `data/processed/dataset_modelo.parquet`: serie horaria 2017-2025 de La Lindosa y Los Micos.
- Dos hallazgos de la fase 1 condicionan el diseño:
  1. **La línea base del nivel cambia con los años**: el nivel normal baja de unos 0.85 m a unos 0.5 m.
  2. **Las crecientes llegan en menos de una hora.**

## 3. Diseño del experimento

### 3.1 Qué se predice

Por la deriva de la línea base, **los modelos no predicen el nivel absoluto sino cuánto va a cambiar**:

- `delta_h(t) = nivel(t+h) − nivel(t)`
- nivel pronosticado = `nivel(t) + delta_pred`

Las alertas se definen sobre la **anomalía**, es decir, cuánto está el río por encima de su nivel normal reciente:

- `anomalía = nivel − línea base`
- `línea base` = mediana del nivel de los **30 días anteriores**, sin incluir la hora actual.

### 3.2 Niveles de alerta (definidos por el proyecto)

| Nivel | Anomalía | Eventos 2018-2025 | Equivale a |
|---|---|---|---|
| Amarilla | 0.5 m o más | 107 | percentil 99.5 de la anomalía |
| Naranja | 1.0 m o más | 23 | |
| Roja | 1.5 m o más | 10 | crecientes como las de febrero y octubre de 2022 |

⚠️ **Son umbrales técnicos del proyecto y no umbrales oficiales.** Hay que validarlos con la CAM o con Gestión del Riesgo de Neiva. La herramienta **es de apoyo y no reemplaza los mecanismos oficiales de alerta**, como indica la propuesta.

### 3.3 Variables de entrada (25 en total; `src/models/features.py`)

Todas usan **solo información disponible en el instante t**. La prueba `test_variables_no_usan_el_futuro` lo verifica: si se alteran los datos futuros, ninguna variable cambia.

| Grupo | Variables |
|---|---|
| Estado del río en La Lindosa | anomalía; diferencia entre el máximo y el promedio de la hora; cambio del nivel en 1, 2, 3, 6 y 12 h |
| Lluvia en La Lindosa | acumulada en 1, 2, 3, 6, 12, 24 y 72 h |
| Lluvia en Los Micos | acumulada en 1, 3, 6 y 24 h |
| Los Micos (afluente) | anomalía; cambio del nivel en 1 y 3 h |
| Calendario | hora del día y día del año, en seno y coseno |

### 3.4 Partición temporal (sin mezclar fechas)

| Conjunto | Periodo | Filas (h = 1) | Uso |
|---|---|---|---|
| Entrenamiento | 2018-2022 | 33,047 | ajustar los modelos |
| Validación | 2023 | 8,245 | elegir hiperparámetros |
| Prueba | 2024-2025 | 11,437 | evaluación final, que se usa **una sola vez** |

Los modelos finales se reentrenan con entrenamiento más validación y luego se evalúan en prueba. Todos los modelos se evalúan sobre **exactamente las mismas filas**. Se usó la semilla 42 para que los resultados sean reproducibles.

### 3.5 Modelos comparados (`src/models/entrenar.py`)

| Modelo | Tipo | Hiperparámetros explorados |
|---|---|---|
| Persistencia | referencia: "el nivel no cambia" | ninguno |
| Ridge | regresión lineal regularizada | alpha ∈ {0.1, 1, 10, 100} |
| Random Forest | ensamble de árboles | profundidad ∈ {10, 20} × hojas mínimas ∈ {5, 20} |
| XGBoost | boosting de gradiente | profundidad ∈ {4, 6, 8} × min_child_weight ∈ {1, 10}, con parada temprana |
| XGBoost ponderado | igual, pero da 21 veces más peso a las horas en que el nivel cambia más de 10 cm | igual |
| LSTM | red neuronal recurrente (deep learning) | 24 h de historia, 2 capas de 64 unidades, dropout 0.2, Adam, parada temprana, misma ponderación |

**Configuración elegida en validación:**
- Random Forest: profundidad 20 y 20 muestras por hoja.
- XGBoost: entre 43 y 86 árboles.
- Ridge: alpha = 100.

### 3.6 Métricas (`src/models/metricas.py`)

- **Error del nivel:** RMSE y MAE (cm), NSE del nivel y **NSE del cambio**. El NSE del cambio mide cuánto mejora el modelo sobre la persistencia: 0 significa que es igual a la persistencia y un valor positivo significa que es mejor.
- **Error en crecientes:** RMSE solo en las horas con anomalía real de 0.5 m o más.
- **Detección de alerta amarilla:**
  - POD: proporción de alertas reales detectadas.
  - FAR: proporción de alertas emitidas que fueron falsas.
  - CSI: índice crítico de éxito, que combina las dos.
- **Detección del INICIO de la creciente:** las mismas métricas, pero solo en las horas en que *ahora no hay alerta* y *dentro de h horas sí la habrá*. **Es lo que realmente sirve para avisar con anticipación.**

## 4. Resultados en prueba (2024-2025)

Tabla completa en `reports/modelos_test.csv`.

### 4.1 Horizonte de 1 hora

| Modelo | RMSE (cm) | MAE (cm) | NSE del nivel | NSE del cambio | RMSE en crecientes (cm) | CSI | POD del inicio |
|---|---|---|---|---|---|---|---|
| Persistencia | 3.29 | 1.31 | 0.941 | 0.00 | 26.3 | 0.61 | 0.00 |
| Ridge | 3.04 | 1.25 | 0.950 | 0.15 | 23.3 | 0.64 | 0.05 |
| **Random Forest** | 3.01 | **1.19** | 0.951 | 0.16 | 22.5 | **0.69** | 0.20 |
| XGBoost | **2.97** | 1.21 | **0.952** | **0.19** | 23.4 | 0.67 | 0.05 |
| XGBoost ponderado | 3.40 | 1.45 | 0.937 | −0.07 | 22.7 | 0.65 | 0.30 |
| LSTM | 3.48 | 1.63 | 0.934 | −0.12 | **20.8** | 0.61 | **0.35** |

### 4.2 Horizonte de 3 horas

| Modelo | RMSE (cm) | MAE (cm) | NSE del nivel | NSE del cambio | RMSE en crecientes (cm) | CSI |
|---|---|---|---|---|---|---|
| Persistencia | 6.66 | 2.81 | 0.760 | 0.00 | 52.7 | 0.33 |
| Ridge | 6.21 | 2.62 | 0.791 | 0.13 | 49.5 | 0.36 |
| **Random Forest** | **6.11** | 2.59 | **0.798** | **0.16** | 47.6 | **0.40** |
| XGBoost | 6.25 | **2.58** | 0.789 | 0.12 | 50.5 | 0.37 |
| XGBoost ponderado | 7.05 | 4.08 | 0.731 | −0.12 | **46.4** | 0.37 |
| LSTM | 7.79 | 4.85 | 0.671 | −0.37 | 49.1 | 0.34 |

### 4.3 Horizonte de 6 horas

| Modelo | RMSE (cm) | MAE (cm) | NSE del nivel | NSE del cambio | RMSE en crecientes (cm) | CSI |
|---|---|---|---|---|---|---|
| Persistencia | 9.32 | 4.26 | 0.530 | 0.00 | 70.9 | 0.13 |
| Ridge | 8.28 | 3.69 | 0.630 | 0.21 | 66.7 | 0.18 |
| **Random Forest** | **8.19** | 3.72 | **0.637** | **0.23** | 64.1 | **0.18** |
| XGBoost | 8.32 | **3.66** | 0.626 | 0.20 | 66.5 | 0.18 |
| XGBoost ponderado | 9.78 | 6.30 | 0.483 | −0.10 | **61.0** | 0.17 |
| LSTM | 11.10 | 6.73 | 0.334 | −0.42 | 65.4 | 0.12 |

### 4.4 Pruebas estadísticas (`src/models/pruebas_estadisticas.py`)

**Procedimiento:**
- Los errores horarios están autocorrelacionados (una hora se parece mucho a la siguiente) y eso viola el supuesto de independencia de las pruebas. Por eso se usa como unidad de análisis el **error absoluto medio diario** de cada modelo, con 468 a 470 días pareados.
- **Shapiro-Wilk** sobre las diferencias diarias: **en todos los casos p < 0.001**, así que las diferencias **no son normales**.
- Por lo tanto, en lugar de la t de Student pareada que planteaba la propuesta, se aplica su alternativa no paramétrica: **Wilcoxon de rangos con signo**. La propuesta contemplaba aplicar las pruebas "de acuerdo con las condiciones definidas para el análisis".
- Se aplica la corrección de **Holm** por comparaciones múltiples, con α = 0.05.

**Resultados:**

| Horizonte | Mejor modelo (MAE diario) | Es significativamente mejor que | **No** hay diferencia significativa con |
|---|---|---|---|
| 1 h | **Random Forest** (1.18 cm) | todos: persistencia, ridge, XGBoost, XGBoost ponderado y LSTM | — |
| 3 h | XGBoost (2.57 cm) | persistencia, ridge, XGBoost ponderado y LSTM | **Random Forest** (p = 0.50) |
| 6 h | XGBoost (3.55 cm) | persistencia, XGBoost ponderado y LSTM | **Random Forest** (p = 0.21) y ridge (p = 0.84) |

Tabla completa en `reports/pruebas_estadisticas.csv`.

### 4.5 Enfoque complementario: clasificador de alerta (`src/models/alerta_clasificador.py`)

Se entrenó un clasificador XGBoost que responde directamente "¿habrá alerta amarilla en las próximas h horas?". El umbral de probabilidad se eligió en validación para maximizar el CSI.

| h | Persistencia: CSI / POD del inicio | Clasificador: CSI / POD del inicio |
|---|---|---|
| 1 | 0.61 / 0.00 | 0.57 / 0.05 |
| 3 | 0.48 / 0.00 | 0.43 / 0.11 |
| 6 | 0.36 / 0.00 | 0.30 / 0.02 |

**El clasificador no supera al modelo de regresión**, así que se descarta como modelo principal.

### 4.6 Experimento: ¿ayuda la lluvia de El Batán (parte alta de la cuenca)?

**Motivación:** al revisar los 107 inicios de creciente se encontró que en 19 de ellos no hubo lluvia ni en La Lindosa ni en Los Micos en las 6 h previas. En varios de esos casos sí llovió fuerte en El Batán; por ejemplo, el 04/12/2025 cayeron 53 mm en El Batán y 0 mm en las estaciones bajas.

**Diseño:** El Batán solo tiene lluvia confiable desde 2023. Por eso se compararon dos clasificadores idénticos, con y sin las variables de El Batán, entrenados entre enero de 2023 y junio de 2024 y probados entre julio de 2024 y diciembre de 2025.

**Resultado:** agregar El Batán **no mejoró** la detección (CSI del inicio a 1 h: 0.13 sin El Batán y 0.12 con El Batán). Con solo 18 meses de entrenamiento hay muy pocas crecientes para aprender esa relación. **Vale la pena repetir este experimento cuando haya más años de datos de El Batán.**

## 5. Decisión: modelo seleccionado

### ✅ **Random Forest** para los tres horizontes (1, 3 y 6 h)

1. A **1 h** es el mejor con diferencia estadísticamente significativa frente a todos los demás.
2. A **3 y 6 h** está **estadísticamente empatado** con el mejor (XGBoost) y, además, fue el mejor en validación.
3. Tiene el **mayor CSI de alerta** en los tres horizontes.
4. Un solo tipo de modelo simplifica la integración con el dashboard y su explicación.

**¿Por qué no la LSTM?** En este problema fue el peor modelo en error general, aunque a 1 h detecta un poco mejor los inicios de creciente (POD 0.35 frente a 0.20, pero con FAR de 0.56). Con unas 33,000 horas de entrenamiento y solo 64 crecientes, los modelos de árboles aprovechan mejor los datos. Este resultado es coherente con la literatura cuando hay pocos eventos extremos.

**¿Por qué no los modelos ponderados?** Reducen el error en crecientes, pero empeoran mucho el resto del tiempo (NSE del cambio negativo) y generan más falsas alarmas.

## 6. Interpretación honesta de los resultados (importante para el artículo)

- **Los modelos mejoran sobre la persistencia, pero poco:** el NSE del cambio está entre 0.16 y 0.23. Cuando la creciente ya empezó, los modelos siguen bien su evolución, por ejemplo la recesión. **Sin embargo, casi nunca anticipan el inicio:** a 1 h el Random Forest solo detecta el 20% de los inicios.
- **Causa física:** en La Lindosa la creciente llega **en menos de una hora**. Además, en el 18% de los inicios no hubo lluvia registrada en las dos estaciones disponibles, porque la tormenta cae en la parte alta de la cuenca, donde no hay medición útil para el modelo. Con datos horarios y solo dos pluviómetros, **la información necesaria para anticipar no está en los datos**.
- La figura `reports/figures/pronostico_nov2024.png` lo muestra: en las crecientes de noviembre de 2024 todos los modelos "llegan tarde", igual que la persistencia, y el retraso crece con el horizonte.
- **Este es un resultado válido y publicable:** cuantifica el límite de predictibilidad de la red actual y justifica de forma concreta qué datos hacen falta (sección 8).

## 7. Cómo reproducirlo

Desde `Proyecto Grado`, en PowerShell. Se necesita haber corrido antes el ETL de la fase 1. El entrenamiento tarda unos 10 minutos.

```powershell
.venv\Scripts\python src\models\entrenar.py
.venv\Scripts\python src\models\pruebas_estadisticas.py
.venv\Scripts\python src\models\alerta_clasificador.py
.venv\Scripts\python -m pytest tests
```

**Archivos generados:**

| Archivo | Contenido |
|---|---|
| `reports/modelos_validacion.csv` | desempeño de cada configuración en validación |
| `reports/modelos_test.csv` | métricas finales en prueba |
| `reports/pruebas_estadisticas.csv` | Shapiro-Wilk, Wilcoxon y Holm |
| `reports/alerta_clasificador.csv` | clasificador y experimento de El Batán |
| `reports/predicciones_test.parquet` | pronóstico de cada hora de prueba y cada modelo (**para el dashboard**) |
| `reports/alerta_probabilidades_test.parquet` | probabilidad de alerta por hora |
| `reports/figures/pronostico_nov2024.png` | pronóstico frente a la realidad, noviembre de 2024 |
| `models/` | modelos entrenados (no se suben a Git: se regeneran con el script) |

**Pruebas automáticas:** 22 en total, todas pasan. Son 14 del ETL y 8 de los modelos; entre estas últimas están la verificación de que no se usa el futuro, de que el objetivo excluye valores imputados y de que las particiones no se solapan.

## 8. Problemas, limitaciones y recomendaciones

1. **Resolución temporal:** el paso horario es demasiado grueso para crecientes que llegan en menos de una hora. **Recomendación:** repetir los modelos a 15 minutos con los datos de MeerKAD (2020-2025, registros cada 5 minutos). Es la mejora con más potencial.
2. **Faltan pluviómetros en la parte alta:** la CAM tiene en la cuenca las estaciones meteorológicas El Mesón, San Bartolo y Santa Rosalía, que no están en los datos entregados. **Recomendación:** solicitarlas a la CAM.
3. **El Batán:** repetir el experimento de la sección 4.6 cuando haya más años de lluvia.
4. **Umbrales de alerta:** validarlos con la CAM o con Gestión del Riesgo.
5. **Pocos eventos extremos:** en el periodo de prueba solo hubo 2 eventos de nivel rojo, así que las métricas de alertas altas tienen mucha incertidumbre.

## 9. Siguiente fase

**Fase 3: dashboard en Power BI.**
- Definir los requisitos y diseñar las pantallas.
- Mostrar las series históricas e indicadores de calidad (fase 1), el pronóstico frente a la realidad y el estado de alerta (`reports/predicciones_test.parquet`), y la comparación de modelos.
- Hacer pruebas de usabilidad.
