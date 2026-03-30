import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_PATH = BASE_DIR / "data" / "saldo_inventaio.json"
OUTPUT_PATH = Path(__file__).resolve().with_name("traslado_movimientos.csv")
UNASSIGNED_WAREHOUSE = "Sin asignar"
CONSIGNMENT_WAREHOUSE = "CONSIG01 - Inventario en consignación"
PRODUCT_COLUMNS = [
    "Code",
    "ProductGUID",
    "Description",
    "ReferenceManufactures",
    "productcode",
]


def load_dataframe() -> pd.DataFrame:
    with INPUT_PATH.open(encoding="utf-8") as source:
        payload = json.load(source)

    return pd.DataFrame(payload["data"]["Value"]["Table"])


def summarize_rows(
    dataframe: pd.DataFrame, mask: pd.Series, quantity_column: str, period_column: str
) -> pd.DataFrame:
    return (
        dataframe.loc[mask, PRODUCT_COLUMNS + ["QuantityBalance", "period"]]
        .assign(period=lambda df: df["period"].astype(str))
        .groupby(PRODUCT_COLUMNS, as_index=False)
        .agg(
            **{
                quantity_column: ("QuantityBalance", "sum"),
                period_column: ("period", lambda values: ",".join(sorted(set(values)))),
            }
        )
    )


def build_report(dataframe: pd.DataFrame) -> pd.DataFrame:
    negative_rows = summarize_rows(
        dataframe,
        (dataframe["CodDesWH"] == UNASSIGNED_WAREHOUSE)
        & (dataframe["QuantityBalance"] < 0),
        "cantidad_negativa",
        "periodos_sin_asignar",
    )
    positive_rows = summarize_rows(
        dataframe,
        (dataframe["CodDesWH"] == CONSIGNMENT_WAREHOUSE)
        & (dataframe["QuantityBalance"] > 0),
        "cantidad_disponible",
        "periodos_consignacion",
    )

    report = negative_rows.merge(positive_rows, on=PRODUCT_COLUMNS, how="left")
    report["cantidad_negativa"] = report["cantidad_negativa"].abs()
    report["cantidad_disponible"] = report["cantidad_disponible"].fillna(0.0)
    report["periodos_consignacion"] = report["periodos_consignacion"].fillna("")
    report["cantidad_a_trasladar"] = report[
        ["cantidad_negativa", "cantidad_disponible"]
    ].min(axis=1)
    report["cantidad_pendiente"] = (
        report["cantidad_negativa"] - report["cantidad_a_trasladar"]
    )
    report["bodega_origen"] = CONSIGNMENT_WAREHOUSE
    report["bodega_destino"] = UNASSIGNED_WAREHOUSE
    report["estado"] = report.apply(build_status, axis=1)

    return (
        report[
            [
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
        ]
        .sort_values(["estado", "Code"])
        .reset_index(drop=True)
    )


def build_status(row: pd.Series) -> str:
    if row["cantidad_a_trasladar"] == 0:
        return "sin_stock"
    if row["cantidad_pendiente"] == 0:
        return "completo"
    return "parcial"


def print_summary(report: pd.DataFrame) -> None:
    total_productos = len(report)
    productos_con_traslado = int((report["cantidad_a_trasladar"] > 0).sum())
    productos_completos = int((report["estado"] == "completo").sum())
    productos_parciales = int((report["estado"] == "parcial").sum())
    productos_sin_stock = int((report["estado"] == "sin_stock").sum())
    cantidad_negativa_total = report["cantidad_negativa"].sum()
    cantidad_a_trasladar_total = report["cantidad_a_trasladar"].sum()
    cantidad_pendiente_total = report["cantidad_pendiente"].sum()

    print(f"Reporte generado en: {OUTPUT_PATH}")
    print(f"Total productos con saldo negativo: {total_productos}")
    print(f"Productos con traslado: {productos_con_traslado}")
    print(f"Traslados completos: {productos_completos}")
    print(f"Traslados parciales: {productos_parciales}")
    print(f"Productos sin stock de cobertura: {productos_sin_stock}")
    print(f"Cantidad negativa total: {cantidad_negativa_total}")
    print(f"Cantidad a trasladar: {cantidad_a_trasladar_total}")
    print(f"Cantidad pendiente: {cantidad_pendiente_total}")


def main() -> None:
    dataframe = load_dataframe()
    report = build_report(dataframe)
    report.to_csv(OUTPUT_PATH, index=False)
    print_summary(report)


if __name__ == "__main__":
    main()
