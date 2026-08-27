import pandas as pd
import json


def analyze_data(input_path, output_path):
    print("\n========== ANALYSIS AGENT STARTED ==========")

    # Load cleaned dataset
    df = pd.read_csv(
        input_path,
        parse_dates=["Order.Date", "Ship.Date"]
    )

    print(f"\nDataset shape: {df.shape}")

    # 1. Total sales
    total_sales = df["Sales"].sum()

    # 2. Total profit
    total_profit = df["Profit"].sum()

    # 3. Total quantity sold
    total_quantity = df["Quantity"].sum()

    # 4. Top 10 products by sales
    top_products = (
        df.groupby("Product.Name")["Sales"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    # 5. Sales by region
    sales_by_region = (
        df.groupby("Region")["Sales"]
        .sum()
        .sort_values(ascending=False)
    )

    # 6. Sales by category
    sales_by_category = (
        df.groupby("Category")["Sales"]
        .sum()
        .sort_values(ascending=False)
    )

    # 7. Sales by year
    sales_by_year = (
        df.groupby("Year")["Sales"]
        .sum()
        .sort_values()
    )

    # Create analysis results
    analysis_results = {
        "total_sales": int(total_sales),
        "total_profit": float(total_profit),
        "total_quantity": int(total_quantity),
        "top_10_products_by_sales": top_products.to_dict(),
        "sales_by_region": sales_by_region.to_dict(),
        "sales_by_category": sales_by_category.to_dict(),
        "sales_by_year": sales_by_year.to_dict()
    }

    # Save results as JSON
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(analysis_results, file, indent=4)

    # Print results
    print("\n---------- KEY INSIGHTS ----------")

    print(f"\nTotal Sales: ${total_sales:,.2f}")
    print(f"Total Profit: ${total_profit:,.2f}")
    print(f"Total Quantity Sold: {total_quantity:,}")

    print("\nTop 10 Products by Sales:")
    print(top_products)

    print("\nSales by Region:")
    print(sales_by_region)

    print("\nSales by Category:")
    print(sales_by_category)

    print("\nSales by Year:")
    print(sales_by_year)

    print(f"\nAnalysis saved to: {output_path}")

    print("\n========== ANALYSIS AGENT COMPLETED ==========")

    return analysis_results


if __name__ == "__main__":
    analyze_data(
        input_path="data/cleaned_retail_data.csv",
        output_path="data/analysis_results.json"
    )