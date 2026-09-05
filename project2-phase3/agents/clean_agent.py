"""
Clean Agent (domain-agnostic, Phase 3)
---------------------------------------
Phase 2's version hardcoded "Order.Date" / "Ship.Date" / "Sales" / "Quantity".
This version cleans ANY tabular dataset generically, using the domain config's
date_columns / numeric_columns lists (falling back to auto-detection if the
config doesn't have them, so this still works standalone).

Error handling: never raises on a single bad column/row -- logs a warning and
keeps going, so one malformed column doesn't take down the whole pipeline.
"""

import json
import pandas as pd


def _load_config(config_path):
    if not config_path:
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"   [clean-agent] warning: could not read domain config ({e}), using auto-detection")
        return {}


def clean_data(input_path, output_path, config_path=None):
    print("\n========== CLEAN AGENT STARTED ==========")

    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        raise RuntimeError(f"Clean Agent could not read '{input_path}': {e}")

    config = _load_config(config_path)
    original_rows = len(df)
    print(f"Original shape: {df.shape}")

    # 1. Drop fully empty rows
    df = df.dropna(how="all")

    # 2. Fill missing values
    missing_before = int(df.isnull().sum().sum())
    numeric_columns = df.select_dtypes(include="number").columns
    for column in numeric_columns:
        if df[column].isnull().sum() > 0:
            try:
                df[column] = df[column].fillna(df[column].median())
            except Exception as e:
                print(f"   [clean-agent] warning: could not fill numeric column '{column}' ({e})")

    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for column in text_columns:
        if df[column].isnull().sum() > 0:
            df[column] = df[column].fillna("Unknown")

    # 3. Parse date columns -- prefer config's date_columns, else auto-detect by name
    date_columns = config.get("date_columns") or [
        c for c in df.columns if "date" in c.lower() or "time" in c.lower()
    ]
    for column in date_columns:
        if column in df.columns:
            try:
                df[column] = pd.to_datetime(df[column], errors="coerce")
            except Exception as e:
                print(f"   [clean-agent] warning: could not parse date column '{column}' ({e})")

    # 4. Remove duplicate rows
    duplicates_before = int(df.duplicated().sum())
    df = df.drop_duplicates()

    # 5. Remove rows with a negative PRIMARY value (e.g. negative Sales/Revenue
    #    is almost always a data error). Deliberately narrow: only the single
    #    primary_value_column, not every numeric metric -- columns like Profit
    #    or Discount can be legitimately negative (a loss-making sale, a
    #    markup), and dropping those rows would silently delete real data.
    rows_before_validation = len(df)
    primary_value_column = config.get("key_columns", {}).get("primary_value_column")

    if primary_value_column and primary_value_column in df.columns \
            and pd.api.types.is_numeric_dtype(df[primary_value_column]):
        df = df[df[primary_value_column].fillna(0) >= 0]

    invalid_rows_removed = rows_before_validation - len(df)

    final_rows = len(df)
    missing_after = int(df.isnull().sum().sum())
    rows_removed = original_rows - final_rows

    try:
        df.to_csv(output_path, index=False)
    except Exception as e:
        raise RuntimeError(f"Clean Agent could not save cleaned data to '{output_path}': {e}")

    print("---------- CLEANING REPORT ----------")
    print(f"Original rows: {original_rows}")
    print(f"Missing values before/after: {missing_before} / {missing_after}")
    print(f"Duplicate rows removed: {duplicates_before}")
    print(f"Invalid rows removed: {invalid_rows_removed}")
    print(f"Final shape: {df.shape}")
    print(f"Cleaned data saved to: {output_path}")
    print("========== CLEAN AGENT COMPLETED ==========")

    return {
        "original_rows": original_rows,
        "final_rows": final_rows,
        "duplicates_removed": duplicates_before,
        "invalid_rows_removed": invalid_rows_removed,
        "missing_before": missing_before,
        "missing_after": missing_after,
    }


if __name__ == "__main__":
    clean_data(
        input_path="../test-datasets/retail_sales.csv",
        output_path="../test-datasets/cleaned_retail_sales.csv",
        config_path="../test-datasets/domain_config.json",
    )
