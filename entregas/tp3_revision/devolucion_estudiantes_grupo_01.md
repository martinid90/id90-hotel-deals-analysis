# Devolución para estudiantes — Grupo 01 (TP3)

Fecha: 2026-10-21

## Resultado general
Muy buen trabajo técnico y metodológico. La entrega está bien estructurada, reproducible y con API funcional.

## Fortalezas destacadas
1. **Ejecución técnica sólida**
   - Docker/API operativos y estables.
   - Respuestas consistentes y explicables.

2. **Calidad metodológica**
   - Pipeline claro y trazable.
   - Lógica robusta de decisión con fallback.
   - Buen control de falsos positivos (muy bajo FPR en benchmark robusto).

3. **Documentación y reproducibilidad**
   - Entrega con buen nivel de detalle.
   - Supuestos y decisiones bien explicitados.

## Qué mejorar
1. **Recall en ofertas extremas**
   - Se observa pérdida de detección en parte de los casos `deal` muy bajos por regla `sospechoso`.
   - Recomendación: recalibrar ese bloque para mejorar sensibilidad sin romper precisión.

2. **Métricas por subsegmento en informe principal**
   - Incluir en el cuerpo principal (no solo anexo) desempeño por:
     - soporte de contexto,
     - duración de estadía,
     - ocupación,
     - país/región.

3. **Batería de robustez API**
   - Consolidar casos automáticos de `invalid_input`, `insufficient_data` y bordes de contrato.

## Prioridades sugeridas
- **P1:** ajustar regla `sospechoso` con validación ciega estratificada.
- **P1:** publicar matriz de confusión y curvas por segmento.
- **P2:** estandarizar suite de regresión de API para entregas futuras.

## Cierre
Entrega **fuerte** y lista para producción académica con ajustes puntuales de sensibilidad.
