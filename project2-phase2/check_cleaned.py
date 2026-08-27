import pandas as pd

df = pd.read_csv(
    "data/cleaned_retail_data.csv",
    parse_dates=["Order.Date", "Ship.Date"]
)

print("\n========== CLEANED DATA VERIFICATION ==========")

print("\nDataset shape:")
print(df.shape)

print("\nData types:")
print(df.dtypes)

print("\nMissing values:")
print(df.isnull().sum().sum())

print("\nDuplicate rows:")
print(df.duplicated().sum())

print("\nFirst 3 rows:")
print(df.head(3))

print("\n========== VERIFICATION COMPLETE ==========")