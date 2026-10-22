# Base de revisión TP3 (Grupo 01 y Grupo 02)

Objetivo: revisar ambas entregas con el mismo criterio técnico y compararlas de forma justa.

## 1) Normalización de ubicación (primero)

Antes de evaluar, consolidar el código final de cada grupo en una ruta única:

- Grupo 01 -> entregas/grupo_01/tp3/
- Grupo 02 -> entregas/grupo_02/tp3/

Estado detectado en este repo:
- Grupo 01 tiene código real en: entregas/grupo_01/ds-mentoring-diplodatos-2026/entregas/grupo_01/tp3_pupi_v2/
- Grupo 02 tiene código real en: entregas/grupo_02/Grupo2_sistema_Deteccion_Oferta_Hotelera/

Sugerencia: copiar solo lo necesario (API, Dockerfile, requirements, src/artifacts, README/reporte) a las carpetas tp3 de cada grupo y evitar duplicados grandes.

## 2) Criterios de revisión (idénticos para ambos)

1. Estructura de entrega y documentación
2. Build y run de Docker
3. API funcionando y contrato claro de input/output
4. Definición de pipeline (unidad de precio, fallback, decisión de oferta)
5. Set de test y metodología de evaluación
6. Métricas reportadas y análisis de errores
7. Trazabilidad/reproducibilidad final

Usar scorecard.csv para puntuar igual a ambos grupos.

## 3) Flujo recomendado de trabajo

1. Completar scorecard de estructura (sin ejecutar nada)
2. Ejecutar Docker/API y completar scorecard técnico
3. Ejecutar casos de test comunes (api_test_cases.csv)
4. Comparar métricas y errores
5. Emitir devolución final por grupo

## 4) Comandos mínimos a validar por grupo

- docker build -t <tag> .
- docker run --rm -p <port>:8000 <tag>
- abrir /docs
- probar POST /predict con payload válido y payload inválido

## 5) Salidas de esta revisión

- scorecard.csv completo
- api_results_grupo_01.csv
- api_results_grupo_02.csv
- informe comparativo final
