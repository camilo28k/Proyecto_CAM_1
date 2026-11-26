# Fase 3: dashboard (Streamlit)

**Proyecto:** Desarrollo de un sistema de calidad de datos y modelos predictivos para alertas tempranas de inundaciones en la cuenca del río Las Ceibas
**Responsable:** Harold Camilo Barrera Giraldo
**Fecha:** 2026-11-26
**Estado:** 🟡 **dashboard construido y con las pruebas funcionales aprobadas; faltan las pruebas de usabilidad con usuarios**
**Objetivo de la propuesta que cubre:** objetivo específico 3, "Desarrollar el dashboard". Incluye requisitos, diseño UI/UX, construcción y pruebas funcionales y de usabilidad.

---

## 1. Objetivo de la fase

Construir un dashboard que integre los datos limpios, las crecientes históricas, los indicadores de calidad, los pronósticos y la comparación de modelos, y evaluar su funcionamiento y su usabilidad.

## 2. Decisión: Streamlit en lugar de Power BI

La propuesta planteaba Power BI. **Harold decidió hacer el dashboard en Streamlit** y lo hablará con el director. Comparación de las dos opciones:

| Criterio | Streamlit | Power BI |
|---|---|---|
| Lenguaje | Python, el mismo del ETL y de los modelos | DAX y la interfaz gráfica |
| Versionable en Git | ✅ es código | ❌ el `.pbix` es un archivo binario |
| Pruebas automáticas | ✅ `streamlit.testing` | ❌ |
| Reproducible con un comando | ✅ | se arma a mano |
| Puede ejecutar el modelo | ✅ (a futuro, pronóstico en vivo) | no directamente |
| Costo y licencia | libre | Desktop gratis; para publicar se necesita licencia |

La preparación que se hizo para Power BI se conserva en `dashboard/powerbi_alternativa/` (guía, medidas DAX y tema) por si el comité la exige. Las tablas que genera `src/dashboard/exportar_powerbi.py` las usan **los dos** dashboards.

## 3. Qué se hizo

### 3.1 Requisitos

**Usuarios:**
- académico: director, comité y jurados;
- técnico de la CAM o de Gestión del Riesgo.

**Requisitos funcionales:**

| ID | El usuario puede… | Página |
|---|---|---|
| RF1 | ver el nivel, la anomalía y el estado de alerta en cualquier hora de 2024-2025 | Estado del río |
| RF2 | ver el pronóstico a 1, 3 y 6 h y compararlo con lo que ocurrió | Estado del río / Pronóstico vs real |
| RF3 | explorar el histórico de nivel y lluvia 2017-2025, por estación y años | Histórico |
| RF4 | consultar la lista de crecientes con pico, duración y lluvia | Histórico |
| RF5 | ver la completitud de los datos por estación y año, y lo que hizo la limpieza | Calidad de datos |
| RF6 | ver en un mapa dónde están las estaciones y por qué se eligió La Lindosa | Calidad de datos |
| RF7 | comparar los modelos y ver las pruebas estadísticas | Comparación de modelos |
| RF8 | ver que la herramienta es de apoyo y no es una alerta oficial | pie de página en todas |

**Requisitos no funcionales:**
- una pregunta por página;
- colores de alerta fijos (verde, amarillo, naranja y rojo);
- funcionamiento sin conexión, salvo el mapa base de OpenStreetMap;
- cifras iguales a las de la bitácora.

### 3.2 Estructura (`app/`)

```
.streamlit/config.toml     tema de colores
app/app.py                 punto de entrada y menú de navegación
app/comun.py               carga de datos con caché, colores, aviso y pie de página
app/paginas/1_estado.py    🚨 Estado del río
app/paginas/2_historico.py 📈 Histórico y crecientes
app/paginas/3_calidad.py   🧹 Calidad de datos
app/paginas/4_pronostico.py 🎯 Pronóstico vs real
app/paginas/5_modelos.py   🏆 Comparación de modelos
```

**Fuente de datos:** las tablas de `dashboard/datos/`, que genera `src/dashboard/exportar_powerbi.py` (etapa 9 de `src/pipeline.py`). Se usan los gráficos interactivos de Plotly.

### 3.3 Páginas

| Página | Qué muestra |
|---|---|
| **Estado del río** | Se elige una fecha y una hora de 2024-2025. Muestra el nivel, la anomalía, la **insignia de alerta** y el pronóstico Random Forest a +1, +3 y +6 h con su valor real; un gráfico de 48 h con el nivel real, los umbrales y los pronósticos, y las barras de lluvia de las dos estaciones. Si en esa hora faltan datos, muestra un aviso. |
| **Histórico y crecientes** | Selector de estación y rango de años. Indicadores: número de crecientes, crecientes rojas, nivel máximo y porcentaje sin lluvia local previa. Gráfico de nivel diario con la lluvia mensual, crecientes por año y alerta, crecientes por mes, y una tabla de eventos con color de alerta. |
| **Calidad de datos** | Mapa con las 6 estaciones y Neiva; "¿Por qué La Lindosa?"; mapa de calor de completitud por estación y año (nivel, lluvia o ambos); bitácora de limpieza y huecos antes y después. |
| **Pronóstico vs real** | Selector de horizonte, modelo y periodo. Indicadores RMSE, MAE, POD, FAR y CSI calculados en vivo; serie real frente a pronóstico; dispersión con la línea y = x; matriz de alertas real frente a pronosticada; e interpretación. |
| **Comparación de modelos** | RMSE y CSI por modelo y horizonte, tabla de métricas resaltada y pruebas estadísticas, con los empates en amarillo y la decisión explicada. |

### 3.4 Ajustes tras la revisión visual en el navegador

- Se desactivó el zoom del mapa con la rueda del ratón y se centró el mapa.
- La matriz de alertas ahora muestra números enteros.
- **Error encontrado y corregido:** los valores p de las pruebas estadísticas se exportaban con 4 decimales y aparecían como 0 (por ejemplo, 3.4e-70 se convertía en 0.0000). Ahora se exportan con precisión completa.

## 4. Resultados

### 4.1 Pruebas funcionales: **8 de 8 aprobadas**

Están en `app/PRUEBAS_USABILIDAD.md`, sección A. Por ejemplo:
- el 14/11/2024 a las 06:00 la página muestra NARANJA, nivel 2.09 m, anomalía +1.41 m y pronóstico de 2.19 m a 1 h (real 2.37 m);
- con Random Forest a 1 h muestra RMSE 3.01 cm y CSI 0.69, **iguales a los de la fase 2**.

### 4.2 Pruebas automáticas

`tests/test_app.py` tiene 7 pruebas: cada página se ejecuta sin errores, el estado del 14/11/2024 es NARANJA y una hora sin datos muestra el aviso. **En total pasan 32 pruebas en el proyecto.**

### 4.3 Pruebas de usabilidad: ⏳ pendientes

El protocolo está listo en `app/PRUEBAS_USABILIDAD.md`, sección B:
- 5 participantes;
- 5 tareas cronometradas;
- cuestionario SUS en español;
- criterio de aceptación: SUS de 68 o más y al menos el 80% de las tareas completadas.

## 5. Cómo reproducirlo

Desde `Proyecto Grado`, en PowerShell.

Generar los datos (si no existen):
```powershell
.venv\Scripts\python src\pipeline.py --rapido
```

Abrir el dashboard (se abre en http://localhost:8501):
```powershell
.venv\Scripts\streamlit run app\app.py
```

Ejecutar las pruebas:
```powershell
.venv\Scripts\python -m pytest tests
```

## 6. Problemas y limitaciones

- **Datos históricos:** la página "Estado del río" simula el monitoreo con datos de 2024-2025. No hay conexión en tiempo real con la CAM.
- **Mapa base:** el mapa de OpenStreetMap necesita internet; el resto del dashboard funciona sin conexión.
- **Publicación:** por ahora el dashboard corre en el computador local. Para publicarlo en la web se puede usar Streamlit Community Cloud, que es gratis y se conecta al repositorio de GitHub, pero habría que subir también los datos o generarlos en la nube.

## 7. Pendientes para cerrar la fase

1. Hacer las pruebas con 5 usuarios y registrar los resultados en la plantilla de `app/PRUEBAS_USABILIDAD.md`.
2. Ajustar el dashboard según los comentarios.
3. Comentar con el director el cambio de Power BI a Streamlit.
