# Fase 1: sistema de calidad de datos (ETL)

**Proyecto:** Desarrollo de un sistema de calidad de datos y modelos predictivos para alertas tempranas de inundaciones en la cuenca del río Las Ceibas
**Responsable:** Harold Camilo Barrera Giraldo
**Fecha de cierre:** 2026-11-26
**Estado:** terminada
**Objetivo de la propuesta que cubre:** objetivo específico 1, "Implementar el sistema de limpieza y validación de datos"

---

## 1. Objetivo de la fase

Construir un proceso **reproducible y probado** que tome los datos crudos de la CAM de las estaciones elegidas en la fase 0, La Lindosa (estación objetivo) y Los Micos (estación de apoyo). El proceso:
- detecta y elimina los datos erróneos;
- imputa solo donde es seguro hacerlo;
- entrega un dataset horario limpio para los modelos (fase 2) y para el dashboard (fase 3).

## 2. Punto de partida

- Datos unificados en `data/interim/` (salida de `cargar_crudos.py`, fase 0).
- Los datos 2017-2019 (MAIGRAI) **no tenían ninguna limpieza**. Los de 2020-2025 (MeerKAD) traían la limpieza de la CAM: control por rangos y eliminación de rachas de más de 20 valores idénticos.
- La tabla de rangos de los PDF de la CAM no se había podido leer bien de forma automática.

## 3. Qué se hizo

### 3.1 Verificación de los rangos oficiales de la CAM

Se revisó visualmente el PDF `Observaciones La Lindosa.pdf`. La tabla correcta es:

| Variable | Rango válido (límites incluidos) |
|---|---|
| temperatura (°C) | [0, 50] |
| humedad (%) | [0, 100] |
| lluvia (mm) | [0, 100] |
| radiación solar (W/m²) | [0, 2000] |
| dirección del viento (°) | [0, 361] |
| velocidad del viento (m/s) | [0, 90] |
| voltaje de batería (VDC) | [0.1, 20] |
| nivel (m) | [0, ∞) |
| presión atmosférica (hPa) | [500, 1100] |

Estos rangos están en `RANGOS_CAM` dentro de `src/etl/calidad.py`.

### 3.2 Exploración de anomalías (antes de diseñar los filtros)

| Revisión | Resultado | Conclusión |
|---|---|---|
| Valores fuera de rango | 0 en las dos estaciones y en las dos fuentes | el filtro se aplica igual, por seguridad, pero no elimina nada |
| Subidas bruscas del nivel (más de 0.5 m en 5 min) | 8 en La Lindosa y 21 en Los Micos | **son crecientes reales**: el nivel sube de golpe y baja de forma gradual. Ejemplo: 1.32 → 2.96 → 3.58 → 3.70 m el 20/02/2022. **No se eliminan** |
| Picos aislados (sube y vuelve de inmediato) | 1 candidato (14/11/2024 06:57, 2.5 m) | está dentro de una creciente real, así que se conserva |
| Nivel idéntico por mucho tiempo | La Lindosa 2017: **0.60 m fijos durante 241 h mientras llovieron 26.6 mm** | sensor pegado: el río no puede quedarse quieto con esa lluvia |
| Huecos de MeerKAD con el mismo valor antes y después | 607 tramos en La Lindosa y 5273 en Los Micos | **la regla de la CAM ("más de 20 valores idénticos = sensor pegado") borró datos válidos**. A 5 minutos, 20 valores son solo 100 minutos, y un río estable medido al centímetro puede quedarse igual ese tiempo |

**Hallazgo importante:** la regla de sensor pegado de la CAM es demasiado agresiva para el nivel en época seca. Por eso se rellenan las "mesetas" (paso 4 del proceso).

### 3.3 El proceso de calidad (`src/etl/calidad.py` y `src/etl/procesar.py`)

Se aplica en este orden sobre los registros originales de cada estación:

| Paso | Función | Regla | Por qué |
|---|---|---|---|
| 1 | `control_rangos` | rangos oficiales de la CAM (tabla 3.1) | mismo criterio que la CAM, y además se aplica a 2017-2019, que nunca se había limpiado |
| 2 | `quitar_picos_aislados` | un registro que se aleja más de 0.5 m de su anterior y de su siguiente, cuando esos dos vecinos difieren 0.15 m o menos entre sí y están a 20 min o menos | elimina errores de un solo registro sin tocar las crecientes reales, en las que el nivel se queda arriba |
| 3 | `quitar_sensor_pegado` | nivel idéntico durante **72 h o más**, o durante **6 h o más con 10 mm o más de lluvia** en la estación | detección con base física: si llueve fuerte y el nivel no se mueve ni 1 cm, el sensor no responde. Un río estable sin lluvia **sí** se conserva |
| 4 | `rellenar_mesetas` | hueco de 60 min o menos con el **mismo valor** antes y después (diferencia de 0.5 cm o menos) → se rellena con ese valor | recupera los datos válidos que borró la regla de la CAM |
| 5 | `horario` (en `procesar.py`) | paso horario regular. Nivel: promedio, y también el máximo en `nivel_max_m`. Lluvia: suma. **Si una hora tiene menos del 50% de los registros esperados, la lluvia de esa hora queda vacía** | frecuencia común a las dos fuentes. Una hora con pocos registros subestimaría la lluvia |
| 6 | `imputar_huecos_cortos` | interpolación lineal **solo en huecos de 6 h o menos** y nunca en los bordes. Se marca en `nivel_m_imputado` | método elegido por el experimento de la sección 3.4 |

### 3.4 Experimento: ¿qué método de imputación es mejor? (`src/etl/evaluar_imputacion.py`)

**Diseño:**
- Se ocultan tramos de nivel **real** de La Lindosa de 1, 2, 3, 6, 12 y 24 horas, se rellenan con cada método y se mide el error contra el valor verdadero.
- Por cada duración se toman 300 tramos normales y 300 tramos que contienen una creciente (nivel de 1.2 m o más), con semilla 42 para que sea reproducible.

**Métodos comparados:**
- **constante:** repetir el último valor.
- **lineal:** interpolación lineal entre los dos bordes del hueco.
- **micos:** regresión lineal desde el nivel de Los Micos, ajustada en ±3.5 días alrededor del hueco y corregida para coincidir con los bordes.

**Resultados** (error absoluto medio, en centímetros):

| Hueco | Método | Sin creciente | Con creciente |
|---|---|---|---|
| 1 h | constante / **lineal** / micos | 0.87 / **0.52** / 0.61 | 12.6 / **6.4** / 7.3 |
| 2 h | constante / **lineal** / micos | 1.04 / **0.73** / 0.82 | 14.5 / **7.2** / 8.6 |
| 3 h | constante / **lineal** / micos | 1.16 / **0.68** / 0.78 | 17.7 / **10.3** / 11.1 |
| 6 h | constante / **lineal** / micos | 1.90 / **1.15** / 1.21 | 18.6 / 10.9 / **10.8** |
| 12 h | constante / lineal / micos | 2.36 / 1.74 / 1.81 | 20.0 / 12.9 / 11.7 |
| 24 h | constante / lineal / micos | 2.80 / 2.11 / 2.12 | 18.2 / 14.2 / 12.2 |

La tabla completa está en `reports/evaluacion_imputacion.csv`.

**Conclusiones:**
1. **La interpolación lineal es el mejor método en huecos de hasta 6 horas.** Fuera de las crecientes su error es de alrededor de 1 cm, menor que la resolución del sensor.
2. Usar Los Micos **solo mejora un poco a partir de las 12 horas**, y ahí el error en crecientes sigue siendo de 12 cm o más. Esa mejora no justifica imputar huecos largos.
3. **Los huecos de más de 6 horas no se imputan.** En plena creciente el error pasaría de 10 cm, y entrenar el modelo con crecientes inventadas sería peor que no tenerlas.

### 3.5 Pruebas automáticas (`tests/test_calidad.py`)

Hay 14 pruebas con pytest y **las 14 pasan**. Verifican, entre otras cosas, que:
- una creciente real **no** se confunde con un pico;
- un río estable sin lluvia **no** se marca como sensor pegado;
- los huecos de más de 6 h y los bordes de la serie **no** se imputan;
- la lectura de fechas en formato día/mes funciona;
- una columna desconocida en un archivo nuevo detiene el proceso, en lugar de ignorarse en silencio.

## 4. Resultados

### 4.1 Qué cambió (`reports/bitacora_limpieza.csv`)

| | La Lindosa | Los Micos |
|---|---|---|
| Registros crudos 2017-2025 | 607,575 | 609,480 |
| Valores fuera de rango | 0 | 0 |
| Picos aislados eliminados | 0 | 0 |
| Sensor pegado: tramos y registros eliminados | 12 / 696 | 13 / 981 |
| Registros recuperados en mesetas | 775 | 5,320 |
| Horas imputadas por interpolación | 96 | 759 |

### 4.2 Antes y después, en serie horaria (`reports/calidad_antes_despues.csv`)

| Estación | Completitud del nivel antes → después | Huecos totales antes → después | Huecos de 6 h o menos antes → después |
|---|---|---|---|
| La Lindosa | 89.2% → 88.5% | 135 → 90 | 54 → 1 |
| Los Micos | 86.1% → 85.8% | 537 → 100 | 449 → 1 |

La completitud baja un poco porque ahora se eliminan datos **malos** que antes contaban como válidos, como el sensor pegado de 2017. A cambio, los huecos se reducen de forma drástica, porque casi todos los huecos cortos quedan resueltos.

### 4.3 Dataset final

`data/processed/dataset_modelo.parquet` (y una copia `.csv` para Power BI): serie horaria del 01/01/2017 al 31/12/2025, con 78,888 filas.

| Columna | Descripción |
|---|---|
| `nivel_lindosa_m` | **variable objetivo**: nivel medio horario en La Lindosa |
| `nivel_max_lindosa_m` | nivel máximo dentro de la hora |
| `nivel_lindosa_imputado` | verdadero si el nivel fue interpolado |
| `lluvia_lindosa_mm`, `temperatura_lindosa_c` | variables de La Lindosa |
| `nivel_micos_m`, `nivel_micos_imputado`, `lluvia_micos_mm`, `temperatura_micos_c` | variables de la estación de apoyo |

Completitud por año (% de horas con dato):

| Año | Nivel La Lindosa | Lluvia La Lindosa | Nivel Los Micos | Lluvia Los Micos |
|---|---|---|---|---|
| 2017 | 33.5 | 41.1 | 22.9 | 43.3 |
| 2018 | 97.7 | 97.4 | 93.9 | 97.7 |
| 2019 | 92.0 | 91.6 | 89.2 | 95.1 |
| 2020 | 97.4 | 97.1 | 81.7 | 81.4 |
| 2021 | 99.8 | 99.8 | 98.9 | 82.7 |
| 2022 | 94.3 | 94.3 | 98.6 | 98.5 |
| 2023 | 98.9 | 99.9 | 99.6 | 99.6 |
| 2024 | 94.6 | 98.3 | 91.9 | 90.8 |
| 2025 | 87.8 | 87.4 | 95.4 | 93.8 |

**Entre 2018 y 2025 el 87.4% de las horas (61,274) tienen completas las 4 variables principales.** Es una base sólida para entrenar los modelos.

Figuras: `reports/figures/limpieza_La_Lindosa.png` y `limpieza_Los_Micos.png` (antes y después, con los puntos imputados en rojo).

## 5. Cómo reproducirlo

Desde `Proyecto Grado`, en PowerShell:

```powershell
.venv\Scripts\python src\etl\cargar_crudos.py
.venv\Scripts\python src\etl\procesar.py
.venv\Scripts\python src\etl\evaluar_imputacion.py
.venv\Scripts\python -m pytest tests
```

## 6. Problemas y limitaciones

- **Deriva de la línea base del nivel:** el nivel normal de La Lindosa baja de unos 0.85 m (2018-2022) a unos 0.5 m (2025). Puede deberse a cambios en el cauce, a una reinstalación o a una recalibración del sensor. **Hay que preguntarle a la CAM** si hubo intervenciones. Para los modelos (fase 2) conviene trabajar con el nivel relativo a una línea base reciente o con variaciones del nivel, no con el valor absoluto.
- **2017 es poco confiable:** las estaciones empiezan a mitad de año y en julio-agosto hay tramos planos en 0.60 m. Se recomienda entrenar desde 2018.
- **Lluvia en 0 sostenida:** la lluvia pasa largos periodos en 0, lo cual es normal. Sin embargo, no hay forma de detectar un pluviómetro tapado que marque 0 mientras llueve. Se podría contrastar con estaciones meteorológicas cercanas de la CAM (El Mesón, San Bartolo), que no están en los datos entregados.
- Los umbrales de sensor pegado (72 h, o 6 h con 10 mm) y de picos (0.5 m) son decisiones del proyecto con justificación física. Conviene validarlas con el director o con la CAM.

## 7. Pendientes y siguiente fase

**Fase 2: modelos predictivos.**
1. Definir el horizonte de predicción (1, 3 y 6 h) y los umbrales de alerta del nivel.
2. Construir las variables de entrada: lluvia acumulada, nivel rezagado, variación del nivel y datos de Los Micos.
3. Hacer una partición temporal de entrenamiento, validación y prueba, sin mezclar fechas.
4. Entrenar modelos base (persistencia, regresión), de machine learning (Random Forest, XGBoost) y de deep learning (LSTM).
5. Comparar con RMSE, MAE, NSE y métricas de detección de crecientes, y aplicar las pruebas estadísticas (Shapiro-Wilk y t pareada o Wilcoxon).
