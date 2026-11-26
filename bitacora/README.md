# Bitácora de fases del proyecto

Si eres nuevo en el proyecto, empieza aquí. Cada fase tiene un informe con lo que se hizo, las decisiones tomadas y por qué, los resultados y cómo reproducirlos.

| Fase | Tema | Estado | Informe |
|---|---|---|---|
| 0 | Organización, inventario de los datos y selección de la estación | ✅ Terminada (2026-11-26) | [FASE-0](FASE-0-organizacion-y-seleccion-estacion.md) |
| 1 | Sistema de calidad de datos (ETL) | ✅ Terminada (2026-11-26) | [FASE-1](FASE-1-sistema-calidad-datos.md) |
| 2 | Modelos predictivos | ✅ Terminada (2026-11-26) | [FASE-2](FASE-2-modelos-predictivos.md) |
| 3 | Dashboard (Streamlit) | 🟡 Construido y con pruebas funcionales aprobadas; faltan las pruebas con usuarios | [FASE-3](FASE-3-dashboard.md) |
| 4 | Integración | ✅ Terminada (2026-11-26) | [FASE-4](FASE-4-integracion.md) |
| 5 | Artículo y documento final | ⏳ Pendiente | — |

**Decisión central hasta ahora:** se predice el nivel del río en la estación **La Lindosa** (cauce principal del río Las Ceibas, a ~16 km de Neiva). **Los Micos** se usa como estación de apoyo.

**Modelo seleccionado (fase 2):** Random Forest, que pronostica el cambio de nivel a 1, 3 y 6 h. Sigue bien la evolución de las crecientes, pero anticipa poco su inicio. La causa es que la creciente llega en menos de una hora y faltan datos de lluvia en la parte alta de la cuenca (ver la sección 6 del informe de la fase 2).
