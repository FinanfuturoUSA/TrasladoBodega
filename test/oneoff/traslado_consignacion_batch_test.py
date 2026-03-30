import csv
import json
from datetime import date
from pathlib import Path

import pytest

from oneoff.traslado_consignacion.batch import (
    LedgerState,
    load_transfer_rows,
    run_batch,
)


CSV_HEADERS = [
    "Code",
    "Description",
    "ReferenceManufactures",
    "productcode",
    "ProductGUID",
    "bodega_origen",
    "bodega_destino",
    "periodos_consignacion",
    "periodos_sin_asignar",
    "cantidad_disponible",
    "cantidad_negativa",
    "cantidad_a_trasladar",
    "cantidad_pendiente",
    "estado",
]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def make_row(
    *,
    code: str,
    product_code: str,
    cantidad_a_trasladar: str,
    cantidad_pendiente: str,
    estado: str,
) -> dict[str, str]:
    return {
        "Code": code,
        "Description": f"Producto {code}",
        "ReferenceManufactures": "Proveedor",
        "productcode": product_code,
        "ProductGUID": f"guid-{code}",
        "bodega_origen": "CONSIG01 - Inventario en consignacion",
        "bodega_destino": "Sin asignar",
        "periodos_consignacion": "202603",
        "periodos_sin_asignar": "202603",
        "cantidad_disponible": "10.0",
        "cantidad_negativa": "10.0",
        "cantidad_a_trasladar": cantidad_a_trasladar,
        "cantidad_pendiente": cantidad_pendiente,
        "estado": estado,
    }


def test_load_transfer_rows_filtra_ejecutables(tmp_path: Path) -> None:
    csv_path = tmp_path / "traslados.csv"
    write_csv(
        csv_path,
        [
            make_row(
                code="A",
                product_code="1001",
                cantidad_a_trasladar="2.0",
                cantidad_pendiente="0.0",
                estado="completo",
            ),
            make_row(
                code="B",
                product_code="1002",
                cantidad_a_trasladar="0.0",
                cantidad_pendiente="2.0",
                estado="sin_stock",
            ),
            make_row(
                code="C",
                product_code="1003",
                cantidad_a_trasladar="1.0",
                cantidad_pendiente="1.0",
                estado="parcial",
            ),
        ],
    )

    rows = load_transfer_rows(
        csv_path,
        doc_date=date(2026, 3, 30),
        warehouse_code=39,
        destination_warehouse_code=-1,
    )

    assert [row.code for row in rows] == ["A", "C"]
    assert [row.cantidad_a_trasladar for row in rows] == [2, 1]
    assert rows[0].operation_key == "20260330|39|-1|1001|2"


def test_ledger_state_bloquea_eventos_previos(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger_path.write_text(
        "\n".join(
            [
                json.dumps({"operation_key": "ok", "event_type": "success"}),
                json.dumps({"operation_key": "amb", "event_type": "sending"}),
                json.dumps({"operation_key": "err", "event_type": "http_error"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    ledger = LedgerState(ledger_path)

    assert ledger.plan_status("ok", allow_retry_failed=False) == (
        "skip",
        "already_succeeded",
        "success",
    )
    assert ledger.plan_status("amb", allow_retry_failed=False) == (
        "skip",
        "ambiguous_previous_attempt",
        "sending",
    )
    assert ledger.plan_status("err", allow_retry_failed=False) == (
        "skip",
        "previous_http_error",
        "http_error",
    )
    assert ledger.plan_status("err", allow_retry_failed=True) == (
        "pending",
        None,
        "http_error",
    )


@pytest.mark.anyio
async def test_run_batch_dry_run_respeta_ledger_y_limit(tmp_path: Path) -> None:
    csv_path = tmp_path / "traslados.csv"
    write_csv(
        csv_path,
        [
            make_row(
                code="A",
                product_code="1001",
                cantidad_a_trasladar="2.0",
                cantidad_pendiente="0.0",
                estado="completo",
            ),
            make_row(
                code="B",
                product_code="1002",
                cantidad_a_trasladar="1.0",
                cantidad_pendiente="0.0",
                estado="completo",
            ),
            make_row(
                code="C",
                product_code="1003",
                cantidad_a_trasladar="3.0",
                cantidad_pendiente="1.0",
                estado="parcial",
            ),
        ],
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ledger.jsonl").write_text(
        json.dumps({"operation_key": "20260330|39|-1|1002|1", "event_type": "success"})
        + "\n",
        encoding="utf-8",
    )

    summary = await run_batch(
        csv_path=csv_path,
        doc_date=date(2026, 3, 30),
        warehouse_code=39,
        destination_warehouse_code=-1,
        run_id="dry-run-test",
        output_dir=output_dir,
        execute=False,
        allow_retry_failed=False,
        limit=1,
    )

    assert summary["counts"] == {
        "total_executable_rows": 3,
        "pending": 1,
        "skip": 2,
        "success": 0,
        "error": 0,
        "stopped": 0,
        "cantidad_total": 6,
        "cantidad_ejecutada": 0,
        "cantidad_pendiente": 2,
    }

    plan_path = output_dir / "dry-run-test" / "plan.csv"
    summary_path = output_dir / "dry-run-test" / "summary.json"
    assert plan_path.exists()
    assert summary_path.exists()

    with plan_path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))

    assert rows[0]["plan_status"] == "pending"
    assert rows[1]["plan_status"] == "skip"
    assert rows[1]["skip_reason"] == "already_succeeded"
    assert rows[2]["plan_status"] == "skip"
    assert rows[2]["skip_reason"] == "outside_limit"
