# Radar SECOP Bogotá

Radar de **riesgo** de fraude en contratación pública **solo para Bogotá** sobre SECOP II (datos abiertos), más un grafo simple de red de proveedores.

> **Importante:** este producto prioriza señales de *riesgo* auditables. **No** afirma ni demuestra fraude probado.

## Fuentes (datos.gov.co)

| Dataset | ID Socrata |
|---------|------------|
| Contratos | `jbjy-vk9h` |
| Procesos | `p6dx-8zbt` |
| Proveedores | `qmzu-gj57` |
| Adiciones | `cb9c-h8sn` |

Alcance geográfico del MVP: **Bogotá únicamente** (sin cobertura nacional).

## Entregables (MVP)

1. **Lista semanal priorizada** de contratos/procesos con señales de riesgo.
2. **Ficha de contrato legible** con enlace `urlproceso`.
3. **Grafo simple** de red de proveedores (relaciones básicas).
4. **Export CSV** de la lista priorizada.

## Anti-alcance (MVP)

- Sin alcance nacional.
- Sin lenguaje de «fraude probado».
- Sin scrape de PDF en el MVP.

## Estructura del repositorio

```
data/raw/        # descargas crudas (no versionar dumps)
data/clean/      # tablas limpias
data/exports/    # CSV y entregables
src/ingest/      # descarga / normalización
src/signals/     # reglas de riesgo
src/graph/       # red de proveedores
src/export/      # exportaciones
docs/signals/    # especificaciones de señales
scripts/         # utilidades de operación
```

## Señales planificadas

Ver [docs/signals/README.md](docs/signals/README.md). Specs formales: `signal-01` … `signal-07` en ese directorio (origen compartido en el box: `/workspace/secop-signals/`).

## Dependencias

Python mínimo: `pandas`, `pyarrow`, `requests` (ver `requirements.txt`).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Estado

Scaffold inicial del MVP. Sin descarga de datasets SECOP en este commit.
