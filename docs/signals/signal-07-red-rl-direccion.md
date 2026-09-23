# Señal: Red de representante legal / dirección / NIT

## Señal
- **Nombre corto:** Red RL / dirección  
- **ID estable:** `red_rl_direccion`  
- **Estado:** borrador v0 — pendiente calibración con muestras Bogotá

## Qué busca
Detectar **NITs distintos** que comparten representante legal (nombre o documento) o dirección normalizada, y que **co-aparecen como proveedores** ante la misma entidad contratante en una ventana de 12 meses. Es una señal de posible red de control común o vínculos no evidentes en la razón social; útil para análisis de conflicto de interés o colusión — **sin afirmar** que exista.

## Campos SECOP

| Dataset | Field API | Rol |
|---|---|---|
| `qmzu-gj57` | `nit` | Identificador proveedor |
| `qmzu-gj57` | `codigo` | Código plataforma (join alterno) |
| `qmzu-gj57` | `nombre` | Razón social |
| `qmzu-gj57` | `nombre_representante_legal` | RL (nombre) |
| `qmzu-gj57` | `tipo_doc_representante_legal` | Tipo doc RL |
| `qmzu-gj57` | `n_mero_doc_representante_legal` | Doc RL (clave fuerte) |
| `qmzu-gj57` | `direccion` | Dirección registrada proveedor |
| `qmzu-gj57` | `municipio` / `departamento` | Contexto geo |
| `jbjy-vk9h` | `documento_proveedor` / `codigo_proveedor` | Join a contratos |
| `jbjy-vk9h` | `nit_entidad` / `nombre_entidad` | Entidad compradora |
| `jbjy-vk9h` | `fecha_de_firma` | Ventana 12 meses |
| `jbjy-vk9h` | `departamento` | Filtro Bogotá |
| `jbjy-vk9h` | `nombre_representante_legal` | RL reportado en contrato (refuerzo) |
| `jbjy-vk9h` | `identificaci_n_representante_legal` | Doc RL en contrato |
| `jbjy-vk9h` | `domicilio_representante_legal` | Domicilio RL en contrato (a menudo pobre) |
| `jbjy-vk9h` | `direcci_n_de_ejecuci_n_del_contrato` | No es domicilio del proveedor — **no usar** como dirección fiscal |

## Definición operativa (v0 — PROVISIONAL)

1. Normalizar:
   - `rl_id = digits(n_mero_doc_representante_legal)` preferido; si vacío, `rl_name = upper(unaccent(trim(nombre_representante_legal)))`.
   - `addr = upper(unaccent(trim(direccion)))` removiendo `#`, `,`, espacios múltiples; excluir valores basura: `No Provisto`, `No Definido`, `Sin Descripcion`, vacíos.
2. Construir aristas entre NITs distintos que compartan `rl_id` **o** (`rl_name` si longitud ≥ 8) **o** `addr` (si longitud ≥ 12).
3. Desde contratos Bogotá en 12 meses (`fecha_de_firma`):
   - Para cada `nit_entidad`, ver proveedores distintos que contrataron.
   - **Hit si** ≥2 NITs distintos ligados por una arista anterior co-aparecen con la misma `nit_entidad` en la ventana.
4. Severidad provisional: más peso si el vínculo es por `rl_id` que solo por dirección.

## Umbrales propuestos v0

| Parámetro | Valor v0 | Rationale |
|---|---|---|
| NITs distintos mínimos | **≥ 2** | Red mínima |
| Ventana co-aparición | **12 meses** | Ciclo presupuestal típico |
| Longitud mínima dirección útil | **≥ 12** chars post-normalización | Evitar “CALLE 1” genéricas |
| Confiar nombre RL sin doc | Solo si len ≥ 8 | Homónimos |

## Cómo explicar el hit
> «Los proveedores `{nit_a} ({nombre_a})` y `{nit_b} ({nombre_b})` comparten `{tipo_vinculo: mismo doc RL / mismo nombre RL / misma dirección}` (`{detalle_vinculo}`) y ambos tienen contratos con `{nombre_entidad}` entre `{fecha_min}` y `{fecha_max}`. Es una **señal de vínculo societario/domiciliario** que sugiere revisar beneficiarios reales y posibles conflictos; el vínculo puede ser lícito (grupo empresarial, coworking, error de registro).»

## Falsos positivos conocidos
- Homónimos en `nombre_representante_legal` sin documento.
- Direcciones genéricas o centros de domiciliación masiva.
- Personas naturales donde NIT = cédula = RL (auto-vínculo trivial — excluir).
- Grupos empresariales declarados (`es_grupo`) con RL común esperado.
- Datos `No Definido` / `No Provisto` mal filtrados.
- `domicilio_representante_legal` en contratos con baja calidad (preferir `qmzu-gj57.direccion`).

## Dependencias de datos / gaps
- Campos RL y dirección en `qmzu-gj57` **verificados**.
- RL en `jbjy-vk9h` verificado; en muestra Bogotá a menudo replica al proveedor persona natural; `domicilio_representante_legal` frecuentemente `No Definido`.
- No hay campo RUES de beneficiario final en estos datasets.
- Normalización de dirección es heurística (sin geocoder) → calibrar.
- Co-aparición exige join robusto `documento_proveedor` ↔ `nit` (formatos con/sin dígito de verificación — **TBD**).

## Referencias públicas
- **SIC:** redes de oferentes relacionados / rotación entre empresas vinculadas (patrón de riesgo de colusión).
- **OCP:** shared ownership, beneficial ownership, same address across bidders (red flags de integridad).
- **Transparencia por Colombia:** análisis de redes de contratistas y posibles conflictos de interés (tipo de alerta pública).

## Estado
**borrador v0 — pendiente calibración con muestras Bogotá**
