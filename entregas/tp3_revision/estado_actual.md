# Estado actual de evaluación TP3

Fecha: 2026-10-20

## 1) Compatibilidad de estructuras

No son idénticas, pero son compatibles para evaluación.

- Grupo 01 (código completo):
  - `entregas/grupo_01/ds-mentoring-diplodatos-2026/entregas/grupo_01/tp3_pupi_v2/`
- Grupo 02 (código completo):
  - `entregas/grupo_02/Grupo2_sistema_Deteccion_Oferta_Hotelera/`

Conclusión: se evalúan con scorecard común y set de casos común.

## 2) Compatibilidad de API

No comparten el mismo contrato de endpoint/payload:

- Grupo 01: `POST /predict` (campo `price`)
- Grupo 02: `POST /evaluate` (campo `price_total`, más `nights`)

Conclusión: para benchmark justo se usa un dataset común y un adaptador por grupo.

## 3) Error de Docker detectado y resolución

Error inicial en ambos builds:
- `Temporary failure in name resolution` durante `pip install`.

Causa:
- DNS de Docker (bridge) no resolvía PyPI en este entorno.

Verificación:
- `docker run --rm busybox nslookup pypi.org` -> falla
- `docker run --rm --network host busybox nslookup pypi.org` -> OK

Resolución aplicada:
- Build con red del host: `docker build --network host ...`

Resultado:
- Grupo 01: build OK
- Grupo 02: build OK

## 4) Prueba de ejecución de APIs (realizada)

Se levantaron ambas APIs en puertos distintos:
- Grupo 01 en `localhost:8001`
- Grupo 02 en `localhost:8002`

Chequeos:
- `/docs` grupo 01: HTTP 200
- `/docs` grupo 02: HTTP 200
- `POST` válido grupo 01: HTTP 200
- `POST` válido grupo 02: HTTP 200

Ejemplo de respuesta:
- Grupo 01 (payload de ejemplo) -> `decision: oferta`, `oferta: SI`
- Grupo 02 (payload de ejemplo) -> `decision: no_deal`

Conclusión: ambas APIs corren y responden correctamente.

## 5) Casos de promoción/no promoción y benchmark

Sí, ya quedó ejecutado benchmark con set común de 8 casos:
- `entregas/tp3_revision/api_test_cases.csv`
- resultados por caso: `entregas/tp3_revision/api_results_comparativo.csv`
- métricas agregadas: `entregas/tp3_revision/comparativo_metricas.csv`

Métricas obtenidas (sobre casos con etiqueta esperada):
- Grupo 01: `accuracy=0.875`, `precision=1.0`, `recall=0.667`, `f1=0.8`, `coverage=1.0`.
- Grupo 02: `accuracy=0.625`, `recall=0.0`, `coverage=1.0`.

Observación clave:
- Grupo 02 tiende a clasificar sistemáticamente como `no_deal` en este set, por sensibilidad alta a la unidad de precio normalizado.

## 6) ¿Están bien en revisión general TP3?

Estado actualizado:
- Sí, ambas entregas son evaluables técnicamente (Docker/API OK).
- Benchmark comparativo ejecutado y documentado.
- Diferencia principal no funcional: contrato API y semántica de precio no alineadas entre grupos (requiere adaptador para comparación justa).

## 7) Entregables de resultados de evaluación

Disponibles en `entregas/tp3_revision/`:
- `scorecard.csv` (criterios por grupo, completado)
- `api_results_comparativo.csv` (predicciones y normalización por caso)
- `comparativo_metricas.csv` (métricas comparables)
- `evaluate_apis.py` (script reproducible)

Pendiente recomendado:
- emitir devolución docente final en `informe_final_tp3.md`.
