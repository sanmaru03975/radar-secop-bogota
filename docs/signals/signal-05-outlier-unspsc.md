# Señal: Outlier de precio UNSPSC

## Señal
- **Nombre corto:** Outlier UNSPSC  
- **ID estable:** `outlier_unspsc`  
- **Estado:** borrador v0 — pendiente calibración con muestras Bogotá

## Qué busca
Marcar contratos cuyo **valor** se desvía de forma extrema respecto de contratos pares en Bogotá con la misma categoría UNSPSC (y, si existe, misma unidad). Ayuda a encontrar posibles sobreprecios o subprecios anómalos para revisión; un outlier estadístico **no** equivale a sobreprecio demostrado.

## Campos SECOP

| Dataset | Field API | Rol |
|---|---|---|
| `jbjy-vk9h` | `id_contrato` | Clave |
| `jbjy-vk9h` | `departamento` | Cohorte Bogotá |
| `jbjy-vk9h` | `codigo_de_categoria_principal` | Grupo UNSPSC |
| `jbjy-vk9h` | `valor_del_contrato` | Métrica de precio (proxy) |
| `jbjy-vk9h` | `tipo_de_contrato` | Estrato / filtro |
| `jbjy-vk9h` | `modalidad_de_contratacion` | Estrato opcional |
| `jbjy-vk9h` | `fecha_de_firma` | Ventana / deflactar **TBD** |
| `jbjy-vk9h` | `nombre_entidad` / `documento_proveedor` | Contexto del hit |
| `p6dx-8zbt` | `codigo_principal_de_categoria`, `valor_total_adjudicacion` | Alternativa a nivel proceso |

### Campos deseados que **NO** existen (gaps)
| Campo conceptual | ¿En metadatos? | Impacto |
|---|---|---|
| Cantidad / `cantidad` | **No** en los 4 datasets | No se puede calcular precio unitario real |
| Unidad de medida | **No** | No hay peer por unidad |
| Precio unitario | **No** | v0 usa valor total como proxy débil |

## Definición operativa (v0 — PROVISIONAL)

1. Cohorte: contratos Bogotá con mismo `codigo_de_categoria_principal` (8 dígitos si está completo; si no, prefijo 6).
2. Filtros de calidad: excluir `valor_del_contrato` nulo o ≤ 0; opcionalmente restringir `tipo_de_contrato`.
3. Exigir tamaño muestral `n ≥ N_min` (**N_min = 30**, PROVISIONAL).
4. Calcular sobre `log1p(valor_del_contrato)` (PROVISIONAL) dentro de la cohorte año‑móvil:
   - `z = (x - mean) / sd`
   - **Hit si** `|z| ≥ 3` **O** `x > P95` (cola superior priorizada para sobreprecio percibido; cola inferior opcional).
5. Etiquetar explícitamente la métrica como **valor total**, no precio unitario.

## Umbrales propuestos v0

| Parámetro | Valor v0 | Rationale |
|---|---|---|
| \|z\| | **≥ 3** | Convención outlier (aprox. 99.7% bajo normalidad) |
| Percentil | **> P95** | Regla no paramétrica de respaldo |
| `N_min` | **30** | Estabilidad mínima del z-score |
| Deflactor IPC | **TBD** | Sin deflactar, inflación genera falsos positivos interanuales |

## Cómo explicar el hit
> «El contrato `{id_contrato}` (`{nombre_entidad}` → `{proveedor_adjudicado}`) en UNSPSC `{codigo_de_categoria_principal}` tiene valor `{valor_del_contrato}` COP. Frente a {n} contratos Bogotá comparables, queda en la cola estadística (|z|={z} / >P95). **Nota:** la comparación usa el valor total del contrato porque el dataset no publica cantidad ni precio unitario. Es una **señal de atipicidad de valor**, no una conclusión de sobreprecio.»

## Falsos positivos conocidos
- Objetos heterogéneos bajo el mismo UNSPSC (servicios vs bienes).
- Contratos multi-año / paquetes vs órdenes pequeñas.
- Inflación o cambio de SMMLV entre años.
- Único contrato de alta complejidad técnica en la categoría.
- Errores de tipificación UNSPSC.

## Dependencias de datos / gaps
- **Gap estructural:** no hay cantidad, unidad ni precio unitario en `jbjy-vk9h` / `p6dx-8zbt` / `qmzu-gj57` / `cb9c-h8sn`.
- v0 es un **proxy por valor total**; radar debe etiquetarlo así en UI.
- Posible enriquecimiento futuro: ítems de proceso (otros datasets CCE no incluidos aquí) — fuera de alcance v0.
- Necesita cohorte Bogotá suficientemente poblada por UNSPSC (`N_min`).

## Referencias públicas
- **OCP:** price outliers / unit price outliers vs peers (red flag); aquí adaptado a valor total por limitación de datos.
- **SIC:** indicios de coordinación de precios o sobreprecios relativos (tipo de riesgo de colusión/competencia).
- **Transparencia por Colombia:** análisis de precios atípicos en compras públicas (metodologías públicas de alerta).

## Estado
**borrador v0 — pendiente calibración con muestras Bogotá**
