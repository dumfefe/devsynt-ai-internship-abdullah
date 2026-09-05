# Test Datasets

| File | Domain | Rows | Source |
|---|---|---|---|
| `retail_sales.csv` | Retail sales | 51,290 | Your existing Phase 1/2 dataset (unchanged) |
| `ecommerce_orders.csv` | E-commerce orders | 800 | Synthetic — generated for this phase's testing |
| `inventory_stock.csv` | Inventory / stock | 500 | Synthetic — generated for this phase's testing |
| `restaurant_sales.csv` | Restaurant sales | 900 | Synthetic — generated for this phase's testing |
| `saas_metrics.csv` | SaaS subscription metrics | 700 | Synthetic — generated for this phase's testing |

The four synthetic datasets were generated locally (not pulled from Kaggle)
to test the pipeline's domain-detection and dashboard logic across genuinely
different column structures without depending on internet access during
development. They're realistic in shape (plausible column names, value
ranges, and category distributions for each domain) but the actual values
are randomly generated, not real transactions.

**If you want real data for the final submission**, swap any of these for an
actual Kaggle dataset in the same domain — the pipeline doesn't care where
the CSV came from, only that the columns look like that domain. Good
replacements:
- E-commerce: "Brazilian E-Commerce Public Dataset by Olist"
- Inventory: search Kaggle for "inventory management dataset" / "retail stock"
- Restaurant: "Restaurant Sales Data" (several available on Kaggle)
- SaaS: "SaaS Sales Data" or "Subscription Analytics" datasets on Kaggle

Re-running `python agents/run_all_datasets.py` after swapping a CSV (same
filename) needs no code changes — that's the point of this phase.
