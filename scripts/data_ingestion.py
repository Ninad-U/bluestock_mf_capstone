import os
import pandas as pd

# ----------------------------------------------------
# Configuration
# ----------------------------------------------------

DATA_FOLDER = "../data/raw"

# Datasets 
csv_files = [
    "fund_master.csv",
    "nav_history.csv",
    "aum_by_fund_house.csv",
    "monthly_sip_inflows.csv",
    "category_inflows.csv",
    "industry_folio_count.csv",
    "scheme_performance.csv",
    "investor_transactions.csv",
    "portfolio_holdings.csv",
    "benchmark_indices.csv",
]

# ----------------------------------------------------
# Load datasets
# ----------------------------------------------------

for filename in csv_files:
    filepath = os.path.join(DATA_FOLDER, filename)

    print("=" * 80)
    print(f"Dataset: {filename}")
    print("=" * 80)

    try:
        df = pd.read_csv(filepath)

        print("\nShape:")
        print(df.shape)

        print("\nData Types:")
        print(df.dtypes)

        print("\nFirst 5 Rows:")
        print(df.head())

        print("\n")

    except FileNotFoundError:
        print(f"File not found: {filepath}\n")

    except Exception as e:
        print(f"Error loading {filename}")
        print(e)
        print()