# Señal: Contratación directa de alto valor

## Señal
- **Nombre corto:** CD alto valor  
- **ID estable:** `cd_alto_valor`  
- **Estado:** borrador v0.1 — listo para stub radar; calibrar con export FP

## Qué busca
Resaltar contrataciones bajo modalidad **directa** (o directa con ofertas) cuyo valor es **alto** frente a un piso provisional calibrado con la distribución Bogotá. Sirve para priorizar control interno o veeduría sobre justificación de la modalidad y cuantía. **No** afirma ilegitimidad de la directa ni fraude.

## Fuente autoritativa para el stub

| Dataset | Uso v0.1 | Nota operativa |
|---|---|---|
| **`p6dx-8zbt` (procesos)** | **Autoritativa** | Conteos Bogotá coherentes (~2,6M filas entidad Bogotá). Dos pistas de valor según modalidad (ver abajo). |
| `jbjy-vk9h` (contratos) | **No usar para umbrales / conteos** | SODA devolvió `count(*)=1000` en el recurso completo y solo **412** filas con `departamento='Distrito Capital de Bogotá'` (2026-09-23). Vista degradada o tope de API — **no** sirve para percentiles ni producción hasta validar ingestión completa. Strings de modalidad/valor sí coinciden en la muestra residual (`valor_del_contrato`, `justificacion_modalidad_de`). |

## Campos SECOP

| Dataset | Field API | Rol |
|---|---|---|
| `p6dx-8zbt` | `id_del_proceso` | Clave proceso |
| `p6dx-8zbt` | `referencia_del_proceso` | Referencia |
| `p6dx-8zbt` | `departamento_entidad` | Filtro Bogotá |
| `p6dx-8zbt` | `entidad` / `nit_entidad` | Entidad |
| `p6dx-8zbt` | `modalidad_de_contratacion` | ∈ lista `D` |
| `p6dx-8zbt` | `estado_del_procedimiento` | Filtro pista CD pura (`Seleccionado`) |
| `p6dx-8zbt` | `adjudicado` | Filtro pista CD con ofertas (`'Si'`) |
| `p6dx-8zbt` | `precio_base` | **Valor pista A** (CD pura) |
| `p6dx-8zbt` | `valor_total_adjudicacion` | **Valor pista B** (CD con ofertas) |
| `p6dx-8zbt` | `justificaci_n_modalidad_de` | Texto libre (UI) |
| `p6dx-8zbt` | `nombre_del_proveedor` / `nit_del_proveedor_adjudicado` | Contraparte (si existe) |
| `p6dx-8zbt` | `urlproceso` | Enlace |
| `jbjy-vk9h` | `valor_del_contrato`, `modalidad_de_contratacion`, `justificacion_modalidad_de`, `departamento` | Solo referencia / join futuro tras fix de ingestión |

## Definición operativa (v0.1 — implementable)

### Lista de INCLUSIÓN `D` (strings exactos API)

Observados en Bogotá `p6dx-8zbt` (2026-09-23):

| `#` | `modalidad_de_contratacion` | Conteos Bogotá | Comportamiento de datos |
|---|---|---:|---|
| 1 | `Contratación directa` | 1 373 550 | `adjudicado` **siempre** `'No'`; `valor_total_adjudicacion` **nunca** > 0; valor usable = `precio_base` |
| 2 | `Contratación Directa (con ofertas)` | 51 792 | `adjudicado='Si'` en 44 165; valor usable = `valor_total_adjudicacion` |

### Lista de EXCLUSIÓN (no disparan `cd_alto_valor`)

| `modalidad_de_contratacion` | Motivo |
|---|---|
| `Contratación régimen especial` | No es directa Ley 80; señal aparte si se desea |
| `Contratación régimen especial (con ofertas)` | Competencia parcial; ya cubierta por otras señales (`unico_oferente`, etc.) |
| Todo lo que esté en `M` de `unico_oferente` | Procesos competitivos |
| `Solicitud de información a los Proveedores` | RFI |
| `Subasta de prueba` / enajenaciones | No operativos / naturaleza distinta |

**Régimen especial: No por defecto** (igual que el borrador v0).

### Dos pistas de evaluación (obligatorio bifurcar)

El stub **debe** ramificar; unificar mal el campo de valor produce 0 hits o ruido masivo.

#### Pista A — `Contratación directa` (pura)

1. `departamento_entidad = 'Distrito Capital de Bogotá'`
2. `modalidad_de_contratacion = 'Contratación directa'`
3. `estado_del_procedimiento = 'Seleccionado'`  
   *(dominante: 1 345 035 / 1 373 550; excluye Borrador / Cancelado / etc.)*
4. `precio_base > 0` **y** `precio_base <= SANITY_MAX_COP`
5. `precio_base >= FLOOR_COP` → **hit**

`SANITY_MAX_COP = 1_000_000_000_000` (1e12) — descarta outliers absurdos (p.ej. `precio_base` ~1e16 con proveedor `No Definido`); solo 8 filas Seleccionado superan el tope en la muestra.

#### Pista B — `Contratación Directa (con ofertas)`

1. `departamento_entidad = 'Distrito Capital de Bogotá'`
2. `modalidad_de_contratacion = 'Contratación Directa (con ofertas)'`
3. `adjudicado = 'Si'`
4. `valor_total_adjudicacion > 0`
5. `valor_total_adjudicacion >= FLOOR_COP` → **hit**

### Valor efectivo para explicación

```
valor_efectivo = precio_base                         # pista A
valor_efectivo = valor_total_adjudicacion            # pista B
```

No mezclar campos entre pistas.

## Umbrales propuestos v0.1

| Parámetro | Valor v0.1 | Rationale |
|---|---|---|
| `FLOOR_COP` | **500 000 000 COP** — **PROVISIONAL** | Excluye directas rutinarias de bajo/medio valor; ver calibración |
| `SANITY_MAX_COP` | **1e12 COP** | Solo pista A; anti-basura |
| Incluir régimen especial | **No** | Ver exclusión |
| Fuente de umbral | `p6dx-8zbt` | `jbjy-vk9h` no usable (cap 1000) |

### Calibración del piso (PROVISIONAL)

**Fecha muestra:** 2026-09-23 (hora Bogotá). Fuente: `p6dx-8zbt`.

#### Pista B — `valor_total_adjudicacion` (CD con ofertas, adjudicado, valor > 0)

- **N:** 44 050  
- Percentiles (sort completo vía API; hay max patológico ~3e15 — **no** usar media):

| Percentil | COP |
|---|---:|
| P50 | ≈ 50 478 000 |
| P75 | ≈ 201 457 992 |
| P90 | ≈ 861 671 499 |
| P95 | ≈ 2 878 659 840 |

| Piso | Hits |
|---|---:|
| ≥ 100 M | 16 199 |
| ≥ 200 M | 11 152 |
| **≥ 500 M** | **6 669** (≈ percentil 85: ≤500 M = 84,9 %) |
| ≥ 1 000 M | 4 038 |

#### Pista A — `precio_base` (CD pura, `Seleccionado`, 0 < precio ≤ 1e12)

- **N:** 1 318 067  
- Distribución concentrada en cuantías bajas/medias (prestación de servicios, etc.):

| Umbral acum. | % ≤ umbral |
|---|---:|
| 50 M | 70,6 % |
| 100 M | 92,6 % |
| 200 M | 98,0 % |
| **500 M** | **99,0 %** |
| 1 000 M | 99,4 % |

| Piso | Hits |
|---|---:|
| ≥ 100 M | 101 180 |
| ≥ 200 M | 26 419 |
| **≥ 500 M** | **13 308** (≈ P99) |
| ≥ 1 000 M | 8 061 |

**Elección:** `FLOOR_COP = 500 000 000` (redondo). En pista B ≈ cola alta (~P85); en pista A ≈ P99 — el mismo número absoluto filtra el grueso de directas rutinarias de prestadores y deja ~20 k hits combinados para priorizar.

**Exclusión de bajo valor:** implícita vía `FLOOR_COP` (no hay lista separada de causales). `justificaci_n_modalidad_de` es texto libre — útil en UI, no en la regla.

## Cómo explicar el hit

Pista A:
> «El proceso `{referencia_del_proceso}` de `{entidad}` usa modalidad `Contratación directa` (estado `{estado_del_procedimiento}`) con `precio_base` = `{precio_base}` COP, por encima del piso provisional v0.1 (500 000 000 COP). Justificación registrada: `{justificaci_n_modalidad_de}`. Es una **señal de priorización por cuantía en modalidad de baja competencia**; la modalidad puede ser válida — conviene revisar el soporte de la causal.»

Pista B:
> «El proceso `{referencia_del_proceso}` de `{entidad}` usa modalidad `Contratación Directa (con ofertas)`, adjudicado a `{nombre_del_proveedor}` por `{valor_total_adjudicacion}` COP, por encima del piso provisional v0.1 (500 000 000 COP). Justificación registrada: `{justificaci_n_modalidad_de}`. Es una **señal de priorización por cuantía en modalidad de baja competencia**; la modalidad puede ser válida — conviene revisar el soporte de la causal.»

## Falsos positivos conocidos
- Causales legales de directa bien soportadas (servicios profesionales, urgencia manifiesta, interadministrativos, arrendamiento, etc.).
- Convenios interadministrativos de alto monto con causal explícita.
- `precio_base` que no coincide con valor final ejecutado / firmado (pista A no tiene `valor_total_adjudicacion`).
- Outliers extremos de valor (usar `SANITY_MAX_COP`; no promediar).
- Umbral único inadecuado para entidades muy grandes o muy pequeñas (percentil por entidad **TBD**).
- Si alguien consulta solo `jbjy-vk9h` sin notar el cap 1000, los “percentiles” serán basura.

## Dependencias de datos / gaps
- **Autoridad v0.1:** `p6dx-8zbt` con bifurcación de valor (`precio_base` vs `valor_total_adjudicacion`).
- **`jbjy-vk9h`:** `count(*)=1000` global / 412 Bogotá — **no** calibrar ni contar ahí hasta confirmar pipeline.
- Umbrales legales exactos por entidad/SMMLV/manuales distritales: **TBD** (no están en estos datasets).
- Pista A no tiene adjudicatario fiable en muchos casos (`nombre_del_proveedor = 'No Definido'`).
- Recalibrar `FLOOR_COP` (p.ej. 1 000 M) tras export FP del stub.
- Join proceso↔contrato para enriquecer con `valor_del_contrato` real: pendiente de ingestión sana de `jbjy-vk9h`.

## Referencias públicas
- **OCP:** non-competitive procedures / direct awards of high value (red flag de transparencia y competencia).
- **Transparencia por Colombia:** seguimiento a uso intensivo de contratación directa de alto monto (tipo de riesgo).
- Marco Ley 80 / 1150 / decretos reglamentarios: causales de contratación directa (contexto normativo).

## Estado
**borrador v0.1 — listo para stub radar; calibrar con export FP**

## Changelog v0.1

Respecto a v0:

- **Estado** → `borrador v0.1 — listo para stub radar; calibrar con export FP`.
- **Fuente autoritativa:** `p6dx-8zbt`; `jbjy-vk9h` documentado como **no usable** para umbrales (cap SODA 1000 / 412 Bogotá).
- **Lista `D`:** strings exactos `Contratación directa` y `Contratación Directa (con ofertas)`; régimen especial excluido.
- **Bifurcación de valor:** pista A = `precio_base` + `estado_del_procedimiento='Seleccionado'`; pista B = `valor_total_adjudicacion` + `adjudicado='Si'` (CD pura nunca trae adjudicación valorada).
- **`FLOOR_COP`:** 500 000 000 COP PROVISIONAL con percentiles Bogotá 2026-09-23 (pista B ≈P85 / 6 669 hits; pista A ≈P99 / 13 308 hits).
- **`SANITY_MAX_COP`:** 1e12 para `precio_base`.
- Plantillas de explicación por pista; lenguaje de señal, nunca fraude.
