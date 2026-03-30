from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

import argparse
import asyncio
from pathlib import Path

from oneoff.traslado_consignacion.batch import (
    DEFAULT_TRANSFER_DATE,
    BatchSafetyError,
    build_run_id,
    parse_input_date,
    run_batch,
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = Path("report/traslado_movimientos.csv")
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_WAREHOUSE_CODE = 39
DEFAULT_DESTINATION_WAREHOUSE_CODE = -1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Proceso one-off para trasladar cantidades desde Inventario en "
            "consignacion (39) hacia Sin asignar (-1)."
        )
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Ruta del CSV fuente. Default: report/traslado_movimientos.csv",
    )
    parser.add_argument(
        "--fecha",
        default=DEFAULT_TRANSFER_DATE.strftime("%d/%m/%Y"),
        help="Fecha contable del traslado. Acepta DD/MM/YYYY o YYYY-MM-DD.",
    )
    parser.add_argument(
        "--warehouse-code",
        type=int,
        default=DEFAULT_WAREHOUSE_CODE,
        help="Codigo de bodega origen. Default: 39",
    )
    parser.add_argument(
        "--destination-warehouse-code",
        type=int,
        default=DEFAULT_DESTINATION_WAREHOUSE_CODE,
        help="Codigo de bodega destino. Default: -1",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directorio para ledger y salidas del run.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Identificador manual del run. Si se omite, se genera automaticamente.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita la cantidad de operaciones elegibles a procesar.",
    )
    parser.add_argument(
        "--allow-retry-failed",
        action="store_true",
        help=(
            "Permite reintentar filas cuyo ultimo evento en el ledger fue http_error. "
            "Por defecto tambien se saltan para evitar duplicados."
        ),
    )
    parser.add_argument(
        "--allow-retry-duplicate",
        action="store_true",
        help=(
            "Permite reintentar filas cuyo ultimo evento fue duplicate_error. "
            "Usalo si cambiaste de estrategia y necesitas volver a incluirlas."
        ),
    )
    parser.add_argument(
        "--allow-retry-success",
        action="store_true",
        help=(
            "Permite volver a incluir filas con success previo en el ledger. "
            "Usalo solo si ya eliminaste manualmente ese traslado en Siigo."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help=(
            "Cantidad de items por traslado. Default: todos los pendientes en una sola operacion."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Ejecuta los traslados reales. Si no se envia, corre en dry-run.",
    )
    return parser


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    doc_date = parse_input_date(args.fecha)
    run_id = args.run_id or build_run_id(execute=args.execute)

    if not input_path.exists():
        raise FileNotFoundError(f"No existe el archivo fuente: {input_path}")
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit debe ser mayor que cero")
    if args.batch_size is not None and args.batch_size <= 0:
        raise ValueError("--batch-size debe ser mayor que cero")

    summary = await run_batch(
        csv_path=input_path,
        doc_date=doc_date,
        warehouse_code=args.warehouse_code,
        destination_warehouse_code=args.destination_warehouse_code,
        run_id=run_id,
        output_dir=output_dir,
        execute=args.execute,
        allow_retry_failed=args.allow_retry_failed,
        allow_retry_duplicate=args.allow_retry_duplicate,
        allow_retry_success=args.allow_retry_success,
        limit=args.limit,
        batch_size=args.batch_size,
        progress_hook=print,
    )

    counts = summary["counts"]
    print(f"run_id={summary['run_id']}")
    print(f"execute={summary['execute']}")
    print(f"doc_date={summary['doc_date']}")
    print(f"input_path={summary['input_path']}")
    print(f"total_executable_rows={counts['total_executable_rows']}")
    print(f"pending={counts['pending']}")
    print(f"skip={counts['skip']}")
    print(f"success={counts['success']}")
    print(f"error={counts['error']}")
    print(f"stopped={counts['stopped']}")
    print(f"cantidad_total={counts['cantidad_total']}")
    print(f"cantidad_ejecutada={counts['cantidad_ejecutada']}")
    print(f"cantidad_pendiente={counts['cantidad_pendiente']}")
    print(f"output_dir={output_dir / run_id}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BatchSafetyError as error:
        raise SystemExit(f"ERROR DE SEGURIDAD: {error}")
