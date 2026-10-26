# Devolución final (resumida) — TP3 + lineamientos para TP4

Estimadxs,

Les compartimos una devolución breve y final del trabajo.

## 1) Proceso de corrección y creación de datos
- Se revisó el proceso completo de ambos grupos.
- Se armó una validación robusta con dataset ampliado y estratificado (no solo casos sueltos).
- Se ejecutaron pruebas end-to-end con Docker + API para los dos equipos.
- Se compararon métricas globales y por segmento, con resultados reproducibles.

## 2) Lo positivo (ambos grupos)
- Muy bien el formato de entrega.
- Muy bien Docker y API: lograron que funcione de punta a punta.
- Excelente el trabajo y el esfuerzo sostenido durante toda la mentoría.

## 3) Qué estaba mal, cómo se detectó y qué se dejó listo

### Grupo 1
- No se detectó error crítico de implementación.
- Hay una decisión conservadora (`sospechoso`) que baja sensibilidad en ofertas extremas, pero protege contra falsos positivos.
- Estado: correcto y consistente.

### Grupo 2 (error importante)
- El problema principal fue de **unidad de precio** (`price_total` + normalización), no de infraestructura.
- Eso afecta directamente la detección de `deal` (recall), porque cambia la escala de `price_std`.
- Cómo se detectó:
  1. En modo actual, quedaban casi todas las ofertas como `no_deal`.
  2. Se aplicó una simulación de transformación alternativa y cambiaron muchas predicciones.
  3. La mejora en recall confirmó que el problema está en la semántica/escala del precio de entrada.

## 4) ¿Esto afecta TP4 (video)?
- **No bloquea TP4.**
- Pueden avanzar con el video final sin problema.
- Sí corresponde mencionar esta limitación metodológica y el plan de corrección.

## 5) Paso a paso para corregir Grupo 2 (y cerrar)
1. Definir una única convención de precio (train + API + documentación).
2. Ajustar la transformación de `price_std` para esa convención.
3. Regenerar artefactos/modelo.
4. Recalibrar umbrales.
5. Re-ejecutar benchmark robusto.
6. Enviar tabla antes/después de métricas.

## 6) Métricas resumidas
- **Grupo 1:** buen desempeño global, precisión alta, FPR muy bajo, con menor recall en extremos por política conservadora.
- **Grupo 2:** en modo actual, recall muy bajo en `deal`; con simulación de transformación mejora de forma clara, confirmando el origen del problema.

## 7) Estado final de aprobación
- **Grupo 1: APROBADO.**
- **Grupo 2: APROBADO** (con corrección metodológica recomendada y revalidación posterior).

---

## 8) En qué hacer hincapié para el video final (TP4) — sugerencia punto por punto

Con base en lineamientos de cátedra:

1. **Objetivo y problema de negocio** (claro en 1 minuto).
2. **Dataset y decisiones clave de EDA/curación** (solo lo más importante).
3. **Modelado**:
   - modelos evaluados,
   - por qué eligieron el final,
   - métricas usadas y tradeoffs.
4. **Resultados concretos**:
   - métricas finales,
   - comportamiento por segmentos,
   - qué funciona bien y qué no.
5. **Conclusión ejecutiva**:
   - si está o no listo para producción,
   - riesgos actuales,
   - próximos pasos.
6. **Desafíos y cómo los resolvieron**:
   - ejemplo: unidad de precio / calibración / fallback.
7. **Comunicación visual**:
   - no mostrar código,
   - sí tablas, gráficos, esquemas y comparativas.
8. **Participación del equipo**:
   - idealmente todos presentan una parte.

## 9) Recordatorio operativo de entrega TP4
- Duración máxima: **15 minutos**.
- Entrega: link (Drive u otro) con permisos de visualización/descarga.
- Fecha de entrega video: **07/11**.
- Jornadas de presentación: **04/12 y 05/12**.

Cierre:
Muy buen trabajo general de ambos equipos. Ya están en etapa de cierre y comunicación ejecutiva. El foco ahora es sintetizar bien, mostrar resultados con criterio y dejar claros límites y mejoras.
