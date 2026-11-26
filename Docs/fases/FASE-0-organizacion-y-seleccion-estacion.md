# Fase 0: organización del proyecto, inventario de los datos y selección de la estación

**Proyecto:** Desarrollo de un sistema de calidad de datos y modelos predictivos para alertas tempranas de inundaciones en la cuenca del río Las Ceibas
**Responsable:** Harold Camilo Barrera Giraldo
**Director:** Ing. Álvaro Hernán Alarcón López
**Fecha de cierre:** 2026-11-26
**Estado:** terminada

---

## 1. Objetivo de la fase

1. Crear desde cero la estructura del proyecto: carpetas, entorno de Python y control de versiones.
2. Hacer el inventario de los datos entregados por la CAM y unificarlos en un solo formato.
3. Medir la calidad de los datos de cada estación.
4. **Elegir la estación** para los modelos predictivos, con base en dos criterios: (a) la calidad de los datos y (b) qué tan cerca está de Neiva y qué riesgo de inundación representa para la ciudad.
5. Definir si hace falta imputar datos y con qué método.

## 2. Punto de partida

- Datos crudos en `Datos_CAM/`: 6 carpetas, una por estación, con 36 CSV, 16 Excel y 6 PDF de observaciones. En total 87 MB.
- No había código, entorno de trabajo ni datos procesados.
- La carpeta `Docs/` (propuesta, cartas y certificado) ya se entregó y **no se modifica**.

## 3. Qué se hizo

### 3.1 Estructura del proyecto

```
Proyecto Grado/
├── Docs/                 documentos entregados (no se tocan)
├── Datos_CAM/            datos originales de la CAM (solo lectura)
├── data/interim/         datos unificados (los genera el ETL, no se versionan)
├── data/processed/       datos finales para los modelos (fase 1)
├── src/etl/              código del ETL
├── src/models/           código de los modelos (fase 2)
├── notebooks/            exploración
├── reports/              tablas y figuras de resultados
├── dashboard/            Power BI (fase 3)
├── paper/                artículo (fase 5)
└── docs/fases/           estos informes
```

- Entorno virtual `.venv` con Python 3.14. Las librerías y sus versiones exactas quedan en `requirements.txt`: pandas, numpy, openpyxl, matplotlib y pyarrow.
- El repositorio Git se inicializó. `.gitignore` excluye `.venv` y `data/`, porque los datos se regeneran con los scripts.

### 3.2 Cómo están los datos crudos

| Aspecto | Datos 2017-2019 (y La Lindosa hasta 26/02/2020) | Datos 2020-2025 |
|---|---|---|
| Aplicación de origen | MAIGRAI | MeerKAD |
| Formato | Excel (`.xlsx`) | CSV con separador `;`, coma decimal y codificación Windows-1252 |
| Frecuencia | horaria | cada ~5 minutos, con horas desfasadas (0:03, 0:08…) |
| Limpieza previa de la CAM | ninguna | valores fuera de rango reemplazados por vacíos (NaN) y rachas de más de 20 valores idénticos eliminadas (según los PDF) |

**Problemas encontrados y cómo se resolvieron:**
- `Las Juntas_2019(1).xlsx` es una copia idéntica de `Las Juntas_2019.xlsx`. Se omite.
- `Las_Juntas_2020.csv` tiene dos columnas sin nombre al final. Se descartan.
- El Batán tiene una columna `Rad,_U (W/m2)` que no está documentada. Se descarta.
- Los nombres de columna varían en tildes, símbolos y orden. Se normalizaron a `nivel_m`, `lluvia_mm`, `temperatura_c`, `humedad_pct`, `radiacion_wm2`, `vel_viento_ms`, `dir_viento_grados`, `vel_agua_ms` y `presion_hpa`.
- La tabla de rangos válidos de los PDF de observaciones sale desordenada al extraer el texto. Hay que verificarla visualmente en la fase 1 antes de usarla.

### 3.3 Unificación (`src/etl/cargar_crudos.py`)

Para cada estación el script lee todos sus archivos y estandariza las columnas, fechas y tipos. También marca la fuente de cada registro (MAIGRAI o MeerKAD) y elimina las marcas de tiempo duplicadas; si se solapan, prefiere MeerKAD.

Genera dos archivos:
- `data/interim/<estacion>_crudo.parquet`: todos los registros originales, unificados.
- `data/interim/<estacion>_horario.parquet`: una serie con paso **horario** regular. El nivel se promedia y además se guarda el máximo de cada hora en `nivel_max_m`. La lluvia se suma.

**Decisión: se trabaja con paso horario**, porque es la frecuencia común a las dos fuentes. Además, si en una hora no hubo registros, la lluvia queda vacía (NaN) y no en 0, para no inventar "horas secas".

### 3.4 Diagnóstico de calidad (`src/etl/diagnostico_calidad.py`)

El script calcula la completitud (% de horas con dato) por estación y por año, los huecos, las rachas de valores constantes y estadísticos básicos. Los resultados quedan en `reports/calidad_por_anio.csv`, `reports/calidad_resumen.csv` y en las figuras `reports/figures/completitud_nivel.png` y `series_nivel.png`.

**Completitud del nivel (% de horas con dato):**

| Estación | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|
| **La Lindosa** | 41 | 98 | 92 | 97 | 100 | 94 | 99 | 94 | 88 |
| **Los Micos** | 24 | 98 | 95 | 78 | 97 | 98 | 100 | 91 | 94 |
| El Batán | 88 | 14 | 0 | 3 | 25 | 54 | 58 | 79 | 93 |
| Las Juntas | 24 | 89 | 0 | 2 | 82 | 82 | 32 | 66 | 74 |
| San Benito | 97 | 8 | 0 | 0 | 0 | 0 | 12 | 84 | 55 |
| Puente Bruselas | 60 | 0 | 0 | 1 | 2 | 10 | 16 | 63 | 88 |

En 2017 la completitud es baja en varias estaciones porque empiezan a registrar a mitad de año, en junio.

**Resumen 2021-2025:**

| Estación | Nivel % | Lluvia % | Nivel y lluvia % | Hueco más largo (días) | Nivel máximo horario (m) |
|---|---|---|---|---|---|
| La Lindosa | 94.9 | 96.1 | 94.9 | 173.5 (en 2017) | 3.70 |
| Los Micos | 95.8 | 93.3 | 92.5 | 277.6 | 2.23 |
| Las Juntas | 67.2 | 83.8 | 67.1 | 469.7 | 2.68 |
| El Batán | 61.6 | 55.5 | 42.8 | 1027 | 4.23 |
| Puente Bruselas | 35.8 | 24.9 | 21.6 | 782 | 1.92 |
| San Benito | 30.1 | 64.4 | 30.1 | 2090 | 7.77 |

### 3.5 Ubicación de las estaciones respecto a Neiva

Las coordenadas y la corriente que mide cada estación se tomaron del inventario oficial de estaciones de la CAM publicado en datos.gov.co (conjunto `6rgn-esfk`). La distancia es en línea recta hasta el centro de Neiva (2.927 N, 75.282 O).

| Estación | Municipio | Corriente | Coordenadas | Distancia a Neiva | ¿Está en la cuenca de Las Ceibas? |
|---|---|---|---|---|---|
| **La Lindosa** | Neiva | **Río Las Ceibas (cauce principal)** | 2°52'38" N, 75°08'52" O | 15.9 km | **Sí** |
| **Los Micos** | Neiva | Quebrada Los Micos (afluente de Las Ceibas) | 2°54'55" N, 75°07'57" O | 16.6 km | **Sí** |
| El Batán | Neiva | Río Las Ceibas (parte alta) | 2°47'48" N, 75°04'30" O | 27.2 km | Sí, pero en la parte alta |
| Las Juntas | Rivera | Río Frío | 2°45'29" N, 75°12'43" O | 20.4 km | **No** |
| San Benito | Garzón | Quebrada Garzón | 2°10'58" N, 75°35'58" O | 90 km | **No** |
| Puente Bruselas | Pitalito | Quebrada Guachicos | 1°47'06" N, 76°09'50" O | 160 km | **No** |

**Hallazgo importante:** Las Juntas, San Benito y Puente Bruselas no miden el río Las Ceibas. No sirven para predecir el nivel de este río, así que quedan fuera del modelo. Se pueden mencionar como estaciones de la red de la CAM, pero no de esta cuenca.

**Hay que confirmar con la CAM o con el director** el caso de El Batán: el inventario lo asigna al río Las Ceibas, pero otro registro de la CAM lo menciona sobre el río Neiva.

### 3.6 Riesgo para Neiva

- El río Las Ceibas atraviesa Neiva y desemboca en el río Magdalena dentro del casco urbano. Además, **es la fuente principal del acueducto de la ciudad**.
- Las crecientes súbitas del río afectan a Neiva de dos formas:
  - **Inundación directa** de asentamientos cercanos al cauce. Las noticias mencionan, por ejemplo, Los Andesitos y Tenerife Bajo.
  - **Cortes de agua**, porque la turbiedad obliga a cerrar las plantas de tratamiento El Jardín y Kennedy. Según Radio Nacional, esto afecta a cerca del 80% del área urbana.
- En febrero de 2017 hubo avenidas torrenciales documentadas en Neiva y en otros municipios del Huila, y la UNGRD atendió a los afectados por las crecientes de los ríos Las Ceibas, Frío y Neiva.
- **En los datos de La Lindosa** el nivel mediano es 0.80 m, pero hay **59 días con nivel máximo por encima de 1.5 m**. Los picos más altos son:
  - 3.70 m el 20 de febrero de 2022;
  - 3.50 m el 29 de octubre de 2022;
  - 3.05 m el 13 de marzo de 2021;
  - 2.86 m el 22 de noviembre de 2022;
  - alrededor de 2.65 m varias veces en noviembre de 2024.

  Son estos eventos los que el modelo debe aprender a anticipar.
- Por estar en el cauce principal y ser la estación hidrometeorológica más cercana a Neiva, La Lindosa es el punto donde mejor se refleja lo que va a llegar a la ciudad. Toda la cuenca alta, incluida la zona de Los Micos, drena hacia ella antes de llegar al casco urbano.

## 4. Decisiones y por qué

### Decisión 1: la estación objetivo es **La Lindosa** (variable a predecir: `nivel_m`)

| Criterio | La Lindosa |
|---|---|
| Calidad de los datos | la mejor: 94.9% de nivel y 96.1% de lluvia en 2021-2025, y más de 88% todos los años desde 2018 |
| Longitud de la serie | 2017-2025, con más de 8 años útiles |
| Ubicación | cauce principal del río Las Ceibas, a ~16 km de Neiva, la estación más cercana |
| Relevancia para el riesgo | registra crecientes de hasta 3.7 m, cuatro veces su nivel normal |
| Variables | nivel, lluvia y temperatura |

### Decisión 2: **Los Micos** se usa como estación de apoyo

Tiene muy buena calidad de datos (95.8% de nivel) y mide un afluente de Las Ceibas aguas arriba. Su lluvia y su nivel se usarán como **variables de entrada** del modelo de La Lindosa, porque aportan información de la cuenca alta.

Una observación técnica: las variaciones horarias de nivel de las dos estaciones se correlacionan sobre todo en la misma hora (r = 0.26 con desfase 0 y 0.04 con desfase de 1 hora). La creciente llega rápido, en menos de una hora. Esto indica que el horizonte de predicción debe ser corto, de 1 a 6 horas, y que en la fase 2 conviene evaluar también datos a 15 minutos.

### Decisión 3: El Batán queda como opcional

Podría aportar información de la parte alta de la cuenca, pero su nivel solo está completo de forma aceptable desde 2024 y su lluvia falta entre 2019 y 2022. Se decidirá en la fase 2 si aporta algo útil.

### Decisión 4: se descartan Las Juntas, San Benito y Puente Bruselas

No pertenecen a la cuenca de Las Ceibas (ver la sección 3.5).

### Decisión 5: estrategia de imputación

Análisis de los huecos del nivel de La Lindosa entre 2018 y 2025 (3352 horas sin dato, el 4.8%):

| Duración del hueco | Tramos | Horas | Qué se hará |
|---|---|---|---|
| 1 hora | 33 | 33 | interpolación lineal |
| 2 a 6 horas | 19 | 63 | interpolación lineal o spline, marcando cada dato como imputado |
| 7 a 24 horas | 45 | 696 | **no se imputa**: se deja vacío y esas ventanas se excluyen del entrenamiento |
| 1 a 7 días | 28 | 1742 | no se imputa |
| más de 7 días | 3 | 818 | no se imputa (mayo de 2019, enero de 2022 y febrero de 2024) |

- **Por qué no se imputan los huecos largos:** en esos periodos tampoco hay lluvia registrada en La Lindosa, porque la estación estaba apagada. Solo se pierden 14.9 mm de los 7734 mm del periodo, así que casi no se pierden eventos de lluvia. Rellenar días enteros inventaría la dinámica del río y le enseñaría patrones falsos al modelo.
- **Alternativa que se evaluará en la fase 1:** en el 75% de las horas sin dato de La Lindosa, Los Micos sí tiene nivel. Se puede probar una imputación por regresión desde Los Micos para los huecos medianos, siempre comparando su error contra la interpolación simple.
- Toda imputación quedará marcada en una columna `nivel_imputado` (verdadero o falso), para que los análisis puedan distinguir el dato medido del dato estimado.

## 5. Resultados (archivos)

| Archivo | Contenido |
|---|---|
| `src/etl/cargar_crudos.py` | carga y unificación de los datos crudos |
| `src/etl/diagnostico_calidad.py` | diagnóstico de calidad |
| `data/interim/*_crudo.parquet` y `*_horario.parquet` | datos unificados por estación |
| `data/interim/resumen_carga.csv` | registros, periodo y variables de cada estación |
| `reports/calidad_por_anio.csv` y `calidad_resumen.csv` | indicadores de calidad |
| `reports/figures/completitud_nivel.png` | mapa de calor de la completitud mensual |
| `reports/figures/series_nivel.png` | series de nivel de las 6 estaciones |

## 6. Cómo reproducirlo

Desde la carpeta `Proyecto Grado`, en PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python src\etl\cargar_crudos.py
.venv\Scripts\python src\etl\diagnostico_calidad.py
```

## 7. Problemas y limitaciones

- La tabla de rangos válidos de los PDF de la CAM no se pudo leer bien de forma automática. Hay que verificarla a mano.
- Hay que confirmar con la CAM si El Batán está sobre el río Las Ceibas o sobre el río Neiva.
- Los datos de 2017-2019 (MAIGRAI) no tuvieron ninguna limpieza previa, así que en la fase 1 se les deben aplicar los mismos filtros que a los de MeerKAD.
- Los Micos tiene 6038 horas en tramos de 24 horas o más con exactamente el mismo valor de nivel. Hay que revisar si es un sensor pegado o un río estable en época seca.
- El paso horario puede ser grueso para crecientes que llegan en menos de una hora. Se evaluará en la fase 2.

## 8. Pendientes y siguiente fase

**Fase 1: sistema de calidad de datos** para La Lindosa y Los Micos:
1. Aplicar el control por rangos (verificados) y la detección de sensor pegado y de saltos imposibles a todo el periodo 2017-2025.
2. Imputar los huecos cortos según la decisión 5 y marcarlos.
3. Producir un reporte de calidad antes y después de la limpieza.
4. Generar el dataset final en `data/processed/`.
5. Agregar pruebas automáticas del ETL.

## Fuentes

- CAM, inventario de estaciones hidrometeorológicas (datos.gov.co, conjunto `6rgn-esfk`): https://www.datos.gov.co/api/views/6rgn-esfk/rows.xml?accessType=DOWNLOAD
- CAM, visita a la cuenca del río Las Ceibas: https://archivo.cam.gov.co/1219-l%C3%ADderes-de-la-comuna-8-de-neiva-recorrieron-la-cuenca-del-r%C3%ADo-las-ceibas.html
- El Universal (2017), ayudas a los afectados por las crecientes en el Huila: https://www.eluniversal.com.co/colombia/2017/02/23/entregan-primeras-ayudas-humanitarias-a-afectados-por-crecientes-en-huila/
- Radio Nacional, Neiva sin agua por lluvias: https://www.radionacional.co/noticia/regiones/huila/ola-invernal/neiva-sin-agua-vias-cerradas
- Radio Nacional, crecientes y viviendas inundadas en Neiva: https://radionacional.co/actualidad/intensas-lluvias-en-neiva-dejan-crecientes-y-cientos-de-viviendas-inundadas
- Estudio sobre las avenidas torrenciales de febrero de 2017 en el Huila: https://core.ac.uk/download/288921883.pdf
