# Señal: Adiciones cerca del 50% (Ley 80)

## Señal
- **Nombre corto:** Adición cerca del 50%  
- **ID estable:** `adicion_cerca_50`  
- **Estado:** borrador v0 — pendiente calibración con muestras Bogotá

## Qué busca
Identificar contratos cuya **suma de adiciones de valor** se acerca al límite orientador del **50%** del valor inicial (referente frecuente: Ley 80 de 1993, art. 40, para adiciones), tipicamente desde un umbral provisional del **45%**. Es una señal de proximidad al tope legal/doctrinal para priorizar revisión de justificación y control de cambios — **no** declara incumplimiento.

## Campos SECOP

| Dataset | Field API | Rol |
|---|---|---|
| `cb9c-h8sn` | `identificador` | ID del evento de modificación |
| `cb9c-h8sn` | `id_contrato` | Join a contrato |
| `cb9c-h8sn` | `tipo` | Filtrar `ADICION EN EL VALOR` (y afines) |
| `cb9c-h8sn` | `descripcion` | Texto libre; a veces menciona montos |
| `cb9c-h8sn` | `fecharegistro` | Orden temporal de adiciones |
| `jbjy-vk9h` | `id_contrato` | Join / valor actual |
| `jbjy-vk9h` | `valor_del_contrato` | Valor actual del contrato (no necesariamente “inicial”) |
| `jbjy-vk9h` | `dias_adicionados` | Proxy débil de adición de plazo |
| `jbjy-vk9h` | `departamento` | Filtro Bogotá vía join |
| `jbjy-vk9h` | `nombre_entidad`, `proveedor_adjudicado`, `urlproceso` | Explicación |

### Campos deseados que **NO** existen
| Campo conceptual | ¿En metadatos `cb9c-h8sn`? | Impacto |
|---|---|---|
| Valor monetario de la adición | **No** (solo 5 columnas) | No se puede calcular ratio preciso sin NLP/parsing |
| Valor inicial del contrato | **No** explícito | `valor_del_contrato` es snapshot actual, posiblemente ya adicionado |
| Separación valor vs plazo | Parcial (`tipo`) | Hay `ADICION EN EL VALOR` vs `EXTENSION` / `MODIFICACION GENERAL` |

## Definición operativa (v0 — PROVISIONAL)

**Ruta A — ideal (bloqueada por gap de datos):**  
`ratio = sum(valor_adiciones) / valor_inicial ≥ 0.45`

**Ruta B — stub v0 (implementable con gaps explícitos):**

1. Join `cb9c-h8sn.id_contrato = jbjy-vk9h.id_contrato` y filtrar Bogotá.
2. Considerar eventos con `tipo = 'ADICION EN EL VALOR'` (y opcionalmente `MODIFICACION GENERAL` si `descripcion` match `(?i)adici[oó]n.*valor|adicionar el valor`).
3. **Proxy débil (marcar como LOW_CONFIDENCE):**
   - Intentar extraer montos en COP desde `descripcion` con parser v0 (regex de `$` / `MILLONES`); sumar extracciones confiables.
   - Si no hay monto parseable: emitir señal cualitativa `tiene_adicion_valor = true` **sin ratio**, o excluir del hit duro.
4. `valor_inicial_proxy` **TBD**: no disponible; posibles heuristics futuras (históricos, documentos) fuera de v0.
5. **Hit duro v0 solo si** se obtuvo `sum_parseada` y `valor_base` confiable y `sum_parseada / valor_base ≥ 0.45`.
6. **Hit suave v0:** ≥1 `ADICION EN EL VALOR` **Y** `dias_adicionados` alto **TBD** — documentar como señal débil aparte si radar lo requiere.

## Umbrales propuestos v0

| Parámetro | Valor v0 | Rationale |
|---|---|---|
| Ratio adiciones / inicial | **≥ 0.45** (PROVISIONAL) | “Cerca” del límite 50% (Ley 80 art. 40 como referente) |
| Límite legal de referencia | **0.50** | Ancla normativa frecuente; excepciones y regímenes especiales aplican |
| Confianza mínima del parseo | **TBD** | Evitar hits por texto ruidoso |

## Cómo explicar el hit
> «El contrato `{id_contrato}` de `{nombre_entidad}` registra adiciones de tipo `{tipo}` (eventos: {k}). Estimación provisional del ratio adiciones/valor de referencia: **{ratio}** (umbral v0: 0.45; referente 50%). **Fuente del monto:** {parseo de descripción | no estructurado}. Es una **señal de proximidad al tope de adición**; verificar el valor inicial real y el soporte de cada modificación. No afirma incumplimiento del artículo 40.»

## Falsos positivos conocidos
- Régimen privado / especial con reglas distintas al 50%.
- `MODIFICACION GENERAL` que no cambia valor.
- Parseo incorrecto de montos en `descripcion` (números de norma, fechas, cédulas).
- `valor_del_contrato` ya incluye adiciones → ratio subestima o se calcula mal.
- Reducciones (`REDUCCION EN EL VALOR`) no neteadas.

## Dependencias de datos / gaps
- **Gap crítico verificado:** `cb9c-h8sn` solo expone `identificador`, `id_contrato`, `tipo`, `descripcion`, `fecharegistro` — **sin campo de valor**.
- Sin valor inicial histórico en `jbjy-vk9h`.
- `dias_adicionados` cubre plazo, no dinero.
- Stub radar: empezar por **conteo/flag de `ADICION EN EL VALOR`** + join Bogotá; diferir ratio hasta fuente de montos (API SECOP, documentos, u otro dataset).

## Referencias públicas
- **Ley 80 de 1993, art. 40** (límite de adición — referente público; aplicabilidad según régimen del contrato).
- **OCP:** contract amendments / value increases near legal ceilings (red flag de modificación).
- **Transparencia por Colombia:** seguimiento a adiciones recurrentes o cercanas al tope (tipo de alerta).

## Estado
**borrador v0 — pendiente calibración con muestras Bogotá**
