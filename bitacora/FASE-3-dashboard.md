# Fase 3: dashboard en Power BI

**Proyecto:** Desarrollo de un sistema de calidad de datos y modelos predictivos para alertas tempranas de inundaciones en la cuenca del río Las Ceibas
**Responsable:** Harold Camilo Barrera Giraldo
**Fecha:** 2026-11-26
**Estado:** 🟡 **preparación terminada; falta construir el .pbix y hacer las pruebas con usuarios**
**Objetivo de la propuesta que cubre:** objetivo específico 3, "Desarrollar el dashboard". Incluye requisitos, diseño UI/UX, construcción y pruebas funcionales y de usabilidad.

---

## 1. Objetivo de la fase

Construir un dashboard en Power BI que integre:
- los datos limpios (fase 1);
- las crecientes históricas;
- los indicadores de calidad;
- los pronósticos y la comparación de modelos (fase 2).

Además, evaluar su funcionamiento y su usabilidad.

## 2. Punto de partida

- Resultados de las fases 1 y 2 en `data/processed/` y `reports/`.
- **Power BI Desktop no estaba instalado en el equipo**, y el archivo `.pbix` solo se puede construir en Power BI Desktop. Por eso esta fase se dividió en dos partes:
  1. **Preparación**, que es todo lo que se puede automatizar y está terminada.
  2. **Construcción y pruebas** en Power BI, que las hace Harold siguiendo la guía.

## 3. Qué se hizo

### 3.1 Requisitos

Están definidos en `dashboard/GUIA_CONSTRUCCION.md` (sección 1):
- **2 perfiles de usuario:** académico, y técnico de la CAM o de Gestión del Riesgo.
- **8 requisitos funcionales (RF1-RF8):** entre ellos, ver el estado de alerta en cualquier momento, comparar el pronóstico con lo que ocurrió, consultar el histórico de crecientes, la calidad de los datos y la comparación de modelos, y el aviso de que la herramienta "no es una alerta oficial".
- **Requisitos no funcionales:** una pregunta por página, colores de alerta consistentes, funcionamiento sin conexión y cifras iguales a las de la bitácora.

### 3.2 Modelo de datos (`src/dashboard/exportar_powerbi.py`)

El modelo es un esquema en estrella con 12 tablas CSV, que se generan en `dashboard/datos/`:

| Tabla | Filas | Contenido |
|---|---|---|
| `dim_estacion` | 6 | coordenadas, municipio, corriente, distancia a Neiva y rol (objetivo, apoyo o descartada) |
| `dim_fecha` | 3,287 | año, mes, temporada (lluviosa: mar-may y oct-dic) y periodo del modelo |
| `dim_alerta` | 4 | normal, amarilla, naranja y roja, con su umbral y color |
| `dim_modelo` | 6 | los 6 modelos, con familia y cuál fue el seleccionado |
| `hechos_hidrologia` | 157,776 | nivel, lluvia, línea base, anomalía y clase de alerta por hora (La Lindosa y Los Micos) |
| `hechos_pronostico` | 185,832 | pronóstico frente a la realidad (2024-2025) para 6 modelos y 3 horizontes |
| `eventos_crecientes` | 112 | cada creciente con anomalía de 0.5 m o más: inicio, duración, pico y lluvia |
| `calidad_anual` | 54 | completitud de nivel y lluvia por estación y año |
| `calidad_antes_despues`, `calidad_bitacora` | 4 y 2 | resultado de la limpieza |
| `metricas_modelos`, `pruebas_estadisticas` | 18 y 15 | resultados de la fase 2 |

### 3.3 Diseño de las páginas (UI/UX)

El diseño completo, con bocetos y la lista de visuales, está en `GUIA_CONSTRUCCION.md` (sección 5):

| Página | Pregunta que responde |
|---|---|
| 1. Estado actual | ¿Cómo está el río ahora y qué se espera en 1, 3 y 6 h? Permite "reproducir" cualquier momento de 2024-2025 |
| 2. Histórico y crecientes | ¿Cuándo y con qué fuerza ha crecido el río entre 2017 y 2025? |
| 3. Calidad de datos | ¿Qué tan confiables son los datos y por qué se eligió La Lindosa? |
| 4. Pronóstico vs real | ¿Qué tan bien pronostica el modelo? |
| 5. Comparación de modelos | ¿Por qué Random Forest? |

**Decisiones de diseño:**
- **Colores de alerta fijos** (verde, amarillo, naranja y rojo), siguiendo la convención de los sistemas de alerta temprana en Colombia.
- **Tema propio:** `dashboard/tema_ceibas.json`.
- **Pie de página obligatorio** con el aviso de herramienta de apoyo, en coherencia con la propuesta.
- La página 1 simula un monitoreo con datos históricos, porque el proyecto no tiene acceso en tiempo real a la transmisión de la CAM.

### 3.4 Medidas DAX (`dashboard/medidas_dax.md`)

Son unas 35 medidas en 5 grupos: hidrología, crecientes, calidad, pronóstico (RMSE, POD, FAR, CSI) y comparación de modelos. Incluyen una **comprobación cruzada**: con Random Forest a 1 h deben dar exactamente las métricas de la fase 2.

### 3.5 Protocolo de pruebas (`dashboard/PRUEBAS_USABILIDAD.md`)

- **8 pruebas funcionales (PF1-PF8)** con el resultado esperado. Los valores se verificaron contra los datos, por ejemplo: el 14/11/2024 a las 06:00 el estado es NARANJA, con nivel de 2.09 m y anomalía de +1.41 m.
- **Prueba de usabilidad con 5 participantes:** 5 tareas con tiempo objetivo y el cuestionario **SUS** en español. El criterio de aceptación es un SUS de 68 o más y al menos el 80% de las tareas completadas.

## 4. Resultados

| Entregable | Estado |
|---|---|
| Requisitos funcionales y no funcionales | ✅ |
| Modelo de datos (12 CSV) y script de exportación | ✅ |
| Diseño de las 5 páginas | ✅ |
| Medidas DAX | ✅ |
| Tema de colores | ✅ |
| Guía de construcción paso a paso | ✅ |
| Protocolo de pruebas funcionales y de usabilidad | ✅ |
| **Archivo `Alertas_Las_Ceibas.pbix`** | ⏳ lo construye Harold |
| **Pruebas funcionales y de usabilidad ejecutadas** | ⏳ pendiente |

## 5. Cómo reproducirlo

Desde `Proyecto Grado`, en PowerShell:

```powershell
.venv\Scripts\python src\dashboard\exportar_powerbi.py
```

Después, seguir `dashboard/GUIA_CONSTRUCCION.md` en Power BI Desktop.

## 6. Problemas y limitaciones

- **Configuración regional:** Power BI con configuración de Colombia lee mal el punto decimal de los CSV. La guía indica cómo evitarlo (sección 2, paso 1).
- **No hay datos en tiempo real:** el dashboard muestra datos históricos. Conectarlo a la transmisión satelital de la CAM queda como trabajo futuro (fase 4).
- **Tamaño de los datos:** los CSV ocupan unos 36 MB y no se suben a Git; se regeneran con el script.

## 7. Pendientes para cerrar la fase

1. Instalar Power BI Desktop y construir el `.pbix` con la guía.
2. Hacer las pruebas funcionales PF1-PF8.
3. Hacer las pruebas con 5 usuarios y registrar los resultados en este informe, con la tabla de la plantilla.
4. Ajustar el dashboard según los comentarios.
5. Exportar el PDF y hacer commit del `.pbix` y del `.pdf`.

## 8. Siguiente fase

**Fase 4: integración.** Un solo comando que ejecute todo el flujo: datos crudos → ETL → modelos → tablas de Power BI. Además, la documentación técnica del flujo completo.
