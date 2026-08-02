import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path

# Project paths

BASE_DIR = Path(__file__).resolve().parent.parent

db_path = BASE_DIR / "data" / "db" / "bluestock_mf.db"

engine = create_engine(f"sqlite:///{db_path}")

try:

    # Load cleaned CSVs

    fund_master = pd.read_csv(BASE_DIR / "data" / "processed" / "fund_master_cleaned.csv")

    nav_history = pd.read_csv(BASE_DIR / "data" / "processed" / "nav_history_cleaned.csv")

    aum_by_fund_house = pd.read_csv(BASE_DIR / "data" / "processed" / "aum_by_fund_house_cleaned.csv")

    monthly_sip_inflows = pd.read_csv(BASE_DIR / "data" / "processed" / "monthly_sip_inflows_cleaned.csv")

    category_inflows = pd.read_csv(BASE_DIR / "data" / "processed" / "category_inflows_cleaned.csv")

    industry_folio_count = pd.read_csv(BASE_DIR / "data" / "processed" / "industry_folio_count_cleaned.csv")

    scheme_performance = pd.read_csv(BASE_DIR / "data" / "processed" / "scheme_performance_cleaned.csv")

    investor_transactions = pd.read_csv(BASE_DIR / "data" / "processed" / "investor_transactions_cleaned.csv")

    portfolio_holdings = pd.read_csv(BASE_DIR / "data" / "processed" / "portfolio_holdings_cleaned.csv")

    benchmark_indices = pd.read_csv(BASE_DIR / "data" / "processed" / "benchmark_indices_cleaned.csv")

    # Load into SQLite

    fund_master.to_sql("dim_fund", engine, if_exists="replace", index=False)

    nav_history.to_sql("fact_nav", engine, if_exists="replace", index=False)

    scheme_performance.to_sql("fact_performance", engine, if_exists="replace", index=False)

    investor_transactions.to_sql("fact_transactions", engine, if_exists="replace", index=False)

    portfolio_holdings.to_sql("fact_portfolio_holdings", engine, if_exists="replace", index=False)

    aum_by_fund_house.to_sql("fact_aum", engine, if_exists="replace", index=False)

    monthly_sip_inflows.to_sql("fact_sip_inflows", engine, if_exists="replace", index=False)

    benchmark_indices.to_sql("fact_benchmark", engine, if_exists="replace", index=False)

    category_inflows.to_sql("fact_category_inflows", engine, if_exists="replace", index=False)

    industry_folio_count.to_sql("fact_industry_folio_count", engine, if_exists="replace", index=False)

    print("All cleaned datasets loaded successfully!")

except Exception as e:
    print(f"\nError: {e}")

finally:
    input("\nPress Enter to exit...")