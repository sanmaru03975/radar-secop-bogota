# Señal: Plazo corto de publicación-ofertas

## Señal
- **Nombre corto:** Plazo corto  
- **ID estable:** `plazo_corto`  
- **Estado:** borrador v0.1 — listo para stub radar; calibrar con export FP

## Qué busca
Detectar procesos **competitivos** en los que el tiempo entre la **publicación** y el **cierre de recepción de respuestas** es inusualmente breve (cola inferior de la distribución Bogotá), lo que puede dificultar la participación efectiva. Es una señal de oportunidad restringida por calendario; requiere contraste con el tipo de proceso y eventuales urgencias justificadas. **No** afirma irregularidad ni fraude.

## Campos SECOP

| Dataset | Field API | Rol |
|---|---|---|
| `p6dx-8zbt` | `id_del_proceso` | Clave |
| `p6dx-8zbt` | `referencia_del_proceso` | Referencia entidad |
| `p6dx-8zbt` | `departamento_entidad` | Filtro Bogotá |
| `p6dx-8zbt` | `entidad` | Nombre entidad (explicación) |
| `p6dx-8zbt` | `modalidad_de_contratacion` | Solo modalidades competitivas (`M`) |
| `p6dx-8zbt` | `adjudicado` | Filtro recomendado (`'Si'`) |
| `p6dx-8zbt` | `fecha_de_publicacion_del` | **t0 primario** — Fecha de Publicacion del Proceso |
| `p6dx-8zbt` | `fecha_de_publicacion_fase_3` | t0 fallback — Fase Seleccion (casi idéntica a t0) |
| `p6dx-8zbt` | `fecha_de_ultima_publicaci` | Contexto (misma cobertura que t0 en adjudicado M) |
| `p6dx-8zbt` | `fecha_de_publicacion_fase_2` | Fase borrador — **casi nula** en adjudicado M (0/327k) |
| `p6dx-8zbt` | `fecha_de_recepcion_de` | **t1 primario** — Fecha de Recepcion de Respuestas |
| `p6dx-8zbt` | `fecha_de_apertura_de_respuesta` | t1 fallback 1 — Apertura de Respuesta |
| `p6dx-8zbt` | `fecha_de_apertura_efectiva` | t1 fallback 2 — Apertura Efectiva |
| `p6dx-8zbt` | `valor_total_adjudicacion` | Severidad / piso opcional |
| `p6dx-8zbt` | `urlproceso` | Enlace |

### Cobertura de fechas (Bogotá, `adjudicado='Si'`, modalidad ∈ `M`)

Muestra SODA `p6dx-8zbt`, 2026-09-23 (hora Bogotá). N base = 328 746.

| Campo | No nulos | % |
|---|---:|---:|
| `fecha_de_publicacion_del` | 327 902 | 99,7 % |
| `fecha_de_publicacion_fase_3` | 327 902 | 99,7 % |
| `fecha_de_ultima_publicaci` | 327 902 | 99,7 % |
| `fecha_de_publicacion_fase_2` | 0 | 0 % |
| `fecha_de_recepcion_de` | 328 422 | 99,9 % |
| `fecha_de_apertura_de_respuesta` | 328 386 | 99,9 % |
| `fecha_de_apertura_efectiva` | 328 555 | 99,9 % |

En adjudicado M con ambos presentes: `fecha_de_publicacion_del = fecha_de_publicacion_fase_3` en 327 474 / 327 902 (≈99,9 %).  
`fecha_de_recepcion_de = fecha_de_apertura_de_respuesta` en 255 831 / 327 901 (≈78 %).

## Definición operativa (v0.1 — implementable)

### Lista de inclusión `M`

**Reutilizar exactamente** la lista `M` de [`signal-01-unico-oferente.md`](signal-01-unico-oferente.md) (10 strings API competitivos). No redefinir aquí.

### Lista de exclusión

**Reutilizar exactamente** la exclusión de `unico_oferente` (directa, directa con ofertas, régimen especial sin ofertas, RFI, subasta de prueba, enajenaciones). Esas modalidades no disparan `plazo_corto`.

### Par de fechas (cascada)

| Rol | Prioridad | Campo | Notas |
|---|---|---|---|
| **t0** | 1 (primario) | `fecha_de_publicacion_del` | Preferido |
| **t0** | 2 (fallback) | `fecha_de_publicacion_fase_3` | Solo si t0 primario es `NULL` |
| **t1** | 1 (primario) | `fecha_de_recepcion_de` | Cierre de recepción — ventana de ofertas |
| **t1** | 2 | `fecha_de_apertura_de_respuesta` | Si t1 primario `NULL` |
| **t1** | 3 | `fecha_de_apertura_efectiva` | Último fallback |

**Regla dura:** si tras la cascada falta t0 o t1 → **no hit**.

### Cálculo de ventana (v0.1)

```
dias_calendario = date_diff_d(t1, t0)   # días calendario (SODA) / equivalente local
```

- **v0.1 usa días calendario**, no hábiles.  
- **Días hábiles Colombia (festivos nacionales + sáb/dom): TBD** — dependencia externa; no bloquear stub.  
- Exigir `dias_calendario >= 0`. Si `t1 < t0` → **no hit** (dato inconsistente; ≈29 casos en cohorte adjudicado M con par primario).

### Hit si (orden)

1. `departamento_entidad = 'Distrito Capital de Bogotá'`
2. `adjudicado = 'Si'` *(recomendado v0.1; mismos valores observados que signal-01: solo `Si` / `No`)*
3. `modalidad_de_contratacion ∈ M`
4. t0 y t1 resueltos por cascada; `dias_calendario >= 0`
5. `dias_calendario ≤ MAX_DIAS_CAL`

### Severidad (opcional)

| Severidad | Condición |
|---|---|
| `hit` | Cumple definición arriba |
| `high_priority` | `hit` **y** `valor_total_adjudicacion >= FLOOR_COP` |

## Umbrales propuestos v0.1

| Parámetro | Valor v0.1 | Rationale |
|---|---|---|
| `MAX_DIAS_CAL` | **≤ 3** días calendario — **PROVISIONAL** | ≈ **P5** de la cohorte Bogotá (ver calibración) |
| Unidad temporal | Calendario (no hábil) | Festivos TBD; documentar gap |
| Lista `M` / exclusión | ver signal-01 | Strings exactos API |
| `adjudicado` | `'Si'` | Reduce ruido de borradores / RFI residuales |
| `FLOOR_COP` (priorización opcional) | **100 000 000 COP** — **PROVISIONAL** | Alineado con `unico_oferente` v0.1; no filtra el hit base |

### Calibración de la ventana (PROVISIONAL)

- **Fuente:** SODA `p6dx-8zbt`.  
- **Filtro:** Bogotá + `adjudicado='Si'` + modalidad ∈ `M` + `fecha_de_publicacion_del` y `fecha_de_recepcion_de` no nulas + `date_diff_d(recep, pub) ∈ [0, 120]` (cola larga truncada solo para histograma; el hit usa ≤3 sin tope superior distinto).  
- **Fecha muestra:** 2026-09-23 (hora Bogotá).  
- **Par primario:** `fecha_de_publicacion_del` → `fecha_de_recepcion_de`.  
- **N (histograma 0–120):** 327 829.

| Percentil | Días calendario (pub→recep) |
|---|---:|
| P5 | **3** |
| P10 | 4 |
| P25 | 7 |
| P50 | 10 |
| P75 | 14 |

| Umbral | Conteos en cohorte (delta ≥ 0, sin tope 120 en el conteo le*) | % aprox. |
|---|---:|---:|
| ≤ 3 | 24 624 | ≈ P5 |
| ≤ 5 | 49 407 | — |
| ≤ 7 | 116 265 | ≈ P25 |

**Elección:** `MAX_DIAS_CAL = 3` (redondo, anclado a P5).

**Por modalidad (adjudicado M, delta ≥ 0)** — tasa ≤3:

| Modalidad | N | ≤3 | % ≤3 |
|---|---:|---:|---:|
| `Selección Abreviada de Menor Cuantía` | 25 033 | 6 339 | 25,3 % |
| `Mínima cuantía` | 76 150 | 13 861 | 18,2 % |
| `Contratación régimen especial (con ofertas)` | 75 195 | 3 589 | 4,8 % |
| `Seleccion Abreviada Menor Cuantia Sin Manifestacion Interes` | 2 580 | 33 | 1,3 % |
| `Selección abreviada subasta inversa` | 80 378 | 758 | 0,9 % |
| `Concurso de méritos abierto` | 11 822 | 40 | 0,3 % |
| `Licitación pública` / obra / AMP | 33 749+11 888+11 069 | 0 | 0 % |

Sin `Mínima cuantía`: N≈251 679, **P5=4**, P10=6, P25=8, P50=12; ≤3 ≈ 10 763. La mínima cuantía concentra ~56 % de los hits ≤3 → principal fuente de FP de bajo valor; el `FLOOR_COP` opcional mitiga.

**Pares alternos (misma cohorte, t0=`fecha_de_publicacion_del`):**

| t1 | N con ambas fechas | ≤3 (delta ≥0) | avg días |
|---|---:|---:|---:|
| `fecha_de_recepcion_de` | 327 902 | 24 624 | ≈12,0 |
| `fecha_de_apertura_de_respuesta` | 327 901 | 23 703 | ≈16,8 |
| `fecha_de_apertura_efectiva` | 327 711 | 22 220 | ≈18,4 |

## Cómo explicar el hit
> «El proceso `{referencia_del_proceso}` de `{entidad}`, modalidad `{modalidad_de_contratacion}`, registra **{dias_calendario} días calendario** entre la publicación (`{t0}` = `fecha_de_publicacion_del`) y el cierre de recepción de respuestas (`{t1}` = `fecha_de_recepcion_de`). El umbral provisional v0.1 es ≤ 3 días (≈ percentil 5 de procesos competitivos adjudicados en Bogotá). Es una **señal de plazo corto** que puede limitar la participación efectiva; debe leerse junto con la justificación del cronograma y la complejidad del objeto. No constituye por sí sola una conclusión de irregularidad.»

Si severidad `high_priority`, añadir: «El valor adjudicado supera el piso provisional de priorización (100 000 000 COP).»

## Falsos positivos conocidos
- Urgencias o calamidades públicamente justificadas.
- `Mínima cuantía` y `Selección Abreviada de Menor Cuantía` con plazos legales cortos (dominan los hits ≤3).
- Precalificación previa o re-publicaciones donde `fecha_de_publicacion_del` no refleja la ventana real de ofertas.
- Fechas mal capturadas / `00:00:00` que comprimen el intervalo (incl. delta 0: 229 casos en cohorte).
- Modalidades con plazos mínimos distintos (licitación vs mínima cuantía).
- Días hábiles reales más cortos/largos que el conteo calendario (festivos Bogotá/nacionales no modelados en v0.1).

## Dependencias de datos / gaps
- Campos de fecha **verificados** en metadatos y muestra Bogotá (2026-09-23).
- **Días hábiles / festivos Colombia: TBD** — stub usa calendario.
- No hay campo precalculado de «plazo de ofertas» en el dataset.
- Recalibrar `MAX_DIAS_CAL` por modalidad (p.ej. excluir o subir umbral en mínima cuantía) tras export FP.
- `fecha_de_publicacion_fase_2` no aporta en adjudicado M.

## Referencias públicas
- **OCP:** short bidding periods / insufficient time to prepare bids (red flag de competencia).
- **SIC:** factores de riesgo cuando el diseño del proceso reduce la posibilidad efectiva de ofertar (tipo de riesgo).
- Buenas prácticas CCE / manuales de contratación: plazos proporcionales a la complejidad (referencia normativa/procedimental).

## Estado
**borrador v0.1 — listo para stub radar; calibrar con export FP**

## Changelog v0.1

Respecto a v0:

- **Estado** → `borrador v0.1 — listo para stub radar; calibrar con export FP`.
- **Par primario fijado:** `fecha_de_publicacion_del` → `fecha_de_recepcion_de`, con cascada documentada y evidencia de cobertura.
- **Umbral:** `MAX_DIAS_CAL ≤ 3` anclado a **P5** empírico Bogotá (N≈327 829, 2026-09-23).
- **Unidad:** días **calendario** v0.1; días hábiles TBD (ya no se exige business_days para stub).
- **Inclusión/exclusión:** reutiliza `M` y exclusión de `unico_oferente`.
- **Filtro** `adjudicado='Si'` recomendado.
- **Severidad opcional** con `FLOOR_COP` 100 M alineado a signal-01.
- Distribución por modalidad y comparación de pares t1 documentadas; gaps honestos (festivos, FP de mínima cuantía).
