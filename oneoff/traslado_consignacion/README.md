# Proceso one-off: traslado de consignacion a Sin asignar

Este proceso NO vive dentro de `src/` porque es una corrida operativa de una sola vez.

## Objetivo

Tomar `report/traslado_movimientos.csv` y crear los traslados necesarios desde:

- bodega origen: `39` (`Inventario en consignacion`)
- bodega destino: `-1` (`Sin asignar`)

La fecha configurada para esta corrida es:

- `30/03/2026`

El criterio del CSV ya viene resuelto desde `report/traslado.py`:

- `completo`: se puede cubrir toda la cantidad negativa
- `parcial`: solo se cubre una parte de la cantidad negativa
- `sin_stock`: no se ejecuta

El proceso ejecuta solo filas con:

- `estado in {completo, parcial}`
- `cantidad_a_trasladar > 0`

## Archivos

- Script principal: `oneoff/traslado_consignacion/run.py`
- Logica del batch: `oneoff/traslado_consignacion/batch.py`
- Fuente: `report/traslado_movimientos.csv`
- Salidas runtime: `oneoff/traslado_consignacion/output/`

## Seguridad contra duplicados

El proceso fue hecho para ser conservador.

### Reglas

- Por defecto corre en `dry-run`; no envia traslados reales salvo que se pase `--execute`.
- Antes de cada request real escribe eventos `sending` en un ledger append-only.
- Si una operacion ya tiene eventos previos, por defecto NO se repite.
- Tambien se saltan por defecto operaciones con `http_error` previo; solo se reintentan si se pasa `--allow-retry-failed`.
- `duplicate_error` y `success` tambien se saltan por defecto; se pueden volver a incluir con `--allow-retry-duplicate` o `--allow-retry-success` si ya reconciliaste manualmente en Siigo.
- Si ocurre cualquier error durante la corrida real, el proceso se detiene y deja el resto como `stopped`.
- Por defecto envia todos los pendientes en una sola operacion de traslado; si hace falta, puedes particionar con `--batch-size`.

### Ledger

Se guarda un historial global en:

- `oneoff/traslado_consignacion/output/ledger.jsonl`

Cada run ademas crea:

- `plan.csv`
- `events.jsonl`
- `summary.json`

## Comandos

### 1. Dry-run recomendado

```bash
PYTHONPATH=. uv run python oneoff/traslado_consignacion/run.py
```

### 2. Dry-run con limite

```bash
PYTHONPATH=. uv run python oneoff/traslado_consignacion/run.py --limit 10
```

### 3. Ejecucion real completa

```bash
PYTHONPATH=. uv run python oneoff/traslado_consignacion/run.py --execute --run-id traslado-20260330
```

### 4. Ejecucion real reintentando filas ya reconciliadas

Ejemplo: si borraste manualmente un traslado exitoso en Siigo o quieres reintentar un `duplicate_error` generado por la estrategia anterior de una fila por comprobante.

```bash
PYTHONPATH=. uv run python oneoff/traslado_consignacion/run.py --execute --run-id traslado-20260330-batch --allow-retry-success --allow-retry-duplicate
```

### 5. Reintento explicito de errores HTTP previos

Usar solo despues de revisar el ledger y confirmar que es seguro.

```bash
PYTHONPATH=. uv run python oneoff/traslado_consignacion/run.py --execute --allow-retry-failed
```

## Parametros utiles

- `--fecha`: default `30/03/2026`
- `--warehouse-code`: default `39`
- `--destination-warehouse-code`: default `-1`
- `--limit`: procesa solo las primeras operaciones elegibles
- `--batch-size`: cantidad de items por traslado; por default envia todos los pendientes en un solo comprobante
- `--run-id`: nombre manual del run
- `--output-dir`: cambia la carpeta de salidas
- `--allow-retry-duplicate`: vuelve a incluir filas con `duplicate_error`
- `--allow-retry-success`: vuelve a incluir filas con `success` ya reconciliado manualmente
- `--execute`: habilita llamadas reales a Siigo

## Formato de salida

### `plan.csv`

Incluye por fila:

- linea del CSV
- producto
- cantidad
- `operation_key`
- estado del plan (`pending`, `skip`, `success`, `error`, `stopped`)
- ultimo evento conocido
- `transfer_id` si aplica
- mensaje de error si aplica

### `events.jsonl`

Registra eventos como:

- `sending`
- `success`
- `duplicate_error`
- `ambiguous_error`
- `http_error`

Cada evento guarda el snapshot de la fila, la operacion, la hora y la respuesta relevante.

## Progreso por consola

Durante `--execute` el script imprime avance por consola, por ejemplo:

- conteo inicial del plan (`total`, `pendientes`, `skip`)
- progreso por batch (`[batch 1/1]`)
- resultado de cada envio (`OK`, `http_error`, `ambiguous_error`, etc.)
- mensaje final con la ruta del `summary.json`

## Nota operativa

Si haces una prueba parcial con `--limit`, luego puedes correr el proceso completo y el ledger evitara repetir los traslados ya enviados o ambiguos.
