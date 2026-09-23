# Señal: Único oferente

## Señal
- **Nombre corto:** Único oferente  
- **ID estable:** `unico_oferente`  
- **Estado:** borrador v0.1 — listo para stub radar; calibrar con export FP

## Qué busca
Identificar procesos de selección que, por su modalidad, se esperaría competitivos, pero en la práctica registran **un solo proveedor** con respuesta u oferta (o un único adjudicatario sin evidencia de competencia). Es una señal de concentración de la demanda útil para priorizar revisión; **no** demuestra irregularidad por sí sola.

## Campos SECOP

| Dataset | Field API | Rol |
|---|---|---|
| `p6dx-8zbt` | `id_del_proceso` | Clave del proceso |
| `p6dx-8zbt` | `referencia_del_proceso` | Referencia entidad |
| `p6dx-8zbt` | `departamento_entidad` | Filtro Bogotá |
| `p6dx-8zbt` | `modalidad_de_contratacion` | ¿Debió ser competitivo? (lista M / exclusión) |
| `p6dx-8zbt` | `proveedores_unicos_con` | **Conteo principal** de oferentes únicos con respuesta |
| `p6dx-8zbt` | `conteo_de_respuestas_a_ofertas` | Fallback 1 de respuestas a ofertas |
| `p6dx-8zbt` | `respuestas_al_procedimiento` | Fallback 2 de respuestas al procedimiento |
| `p6dx-8zbt` | `adjudicado` | Solo procesos adjudicados (filtro) |
| `p6dx-8zbt` | `nombre_del_proveedor` | Adjudicatario (explicación) |
| `p6dx-8zbt` | `nit_del_proveedor_adjudicado` | NIT adjudicatario |
| `p6dx-8zbt` | `valor_total_adjudicacion` | Magnitud / piso de priorización |
| `p6dx-8zbt` | `urlproceso` | Enlace a SECOP II |
| `jbjy-vk9h` | `proceso_de_compra` | Join opcional proceso→contrato |
| `jbjy-vk9h` | `documento_proveedor` / `proveedor_adjudicado` | Refuerzo si el join existe |

## Definición operativa (v0.1 — implementable)

### Valores observados de `adjudicado` (Bogotá, `p6dx-8zbt`)

Consulta SODA `$select=adjudicado,count(*)` con `departamento_entidad = 'Distrito Capital de Bogotá'` (2026-09-23, hora Bogotá):

| Valor API | Conteos Bogotá |
|---|---|
| `No` | 2 230 953 |
| `Si` | 373 071 |

**No** apareció `Sí` (con tilde) ni otras variantes. Usar **exactamente** `adjudicado = 'Si'`.

### Lista de INCLUSIÓN `M` (disparan la señal)

Modalidades que **aparecen en datos Bogotá** y son **competitivas por naturaleza** (pluralidad de ofertas esperable). Strings exactos de la API:

| `#` | `modalidad_de_contratacion` (string exacto) | Conteos totales Bogotá | Sole-bidder adjudicado (`proveedores_unicos_con=1`, `adjudicado='Si'`) |
|---|---|---:|---:|
| 1 | `Licitación pública` | 41 150 | 931 |
| 2 | `Licitación pública Obra Publica` | 15 080 | 128 |
| 3 | `Licitación Pública Acuerdo Marco de Precios` | 11 230 | 3 |
| 4 | `Selección abreviada subasta inversa` | 104 377 | 4 105 |
| 5 | `Selección Abreviada de Menor Cuantía` | 70 799 | 4 064 |
| 6 | `Seleccion Abreviada Menor Cuantia Sin Manifestacion Interes` | 3 100 | 125 |
| 7 | `Concurso de méritos abierto` | 21 243 | 723 |
| 8 | `Concurso de méritos con precalificación` | 43 | 1 |
| 9 | `Mínima cuantía` | 94 807 | 15 462 |
| 10 | `Contratación régimen especial (con ofertas)` | 79 345 | 3 372 |

**Total hits base en M (adjudicado + `proveedores_unicos_con=1`):** ≈ 28 914.

### Lista de EXCLUSIÓN (nunca disparan `unico_oferente`)

Sole bidder es **esperado** o la modalidad no es de competencia de adjudicación. Strings exactos observados en Bogotá:

| `modalidad_de_contratacion` | Conteos Bogotá | Motivo de exclusión |
|---|---:|---|
| `Contratación directa` | 1 373 550 | Directa pura; usar `cd_alto_valor` |
| `Contratación Directa (con ofertas)` | 51 792 | Sigue siendo directa; ≈23 164 sole-bidder adjudicado (ruido masivo) |
| `Contratación régimen especial` | 646 087 | Régimen especial sin fase de ofertas |
| `Solicitud de información a los Proveedores` | 88 169 | RFI / pre-proceso, no selección competitiva de adjudicación |
| `Subasta de prueba` | 2 860 | Prueba / no operativo |
| `Enajenación de bienes con subasta` | 228 | Enajenación de bienes (naturaleza distinta) |
| `Enajenación de bienes con sobre cerrado` | 164 | Enajenación de bienes (naturaleza distinta) |

### Hit si (orden de evaluación)

1. `departamento_entidad = 'Distrito Capital de Bogotá'`
2. `adjudicado = 'Si'`
3. `modalidad_de_contratacion ∈ M` (inclusión) **y** `∉` exclusión
4. Conteo de oferentes = 1 según **cascada** (ver abajo)

### Cascada de conteo (obligatoria)

| Prioridad | Campo | Condición de hit |
|---|---|---|
| 1 (principal) | `proveedores_unicos_con` | `= 1` |
| 2 (fallback) | `conteo_de_respuestas_a_ofertas` | Solo si `proveedores_unicos_con IS NULL` **y** este campo `= 1` |
| 3 (fallback) | `respuestas_al_procedimiento` | Solo si los dos anteriores son `NULL` **y** este campo `= 1` |

**Regla dura:** si **los tres** conteos son `NULL` → **no hit**. No inferir único oferente por ausencia de dato.

Nota de muestra (2026-09-23): entre procesos Bogotá adjudicado ∈ M, `proveedores_unicos_con IS NULL` = 0; la cascada de fallbacks es defensiva para histórico / otras sedes.

### Severidad (opcional para stub radar)

| Severidad | Condición |
|---|---|
| `hit` | Cumple definición de hit arriba |
| `high_priority` | `hit` **y** `valor_total_adjudicacion >= FLOOR_COP` |

## Umbrales propuestos v0.1

| Parámetro | Valor v0.1 | Rationale |
|---|---|---|
| Número de oferentes únicos | `= 1` | Definición literal de único oferente |
| Lista `M` / exclusión | ver tablas | Strings exactos API; solo modalidades competitivas por naturaleza |
| `FLOOR_COP` (priorización) | **100 000 000 COP** — **PROVISIONAL** | Ver calibración abajo |
| `adjudicado` | `'Si'` | Único valor afirmativo observado |

### Calibración del piso de valor (PROVISIONAL)

- **Fuente:** SODA `p6dx-8zbt`, filtro Bogotá + `adjudicado='Si'` + `modalidad ∈ M` + `proveedores_unicos_con=1` + `valor_total_adjudicacion > 0`.
- **Fecha muestra:** 2026-09-23 (hora Bogotá).
- **N:** 28 681 filas con valor > 0 (de ≈28 914 sole-bidder en M).
- **Percentiles empíricos** (muestra completa ordenada vía API, no approx):

| Percentil | COP |
|---|---:|
| P50 | ≈ 41 411 421 |
| P75 | 180 000 000 |
| P90 | ≈ 745 762 500 |

- **Elección:** `FLOOR_COP = 100 000 000` (redondo, entre P50 y P75).
- **Sensibilidad en la misma cohorte:** ≥50M → ≈13 441; **≥100M → ≈9 360**; ≥180M (P75) → ≈7 194.
- **Caveats API / datos:**
  - SODA no expone `PERCENTILE_CONT` fiable en este recurso; percentiles = sort client-side de la cohorte completa (~29k), no sample aleatorio.
  - Hay outliers extremos de `valor_total_adjudicacion` (max observado ~6e15) que rompen la media; **no** usar media; el piso se basa en percentiles.
  - Recalibrar con export FP del stub antes de producción.

## Cómo explicar el hit
> «El proceso `{referencia_del_proceso}` de `{entidad}`, modalidad `{modalidad_de_contratacion}`, registra **un solo proveedor** con respuesta (`proveedores_unicos_con = 1`). Quedó adjudicado a `{nombre_del_proveedor}` por `{valor_total_adjudicacion}` COP. Esto es una **señal de baja competencia observada** que conviene contrastar con el pliego, invitaciones y justificación; no implica por sí sola una irregularidad.»

Si severidad `high_priority`, añadir: «El valor adjudicado supera el piso provisional de priorización (100 000 000 COP).»

## Falsos positivos conocidos
- Procesos con invitaciones directas legítimas y un solo interesado.
- Cancelaciones parciales / lotes donde solo un lote tuvo oferta.
- Campos de conteo que incluyen respuestas de la entidad u observaciones (preferir `proveedores_unicos_con`).
- Régimen especial (con ofertas) o AMP donde la competencia ocurre en otra etapa / mercado.
- `Mínima cuantía` concentra ~53 % de los hits en M → muchos FP de bajo valor; el `FLOOR_COP` mitiga ruido.
- Datos históricos con nulos en **todos** los conteos → no forzar hit (cascada).

## Dependencias de datos / gaps
- **Preferido:** `proveedores_unicos_con` (verificado; principal en cascada).
- No hay dataset público de «lista de oferentes» fila a fila en estos recursos → no se puede auditar *quiénes* ofertaron, solo el conteo.
- Join proceso↔contrato vía `proceso_de_compra` / `id_del_proceso` no está documentado 1:1 en metadatos; validar en muestra.
- Recalibrar `FLOOR_COP` y posible exclusión de `Mínima cuantía` / `Contratación régimen especial (con ofertas)` tras export FP del stub.

## Referencias públicas
- **OCP red flags:** single bidder / limited competition in competitive procedures.
- **SIC (Superintendencia de Industria y Comercio):** patrones de riesgo de colusión asociados a baja participación de oferentes (tipo de riesgo, no score).
- **Transparencia por Colombia / contrataciones abiertas:** alertas de competencia restringida en procesos que debieran ser plurales.
- Ley 80 / 1150: principio de selección objetiva (marco normativo, no tipificación automática).

## Estado
**borrador v0.1 — listo para stub radar; calibrar con export FP**

## Changelog v0.1

Respecto a v0:

- **Estado** → `borrador v0.1 — listo para stub radar; calibrar con export FP`.
- **Inclusión `M`:** lista cerrada de 10 strings exactos observados en SODA Bogotá (competitivos por naturaleza).
- **Exclusión explícita:** `Contratación directa`, `Contratación Directa (con ofertas)`, régimen especial sin ofertas, RFI, subasta de prueba, enajenaciones.
- **`adjudicado`:** documentado como solo `Si` / `No` (sin `Sí`).
- **Cascada de conteo:** principal `proveedores_unicos_con`; fallbacks ordenados; **no hit si los tres son null**.
- **`FLOOR_COP`:** 100 000 000 COP PROVISIONAL (N=28 681, P50≈41M / P75=180M, 2026-09-23 Bogotá).
- **Severidad opcional:** `hit` vs `high_priority` si valor ≥ piso.
- Quitado el TBD de umbral de valor; calibración grounded en API `p6dx-8zbt`.
