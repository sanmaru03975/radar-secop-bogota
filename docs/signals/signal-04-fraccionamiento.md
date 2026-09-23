# Señal: Fraccionamiento bajo umbral

## Señal
- **Nombre corto:** Fraccionamiento  
- **ID estable:** `fraccionamiento`  
- **Estado:** borrador v0 — pendiente calibración con muestras Bogotá

## Qué busca
Detectar series de contratos **pequeños y cercanos en el tiempo**, entre la misma entidad y el mismo proveedor (y objeto/UNSPSC similar), cada uno bajo un umbral de modalidad, pero cuya **suma** lo supera. Es una señal clásica de posible fraccionamiento artificial del objeto; requiere revisión del objeto contractual y de la planeación — no prueba por sí sola una práctica indebida.

## Campos SECOP

| Dataset | Field API | Rol |
|---|---|---|
| `jbjy-vk9h` | `id_contrato` | Clave |
| `jbjy-vk9h` | `departamento` | Filtro Bogotá |
| `jbjy-vk9h` | `nit_entidad` / `nombre_entidad` | Entidad |
| `jbjy-vk9h` | `documento_proveedor` / `codigo_proveedor` | Proveedor |
| `jbjy-vk9h` | `codigo_de_categoria_principal` | Objeto UNSPSC (agrupador) |
| `jbjy-vk9h` | `objeto_del_contrato` / `descripcion_del_proceso` | Similitud textual (opcional v1) |
| `jbjy-vk9h` | `modalidad_de_contratacion` | Umbral de modalidad |
| `jbjy-vk9h` | `valor_del_contrato` | Cuantía unitaria y suma |
| `jbjy-vk9h` | `fecha_de_firma` | Ventana temporal |
| `jbjy-vk9h` | `tipo_de_contrato` | Contexto |

## Definición operativa (v0 — PROVISIONAL)

Agrupar contratos Bogotá por clave:

`G = (nit_entidad, documento_proveedor, unspsc_prefijo)`

donde `unspsc_prefijo` = primeros **6** dígitos de `codigo_de_categoria_principal` (PROVISIONAL; calibrar 4 vs 8).

Dentro de una ventana deslizante de **90 días** sobre `fecha_de_firma`:

1. Tomar contratos con `modalidad_de_contratacion` en conjunto de “bajo umbral” v0 `B`:
   - `Mínima cuantía`
   - `Selección Abreviada de Menor Cuantía`
   - `Seleccion Abreviada Menor Cuantia Sin Manifestacion Interes`
   - *(opcional)* otras según calibración
2. Cada contrato cumple `valor_del_contrato < T_modalidad` (**T_modalidad = TBD** por vigencia/SMMLV; placeholder v0: usar solo la condición de modalidad ∈ `B` si el tope legal no está disponible).
3. **Hit si** en la ventana: `count(contratos) ≥ 3` **Y** `sum(valor_del_contrato) ≥ T_modalidad_ref`  
   con `T_modalidad_ref` **TBD** (mientras tanto, proxy: suma ≥ umbral absoluto provisional **COP 100M** o ≥ 3× mediana del grupo — marcar proxy).

## Umbrales propuestos v0

| Parámetro | Valor v0 | Rationale |
|---|---|---|
| Mínimo de contratos | **≥ 3** | Serie, no par aislado |
| Ventana | **90 días** | Cercanía temporal típica en literature de split purchases |
| Prefijo UNSPSC | **6 dígitos** | Equilibrio entre especificidad y cobertura |
| Umbral legal `T` | **TBD** (SMMLV / tope mínima cuantía vigencia) | Debe anclarse a norma vigente |
| Proxy suma | **COP 100M** (PROVISIONAL) | Solo mientras `T` legal no esté cableado |

## Cómo explicar el hit
> «Entre `{fecha_min}` y `{fecha_max}`, `{nombre_entidad}` firmó **{n}** contratos con `{proveedor_adjudicado}` (documento `{documento_proveedor}`) en categoría UNSPSC `{unspsc_prefijo}*`, cada uno en modalidad de baja cuantía, por un total de `{suma}` COP. El patrón es una **señal de posible fraccionamiento bajo umbral** (v0); puede haber planeación legítima por vigencias o necesidades sucesivas — revisar objetos y estudios previos.»

## Falsos positivos conocidos
- Contratos de prestación de servicios mensuales / por vigencia con el mismo profesional.
- Órdenes sucesivas en Acuerdos Marco (competencia ya ocurrió en el AMP).
- UNSPSC genérico compartido por objetos realmente distintos.
- Pagos/contratos de sedes o proyectos independientes con el mismo NIT proveedor.
- Errores de digitación de NIT/UNSPSC.

## Dependencias de datos / gaps
- Campos de agrupación y valor **existen** en `jbjy-vk9h`.
- **Gap crítico:** topes legales de mínima/menor cuantía **no** están en el dataset → `T_modalidad` es dependencia normativa externa (TBD por vigencia).
- Sin campo de “objeto canónico” estructurado más allá de UNSPSC + texto libre.
- Cobertura incompleta de `jbjy-vk9h` vía SODA en verificación (ver README) → riesgo de falsos negativos.

## Referencias públicas
- **OCP:** contract splitting / fragmentation to avoid procurement thresholds.
- **SIC / literatura de colusión en compras:** patrones de fragmentación y rotación (tipo de riesgo).
- **Transparencia por Colombia:** alertas sobre contratación fraccionada para eludir modalidades competitivas.
- Principio de planeación y prohibición de fraccionamiento (doctrina contractual pública colombiana).

## Estado
**borrador v0 — pendiente calibración con muestras Bogotá**
