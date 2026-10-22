# Devolución para estudiantes — Grupo 02 (TP3)

Fecha: 2026-10-21

## Resultado general
Entrega técnicamente correcta en ejecución (Docker/API funcionan), con buena arquitectura de servicio y explicabilidad. El punto crítico está en la consistencia metodológica de la unidad de precio.

## Fortalezas destacadas
1. **Infraestructura y servicio**
   - API estable y bien organizada.
   - Respuestas con explicación legible.

2. **Diseño de cascada**
   - Estrategia de fallback clara y mantenible.

3. **Trazabilidad del pipeline**
   - Estructura de proyecto y artefactos en buen estado.

## Hallazgo crítico
1. **Unidad de precio / normalización**
   - Se detecta sensibilidad muy alta a cómo se codifica `price_total`.
   - En benchmark robusto, el recall para `deal` cambia fuertemente según convención de entrada.
   - Esto impacta directamente en subdetección de ofertas.

## Qué mejorar (prioridad)
1. **P0 — Cerrar contrato de unidad de precio**
   - Alinear entrenamiento, inferencia y documentación con una única convención.
   - Agregar ejemplos canónicos y casos de test que validen esa convención.

2. **P0 — Recalibrar umbrales tras alinear unidad**
   - Reestimar `z_log_threshold`/`min_discount` con validación ciega estratificada.

3. **P1 — Reportar métricas por segmento**
   - Soporte de contexto, país, estadía y ocupación.
   - Mostrar explícitamente recall/FPR por estrato.

4. **P1 — Fortalecer tests funcionales API**
   - Casos `invalid_input`, `invalid_price`, `insufficient_data` y payloads borde.

## Prioridades sugeridas
- **Semana 1 (P0):** unidad + contrato + tests de consistencia.
- **Semana 2 (P0/P1):** recalibración de umbrales + benchmark robusto.
- **Semana 3 (P1):** informe segmentado y cierre final.

## Cierre
La base técnica es buena. Con corrección de unidad y recalibración, el sistema debería mejorar significativamente su capacidad de detectar `deal` sin perder control operativo.
