# Medidas DAX del dashboard

Créalas en Power BI Desktop desde **Modelado → Nueva medida**. Antes conviene crear una tabla vacía llamada `_Medidas` (**Inicio → Especificar datos → Cargar**) y guardarlas todas ahí.

Los nombres de tablas y columnas son los de los CSV de `dashboard/datos/`.

## 1. Hidrología (páginas "Estado actual" e "Histórico")

```DAX
Nivel promedio (m) = AVERAGE ( hechos_hidrologia[nivel_m] )

Nivel máximo (m) = MAX ( hechos_hidrologia[nivel_max_m] )

Lluvia total (mm) = SUM ( hechos_hidrologia[lluvia_mm] )

Anomalía actual (m) =
VAR ultima = MAX ( hechos_hidrologia[fecha_hora] )
RETURN
    CALCULATE ( AVERAGE ( hechos_hidrologia[anomalia_m] ), hechos_hidrologia[fecha_hora] = ultima )

Nivel actual (m) =
VAR ultima = MAX ( hechos_hidrologia[fecha_hora] )
RETURN
    CALCULATE ( AVERAGE ( hechos_hidrologia[nivel_m] ), hechos_hidrologia[fecha_hora] = ultima )

Línea base (m) = AVERAGE ( hechos_hidrologia[linea_base_m] )

Umbral amarilla (m) = [Línea base (m)] + 0.5
Umbral naranja (m)  = [Línea base (m)] + 1.0
Umbral roja (m)     = [Línea base (m)] + 1.5

Estado de alerta actual =
VAR a = [Anomalía actual (m)]
RETURN
    SWITCH ( TRUE (),
        ISBLANK ( a ), "Sin dato",
        a >= 1.5, "ROJA",
        a >= 1.0, "NARANJA",
        a >= 0.5, "AMARILLA",
        "NORMAL" )

Color alerta actual =
SWITCH ( [Estado de alerta actual],
    "ROJA", "#C62828", "NARANJA", "#EF6C00", "AMARILLA", "#F9A825",
    "NORMAL", "#2E7D32", "#9E9E9E" )

Horas en alerta = CALCULATE ( COUNTROWS ( hechos_hidrologia ), hechos_hidrologia[clase_alerta] >= 1 )

% horas imputadas =
DIVIDE (
    CALCULATE ( COUNTROWS ( hechos_hidrologia ), hechos_hidrologia[nivel_imputado] = TRUE () ),
    CALCULATE ( COUNTROWS ( hechos_hidrologia ), NOT ISBLANK ( hechos_hidrologia[nivel_m] ) ) )
```

## 2. Eventos de creciente

```DAX
N° crecientes = COUNTROWS ( eventos_crecientes )

N° crecientes rojas = CALCULATE ( [N° crecientes], eventos_crecientes[clase_alerta] = 3 )

Pico máximo (m) = MAX ( eventos_crecientes[nivel_max_instantaneo_m] )

Duración media (h) = AVERAGE ( eventos_crecientes[duracion_h] )

% crecientes sin lluvia previa local =
DIVIDE (
    CALCULATE ( [N° crecientes], eventos_crecientes[lluvia_6h_previas_mm] < 1 ),
    [N° crecientes] )
```

## 3. Calidad de datos

```DAX
Completitud nivel (%) = AVERAGE ( calidad_anual[nivel_pct] )

Completitud lluvia (%) = AVERAGE ( calidad_anual[lluvia_pct] )

Completitud ambos (%) = AVERAGE ( calidad_anual[ambos_pct] )
```

## 4. Pronóstico (página "Pronóstico vs real")

En esta página filtra siempre por **horizonte** y por **modelo** con segmentadores.

```DAX
Nivel real (m) = AVERAGE ( hechos_pronostico[nivel_real_m] )

Nivel pronosticado (m) = AVERAGE ( hechos_pronostico[nivel_pred_m] )

Error absoluto medio (cm) = AVERAGE ( hechos_pronostico[error_abs_cm] )

RMSE (cm) = 100 * SQRT ( AVERAGEX ( hechos_pronostico, hechos_pronostico[error_m] ^ 2 ) )

Alertas reales (h) = CALCULATE ( COUNTROWS ( hechos_pronostico ), hechos_pronostico[clase_alerta_real] >= 1 )

Aciertos alerta (h) =
CALCULATE ( COUNTROWS ( hechos_pronostico ),
    hechos_pronostico[clase_alerta_real] >= 1, hechos_pronostico[clase_alerta_pred] >= 1 )

Falsas alarmas (h) =
CALCULATE ( COUNTROWS ( hechos_pronostico ),
    hechos_pronostico[clase_alerta_real] = 0, hechos_pronostico[clase_alerta_pred] >= 1 )

POD = DIVIDE ( [Aciertos alerta (h)], [Alertas reales (h)] )

FAR = DIVIDE ( [Falsas alarmas (h)], [Aciertos alerta (h)] + [Falsas alarmas (h)] )

CSI =
DIVIDE ( [Aciertos alerta (h)],
    [Alertas reales (h)] + [Falsas alarmas (h)] )
```

> Comprobación: con el horizonte "1 h" y el modelo "random_forest", los valores de **POD**, **FAR**, **CSI** y **RMSE** deben coincidir con los de `metricas_modelos.csv` (POD 0.780, FAR 0.147, CSI 0.688, RMSE 3.01 cm). Si no coinciden, revisa la configuración regional, que se explica en la guía.

## 5. Comparación de modelos

```DAX
RMSE test (cm) = AVERAGE ( metricas_modelos[rmse_cm] )

NSE del cambio = AVERAGE ( metricas_modelos[nse_delta] )

CSI test = AVERAGE ( metricas_modelos[csi] )

POD inicio = AVERAGE ( metricas_modelos[pod_inicio] )

Mejora vs persistencia (%) =
VAR persist =
    CALCULATE ( AVERAGE ( metricas_modelos[rmse_cm] ),
        metricas_modelos[modelo] = "persistencia",
        REMOVEFILTERS ( dim_modelo ) )
RETURN
    DIVIDE ( persist - [RMSE test (cm)], persist )
```
