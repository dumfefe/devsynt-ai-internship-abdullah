import pandas as pd


def clean_data(input_path, output_path):
    print("\n========== CLEAN AGENT STARTED ==========")

    # Load raw dataset
    df = pd.read_csv(input_path)

    original_rows = len(df)

    print(f"\nOriginal shape: {df.shape}")

    # 1. Check and handle missing values
    missing_before = df.isnull().sum().sum()
    print(f"Missing values before cleaning: {missing_before}")

    # Remove rows that are completely empty
    df = df.dropna(how="all")

    # Fill numeric missing values with median
    numeric_columns = df.select_dtypes(include="number").columns
    for column in numeric_columns:
        if df[column].isnull().sum() > 0:
            df[column] = df[column].fillna(df[column].median())

    # Fill text missing values with "Unknown"
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for column in text_columns:
        if df[column].isnull().sum() > 0:
            df[column] = df[column].fillna("Unknown")

    # 2. Fix incorrect date data types
    date_columns = ["Order.Date", "Ship.Date"]

    for column in date_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
                dayfirst=False
            )

    # 3. Remove duplicate rows
    duplicates_before = df.duplicated().sum()
    df = df.drop_duplicates()

    # 4. Remove rows with invalid sales or quantity
    rows_before_validation = len(df)

    if "Sales" in df.columns:
        df = df[df["Sales"] >= 0]

    if "Quantity" in df.columns:
        df = df[df["Quantity"] > 0]

    invalid_rows_removed = rows_before_validation - len(df)

    # Final cleaning statistics
    final_rows = len(df)
    missing_after = df.isnull().sum().sum()
    rows_removed = original_rows - final_rows

    # Save cleaned dataset
    df.to_csv(output_path, index=False)

    print("\n---------- CLEANING REPORT ----------")
    print(f"Original rows: {original_rows}")
    print(f"Duplicate rows found: {duplicates_before}")
    print(f"Invalid rows removed: {invalid_rows_removed}")
    print(f"Total rows removed: {rows_removed}")
    print(f"Missing values after cleaning: {missing_after}")
    print(f"Final shape: {df.shape}")
    print(f"\nCleaned data saved to: {output_path}")
    print("\n========== CLEAN AGENT COMPLETED ==========")

    return df


if __name__ == "__main__":
    clean_data(
        input_path="data/retail_data.csv",
        output_path="data/cleaned_retail_data.csv"
    )