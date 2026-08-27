import json
import os
import matplotlib.pyplot as plt


def create_visualizations(input_path, output_folder):
    print("\n========== VISUALIZATION AGENT STARTED ==========")

    # Create assets folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Load analysis results
    with open(input_path, "r", encoding="utf-8") as file:
        results = json.load(file)

    # -------------------------------
    # 1. Sales by Category
    # -------------------------------
    categories = results["sales_by_category"]

    plt.figure(figsize=(8, 5))
    plt.bar(categories.keys(), categories.values())
    plt.title("Sales by Category")
    plt.xlabel("Category")
    plt.ylabel("Sales ($)")
    plt.tight_layout()

    category_chart = os.path.join(
        output_folder,
        "sales_by_category.png"
    )

    plt.savefig(category_chart)
    plt.close()

    print(f"Created: {category_chart}")

    # -------------------------------
    # 2. Sales by Region
    # -------------------------------
    regions = results["sales_by_region"]

    plt.figure(figsize=(10, 6))
    plt.barh(
        list(regions.keys())[::-1],
        list(regions.values())[::-1]
    )

    plt.title("Sales by Region")
    plt.xlabel("Sales ($)")
    plt.ylabel("Region")
    plt.tight_layout()

    region_chart = os.path.join(
        output_folder,
        "sales_by_region.png"
    )

    plt.savefig(region_chart)
    plt.close()

    print(f"Created: {region_chart}")

    # -------------------------------
    # 3. Sales Growth by Year
    # -------------------------------
    years = results["sales_by_year"]

    plt.figure(figsize=(8, 5))
    plt.plot(
        list(years.keys()),
        list(years.values()),
        marker="o"
    )

    plt.title("Sales Growth by Year")
    plt.xlabel("Year")
    plt.ylabel("Sales ($)")
    plt.grid(True)
    plt.tight_layout()

    yearly_chart = os.path.join(
        output_folder,
        "sales_by_year.png"
    )

    plt.savefig(yearly_chart)
    plt.close()

    print(f"Created: {yearly_chart}")

    # -------------------------------
    # 4. Top 10 Products
    # -------------------------------
    products = results["top_10_products_by_sales"]

    plt.figure(figsize=(12, 7))
    plt.barh(
        list(products.keys())[::-1],
        list(products.values())[::-1]
    )

    plt.title("Top 10 Products by Sales")
    plt.xlabel("Sales ($)")
    plt.ylabel("Product")
    plt.tight_layout()

    products_chart = os.path.join(
        output_folder,
        "top_10_products.png"
    )

    plt.savefig(products_chart)
    plt.close()

    print(f"Created: {products_chart}")

    print("\n========== VISUALIZATION AGENT COMPLETED ==========")


if __name__ == "__main__":
    create_visualizations(
        input_path="data/analysis_results.json",
        output_folder="assets"
    )