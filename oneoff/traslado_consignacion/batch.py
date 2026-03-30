from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from src.shared.infraestructure.httpclient.base import ClientException
from src.siigo.infraestructure.servicespd import ServicesPdSiigoWarehouseTransferClient

EXECUTABLE_STATES = {"completo", "parcial"}
PROTECTED_EVENT_TYPES = {
    "sending",
    "success",
    "duplicate_error",
    "ambiguous_error",
    "http_error",
}
DEFAULT_TRANSFER_DATE = date(2026, 3, 30)


@dataclass(frozen=True)
class TransferBatchRow:
    csv_line_number: int
    code: str
    description: str
    reference_manufactures: str
    product_code: int
    product_guid: str
    source_warehouse_label: str
    destination_warehouse_label: str
    periodos_consignacion: str
    periodos_sin_asignar: str
    cantidad_disponible: Decimal
    cantidad_negativa: Decimal
    cantidad_a_trasladar: int
    cantidad_pendiente: Decimal
    estado: str
    doc_date: date
    warehouse_code: int
    destination_warehouse_code: int

    @property
    def operation_key(self) -> str:
        return "|".join(
            [
                self.doc_date.strftime("%Y%m%d"),
                str(self.warehouse_code),
                str(self.destination_warehouse_code),
                str(self.product_code),
                str(self.cantidad_a_trasladar),
            ]
        )

    def to_log_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["cantidad_disponible"] = str(self.cantidad_disponible)
        payload["cantidad_negativa"] = str(self.cantidad_negativa)
        payload["cantidad_pendiente"] = str(self.cantidad_pendiente)
        payload["doc_date"] = self.doc_date.isoformat()
        payload["operation_key"] = self.operation_key
        return payload


@dataclass(frozen=True)
class PlanRowStatus:
    row: TransferBatchRow
    plan_status: str
    skip_reason: str | None = None
    last_event_type: str | None = None
    transfer_id: int | None = None
    error_message: str | None = None
    status_code: int | None = None

    def to_csv_dict(self) -> dict[str, Any]:
        return {
            "csv_line_number": self.row.csv_line_number,
            "code": self.row.code,
            "description": self.row.description,
            "product_code": self.row.product_code,
            "cantidad_a_trasladar": self.row.cantidad_a_trasladar,
            "estado": self.row.estado,
            "fecha": self.row.doc_date.strftime("%d/%m/%Y"),
            "warehouse_code": self.row.warehouse_code,
            "destination_warehouse_code": self.row.destination_warehouse_code,
            "operation_key": self.row.operation_key,
            "plan_status": self.plan_status,
            "skip_reason": self.skip_reason or "",
            "last_event_type": self.last_event_type or "",
            "transfer_id": self.transfer_id or "",
            "status_code": self.status_code or "",
            "error_message": self.error_message or "",
        }


class BatchSafetyError(Exception):
    pass


def parse_input_date(raw: str) -> date:
    stripped = raw.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(stripped, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Formato de fecha no soportado: {raw!r}")


def timestamp_utc() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    return str(value)


def build_run_id(*, execute: bool) -> str:
    mode = "execute" if execute else "dry-run"
    return f"{mode}-{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%SZ')}"


def parse_decimal(raw: str, *, field_name: str, csv_line_number: int) -> Decimal:
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(
            f"Linea {csv_line_number}: valor invalido para {field_name}: {raw!r}"
        ) from exc


def parse_transfer_quantity(raw: str, *, csv_line_number: int) -> int:
    quantity = parse_decimal(
        raw,
        field_name="cantidad_a_trasladar",
        csv_line_number=csv_line_number,
    )
    integral = quantity.to_integral_value()
    if quantity != integral:
        raise ValueError(
            f"Linea {csv_line_number}: cantidad_a_trasladar debe ser entera, se recibio {raw!r}"
        )
    if integral <= 0:
        raise ValueError(
            f"Linea {csv_line_number}: cantidad_a_trasladar debe ser positiva, se recibio {raw!r}"
        )
    return int(integral)


def load_transfer_rows(
    csv_path: Path,
    *,
    doc_date: date,
    warehouse_code: int,
    destination_warehouse_code: int,
) -> list[TransferBatchRow]:
    rows: list[TransferBatchRow] = []
    with csv_path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        for index, raw_row in enumerate(reader, start=2):
            estado = raw_row["estado"].strip().lower()
            cantidad_a_trasladar = parse_decimal(
                raw_row["cantidad_a_trasladar"],
                field_name="cantidad_a_trasladar",
                csv_line_number=index,
            )
            if estado not in EXECUTABLE_STATES or cantidad_a_trasladar <= 0:
                continue

            rows.append(
                TransferBatchRow(
                    csv_line_number=index,
                    code=raw_row["Code"].strip(),
                    description=raw_row["Description"].strip(),
                    reference_manufactures=raw_row["ReferenceManufactures"].strip(),
                    product_code=int(raw_row["productcode"]),
                    product_guid=raw_row["ProductGUID"].strip(),
                    source_warehouse_label=raw_row["bodega_origen"].strip(),
                    destination_warehouse_label=raw_row["bodega_destino"].strip(),
                    periodos_consignacion=raw_row["periodos_consignacion"].strip(),
                    periodos_sin_asignar=raw_row["periodos_sin_asignar"].strip(),
                    cantidad_disponible=parse_decimal(
                        raw_row["cantidad_disponible"],
                        field_name="cantidad_disponible",
                        csv_line_number=index,
                    ),
                    cantidad_negativa=parse_decimal(
                        raw_row["cantidad_negativa"],
                        field_name="cantidad_negativa",
                        csv_line_number=index,
                    ),
                    cantidad_a_trasladar=parse_transfer_quantity(
                        raw_row["cantidad_a_trasladar"],
                        csv_line_number=index,
                    ),
                    cantidad_pendiente=parse_decimal(
                        raw_row["cantidad_pendiente"],
                        field_name="cantidad_pendiente",
                        csv_line_number=index,
                    ),
                    estado=estado,
                    doc_date=doc_date,
                    warehouse_code=warehouse_code,
                    destination_warehouse_code=destination_warehouse_code,
                )
            )
    return rows


class LedgerState:
    def __init__(self, ledger_path: Path) -> None:
        self.ledger_path = ledger_path
        self.events_by_key: dict[str, list[dict[str, Any]]] = {}
        if not ledger_path.exists():
            return

        with ledger_path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise BatchSafetyError(
                        f"Ledger invalido en linea {line_number}: {exc.msg}"
                    ) from exc

                operation_key = event.get("operation_key")
                if not operation_key:
                    raise BatchSafetyError(
                        f"Ledger invalido en linea {line_number}: falta operation_key"
                    )
                self.events_by_key.setdefault(operation_key, []).append(event)

    def last_event(self, operation_key: str) -> dict[str, Any] | None:
        events = self.events_by_key.get(operation_key)
        if not events:
            return None
        return events[-1]

    def plan_status(
        self,
        operation_key: str,
        *,
        allow_retry_failed: bool,
    ) -> tuple[str, str | None, str | None]:
        last_event = self.last_event(operation_key)
        if last_event is None:
            return "pending", None, None

        last_event_type = str(last_event.get("event_type", ""))
        if last_event_type == "success":
            return "skip", "already_succeeded", last_event_type
        if last_event_type in {"sending", "ambiguous_error"}:
            return "skip", "ambiguous_previous_attempt", last_event_type
        if last_event_type == "duplicate_error":
            return "skip", "already_reported_duplicate", last_event_type
        if last_event_type == "http_error" and not allow_retry_failed:
            return "skip", "previous_http_error", last_event_type

        return "pending", None, last_event_type

    def record(self, event: dict[str, Any]) -> None:
        operation_key = str(event["operation_key"])
        self.events_by_key.setdefault(operation_key, []).append(event)


class EventLogger:
    def __init__(self, *, run_events_path: Path, global_ledger_path: Path) -> None:
        self.run_events_path = run_events_path
        self.global_ledger_path = global_ledger_path
        self.run_events_path.parent.mkdir(parents=True, exist_ok=True)
        self.global_ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=True, sort_keys=True)
        with self.run_events_path.open("a", encoding="utf-8") as run_file:
            run_file.write(line)
            run_file.write("\n")
        with self.global_ledger_path.open("a", encoding="utf-8") as ledger_file:
            ledger_file.write(line)
            ledger_file.write("\n")


def classify_client_exception(error: ClientException) -> tuple[str, bool]:
    response_text = ""
    if isinstance(error.response, str):
        response_text = error.response.lower()

    if error.status_code == 400 and "duplicidad" in response_text:
        return "duplicate_error", True
    if error.status_code is None or error.status_code >= 500:
        return "ambiguous_error", True
    return "http_error", True


def build_event(
    *,
    event_type: str,
    run_id: str,
    row: TransferBatchRow,
    execute: bool,
    **extra: Any,
) -> dict[str, Any]:
    event = {
        "event_type": event_type,
        "occurred_at": timestamp_utc(),
        "run_id": run_id,
        "execute": execute,
        "operation_key": row.operation_key,
        "row": row.to_log_dict(),
    }
    event.update({key: to_jsonable(value) for key, value in extra.items()})
    return event


def write_plan_csv(output_path: Path, plan_rows: list[PlanRowStatus]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        list(plan_rows[0].to_csv_dict().keys())
        if plan_rows
        else [
            "csv_line_number",
            "code",
            "description",
            "product_code",
            "cantidad_a_trasladar",
            "estado",
            "fecha",
            "warehouse_code",
            "destination_warehouse_code",
            "operation_key",
            "plan_status",
            "skip_reason",
            "last_event_type",
            "transfer_id",
            "status_code",
            "error_message",
        ]
    )

    with output_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        for item in plan_rows:
            writer.writerow(item.to_csv_dict())


def build_summary(
    *,
    run_id: str,
    execute: bool,
    doc_date: date,
    warehouse_code: int,
    destination_warehouse_code: int,
    input_path: Path,
    plan_rows: list[PlanRowStatus],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "run_id": run_id,
        "execute": execute,
        "doc_date": doc_date.isoformat(),
        "warehouse_code": warehouse_code,
        "destination_warehouse_code": destination_warehouse_code,
        "input_path": str(input_path),
        "generated_at": timestamp_utc(),
        "counts": {},
    }
    counts = summary["counts"]
    counts["total_executable_rows"] = len(plan_rows)
    counts["pending"] = sum(1 for item in plan_rows if item.plan_status == "pending")
    counts["success"] = sum(1 for item in plan_rows if item.plan_status == "success")
    counts["skip"] = sum(1 for item in plan_rows if item.plan_status == "skip")
    counts["error"] = sum(1 for item in plan_rows if item.plan_status == "error")
    counts["stopped"] = sum(1 for item in plan_rows if item.plan_status == "stopped")
    counts["cantidad_total"] = sum(item.row.cantidad_a_trasladar for item in plan_rows)
    counts["cantidad_ejecutada"] = sum(
        item.row.cantidad_a_trasladar
        for item in plan_rows
        if item.plan_status == "success"
    )
    counts["cantidad_pendiente"] = sum(
        item.row.cantidad_a_trasladar
        for item in plan_rows
        if item.plan_status in {"pending", "error", "stopped"}
    )
    return summary


def write_summary(output_path: Path, summary: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as target:
        json.dump(summary, target, indent=2, ensure_ascii=True, sort_keys=True)
        target.write("\n")


async def run_batch(
    *,
    csv_path: Path,
    doc_date: date,
    warehouse_code: int,
    destination_warehouse_code: int,
    run_id: str,
    output_dir: Path,
    execute: bool,
    allow_retry_failed: bool,
    limit: int | None,
) -> dict[str, Any]:
    ledger_path = output_dir / "ledger.jsonl"
    run_dir = output_dir / run_id
    plan_path = run_dir / "plan.csv"
    run_events_path = run_dir / "events.jsonl"
    summary_path = run_dir / "summary.json"

    ledger = LedgerState(ledger_path)
    logger = EventLogger(
        run_events_path=run_events_path,
        global_ledger_path=ledger_path,
    )
    all_rows = load_transfer_rows(
        csv_path,
        doc_date=doc_date,
        warehouse_code=warehouse_code,
        destination_warehouse_code=destination_warehouse_code,
    )

    plan_rows: list[PlanRowStatus] = []
    eligible_indexes: list[int] = []
    for row in all_rows:
        plan_status, skip_reason, last_event_type = ledger.plan_status(
            row.operation_key,
            allow_retry_failed=allow_retry_failed,
        )
        plan_rows.append(
            PlanRowStatus(
                row=row,
                plan_status=plan_status,
                skip_reason=skip_reason,
                last_event_type=last_event_type,
            )
        )
        if plan_status == "pending":
            eligible_indexes.append(len(plan_rows) - 1)

    if limit is not None:
        eligible_indexes = eligible_indexes[:limit]
        eligible_index_set = set(eligible_indexes)
        for index, item in enumerate(plan_rows):
            if item.plan_status == "pending" and index not in eligible_index_set:
                plan_rows[index] = PlanRowStatus(
                    row=item.row,
                    plan_status="skip",
                    skip_reason="outside_limit",
                    last_event_type=item.last_event_type,
                )

    write_plan_csv(plan_path, plan_rows)

    if not execute:
        summary = build_summary(
            run_id=run_id,
            execute=execute,
            doc_date=doc_date,
            warehouse_code=warehouse_code,
            destination_warehouse_code=destination_warehouse_code,
            input_path=csv_path,
            plan_rows=plan_rows,
        )
        write_summary(summary_path, summary)
        return summary

    client = ServicesPdSiigoWarehouseTransferClient()

    for index in eligible_indexes:
        item = plan_rows[index]
        row = item.row
        sending_event = build_event(
            event_type="sending",
            run_id=run_id,
            row=row,
            execute=execute,
        )
        logger.append(sending_event)
        ledger.record(sending_event)

        try:
            response = await client.crear_traslado_bodega(
                fecha=row.doc_date,
                codigo_producto=row.product_code,
                cantidad=row.cantidad_a_trasladar,
                warehouse_code=row.warehouse_code,
                destination_warehouse_code=row.destination_warehouse_code,
            )
        except ClientException as error:
            event_type, stop_execution = classify_client_exception(error)
            error_event = build_event(
                event_type=event_type,
                run_id=run_id,
                row=row,
                execute=execute,
                status_code=error.status_code,
                response=error.response,
                response_type=error.response_type,
                message=error.msg,
            )
            logger.append(error_event)
            ledger.record(error_event)
            plan_rows[index] = PlanRowStatus(
                row=row,
                plan_status="error",
                skip_reason=event_type,
                last_event_type=event_type,
                error_message=error.msg,
                status_code=error.status_code,
            )

            if stop_execution:
                for rest_index in eligible_indexes[eligible_indexes.index(index) + 1 :]:
                    rest_item = plan_rows[rest_index]
                    if rest_item.plan_status == "pending":
                        plan_rows[rest_index] = PlanRowStatus(
                            row=rest_item.row,
                            plan_status="stopped",
                            skip_reason="stopped_after_error",
                            last_event_type=rest_item.last_event_type,
                        )
                break
        except Exception as error:
            ambiguous_event = build_event(
                event_type="ambiguous_error",
                run_id=run_id,
                row=row,
                execute=execute,
                response=str(error),
                response_type=type(error).__name__,
                message=str(error),
            )
            logger.append(ambiguous_event)
            ledger.record(ambiguous_event)
            plan_rows[index] = PlanRowStatus(
                row=row,
                plan_status="error",
                skip_reason="ambiguous_error",
                last_event_type="ambiguous_error",
                error_message=str(error),
            )
            for rest_index in eligible_indexes[eligible_indexes.index(index) + 1 :]:
                rest_item = plan_rows[rest_index]
                if rest_item.plan_status == "pending":
                    plan_rows[rest_index] = PlanRowStatus(
                        row=rest_item.row,
                        plan_status="stopped",
                        skip_reason="stopped_after_error",
                        last_event_type=rest_item.last_event_type,
                    )
            break
        else:
            success_event = build_event(
                event_type="success",
                run_id=run_id,
                row=row,
                execute=execute,
                transfer_id=response.transfer_id,
            )
            logger.append(success_event)
            ledger.record(success_event)
            plan_rows[index] = PlanRowStatus(
                row=row,
                plan_status="success",
                last_event_type="success",
                transfer_id=response.transfer_id,
            )

    write_plan_csv(plan_path, plan_rows)
    summary = build_summary(
        run_id=run_id,
        execute=execute,
        doc_date=doc_date,
        warehouse_code=warehouse_code,
        destination_warehouse_code=destination_warehouse_code,
        input_path=csv_path,
        plan_rows=plan_rows,
    )
    write_summary(summary_path, summary)
    return summary
