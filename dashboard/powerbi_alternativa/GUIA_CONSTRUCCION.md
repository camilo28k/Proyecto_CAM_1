# Guía para construir el dashboard en Power BI Desktop

**Resultado esperado:** el archivo `dashboard/Alertas_Las_Ceibas.pbix`, con 5 páginas.
**Tiempo estimado:** de 3 a 4 horas.

## 0. Requisitos previos

1. Instala **Power BI Desktop**. Es gratis y está en Microsoft Store.
2. Genera los datos del dashboard. Desde `Proyecto Grado`, en PowerShell:
   ```powershell
   .venv\Scripts\python src\dashboard\exportar_powerbi.py
   ```
   Esto crea 12 archivos CSV en `dashboard/datos/`. No se suben a Git porque se regeneran con el script.

---

## 1. Requisitos del dashboard

### 1.1 Usuarios
- **Director, comité y jurados:** quieren entender el proyecto y sus resultados.
- **Técnico de la CAM o de Gestión del Riesgo:** quiere ver el estado del río, las crecientes y qué tan confiable es el pronóstico.

### 1.2 Requisitos funcionales

| ID | El usuario puede… | Página |
|---|---|---|
| RF1 | ver el nivel, la anomalía y el **estado de alerta** en cualquier fecha y hora del periodo de prueba | Estado actual |
| RF2 | ver el pronóstico a 1, 3 y 6 h junto con el nivel que realmente ocurrió | Estado actual / Pronóstico |
| RF3 | explorar la serie histórica 2017-2025 de nivel y lluvia, filtrando por estación y fecha | Histórico |
| RF4 | consultar la lista de crecientes: fecha, pico, duración y lluvia | Histórico |
| RF5 | ver la completitud de los datos por estación y año, y lo que hizo la limpieza | Calidad de datos |
| RF6 | ver dónde están las estaciones y por qué se eligió La Lindosa | Calidad de datos |
| RF7 | comparar los modelos con sus métricas y las pruebas estadísticas | Modelos |
| RF8 | entender que la herramienta **es de apoyo y no es una alerta oficial** | todas (pie de página) |

### 1.3 Requisitos no funcionales
- Se entiende en menos de 10 segundos qué muestra cada página: título claro y una sola pregunta por página.
- La alerta siempre usa los mismos colores: verde = normal, amarillo, naranja y rojo.
- Funciona sin conexión, porque los datos son locales.
- Todas las cifras coinciden con los informes de la bitácora.

---

## 2. Cargar los datos

1. **Archivo → Opciones → Archivo actual → Configuración regional → Inglés (Estados Unidos).**
   ⚠️ **Esto es crítico.** Los CSV usan punto decimal. Con la configuración regional de Colombia, `0.85` se leería como 85.
2. **Inicio → Obtener datos → Texto/CSV** y carga uno por uno los 12 archivos de `dashboard/datos/`.
3. En Power Query revisa los tipos de cada columna:
   - `fecha_hora`, `fecha_hora_origen`, `fecha_hora_objetivo`, `inicio`, `fin` y `fecha_pico` → **Fecha y hora**.
   - `fecha` → **Fecha**.
   - `nivel_imputado`, `en_cuenca_ceibas`, `seleccionado` → **Verdadero/Falso**.
4. **Cerrar y aplicar.**
5. **Ver → Temas → Examinar temas** y selecciona `dashboard/tema_ceibas.json`.

## 3. Relaciones (vista de modelo)

| Desde (1) | Hacia (varios) | Dirección del filtro |
|---|---|---|
| `dim_estacion[estacion]` | `hechos_hidrologia[estacion]` | única |
| `dim_estacion[estacion]` | `calidad_anual[estacion]` | única |
| `dim_estacion[estacion]` | `calidad_antes_despues[estacion]` | única |
| `dim_fecha[fecha]` | `hechos_hidrologia[fecha]` | única |
| `dim_fecha[fecha]` | `hechos_pronostico[fecha]` | única |
| `dim_fecha[fecha]` | `eventos_crecientes[fecha]` | única |
| `dim_alerta[clase_alerta]` | `hechos_hidrologia[clase_alerta]` | única |
| `dim_alerta[clase_alerta]` | `eventos_crecientes[clase_alerta]` | única |
| `dim_modelo[modelo]` | `hechos_pronostico[modelo]` | única |
| `dim_modelo[modelo]` | `metricas_modelos[modelo]` | única |

Borra cualquier relación que Power BI haya creado sola y no esté en esta tabla.

**Orden y formato:**
- Ordena `dim_alerta[alerta]` por la columna `orden` (**Herramientas de columnas → Ordenar por columna**).
- Ordena `dim_fecha[nombre_mes]` por `mes`.
- En la columna `latitud` elige **Categoría de datos → Latitud**, y en `longitud` elige **Longitud**.

## 4. Medidas

Crea las medidas de [`medidas_dax.md`](medidas_dax.md). Al terminar, haz la **comprobación** del final de la sección 4 de ese archivo.

---

## 5. Diseño de las páginas

Todas las páginas tienen tamaño 16:9. Llevan un título arriba a la izquierda y un pie de página con este texto:
*"Herramienta académica de apoyo. No reemplaza las alertas oficiales de la CAM ni de Gestión del Riesgo."*

### Página 1: Estado actual (simulación de monitoreo)

**Pregunta que responde:** ¿cómo está el río en este momento y qué se espera en las próximas horas?

```
┌──────────────────────────────────────────────────────────────────────┐
│ Estado del río Las Ceibas – La Lindosa      [Segmentador fecha-hora] │
├──────────────┬──────────────┬──────────────┬─────────────────────────┤
│ NIVEL ACTUAL │  ANOMALÍA    │ ESTADO       │  Pronóstico RF          │
│   1.87 m     │  +1.05 m     │  NARANJA     │  +1h 1.95 │+3h 1.80│+6h │
│ (tarjeta)    │ (tarjeta)    │ (tarjeta     │  (tarjeta de varias filas)│
│              │              │  con color)  │                         │
├──────────────┴──────────────┴──────────────┴─────────────────────────┤
│ Gráfico de líneas: nivel real (negro) y pronóstico RF a 1/3/6 h,     │
│ más las líneas de umbral amarilla, naranja y roja, en las 48 h       │
│ alrededor del momento elegido                                        │
├──────────────────────────────────────┬───────────────────────────────┤
│ Columnas: lluvia horaria             │ Tarjeta de texto: qué significa│
│ en La Lindosa y Los Micos            │ cada color y sus umbrales     │
└──────────────────────────────────────┴───────────────────────────────┘
```

**Cómo armarla:**
- **Segmentador:** `hechos_pronostico[fecha_hora_origen]`, de tipo "Entre", limitado a 2024-2025. Así se "reproduce" cualquier momento del periodo de prueba.
- **Tarjeta de estado:** muestra la medida `Estado de alerta actual`. En **Formato → Valor → fx**, pon el color de fuente con `Color alerta actual`.
- **Gráfico de pronóstico:**
  - Eje X: `fecha_hora_objetivo`.
  - Valores: `Nivel real (m)` y `Nivel pronosticado (m)`.
  - Leyenda: `horizonte`.
  - Filtro del visual: `modelo = random_forest`.
- **Evento recomendado para la sustentación:** del 13 al 16 de noviembre de 2024, con picos de 1.9 y 2.6 m.

### Página 2: Histórico y crecientes

**Pregunta que responde:** ¿cuándo y con qué fuerza ha crecido el río entre 2017 y 2025?

- **Segmentadores:** estación (`dim_estacion[nombre]`), año (`dim_fecha[anio]`) y temporada.
- **Gráfico de líneas:** eje X `fecha` (con jerarquía año/mes/día); valores `Nivel promedio (m)` y `Nivel máximo (m)`.
- **Gráfico de columnas:** `Lluvia total (mm)` por `anio_mes`.
- **Tarjetas:**
  - `N° crecientes`
  - `N° crecientes rojas`
  - `Pico máximo (m)` (usa `nivel_max_instantaneo_m`)
  - `% crecientes sin lluvia previa local`

  Esta última apoya un hallazgo de la fase 2: casi 1 de cada 5 crecientes ocurre sin lluvia local previa.
- **Tabla de eventos:** `inicio`, `duracion_h`, `nivel_max_instantaneo_m`, `anomalia_pico_m`, `lluvia_evento_mm` y `alerta`. Aplica formato condicional por color de alerta.
- **Columnas apiladas:** crecientes por `anio` y por `alerta`, para mostrar en qué meses y años se concentran.

### Página 3: Calidad de datos

**Pregunta que responde:** ¿qué tan confiables son los datos y qué se hizo para limpiarlos?

- **Mapa** (visual "Mapa" o "Mapa de Azure"):
  - Latitud y longitud de `dim_estacion`.
  - Leyenda: `rol`.
  - Tamaño: `distancia_neiva_km`.
  - Agrega un punto de referencia para Neiva (2.927, −75.282) como texto en la página.
- **Matriz de completitud:**
  - Filas: estación. Columnas: año. Valor: `nivel_pct`.
  - Formato condicional de fondo en escala rojo (0) → verde (100). Reproduce el mapa de calor de la fase 0.
- **Tabla `calidad_bitacora`:** sensor pegado, mesetas recuperadas y horas imputadas.
- **Columnas agrupadas `calidad_antes_despues`:** completitud y huecos, antes y después.
- **Cuadro de texto:** "¿Por qué La Lindosa?", con 3 viñetas de la fase 0: mejores datos (95%), la más cercana a Neiva (16 km) y cauce principal.

### Página 4: Pronóstico vs real

**Pregunta que responde:** ¿qué tan bien pronostica el modelo?

- **Segmentadores:** `horizonte` y `dim_modelo[nombre_modelo]`, este último con Random Forest preseleccionado.
- **Gráfico de líneas:** `Nivel real (m)` frente a `Nivel pronosticado (m)` por `fecha_hora_objetivo`.
- **Gráfico de dispersión:**
  - Eje X `nivel_real_m`, eje Y `nivel_pred_m` (con detalle por `fecha_hora_origen`).
  - Agrega una línea de referencia y = x.
- **Tarjetas:** `RMSE (cm)`, `Error absoluto medio (cm)`, `POD`, `FAR` y `CSI`.
- **Matriz "alerta real vs alerta pronosticada":**
  - Filas `clase_alerta_real`, columnas `clase_alerta_pred`, valores = recuento.
  - Funciona como matriz de confusión.
- **Cuadro de texto con la interpretación de la fase 2:** "El modelo sigue bien la evolución de la creciente, pero anticipa poco su inicio porque la creciente llega en menos de 1 hora."

### Página 5: Comparación de modelos

**Pregunta que responde:** ¿por qué se eligió Random Forest?

- **Barras agrupadas:** `RMSE test (cm)` por modelo, con leyenda `h`.
- **Barras agrupadas:** `CSI test` por modelo y `h`.
- **Tabla `metricas_modelos`:** modelo, h, rmse_cm, mae_cm, nse_delta, csi y pod_inicio. Usa barras de datos en el RMSE.
- **Tabla `pruebas_estadisticas`:** h, mejor, comparado_con, prueba, p_holm y diferencia_significativa. Resalta en verde las filas con `diferencia_significativa = Falso`, que son los empates estadísticos.
- **Tarjeta:** "Modelo seleccionado: Random Forest". Usa `Mejora vs persistencia (%)` filtrada a random_forest.

## 6. Interacciones y navegación
- Agrega botones de navegación entre las páginas (**Insertar → Botones → Navegador → Navegador de páginas**).
- En la página 2, al hacer clic en un evento de la tabla se debe filtrar el gráfico de líneas. Es el comportamiento por defecto de Power BI.
- Información sobre herramientas: al pasar el mouse sobre el nivel, debe mostrar también la anomalía y la clase de alerta.

## 7. Guardar
- Guarda como `dashboard/Alertas_Las_Ceibas.pbix`.
- Exporta un PDF (**Archivo → Exportar → PDF**) a `dashboard/Alertas_Las_Ceibas.pdf`, para anexarlo al documento final.
- Después de cerrar Power BI, haz commit del `.pbix` y del `.pdf`.

## 8. Lista de verificación final

- [ ] Configuración regional en Inglés (EE. UU.): los niveles se ven como 0.8 y no como 80.
- [ ] Con `random_forest` y `1 h`, la página 4 muestra un CSI de 0.688 y un RMSE de 3.01 cm.
- [ ] La matriz de completitud coincide con la tabla de la sección 3.4 del informe de la fase 0.
- [ ] La página 2 muestra 112 crecientes en total (2017-2025).
- [ ] Todas las páginas tienen el pie de página de "herramienta de apoyo".
- [ ] Se hicieron las pruebas de usabilidad (`PRUEBAS_USABILIDAD.md`).
