import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_PATH = BASE_DIR / "data" / "saldo_inventaio.json"
OUTPUT_PATH = Path(__file__).resolve().with_name("saldo_inventaio.csv")


def main() -> None:
    with INPUT_PATH.open(encoding="utf-8") as source:
        payload = json.load(source)

    rows = payload["data"]["Value"]["Table"]
    dataframe = pd.DataFrame(rows)
    dataframe.to_csv(OUTPUT_PATH, index=False)

    print(f"CSV generado en: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
