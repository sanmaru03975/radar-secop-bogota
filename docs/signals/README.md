# Señales de riesgo (SECOP Bogotá)

Siete reglas auditables planificadas para el MVP. Cada una produce una señal de **riesgo** (no prueba de fraude).

Las especificaciones formales viven con el teammate *reglas secop* en `/workspace/secop-signals/` en el box compartido. En este repo se copian los archivos `signal-01` … `signal-07` cuando existen y son cortos.

| ID | Regla | Spec |
|----|-------|------|
| 01 | `unico_oferente` | [signal-01-unico-oferente.md](signal-01-unico-oferente.md) |
| 02 | `plazo_corto` | [signal-02-plazo-corto.md](signal-02-plazo-corto.md) |
| 03 | `cd_alto_valor` | [signal-03-cd-alto-valor.md](signal-03-cd-alto-valor.md) |
| 04 | `fraccionamiento` | [signal-04-fraccionamiento.md](signal-04-fraccionamiento.md) |
| 05 | `outlier_unspsc` | [signal-05-outlier-unspsc.md](signal-05-outlier-unspsc.md) |
| 06 | `adicion_cerca_50` | [signal-06-adicion-cerca-50.md](signal-06-adicion-cerca-50.md) |
| 07 | `red_rl_direccion` | [signal-07-red-rl-direccion.md](signal-07-red-rl-direccion.md) |

Implementación prevista en `src/signals/`.
