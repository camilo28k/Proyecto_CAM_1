# Manual de uso: cómo descargar, ejecutar y revisar el proyecto

**Proyecto:** Desarrollo de un sistema de calidad de datos y modelos predictivos para alertas tempranas de inundaciones en la cuenca del río Las Ceibas
**Autor:** Harold Camilo Barrera Giraldo – Ingeniería de Sistemas, CORHUILA
**Director:** Ing. Álvaro Hernán Alarcón López
**Repositorio:** https://github.com/camilo28k/Proyecto_CAM_1

Este manual explica, paso a paso y en orden, cómo poner a funcionar el proyecto en un computador con Windows y qué revisar primero. No se necesita experiencia previa con el proyecto.

---

## 1. Qué hace el proyecto (en un minuto)

1. **Limpia los datos** de las estaciones hidrometeorológicas de la CAM (2017-2025). Detecta sensores pegados, picos falsos y huecos, y rellena solo los huecos cortos.
2. **Pronostica el nivel del río Las Ceibas** en la estación **La Lindosa**, la más cercana a Neiva, **a 1, 3 y 6 horas**. Usa un modelo **Random Forest**, elegido tras comparar 6 modelos con pruebas estadísticas.
3. **Muestra todo en un dashboard web** hecho en Streamlit: el estado del río, la alerta (verde, amarilla, naranja o roja), las crecientes históricas, la calidad de los datos y la comparación de modelos.

> ⚠️ Es una herramienta académica de apoyo. **No reemplaza las alertas oficiales** de la CAM ni de Gestión del Riesgo.

---

## 2. Requisitos (se instalan una sola vez)

| Programa | Para qué | Dónde se obtiene |
|---|---|---|
| **Python 3.14** | ejecutar el proyecto | https://www.python.org/downloads/. Durante la instalación, marcar **"Add python.exe to PATH"** |
| **Git** | descargar el repositorio | https://git-scm.com/download/win. Opcional: también se puede descargar el ZIP desde GitHub |

**Espacio en disco:** unos 2 GB, por las librerías de Python y los datos generados.
**Internet:** se necesita para la instalación y para ver el mapa del dashboard.

---

## 3. Paso a paso

Todos los comandos se escriben en **PowerShell**: menú Inicio → escribir "PowerShell" → Enter.

### Paso 1. Descargar el proyecto

```powershell
cd $HOME\Desktop
```
```powershell
git clone https://github.com/camilo28k/Proyecto_CAM_1.git
```
```powershell
cd Proyecto_CAM_1
```

> **Sin Git:** en la página del repositorio, pulsar **Code → Download ZIP**, descomprimirlo en el Escritorio y entrar a la carpeta con `cd`.

### Paso 2. Crear el entorno de Python e instalar las librerías (unos 5 minutos)

```powershell
python -m venv .venv
```
```powershell
.venv\Scripts\python -m pip install -r requirements.txt
```

### Paso 3. Generar los datos y el modelo (unos 4 minutos)

Los datos procesados y los modelos **no se suben a GitHub** porque se regeneran a partir de los datos originales de la CAM, que sí están en `Datos_CAM/`. Este comando hace todo:

```powershell
.venv\Scripts\python src\pipeline.py --rapido
```

Al final debe aparecer algo así:

```
[1/6] carga ... ok
[2/6] diagnostico ... ok
[3/6] limpieza ... ok
[4/6] operativo ... ok
[5/6] powerbi ... ok
[6/6] pronostico ... ok
Flujo completo en 3.4 min.
```

> `--rapido` usa los resultados de la comparación de modelos que ya vienen en el repositorio, en `reports/`. Para **repetir todo el experimento** (entrenar y comparar los 6 modelos, unos 15 minutos), usar `.venv\Scripts\python src\pipeline.py` sin `--rapido`. Los resultados son idénticos.

### Paso 4. Abrir el dashboard

```powershell
.venv\Scripts\streamlit run app\app.py
```

El navegador se abre solo en **http://localhost:8501**. Si no se abre, hay que copiar esa dirección en el navegador. Para cerrar el dashboard, pulsar `Ctrl + C` en PowerShell.

### Paso 5 (opcional). Verificar que todo funciona

```powershell
.venv\Scripts\python -m pytest tests
```

Debe terminar con **`32 passed`**.

---

## 4. Qué revisar primero en el dashboard (recorrido de 10 minutos)

| Orden | Página | Qué hacer | Qué se debe ver |
|---|---|---|---|
| 1 | 🚨 **Estado del río** | Dejar la fecha que viene por defecto: **14/11/2024 a las 06:00** | Estado **NARANJA**, nivel de 2.09 m. Pronóstico a +1 h de 2.19 m (real 2.37 m) y la gráfica de la creciente |
| 2 | 🚨 Estado del río | Cambiar a **01/02/2024 a las 12:00** | Estado **NORMAL** |
| 3 | 📈 **Histórico y crecientes** | Mover el rango de años a **2022-2022** | 20 crecientes y nivel máximo de **3.70 m** |
| 4 | 🧹 **Calidad de datos** | Ver el mapa y el mapa de calor | Por qué se eligió **La Lindosa**: los mejores datos (95%), la más cercana a Neiva (16 km) y sobre el cauce principal. Tres estaciones son de **otras cuencas** |
| 5 | 🎯 **Pronóstico vs real** | Random Forest a 1 h | RMSE de **3.01 cm** y CSI de **0.69**; cambiar el horizonte a 3 h y a 6 h para ver cómo crece el error |
| 6 | 🏆 **Comparación de modelos** | Leer la decisión | Random Forest es el mejor a 1 h, con diferencia significativa; la LSTM fue la peor |

**Pronóstico desde la terminal, para cualquier fecha:**
```powershell
.venv\Scripts\python src\pronosticar.py pronosticar --fecha "2024-11-14 06:00"
```

---

## 5. Dónde está la documentación

**Para entender el proyecto, leer en este orden:**

1. [`bitacora/README.md`](bitacora/README.md): estado de cada fase y las decisiones principales.
2. [`bitacora/FASE-0-…`](bitacora/FASE-0-organizacion-y-seleccion-estacion.md): los datos y por qué se eligió La Lindosa.
3. [`bitacora/FASE-1-…`](bitacora/FASE-1-sistema-calidad-datos.md): el sistema de calidad de datos (objetivo específico 1).
4. [`bitacora/FASE-2-…`](bitacora/FASE-2-modelos-predictivos.md): los modelos predictivos y las pruebas estadísticas (objetivo específico 2). **La sección 6 explica el alcance y las limitaciones del pronóstico.**
5. [`bitacora/FASE-3-…`](bitacora/FASE-3-dashboard.md): el dashboard (objetivo específico 3) y por qué se usó Streamlit.
6. [`bitacora/FASE-4-…`](bitacora/FASE-4-integracion.md): la integración y la reproducibilidad.
7. [`ARQUITECTURA.md`](ARQUITECTURA.md): el diagrama técnico y cómo agregar datos nuevos de la CAM.

### Estructura de carpetas

```
Proyecto_CAM_1/
├── MANUAL.md            ← este archivo
├── README.md            resumen corto
├── ARQUITECTURA.md      documentación técnica
├── bitacora/            informe de cada fase (qué se hizo, decisiones, resultados)
├── Docs/                documentos entregados (propuesta, cartas, certificado)
├── Datos_CAM/           datos originales de la CAM (no se modifican)
├── src/
│   ├── etl/             sistema de calidad de datos
│   ├── models/          modelos predictivos y pruebas estadísticas
│   ├── dashboard/       exportación de tablas para el dashboard
│   ├── pipeline.py      ejecuta todo el flujo
│   └── pronosticar.py   pronóstico operativo
├── app/                 dashboard Streamlit (5 páginas)
├── tests/               32 pruebas automáticas
├── reports/             tablas y figuras de resultados
└── .streamlit/          configuración del tema del dashboard
```

---

## 6. Problemas frecuentes

| Problema | Solución |
|---|---|
| `python` no se reconoce como comando | Reinstalar Python marcando **"Add python.exe to PATH"**, o usar `py` en lugar de `python` en el paso 2 |
| PowerShell no deja ejecutar scripts | Los comandos de este manual no usan `Activate.ps1`, así que no debería ocurrir. Si aparece, ejecutar `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| El dashboard dice "Falta dashboard/datos/…" | No se hizo el paso 3. Ejecutar `.venv\Scripts\python src\pipeline.py --rapido` |
| El mapa de la página "Calidad" sale en blanco | El mapa base necesita internet; el resto funciona sin conexión |
| El puerto 8501 está ocupado | `.venv\Scripts\streamlit run app\app.py --server.port 8502` |
| El paso 2 falla al instalar `torch` con un mensaje sobre *Long Path* | La carpeta tiene una ruta muy larga. Clonar el proyecto en una ruta corta, por ejemplo `C:\Proyecto_CAM_1` o el Escritorio, y repetir el paso 2 |
| El paso 2 falla al instalar `torch` por otro motivo | Verificar la conexión a internet. `torch` se descarga del repositorio oficial de PyTorch, como indica `requirements.txt` |

---

## 7. Cómo subir cambios al repositorio (para Harold)

Desde la carpeta del proyecto:

```powershell
git add -A
```
```powershell
git commit -m "Descripción del cambio"
```
```powershell
git push
```

**Qué no se sube:**
- `.venv/`, `data/`, `models/`, `dashboard/datos/` y `logs/`. Se regeneran con el paso 3 y están en `.gitignore`.
- Al terminar una fase se actualiza su informe en `bitacora/`.
